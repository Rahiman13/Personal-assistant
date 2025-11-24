import os
import math
import struct
import threading
import time
from typing import Callable, Optional

try:
    import speech_recognition as sr
except Exception:
    sr = None  # type: ignore

try:
    import pyttsx3
except Exception:
    pyttsx3 = None  # type: ignore

try:
    import pvporcupine
except Exception:
    pvporcupine = None  # type: ignore

try:
    import pyaudio
except Exception:
    pyaudio = None  # type: ignore


class PorcupineWakeDetector:
    """Background wake-word detector powered by Porcupine."""

    def __init__(
        self,
        callback: Callable[[], None],
        *,
        access_key: Optional[str],
        keyword_path: Optional[str],
        sensitivity: float = 0.65,
        noise_floor: float = 0.0,
        device_index: Optional[int] = None,
    ):
        self._callback = callback
        self._access_key = access_key
        self._keyword_path = keyword_path
        self._sensitivity = max(0.0, min(0.99, sensitivity))
        self._noise_floor = max(0.0, noise_floor)
        self._device_index = device_index
        self._porcupine = None
        self._pa = None
        self._stream = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._paused = threading.Event()
        self._last_error: Optional[str] = None

        if not pvporcupine or not pyaudio:
            self._last_error = "Porcupine wake word requires pvporcupine and PyAudio."
            return
        if not self._access_key:
            self._last_error = "Set PORCUPINE_ACCESS_KEY for wake-word detection."
            return
        if not self._keyword_path:
            self._last_error = "Set PORCUPINE_KEYWORD_PATH (.ppn) for wake-word detection."
            return
        try:
            self._porcupine = pvporcupine.create(
                access_key=self._access_key,
                keyword_paths=[self._keyword_path],
                sensitivities=[self._sensitivity],
            )
            self._pa = pyaudio.PyAudio()
        except Exception as exc:
            self._last_error = f"Failed to initialize Porcupine: {exc}"
            self._porcupine = None

    @property
    def is_available(self) -> bool:
        return self._porcupine is not None

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def start(self) -> bool:
        if not self.is_available or self._running:
            return self.is_available and self._running
        try:
            assert self._porcupine and self._pa
            self._stream = self._pa.open(
                rate=self._porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self._porcupine.frame_length,
                input_device_index=self._device_index,
            )
            self._running = True
            self._paused.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            return True
        except Exception as exc:
            self._last_error = f"Failed to start Porcupine stream: {exc}"
            self._running = False
            return False

    def stop(self) -> None:
        self._running = False
        if self._wake_detector:
            try:
                self._wake_detector.stop()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None
        if self._porcupine:
            try:
                self._porcupine.delete()
            except Exception:
                pass
            self._porcupine = None

    def pause(self, enabled: bool) -> None:
        if enabled:
            self._paused.set()
        else:
            self._paused.clear()

    def is_running(self) -> bool:
        return self._running

    def _run(self) -> None:
        assert self._porcupine and self._stream
        frame_length = self._porcupine.frame_length
        while self._running:
            if self._paused.is_set():
                time.sleep(0.1)
                continue
            try:
                pcm = self._stream.read(frame_length, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * frame_length, pcm)
                if self._noise_floor:
                    rms = math.sqrt(sum(sample * sample for sample in pcm) / len(pcm))
                    if rms < self._noise_floor:
                        continue
                result = self._porcupine.process(pcm)
                if result >= 0:
                    self._callback()
            except Exception as exc:
                self._last_error = f"Porcupine stream error: {exc}"
                time.sleep(0.2)

class VoiceAssistant:
    """Simple voice assistant engine: continuous listen + TTS.
    - Uses SpeechRecognition (microphone) for STT
    - Uses pyttsx3 for offline TTS
    """

    def __init__(self, on_transcript: Callable[[str], None]):
        self.on_transcript = on_transcript
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._noise_threshold = int(os.getenv("VOICE_NOISE_THRESHOLD", "300"))
        self._recognizer = sr.Recognizer() if sr else None
        if self._recognizer:
            self._recognizer.energy_threshold = self._noise_threshold
            self._recognizer.dynamic_energy_threshold = True
            # Enhanced settings for better accuracy (like Siri/Alexa)
            self._recognizer.dynamic_energy_adjustment_damping = 0.15
            self._recognizer.dynamic_energy_ratio = 1.5
            self._recognizer.pause_threshold = 0.8  # Longer pause for better word separation
            self._recognizer.phrase_threshold = 0.3  # Better phrase detection
            self._recognizer.non_speaking_duration = 0.5  # Better silence detection
        self._tts = None
        self._tts_lock = threading.Lock()
        self._is_speaking = False
        self._command_lock = threading.Lock()
        self._state = "idle"
        self.using_wake_detector = False
        # How long to wait for the user to START speaking after wake word
        # Optimized for faster response - reduced from 6.0 to 3.0
        self._command_timeout = float(os.getenv("VOICE_COMMAND_TIMEOUT", "3.0"))
        # How long to wait for speech before giving up (no audio detected)
        # Optimized for faster response - reduced from 3.0 to 1.5
        # After you start talking, SpeechRecognition will still stop as soon as you
        # pause for ~0.8s (see pause_threshold/non_speaking_duration below), so this
        # mainly controls "no speech" time, not the full command length.
        self._listen_timeout = float(os.getenv("VOICE_LISTEN_TIMEOUT", "1.5"))
        # Maximum length of a single spoken command (in seconds).
        # Optimized for faster response - reduced from 10.0 to 5.0
        # The recognizer will still finish early once you stop speaking for ~0.8s.
        self._phrase_time_limit = float(os.getenv("VOICE_PHRASE_TIME_LIMIT", "5.0"))
        # Allow continuous listening even while TTS is speaking (default OFF to avoid self-trigger)
        self._allow_listen_during_tts = os.getenv("VOICE_ALLOW_LISTEN_DURING_TTS", "0") != "0"
        self._max_stt_errors = int(os.getenv("VOICE_MAX_STT_ERRORS", "6"))
        self._max_command_retries = max(1, int(os.getenv("VOICE_COMMAND_RETRIES", "2")))
        self._calibration_interval = float(os.getenv("VOICE_CALIBRATION_INTERVAL", "60.0"))
        self._last_calibration = 0.0
        self._wake_detector: Optional[PorcupineWakeDetector] = None
        # Initialize cooldown to 0 so we can start listening immediately
        import time
        self._speak_cooldown_until: float = 0.0
        # Initialize error field BEFORE any component init uses it
        self.last_error: Optional[str] = None
        if pyttsx3:
            try:
                self._tts = pyttsx3.init()
                # Configure TTS settings for better quality
                if self._tts:
                    voices = self._tts.getProperty('voices')
                    if voices:
                        # Try to use a more natural voice if available
                        for voice in voices:
                            if 'english' in voice.name.lower() or 'en' in voice.id.lower():
                                self._tts.setProperty('voice', voice.id)
                                break
                    # Slightly faster speech so Bittu resumes listening sooner
                    self._tts.setProperty('rate', 190)
                    self._tts.setProperty('volume', 0.8)  # Volume level
            except Exception as e:
                self._tts = None
                if not self.last_error:  # Don't override microphone errors
                    self.last_error = f"TTS initialization failed: {str(e)}"
        self._mic = None
        if sr:
            try:
                # Try to initialize microphone with better error handling
                self._mic = sr.Microphone()
                # Test if microphone is actually accessible
                with self._mic as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.1)
            except Exception as e:
                self._mic = None
                self.last_error = f"Microphone initialization failed: {str(e)}. Check device permissions and availability."

        self._porcupine_enabled = os.getenv("ENABLE_PORCUPINE_WAKE", "1") != "0"
        if self._porcupine_enabled:
            self._wake_detector = PorcupineWakeDetector(
                callback=self._on_wake_word_detected,
                access_key=os.getenv("PORCUPINE_ACCESS_KEY"),
                keyword_path=os.getenv("PORCUPINE_KEYWORD_PATH"),
                sensitivity=float(os.getenv("PORCUPINE_SENSITIVITY", "0.65")),
                noise_floor=float(os.getenv("PORCUPINE_NOISE_FLOOR", "0.0")),
                device_index=self._get_env_int("PORCUPINE_AUDIO_DEVICE_INDEX"),
            )
            if self._wake_detector and self._wake_detector.is_available:
                self.using_wake_detector = True
            else:
                if self._wake_detector and self._wake_detector.last_error and not self.last_error:
                    self.last_error = self._wake_detector.last_error
                self._wake_detector = None
        self._legacy_mode = not self.using_wake_detector
        self._calibrate_energy(force=True)

    def speak(self, text: str) -> None:
        """Speak text using TTS. This method is non-blocking and runs TTS in a separate thread."""
        if not text or not text.strip():
            print("⚠️ TTS: Empty text, skipping...")
            return
        
        if not self._tts:
            print("❌ TTS ERROR: TTS engine not initialized!")
            print("   Install pyttsx3: pip install pyttsx3")
            # Try to reinitialize TTS
            try:
                if pyttsx3:
                    self._tts = pyttsx3.init()
                    if self._tts:
                        print("✅ TTS reinitialized successfully")
                    else:
                        return
                else:
                    return
            except Exception as e:
                print(f"❌ Failed to reinitialize TTS: {e}")
                return
        
        def _speak_in_thread():
            try:
                # Serialize TTS engine to avoid overlapping run loops
                with self._tts_lock:
                    self._is_speaking = True
                    if self._wake_detector and self.using_wake_detector and not self._allow_listen_during_tts:
                        self._wake_detector.pause(True)
                    text_to_speak = text.strip()
                    print(f"🔊 TTS Speaking: '{text_to_speak}'")
                    try:
                        # Clear any pending speech first
                        self._tts.stop()
                    except:
                        pass
                    self._tts.say(text_to_speak)
                    self._tts.runAndWait()
                    print(f"✅ TTS Finished speaking: '{text_to_speak}'")
            except Exception as e:
                # Log the error but don't crash the application
                print(f"❌ TTS Error: {str(e)}")
                import traceback
                traceback.print_exc()
                # Try to reinitialize TTS if it failed
                try:
                    if pyttsx3:
                        self._tts = pyttsx3.init()
                        print("🔄 TTS reinitialized after error")
                except:
                    pass
            finally:
                # Small cooldown to let audio device switch back to mic cleanly
                try:
                    import time as _t
                    if self._allow_listen_during_tts:
                        # No cooldown needed – resume immediately
                        self._speak_cooldown_until = 0.0
                    else:
                        # Ultra-short cooldown for faster response to next wake word
                        self._speak_cooldown_until = _t.time() + 0.05
                except Exception:
                    pass
                self._is_speaking = False
                if self._wake_detector and self.using_wake_detector and not self._allow_listen_during_tts:
                    self._wake_detector.pause(False)
        
        # Run TTS in a separate daemon thread so it doesn't block
        threading.Thread(target=_speak_in_thread, daemon=True).start()

    def stop_speaking(self) -> None:
        """Immediately stop any ongoing TTS playback."""
        if not self._tts:
            self._is_speaking = False
            return
        with self._tts_lock:
            try:
                self._tts.stop()
            except Exception:
                pass
            finally:
                self._is_speaking = False

    def is_speaking(self) -> bool:
        """Return True if TTS is currently speaking."""
        return self._is_speaking

    def start(self) -> bool:
        if self.using_wake_detector and self._wake_detector:
            if not self._mic or not self._recognizer:
                self.last_error = "Microphone not available for wake-word mode."
                return False
            if self._running and self._wake_detector.is_running():
                return True
            if self._wake_detector.start():
                self._state = "idle"
                self._running = True
                print("🎧 Porcupine wake-word detector active. Waiting for 'Hey Bittu'.")
                return True
            self.last_error = self._wake_detector.last_error or "Wake-word detector failed to start."
            # Fallback to legacy mode if Porcupine failed
            self.using_wake_detector = False
            self._legacy_mode = True
        return self._start_legacy_loop()

    def _start_legacy_loop(self) -> bool:
        if not sr or not self._recognizer:
            self.last_error = "SpeechRecognition not available."
            print("❌ VoiceAssistant: SpeechRecognition not available")
            return False
        if not self._mic:
            try:
                print("🎤 VoiceAssistant: Initializing microphone...")
                self._mic = sr.Microphone()
                with self._mic as source:
                    print("🎤 VoiceAssistant: Calibrating microphone...")
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.1)
                    print("✅ VoiceAssistant: Microphone calibrated")
            except Exception as e:
                self.last_error = f"Microphone init failed: {e}. Please check microphone permissions and ensure no other application is using the microphone."
                print(f"❌ VoiceAssistant: Microphone init failed: {e}")
                return False
        if self._running and self._thread and self._thread.is_alive():
            print("✅ VoiceAssistant: Already running")
            return True
        print("🎤 VoiceAssistant: Starting listening thread...")
        self._running = True
        self._thread = threading.Thread(target=self._legacy_loop, daemon=True)
        self._thread.start()
        print("✅ VoiceAssistant: Listening thread started")
        return True

    def _calibrate_energy(self, force: bool = False) -> None:
        if not self._recognizer or not self._mic:
            return
        now = time.time()
        if not force and (now - self._last_calibration) < self._calibration_interval:
            return
        try:
            with self._mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.4)
            self._last_calibration = now
            print("🔧 Recalibrated ambient noise levels.")
        except Exception as exc:
            print(f"⚠️ Noise calibration skipped: {exc}")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
    
    def is_running(self) -> bool:
        """Check if the voice assistant is currently running"""
        if self.using_wake_detector and self._wake_detector:
            return self._running and self._wake_detector.is_running()
        return self._running and self._thread and self._thread.is_alive()
    
    def restart(self) -> bool:
        """Restart the voice assistant if it's not running"""
        if not self.is_running():
            self.stop()
            time.sleep(0.5)  # Brief pause before restart
            return self.start()
        return True

    def is_ready_for_listen(self) -> bool:
        """Return True if TTS is not speaking and cooldown passed."""
        try:
            import time as _t
            return (not self._is_speaking) and (_t.time() >= self._speak_cooldown_until)
        except Exception:
            return not self._is_speaking

    def _on_wake_word_detected(self) -> None:
        if not self._running or not self.on_transcript:
            return
        if self._is_speaking and not self._allow_listen_during_tts:
            return
        if not self._command_lock.acquire(blocking=False):
            return
        threading.Thread(target=self._capture_active_command, daemon=True).start()

    def _capture_active_command(self) -> None:
        try:
            self._state = "command"
            if self._wake_detector and not self._allow_listen_during_tts:
                self._wake_detector.pause(True)
            print("👂 Wake word detected. Listening for command…")
            text = self._listen_for_command()
            if text:
                print(f"✅ Voice command captured: '{text}'")
                try:
                    self.on_transcript(text)
                except Exception as callback_error:
                    print(f"❌ Error in voice command callback: {callback_error}")
            else:
                print("⚠️ No command detected within timeout window.")
        finally:
            self._state = "idle"
            if self._wake_detector and not self._allow_listen_during_tts:
                self._wake_detector.pause(False)
            self._command_lock.release()

    def _listen_for_command(self) -> Optional[str]:
        if not self._recognizer or not self._mic:
            return None
        attempts = 0
        max_attempts = getattr(self, "_max_command_retries", 2)
        while attempts < max_attempts:
            attempts += 1
            with self._mic as source:
                try:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.2)
                except Exception:
                    pass
                try:
                    audio = self._recognizer.listen(
                        source,
                        timeout=self._listen_timeout,
                        phrase_time_limit=self._phrase_time_limit,
                    )
                except Exception as listen_err:
                    print(f"⚠️ Command capture timeout (attempt {attempts}/{max_attempts}): {listen_err}")
                    if attempts >= max_attempts:
                        return None
                    continue
            try:
                text = self._recognizer.recognize_google(audio, language='en-US')
                if text:
                    if attempts > 1:
                        print(f"✅ Speech recognized on retry {attempts}: '{text}'")
                    return text
            except sr.UnknownValueError:
                if attempts < max_attempts:
                    print(f"🔁 Speech not understood (attempt {attempts}/{max_attempts}). Retrying...")
                    continue
                return None
            except Exception as rec_err:
                print(f"⚠️ Speech recognition error (attempt {attempts}/{max_attempts}): {rec_err}")
                if attempts >= max_attempts:
                    return None
        return None

    def _legacy_loop(self) -> None:
        assert self._recognizer is not None
        assert self._mic is not None
        
        # Enhanced configuration for Siri/Alexa-level accuracy
        self._recognizer.energy_threshold = self._noise_threshold
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.dynamic_energy_adjustment_damping = 0.15
        self._recognizer.dynamic_energy_ratio = 1.5
        self._recognizer.pause_threshold = 0.6  # Optimized for faster response (was 0.8)
        self._recognizer.operation_timeout = None
        self._recognizer.phrase_threshold = 0.2  # Optimized for faster response (was 0.3)
        self._recognizer.non_speaking_duration = 0.4  # Optimized for faster response (was 0.5)
        
        print("=" * 60)
        print("Voice assistant is now listening continuously...")
        print("🎤 Ready to receive voice commands. Say 'Bittu' followed by your command.")
        print(f"   Callback function: {self.on_transcript}")
        print(f"   Callback is None: {self.on_transcript is None}")
        print("=" * 60)
        
        consecutive_errors = 0
        max_consecutive_errors = self._max_stt_errors
        first_listen = True  # Flag to start listening immediately on first iteration
        
        while self._running:
            try:
                # If currently speaking, wait briefly to avoid picking up TTS
                import time as _t
                current_time = _t.time()
                
                # On first iteration, start listening immediately (don't wait for TTS or cooldown)
                if first_listen:
                    first_listen = False
                    print("🎤 Starting first listen cycle - ready to hear commands!")
                    # Skip TTS and cooldown checks on first iteration - start listening immediately
                else:
                    if not self._allow_listen_during_tts:
                        # After first iteration, check if TTS is speaking
                        if self._is_speaking:
                            # TTS is active - wait a bit and check again
                            _t.sleep(0.2)
                            continue
                        
                        # Short cooldown after speaking to let audio device switch back to mic
                        # Only check cooldown if it's actually set (greater than 0)
                        if self._speak_cooldown_until > 0:
                            if current_time < self._speak_cooldown_until:
                                remaining_cooldown = self._speak_cooldown_until - current_time
                                if remaining_cooldown > 0.1:
                                    _t.sleep(0.1)
                                else:
                                    _t.sleep(remaining_cooldown)
                                continue
                            else:
                                # Cooldown expired - reset it
                                self._speak_cooldown_until = 0.0
                    else:
                        # Full-duplex mode: clear any leftover cooldown so we keep listening
                        self._speak_cooldown_until = 0.0
                
                # Ready to listen - TTS is done and cooldown passed
                if hasattr(self, '_last_ready_log'):
                    if current_time - self._last_ready_log > 5:
                        print("✅ Ready to listen (TTS finished, cooldown passed)")
                        self._last_ready_log = current_time
                else:
                    self._last_ready_log = current_time
                
                # Reset error counter on successful iteration
                consecutive_errors = 0
                
                # Debug: periodically log that we're still listening (every 30 seconds of inactivity)
                if not hasattr(self, '_last_listen_log'):
                    self._last_listen_log = _t.time()
                elif _t.time() - self._last_listen_log > 30:
                    print("🔄 Still listening for 'bittu'...")
                    self._last_listen_log = _t.time()

                if current_time - self._last_calibration > self._calibration_interval:
                    self._calibrate_energy()
                
                # Debug: log when we're about to listen (first few times, then periodically)
                if not hasattr(self, '_listen_count'):
                    self._listen_count = 0
                self._listen_count += 1
                if self._listen_count <= 3 or self._listen_count % 20 == 0:
                    print(f"👂 Listening for speech... (iteration {self._listen_count})")
                
                with self._mic as source:
                    try:
                        audio = self._recognizer.listen(
                            source,
                            timeout=self._listen_timeout,
                            phrase_time_limit=self._phrase_time_limit,
                        )
                    except sr.WaitTimeoutError:  # type: ignore[attr-defined]
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            self._calibrate_energy(force=True)
                            consecutive_errors = 0
                        continue
                    except Exception as listen_err:
                        print(f"⚠️ Error in listen(): {listen_err}")
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            self._calibrate_energy(force=True)
                            consecutive_errors = 0
                        continue
                
                # Recognize speech using multiple methods for better accuracy (like Siri/Alexa)
                text = None
                confidence = 0.0
                
                # Try Google Speech Recognition first (most accurate)
                try:
                    result = self._recognizer.recognize_google(
                        audio,
                        language='en-US',
                        show_all=True  # Get all alternatives for confidence
                    )
                    if isinstance(result, dict) and 'alternative' in result:
                        # Use the highest confidence result
                        best_match = result['alternative'][0]
                        text = best_match.get('transcript', '')
                        confidence = best_match.get('confidence', 0.8)
                    elif isinstance(result, str):
                        text = result
                        confidence = 0.8  # Default confidence for string results
                    else:
                        text = str(result) if result else None
                        confidence = 0.7
                    consecutive_errors = 0
                except sr.UnknownValueError:
                    # Try alternative recognition engines for better accuracy
                    try:
                        # Fallback to Sphinx (offline, less accurate but works offline)
                        text = self._recognizer.recognize_sphinx(audio)
                        confidence = 0.6
                        consecutive_errors = 0
                        print("⚠️ Using Sphinx (offline) recognition - lower accuracy")
                    except:
                        consecutive_errors += 1
                        if consecutive_errors >= max_consecutive_errors:
                            self._calibrate_energy(force=True)
                            consecutive_errors = 0
                        continue
                except sr.RequestError as rec_err:  # type: ignore[attr-defined]
                    print(f"⚠️ Speech service error: {rec_err}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        self._calibrate_energy(force=True)
                        consecutive_errors = 0
                    time.sleep(0.3)  # Reduced from 0.8 for faster retry
                    continue
                except Exception as rec_err:
                    print(f"⚠️ Error in recognize_google(): {rec_err}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        self._calibrate_energy(force=True)
                        consecutive_errors = 0
                    continue
                
                if text and text.strip():
                    text_clean = text.strip()
                    # Log confidence for accuracy tracking
                    conf_str = f" (confidence: {confidence:.2f})" if confidence > 0 else ""
                    print(f"✅ Recognized: '{text_clean}'{conf_str}")
                    
                    # Only process if confidence is reasonable (like Siri/Alexa)
                    if confidence < 0.3:
                        print(f"⚠️ Low confidence ({confidence:.2f}) - ignoring uncertain recognition")
                        continue
                    
                    if self.on_transcript:
                        try:
                            # Pass confidence to callback for better decision making
                            # Call the callback with error handling to ensure loop continues
                            print(f"📞 Calling callback with: '{text_clean}'")
                            self.on_transcript(text_clean)
                            print("✅ Callback completed successfully - loop will continue")
                            # Minimal delay to ensure we don't immediately pick up TTS feedback
                            import time as _t
                            _t.sleep(0.05)  # Reduced from 0.1 for faster response
                        except Exception as callback_error:
                            # Log but don't break the loop
                            print(f"❌ Error in callback: {callback_error}")
                            import traceback
                            traceback.print_exc()
                            print("🔄 Loop will continue despite callback error")
                            # Still continue listening even after callback error
                            import time as _t
                            _t.sleep(0.05)  # Reduced from 0.1
                    else:
                        print("⚠️ WARNING: No callback registered! Text was recognized but won't be processed.")
                        print(f"   Recognized text: '{text_clean}'")
                else:
                    print("⏭️ No speech detected in audio")
                    
            except Exception as e:
                # Other errors - log and continue
                consecutive_errors += 1
                print(f"Voice recognition error ({consecutive_errors}/{max_consecutive_errors}): {e}")
                import traceback
                traceback.print_exc()
                
                # If too many consecutive errors, wait longer before retrying
                if consecutive_errors >= max_consecutive_errors:
                    print("⚠️ Too many consecutive errors. Waiting longer before retry...")
                    time.sleep(2)
                    consecutive_errors = 0  # Reset after wait
                else:
                    time.sleep(0.5)
                continue

    def diagnostics(self) -> str:
        parts: list[str] = []
        parts.append(f"SpeechRecognition: {'OK' if sr else 'MISSING'}")
        parts.append(f"TTS (pyttsx3): {'OK' if self._tts else 'MISSING'}")
        parts.append(f"Wake word: {'Porcupine' if self.using_wake_detector and self._wake_detector else 'legacy'}")
        if self._wake_detector and self._wake_detector.last_error:
            parts.append(f"Wake error: {self._wake_detector.last_error}")
        parts.append(f"Recognizer: {'OK' if self._recognizer else 'MISSING'}")
        parts.append(f"Mic: {'OK' if self._mic else 'NOT INITIALIZED'}")
        if self.last_error:
            parts.append(f"Last error: {self.last_error}")
        # Try to list devices via PyAudio if available
        try:
            import pyaudio  # type: ignore
            pa = pyaudio.PyAudio()
            count = pa.get_device_count()
            names = []
            for i in range(count):
                info = pa.get_device_info_by_index(i)
                if int(info.get('maxInputChannels', 0)) > 0:
                    names.append(info.get('name', f'dev{i}'))
            pa.terminate()
            parts.append(f"Input devices: {', '.join(names) if names else 'none detected'}")
        except Exception:
            parts.append("Input devices: unavailable (PyAudio error)")
        return "\n".join(parts)

    @staticmethod
    def _get_env_int(var: str) -> Optional[int]:
        value = os.getenv(var)
        if value is None or str(value).strip() == "":
            return None
        try:
            return int(value)
        except ValueError:
            return None


