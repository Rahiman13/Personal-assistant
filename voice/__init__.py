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


class VoiceAssistant:
    """Simple voice assistant engine: continuous listen + TTS.
    - Uses SpeechRecognition (microphone) for STT
    - Uses pyttsx3 for offline TTS
    """

    def __init__(self, on_transcript: Callable[[str], None]):
        self.on_transcript = on_transcript
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._recognizer = sr.Recognizer() if sr else None
        self._tts = None
        self._tts_lock = threading.Lock()
        self._is_speaking = False
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
                    self._tts.setProperty('rate', 150)  # Speech rate
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

    def speak(self, text: str) -> None:
        """Speak text using TTS. This method is non-blocking and runs TTS in a separate thread."""
        if not self._tts or not text or not text.strip():
            return
        
        def _speak_in_thread():
            try:
                # Serialize TTS engine to avoid overlapping run loops
                with self._tts_lock:
                    self._is_speaking = True
                    print(f"🔊 Speaking: '{text.strip()[:50]}...'")
                    self._tts.say(text.strip())
                    self._tts.runAndWait()
            except Exception as e:
                # Log the error but don't crash the application
                print(f"TTS Error: {str(e)}")
            finally:
                # Small cooldown to let audio device switch back to mic cleanly
                try:
                    import time as _t
                    # Very short cooldown for faster response to next wake word (like Alexa)
                    self._speak_cooldown_until = _t.time() + 0.2  # Reduced for faster turn-taking
                    print(f"✅ TTS finished. Cooldown until: {self._speak_cooldown_until} (0.2s)")
                except Exception:
                    pass
                self._is_speaking = False
                print("🎤 TTS flag cleared - ready to listen again after cooldown")
        
        # Run TTS in a separate daemon thread so it doesn't block
        threading.Thread(target=_speak_in_thread, daemon=True).start()

    def start(self) -> bool:
        if not sr or not self._recognizer:
            self.last_error = "SpeechRecognition not available."
            return False
        if not self._mic:
            # Try to create mic again in case device appeared later
            try:
                self._mic = sr.Microphone()
                # Test microphone access
                with self._mic as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.1)
            except Exception as e:
                self.last_error = f"Microphone init failed: {e}. Please check microphone permissions and ensure no other application is using the microphone."
                return False
        if self._running:
            return True
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
    
    def is_running(self) -> bool:
        """Check if the voice assistant is currently running"""
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

    def _loop(self) -> None:
        assert self._recognizer is not None
        assert self._mic is not None
        
        # Configure recognizer for better accuracy and continuous listening
        self._recognizer.energy_threshold = 300  # Minimum audio energy to consider for recording
        self._recognizer.dynamic_energy_threshold = True
        self._recognizer.dynamic_energy_adjustment_damping = 0.15
        self._recognizer.dynamic_energy_ratio = 1.5
        self._recognizer.pause_threshold = 0.8  # Seconds of non-speaking audio before a phrase is considered complete
        self._recognizer.operation_timeout = None  # No timeout for operations
        self._recognizer.phrase_threshold = 0.3  # Minimum seconds of speaking audio before we consider the speaking audio a phrase
        self._recognizer.non_speaking_duration = 0.5  # Seconds of non-speaking audio to keep on both sides of the recording
        
        # Adjust for ambient noise once at the start
        with self._mic as source:
            try:
                self._recognizer.adjust_for_ambient_noise(source, duration=1.0)
                print("Microphone calibrated for ambient noise")
            except Exception:
                pass
        
        print("Voice assistant is now listening continuously...")
        print("🎤 Ready to receive voice commands. Say 'Bittu' followed by your command.")
        
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while self._running:
            try:
                # If currently speaking, wait briefly to avoid picking up TTS
                import time as _t
                current_time = _t.time()
                
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
                
                # Debug: log when we're about to listen (first few times, then periodically)
                if not hasattr(self, '_listen_count'):
                    self._listen_count = 0
                self._listen_count += 1
                if self._listen_count <= 3 or self._listen_count % 20 == 0:
                    print(f"👂 Listening for speech... (iteration {self._listen_count})")
                
                with self._mic as source:
                    # Listen for audio with better settings for continuous listening
                    # Use shorter timeout for more responsive wake word detection
                    try:
                        audio = self._recognizer.listen(source, timeout=0.5, phrase_time_limit=10)
                    except Exception as listen_err:
                        print(f"⚠️ Error in listen(): {listen_err}")
                        continue
                
                # Recognize speech using Google's service with better settings
                try:
                    text = self._recognizer.recognize_google(
                        audio, 
                        language='en-US',
                        show_all=False  # Only return the best result
                    )
                except Exception as rec_err:
                    print(f"⚠️ Error in recognize_google(): {rec_err}")
                    continue
                
                if text and text.strip():
                    print(f"✅ Recognized: '{text.strip()}'")
                    if self.on_transcript:
                        try:
                            # Call the callback with error handling to ensure loop continues
                            print(f"📞 Calling callback with: '{text.strip()}'")
                            self.on_transcript(text.strip())
                            print("✅ Callback completed successfully - loop will continue")
                            # Small delay to ensure we don't immediately pick up TTS feedback
                            import time as _t
                            _t.sleep(0.1)
                        except Exception as callback_error:
                            # Log but don't break the loop
                            print(f"❌ Error in callback: {callback_error}")
                            import traceback
                            traceback.print_exc()
                            print("🔄 Loop will continue despite callback error")
                            # Still continue listening even after callback error
                            import time as _t
                            _t.sleep(0.1)
                    else:
                        print("⚠️ WARNING: No callback registered! Text was recognized but won't be processed.")
                        print(f"   Recognized text: '{text.strip()}'")
                else:
                    print("⏭️ No speech detected in audio")
                    
            except sr.WaitTimeoutError:  # type: ignore[attr-defined]
                # No speech detected within timeout - this is normal, continue listening
                continue
            except sr.UnknownValueError:  # type: ignore[attr-defined]
                # Speech was detected but not understood - this is normal
                print("Speech detected but not understood, continuing to listen...")
                continue
            except sr.RequestError as e:  # type: ignore[attr-defined]
                # API request failed - log and continue
                print(f"Speech recognition API error: {e}")
                time.sleep(2)  # Wait a bit longer before retrying
                continue
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


