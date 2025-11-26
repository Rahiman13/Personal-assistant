# main.py
import os
import time
import threading

from interface.cli_interface import (
    get_input, show_output, show_welcome, show_goodbye, 
    show_help_menu, show_error, show_success
)
# Import with fallback to ensure it always works
try:
    from core.brain import process_command_with_learning as process_command
except Exception:
    # Fallback if learning system fails
    from core.brain import process_command
    print("⚠️ Using basic command processor (learning disabled)")
from skills.system_controls import is_alarm_active, stop_alarm_now
from voice import VoiceAssistant
from interface import web_server
from knowledge.llm_connector import get_last_llm_label

def main():
    """Main function to run the Personal AI Assistant"""
    try:
        # Show welcome message
        show_welcome()
        
        # Voice assistant state - auto-start enabled
        voice_enabled = False
        # Pending multi-turn intent (e.g., waiting for a YouTube song after asking)
        pending_youtube_song: bool = False
        # Pending command after wake word (user said "Bittu" and paused)
        pending_wake_command: bool = False
        pending_command_buffer: str = ""

        voice_wake_ack_enabled = os.getenv("VOICE_WAKE_ACK", "1") != "0"
        voice_wake_prompt = os.getenv("VOICE_WAKE_PROMPT", "Yes, I'm listening.")
        voice_wake_repeat_prompt = os.getenv(
            "VOICE_WAKE_REPEAT_PROMPT",
            "I didn't catch that. Please tell me your request."
        )
        require_wake_word = os.getenv("VOICE_REQUIRE_WAKE_WORD", "1") != "0"
        auto_listen_after_command = os.getenv("VOICE_AUTO_LISTEN_AFTER_COMMAND", "1") != "0"
        voice_ready_prompt = os.getenv("VOICE_READY_PROMPT", "Waiting for your next command.")
        pending_wake_timeout = float(os.getenv("VOICE_PENDING_TIMEOUT", "4.0"))
        pending_wake_started_at: float | None = None
        pending_wake_prompted = False
        voice_tts_enabled = os.getenv("VOICE_TTS_ENABLED", "1") != "0"
        voice_spoken_greeting_enabled = os.getenv("VOICE_SPOKEN_GREETING", "0") != "0"
        voice_greeting_text = os.getenv("VOICE_GREETING_TEXT", "Bittu is listening.")
        current_voice_task = {"thread": None, "cancel": None}
        current_voice_task_lock = threading.Lock()
        command_queue: list[str] = []
        command_queue_lock = threading.Lock()

        def _force_speak(text: str) -> None:
            if not voice_engine or not hasattr(voice_engine, "speak"):
                return
            if not text or not text.strip():
                return
            try:
                voice_engine.speak(text)
            except Exception:
                pass

        def speak_if_allowed(text: str) -> None:
            if not voice_tts_enabled:
                return
            _force_speak(text)

        def _is_voice_task_running() -> bool:
            with current_voice_task_lock:
                thread = current_voice_task.get("thread")
            return bool(thread and thread.is_alive())

        def _cancel_active_voice_task(reason: str = "") -> None:
            nonlocal pending_youtube_song, pending_command_buffer, pending_wake_command
            cancel = None
            with current_voice_task_lock:
                cancel = current_voice_task.get("cancel")
            if cancel and not cancel.is_set():
                cancel.set()
            pending_youtube_song = False
            pending_command_buffer = ""
            pending_wake_command = False
            if voice_engine and hasattr(voice_engine, "stop_speaking"):
                voice_engine.stop_speaking()
            if reason:
                print(reason)

        def _maybe_run_next_queued_command() -> None:
            next_command = None
            with command_queue_lock:
                if command_queue:
                    next_command = command_queue.pop(0)
            if next_command:
                print(f"▶️ Running queued command: '{next_command}'")
                _start_voice_task(next_command)

        def _start_voice_task(command: str) -> None:
            nonlocal pending_youtube_song, pending_command_buffer, voice_enabled
            nonlocal pending_wake_command, pending_wake_started_at, pending_wake_prompted
            nonlocal auto_listen_after_command, voice_ready_prompt
            print(f"🚀 _start_voice_task called with: '{command}'")
            cancel_event = threading.Event()

            def worker() -> None:
                nonlocal pending_youtube_song, pending_command_buffer, voice_enabled
                nonlocal pending_wake_command, pending_wake_started_at, pending_wake_prompted
                nonlocal voice_ready_prompt, auto_listen_after_command
                start_time = time.time()
                try:
                    try:
                        web_server.emit_processing()
                    except Exception:
                        pass
                    print("⏳ Working on your request...")
                    def delayed_hint():
                        if not cancel_event.is_set():
                            speak_if_allowed("Working on it.")
                    hint_timer = threading.Timer(1.0, delayed_hint)
                    hint_timer.start()
                    try:
                        print(f"🔄 Calling process_command('{command}')...")
                        resp = process_command(command)
                        elapsed = time.time() - start_time
                        print(f"⏱️ process_command completed in {elapsed:.2f}s")
                    except Exception as e:
                        elapsed = time.time() - start_time
                        print(f"❌ process_command failed after {elapsed:.2f}s: {e}")
                        import traceback
                        traceback.print_exc()
                        resp = f"❌ Error processing command: {str(e)}"
                    finally:
                        hint_timer.cancel()
                    if cancel_event.is_set():
                        print(f"⛔ Command '{command}' cancelled before completion.")
                        announce_ready(command, "")
                        return
                    if not resp:
                        resp = "I'm not sure how to respond to that. Could you please rephrase your question?"
                    print_response(resp)
                    if isinstance(resp, str) and resp.strip().lower().startswith("which song should i play on youtube"):
                        pending_youtube_song = True
                        speak_if_allowed("Which song should I play on YouTube?")
                    voice_response = create_voice_response(resp, command)
                    if voice_response and voice_response.strip():
                        try:
                            web_server.emit_speaking(voice_response)
                        except Exception:
                            pass
                        speak_if_allowed(voice_response)
                    pending_command_buffer = ""
                    announce_ready(command, resp)
                    if auto_listen_after_command:
                        pending_wake_command = True
                        pending_wake_started_at = time.time()
                        pending_wake_prompted = False
                    total_elapsed = time.time() - start_time
                    print(f"✅ Command completed in {total_elapsed:.2f}s. 🎤 Listening for 'bittu'...")
                    if voice_enabled and voice_engine and not voice_engine.is_running():
                        print("⚠️ Voice assistant stopped! Restarting...")
                        if voice_engine.restart():
                            print("✅ Voice assistant restarted")
                        else:
                            print("❌ Failed to restart voice assistant")
                            voice_enabled = False
                except Exception as worker_err:
                    print(f"❌ CRITICAL ERROR in worker thread: {worker_err}")
                    import traceback
                    traceback.print_exc()
                finally:
                    cancel_event.set()
                    with current_voice_task_lock:
                        if current_voice_task.get("cancel") is cancel_event:
                            current_voice_task["thread"] = None
                            current_voice_task["cancel"] = None
                    _maybe_run_next_queued_command()

            thread = threading.Thread(target=worker, daemon=True)
            with current_voice_task_lock:
                current_voice_task["thread"] = thread
                current_voice_task["cancel"] = cancel_event
            thread.start()
            print(f"✅ Worker thread started for command: '{command}'")
        
        # Start lightweight SSE server for web brain
        try:
            web_server.start_server()
        except Exception:
            pass

        # Auto-open Jarvis-style UI
        try:
            import webbrowser as _wb
            from pathlib import Path as _Path
            ui_path = _Path(__file__).parent / "interface" / "ui.html"
            if ui_path.exists():
                _wb.open_new_tab(ui_path.as_uri())
        except Exception:
            pass

        def tts_clean(s: str) -> str:
            # Keep a short, readable spoken summary (strip emojis and excessive whitespace)
            try:
                import re
                s = re.sub(r"[\u2600-\u27BF\U0001F300-\U0001FAFF]", "", s)
            except Exception:
                pass
            s = s.replace("\n", " ").strip()
            return s[:200]

        def normalize_text(s: str) -> str:
            try:
                import re
                s = s.lower()
                s = re.sub(r"[^a-z0-9\s]", " ", s)
                s = re.sub(r"\s+", " ", s).strip()
            except Exception:
                s = s.lower().strip()
            return s

        def has_wake_word(s: str) -> bool:
            """Enhanced wake word detection with confidence scoring (Siri/Alexa-like)"""
            text = normalize_text(s)
            
            # Exact matches (highest confidence)
            exact_wake_words = {
                "bittu", "bitu", "bitto", "beetu", "bithu", "bito"
            }
            if any(w == text or text.startswith(w + " ") for w in exact_wake_words):
                return True
            
            # Common variants and greetings (high confidence)
            wake_variants = {
                "bittu ji", "bittuji", "hey bittu", "hi bittu", "ok bittu", "okay bittu",
                "bittu please", "please bittu", "bittu can you", "bittu could you"
            }
            if any(w in text for w in wake_variants):
                return True
            
            # Regex-based fuzzy match (captures common STT confusions) - medium confidence
            try:
                import re
                patterns = [
                    r"\bb[iy]tt?u\b",      # bittu/bitu variations (word boundary)
                    r"\bb[iy]t+u+\b",      # elongated vowels/consonants
                    r"\bbe+tu+\b",         # beetu/betu
                    r"\bbit+o\b",          # bitto
                    r"^bittu\b",           # Start with bittu
                    r"\bbittu\s",          # bittu followed by space
                    r"\bb[iy]t+[ou]+\b",  # Additional variations
                ]
                for p in patterns:
                    if re.search(p, text):
                        return True
            except Exception:
                pass
            
            # Token match - check if bittu is a separate word (lower confidence but still valid)
            tokens = text.split()
            if "bittu" in tokens:
                return True

            # Misheard variants that frequently appear in STT results (e.g., "vitamin")
            misheard_variants = {
                "vitamin", "bitten", "bitton", "button", "beetle", "beetle",
                "bitten,", "bit two", "bit too", "b2", "b two", "be too",
                "b to", "beta", "beetoo"
            }
            for token in tokens:
                if token in misheard_variants:
                    return True
            if any(text.startswith(variant + " ") for variant in misheard_variants):
                return True
            
            # Partial match - check if any token starts with "bitt" (lowest confidence)
            if any(t.startswith("bitt") and len(t) <= 6 for t in tokens):
                return True
            
            return False

        def strip_wake_word(s: str) -> str:
            """Remove wake word and clean up duplicated/malformed text."""
            text = normalize_text(s)
            try:
                import re
                # Normalize greeting forms to just 'bittu'
                for w in ["hey", "hi", "ok", "please"]:
                    text = text.replace(f"{w} bittu", "bittu").strip()
                # Remove fuzzy variants
                patterns = [
                    r"\bb[iy]tt?u\b",
                    r"\bb[iy]t+u+\b",
                    r"\bbe+tu+\b",
                    r"\bbit+o\b",
                    r"\bbittu\b",
                ]
                for p in patterns:
                    text = re.sub(p, " ", text).strip()
                # Collapse extra spaces
                text = re.sub(r"\s+", " ", text).strip()
            except Exception:
                # Fallback simple replace
                for w in ["hey", "hi", "ok", "please"]:
                    text = text.replace(f"{w} bittu", "bittu").strip()
                text = text.replace("bittu", "").strip()

            # Remove known misheard variants as wake words
            misheard_variants = [
                "vitamin", "bitten", "bitton", "button", "beetle", "bit two",
                "bit too", "b two", "b2", "beta", "beetoo", "be too", "b to"
            ]
            for variant in misheard_variants:
                text = text.replace(variant, " ").strip()
            try:
                import re as _re
                text = _re.sub(r"\s+", " ", text).strip()
            except Exception:
                text = " ".join(text.split())
            
            # Remove duplicate phrases (e.g., "open Notepad Bittu open Notepad" -> "open Notepad")
            # After removing wake word, we might have "open notepad open notepad"
            words = text.split()
            if len(words) >= 2:
                # Simple and effective: remove consecutive duplicate 2-word phrases
                cleaned_words = []
                i = 0
                while i < len(words):
                    # Check if we have a duplicate 2-word phrase starting at i
                    if i + 3 < len(words):  # Need at least 4 words: "a b a b"
                        if words[i] == words[i+2] and words[i+1] == words[i+3]:
                            # Found duplicate 2-word phrase, keep only first occurrence
                            cleaned_words.append(words[i])
                            cleaned_words.append(words[i+1])
                            i += 4  # Skip all 4 words
                            continue
                    # Check for duplicate single word (less common but possible)
                    if i + 1 < len(words) and words[i] == words[i+1]:
                        cleaned_words.append(words[i])
                        i += 2  # Skip duplicate
                        continue
                    # No duplicate, keep the word
                    cleaned_words.append(words[i])
                    i += 1
                if cleaned_words:
                    text = " ".join(cleaned_words)
            
            return text.strip()
        
        def normalize_command_typos(command: str) -> str:
            """Normalize common typos and variations in commands without over-replacing."""
            if not command:
                return command
            
            cmd_lower = command.lower().strip()
            
            # Common typo corrections (only apply when the typo is a standalone word)
            typo_map = {
                "utube": "youtube",
                "u tube": "youtube",
                "you tube": "youtube",
                "yt": "youtube",
                "fb": "facebook",
                "gmail": "gmail",
                "google": "google",
                "github": "github",
                "calc": "calculator",
                "notepad": "notepad",
                "code": "vs code",
                "vscode": "vs code",
                "vs code": "vs code",
            }
            
            try:
                import re as _re
            except Exception:
                _re = None
            
            for typo, correct in typo_map.items():
                if typo not in cmd_lower:
                    continue
                if _re:
                    pattern = r"\b" + _re.escape(typo) + r"\b"
                    if _re.search(pattern, cmd_lower):
                        command = _re.sub(pattern, correct, command, count=1, flags=_re.IGNORECASE)
                        break
                else:
                    tokens = command.split()
                    new_tokens = []
                    replaced = False
                    for token in tokens:
                        if not replaced and token.lower() == typo:
                            new_tokens.append(correct)
                            replaced = True
                        else:
                            new_tokens.append(token)
                    command = " ".join(new_tokens)
                    if replaced:
                        break
            
            return command
        
        def create_voice_response(full_response: str, command: str) -> str:
            """Create very short, concise voice responses (max 80 characters)."""
            if not full_response or not full_response.strip():
                return "Done."
            command_lower = (command or "").lower().strip()

            # Handle specific commands with deterministic responses
            if "open youtube" in command_lower or "youtube" in command_lower:
                return "Opening YouTube."
            if "open google" in command_lower or "google" in command_lower:
                return "Opening Google."
            if "open gmail" in command_lower or "gmail" in command_lower:
                return "Opening Gmail."
            if "open github" in command_lower or "github" in command_lower:
                return "Opening GitHub."
            if "open calculator" in command_lower or "calculator" in command_lower:
                return "Opening Calculator."
            if "open notepad" in command_lower or "notepad" in command_lower:
                return "Opening Notepad."
            if "open vs code" in command_lower or "code" in command_lower:
                return "Opening VS Code."
            if "weather" in command_lower:
                import re
                temp_match = re.search(r"(\d+[°°]?[CF]?)", full_response)
                if temp_match:
                    return f"Temperature is {temp_match.group(1)}."
                return "Weather information retrieved."
            if "create" in command_lower and ("file" in command_lower or "script" in command_lower):
                if "python" in command_lower:
                    return "Python file created."
                if "html" in command_lower:
                    return "HTML file created."
                if "css" in command_lower:
                    return "CSS file created."
                if "javascript" in command_lower or "js" in command_lower:
                    return "JavaScript file created."
                return "File created."
            if "remind" in command_lower or "reminder" in command_lower:
                return "Reminder set."
            if "help" in command_lower:
                return "Check the terminal for available commands."
            if "hello" in command_lower or "hi" in command_lower:
                return "Hello! How can I help?"
            if "thank" in command_lower:
                return "You're welcome!"
            if "bye" in command_lower or "goodbye" in command_lower:
                return "Goodbye!"
            if "time" in command_lower:
                import re
                time_match = re.search(r"(\d{1,2}:\d{2}(?:\s*[AP]M)?)", full_response, re.IGNORECASE)
                if time_match:
                    return f"The time is {time_match.group(1)}."
                return "Time retrieved."
            if "date" in command_lower:
                return "Date retrieved."
            if "search" in command_lower:
                return "Searching."
            if "play" in command_lower:
                return "Playing."

            cleaned = tts_clean(full_response)
            if "✅" in full_response or "success" in cleaned.lower():
                return "Done."
            if "❌" in full_response or "error" in cleaned.lower() or "failed" in cleaned.lower():
                return "Sorry, couldn't do that."

            import re
            sentences = [s.strip() for s in re.split(r"[.!?]\s+", cleaned) if s.strip()]
            if sentences:
                first_sentence = sentences[0]
                if len(first_sentence) <= 50:
                    return first_sentence + "."
                truncated = first_sentence[:47]
                last_space = truncated.rfind(" ")
                if last_space > 25:
                    truncated = truncated[:last_space]
                return truncated + "..."

            return "Done."

        def command_needs_followup(command: str) -> bool:
            """Heuristic to detect when user hasn't finished the command."""
            if not command:
                return True
            lower = command.lower().strip()
            incomplete_endings = (
                " for", " to", " about", " regarding", " on", " with",
                " into", " inside", " over", " under", " by", " of"
            )
            if any(lower.endswith(end) for end in incomplete_endings):
                return True
            short_commands = {
                "write", "create", "make", "open", "generate", "code",
                "build", "explain", "search", "find"
            }
            if lower in short_commands:
                return True
            short_two_word_patterns = (
                "write a", "write the", "create a", "create the",
                "make a", "make the", "open a", "open the",
                "generate a", "generate the", "code a", "code the",
                "search for", "find a", "find the"
            )
            if any(
                lower.startswith(pattern) and len(lower.split()) <= len(pattern.split()) + 1
                for pattern in short_two_word_patterns
            ):
                return True
            return False

        def announce_ready(command_or_text: str, full_response: str | None = None) -> None:
            """Signal that the assistant is ready for the next command and optionally speak a prompt."""
            nonlocal voice_ready_prompt, voice_engine, voice_tts_enabled
            try:
                from interface.web_server import emit_log as _emit_log
            except Exception:
                def _emit_log(_m: str):
                    return
            try:
                web_server.emit_listening()
            except Exception:
                pass
            _emit_log("Status: listening for wake word 'bittu'")
            if (
                voice_ready_prompt
                and voice_tts_enabled
                and voice_engine
                and voice_engine.is_running()
            ):
                try:
                    print(f"🔊 Speaking ready prompt: '{voice_ready_prompt}'")
                    speak_if_allowed(voice_ready_prompt)
                    print(f"✅ Ready prompt spoken successfully")
                except Exception as e:
                    print(f"⚠️ Failed to speak ready prompt: {e}")
                    import traceback
                    traceback.print_exc()

        # Create voice_engine variable placeholder (will be set before use)
        voice_engine = None
        
        def on_voice_text(text: str) -> None:
            nonlocal voice_enabled
            nonlocal pending_youtube_song
            nonlocal pending_wake_command
            nonlocal pending_command_buffer
            nonlocal voice_engine
            nonlocal pending_wake_started_at
            nonlocal pending_wake_prompted
            nonlocal voice_tts_enabled
            nonlocal require_wake_word
            """Handle voice input - simplified Alexa-like behavior: always listen for wake word."""
            # Reduced logging for faster processing
            print(f"\n🎤 Voice input: '{text}'")
            print(f"🔍 on_voice_text called, pending_wake_command={pending_wake_command}")
            import sys
            sys.stdout.flush()
            try:
                if not text or not text.strip():
                    print("⚠️ Empty text received, ignoring...")
                    return
                if not voice_engine:
                    print("❌ ERROR: voice_engine is None!")
                    return

                normalized_text = normalize_text(text)

                if normalized_text in {"mute responses", "mute response", "bittu mute responses", "silent mode"}:
                    if voice_tts_enabled:
                        _force_speak("Okay, I'll stay quiet.")
                    voice_tts_enabled = False
                    print("🔇 Voice responses muted.")
                    return
                if normalized_text in {"unmute responses", "voice on", "bittu speak", "enable responses"}:
                    voice_tts_enabled = True
                    _force_speak("Voice responses are back on.")
                    print("🔊 Voice responses re-enabled.")
                    return

                # Check timeout ONLY if text doesn't look like a command
                # If text looks like a command, process it immediately
                text_looks_like_command = any(
                    text.lower().strip().startswith(cmd) 
                    for cmd in ["open ", "start ", "launch ", "create ", "set ", "play ", "what ", "who ", "how ", "where "]
                ) or any(keyword in text.lower() for keyword in ["youtube", "google", "facebook", "weather", "reminder", "notepad"])
                
                if pending_wake_command and pending_wake_started_at and pending_wake_timeout > 0 and not text_looks_like_command:
                    elapsed = time.time() - pending_wake_started_at
                    if elapsed >= pending_wake_timeout and not pending_wake_prompted:
                        pending_wake_prompted = True
                        print("⌛ Wake word heard but no command yet. Prompting user...")
                        if voice_wake_ack_enabled:
                            try:
                                speak_if_allowed(voice_wake_repeat_prompt)
                            except Exception:
                                pass
                        pending_wake_started_at = time.time()
                elif text_looks_like_command and pending_wake_command:
                    print(f"✅ Command-like text detected, processing immediately (pending_wake_command=True)")
                    
                print(f"🎤 Processing voice input: '{text}'")
                try:
                    web_server.emit_heard(text)
                except Exception:
                    pass
                
                # Handle follow-up for pending YouTube song selection
                if pending_youtube_song:
                    song_query = text.strip()
                    if not song_query:
                        return
                    cmd = f"open youtube play {song_query}"
                    print(f"🎯 Processing follow-up YouTube song: '{song_query}'")
                    pending_youtube_song = False
                    speak_if_allowed(f"Searching YouTube for {song_query}")
                    _start_voice_task(cmd)
                    return

                # Enhanced wake word detection with confidence (Siri/Alexa-like accuracy)
                print(f"🔍 Step 1: Checking wake word in text: '{text}'")
                import sys
                sys.stdout.flush()
                # Track if this is a pending wake command - these MUST be processed
                was_pending_wake = pending_wake_command
                try:
                    if pending_wake_command:
                        # If pending_wake_command is True, we're expecting a command
                        # The text might contain "Bittu" or not - either way, process it
                        wake_present = True
                        wake_confidence = "pending"
                        print("🔔 Wake word pending - expecting command (may or may not include 'Bittu').")
                        pending_wake_command = False
                        print(f"🔍 Set wake_present=True, pending_wake_command=False (was_pending={was_pending_wake})")
                        print(f"🔍 Text received: '{text}' - will process as command")
                        sys.stdout.flush()
                    else:
                        wake_present = voice_engine.using_wake_detector or has_wake_word(text)
                        wake_confidence = "high" if voice_engine.using_wake_detector else ("high" if has_wake_word(text) else "none")
                    print(f"🔍 Wake word detected: {wake_present} (confidence: {wake_confidence})")
                    print(f"🔍 About to proceed to Step 2...")
                    sys.stdout.flush()
                except Exception as step1_err:
                    print(f"❌ ERROR in Step 1: {step1_err}")
                    import traceback
                    traceback.print_exc()
                    # Set defaults and continue - especially for pending wake commands
                    wake_present = was_pending_wake if was_pending_wake else False
                    wake_confidence = "error"
                    print(f"🔍 After Step 1 error: wake_present={wake_present}, was_pending_wake={was_pending_wake}")
                    print(f"🔍 About to proceed to Step 2 (after error recovery)...")
                    sys.stdout.flush()
                finally:
                    # Ensure we always proceed to Step 2, especially for pending wake commands
                    if was_pending_wake:
                        print(f"✅ Step 1 complete for pending wake command, ensuring continuation...")
                        sys.stdout.flush()

                # Check if previous task is running (non-blocking check)
                # CRITICAL: This must always execute, especially for pending wake commands
                print(f"🔍 Step 2: Checking if previous task is running... (was_pending_wake={was_pending_wake})")
                import sys
                sys.stdout.flush()
                task_running = False
                is_speaking = False
                try:
                    task_running = _is_voice_task_running()
                    is_speaking = bool(
                        voice_engine and hasattr(voice_engine, "is_speaking") and voice_engine.is_speaking()
                    )
                    print(f"🔍 Step 2 result: task_running={task_running}, is_speaking={is_speaking}, was_pending_wake={was_pending_wake}")
                    
                    # For pending wake commands, skip TTS checks and proceed immediately
                    # CRITICAL: Pending wake commands must always process, regardless of TTS state
                    if was_pending_wake and not task_running:
                        # Pending wake command - request TTS stop in background, don't wait
                        if is_speaking:
                            print("🎧 Pending wake command: TTS is speaking, will stop in background...")
                            sys.stdout.flush()
                            # Stop TTS in a separate thread to avoid blocking
                            def stop_tts_async():
                                try:
                                    if voice_engine and hasattr(voice_engine, "stop_speaking"):
                                        voice_engine.stop_speaking()
                                except:
                                    pass
                            threading.Thread(target=stop_tts_async, daemon=True).start()
                        print(f"✅ Pending wake command: Proceeding immediately (TTS stop requested in background)")
                        sys.stdout.flush()
                        # Continue immediately - don't wait for TTS to stop
                    elif wake_present and task_running:
                        print("⏳ Still working on the previous task. Incoming command will be queued once ready.")
                    elif wake_present and is_speaking and not task_running:
                        if was_pending_wake:
                            print("🎧 Pending wake command detected while TTS is speaking. FORCING TTS stop and immediate processing...")
                        else:
                            print("🎧 Wake word detected while TTS is speaking. Stopping TTS immediately...")
                        import sys
                        import time as _t
                        sys.stdout.flush()
                        # Aggressively stop TTS - this is critical for continuous listening
                        # For pending wake commands, be even more aggressive
                        try:
                            if voice_engine:
                                # Try multiple methods to ensure TTS stops
                                if hasattr(voice_engine, "stop_speaking"):
                                    voice_engine.stop_speaking()
                                    print(f"🔍 TTS stop_speaking() called")
                                if hasattr(voice_engine, "stop"):
                                    try:
                                        voice_engine.stop()
                                        print(f"🔍 TTS stop() called")
                                    except:
                                        pass
                                # For pending wake commands, use shorter delay
                                delay = 0.05 if was_pending_wake else 0.1
                                _t.sleep(delay)
                                # Verify TTS stopped (but don't block if it didn't)
                                try:
                                    is_still_speaking = bool(
                                        voice_engine and hasattr(voice_engine, "is_speaking") and voice_engine.is_speaking()
                                    )
                                    if is_still_speaking:
                                        print(f"⚠️ TTS still speaking after stop attempt, continuing anyway (pending_wake={was_pending_wake})")
                                    else:
                                        print(f"✅ TTS stopped successfully")
                                except:
                                    print(f"⚠️ Could not verify TTS state, continuing anyway")
                        except Exception as e:
                            print(f"⚠️ Error stopping TTS: {e}")
                            import traceback
                            traceback.print_exc()
                        finally:
                            # ALWAYS continue - never let TTS block command processing
                            # Especially for pending wake commands
                            if was_pending_wake:
                                print(f"✅ FORCING command processing (pending wake command, TTS handled)")
                            else:
                                print(f"✅ Proceeding with command processing (TTS stop attempted)")
                            sys.stdout.flush()
                            # CRITICAL: Mark that we've handled TTS, so processing can continue
                            print(f"✅ TTS handling complete, proceeding to continuation point...")
                            sys.stdout.flush()
                except Exception as check_err:
                    print(f"⚠️ Error checking task status: {check_err}")
                    import traceback
                    traceback.print_exc()
                    import sys
                    sys.stdout.flush()
                    # Continue anyway - don't let errors block command processing
                    # For pending wake commands, we MUST continue
                    if was_pending_wake:
                        print(f"✅ FORCING continuation despite Step 2 error (pending wake)")
                        sys.stdout.flush()

                # ALWAYS continue processing command after checking task status
                # This is CRITICAL - must execute for all commands, especially pending wake
                print(f"✅ Step 2 complete, proceeding to continuation (was_pending_wake={was_pending_wake})")
                import sys
                sys.stdout.flush()
                # This should ALWAYS execute - if it doesn't, there's a bug
                # CRITICAL: For pending wake commands, we MUST continue
                try:
                    print(f"✅ About to reach continuation point (was_pending_wake={was_pending_wake})...")
                    import sys
                    sys.stdout.flush()
                    
                    # FORCE continuation for pending wake commands - no exceptions
                    if was_pending_wake:
                        print(f"✅ FORCED continuation point after Step 2 (pending wake command - MUST process)")
                        print(f"🔄 FORCING command processing (pending wake, ignoring TTS state)...")
                        print(f"🔄 Text being processed: '{text}', wake_present={wake_present}, was_pending_wake={was_pending_wake}")
                        sys.stdout.flush()
                    else:
                        print(f"✅ Reached continuation point after Step 2")
                        print(f"🔄 Continuing command processing after TTS stop...")
                        print(f"🔄 Text being processed: '{text}', wake_present={wake_present}, was_pending_wake={was_pending_wake}")
                        sys.stdout.flush()
                    
                    # Enhanced command detection with better intent recognition
                    print(f"🔍 Step 3: Analyzing command intent...")
                    sys.stdout.flush()
                except Exception as cont_err:
                    print(f"❌ ERROR in continuation block: {cont_err}")
                    import traceback
                    traceback.print_exc()
                    # Even on error, continue if it was a pending wake
                    if was_pending_wake:
                        print(f"🔄 FORCING continuation despite error (pending wake)")
                        sys.stdout.flush()
                    else:
                        print(f"🔄 Continuing despite error")
                        sys.stdout.flush()
                
                # CRITICAL: Ensure we always reach Step 3, especially for pending wake commands
                if was_pending_wake:
                    print(f"🔍 FORCING Step 3 execution (pending wake command)")
                    import sys
                    sys.stdout.flush()
                
                is_command_like = False
                command_confidence = 0.0
                try:
                    nl = normalize_text(text)
                    print(f"🔍 Normalized text: '{nl}'")
                    # High confidence command patterns
                    # Extended with common voice patterns for coding so you can just say
                    # "python code for leap year" and it will still be treated as a command,
                    # even without explicitly saying "Bittu" first.
                    high_confidence_starts = (
                        "open ", "start ", "launch ", "run ", "execute ",
                        "set ", "create ", "make ", "write ", "play ",
                        "what ", "who ", "how ", "where ", "show ", "list ",
                        "increase ", "decrease ", "turn on ", "turn off ",
                        "enable ", "disable", "shutdown", "restart", "sleep", "lock",
                        "tell me", "explain", "define", "search", "find",
                        # Voice-friendly code generation triggers
                        "python code", "java code", "javascript code", "c code",
                        "c++ code", "c# code", "html code", "css code", "sql code",
                        "code for", "program for", "write a program", "write python program"
                    )
                    # Medium confidence patterns
                    medium_confidence_starts = (
                        "can you", "could you", "please", "i want", "i need",
                        "help me", "show me", "give me"
                    )
                    
                    if any(nl.startswith(prefix) for prefix in high_confidence_starts):
                        is_command_like = True
                        command_confidence = 0.9
                        print(f"🔍 High confidence command pattern detected")
                    elif any(nl.startswith(prefix) for prefix in medium_confidence_starts):
                        is_command_like = True
                        command_confidence = 0.6
                        print(f"🔍 Medium confidence command pattern detected")
                    else:
                        keyword_triggers = (
                            " song", " music", " youtube", " google", " calculator",
                            " notepad", " weather", " reminder", " open ", " launch ",
                            " play ", " search ", " find ", " show ", " list ", " email"
                        )
                        if any(keyword in nl for keyword in keyword_triggers):
                            is_command_like = True
                            command_confidence = max(command_confidence, 0.7)
                            print(f"🔍 Keyword-based command intent detected")
                except Exception as intent_err:
                    print(f"⚠️ Error in intent detection: {intent_err}")
                    import traceback
                    traceback.print_exc()

                # Process if wake word detected OR phrase looks like a command (with confidence threshold)
                # CRITICAL: If this was a pending wake command, we MUST process it - no exceptions
                if was_pending_wake:
                    should_process = True
                    # Force command_like and confidence for pending wake commands
                    if not is_command_like:
                        is_command_like = True
                        command_confidence = 0.9
                        print(f"🔍 Step 4: FORCING is_command_like=True for pending wake command")
                    print(f"🔍 Step 4: FORCING should_process=True (was_pending_wake=True)")
                    import sys
                    sys.stdout.flush()
                elif require_wake_word:
                    should_process = wake_present
                else:
                    should_process = wake_present or (is_command_like and command_confidence >= 0.6)
                print(
                    f"🔍 Step 4: should_process={should_process} "
                    f"(was_pending_wake={was_pending_wake}, require_wake_word={require_wake_word}, wake_present={wake_present}, "
                    f"is_command_like={is_command_like}, confidence={command_confidence})"
                )
                import sys
                sys.stdout.flush()
                
                if should_process:
                    print(f"🔍 Step 5: Entering command processing block...")
                    print(f"🔍 Command will be processed: wake_present={wake_present}, is_command_like={is_command_like}")
                    try:
                        # Remove wake word and get the command (or use full text for command-like)
                        if voice_engine.using_wake_detector:
                            command = text.strip()
                            print(f"🔍 Using wake detector mode, command: '{command}'")
                        else:
                            # Strip wake word if present, otherwise use text as-is
                            if wake_present:
                                # If text contains wake word, strip it; otherwise use text as command
                                if has_wake_word(text):
                                    command = strip_wake_word(text)
                                    print(f"🔍 Stripped wake word, command: '{command}'")
                                else:
                                    # Wake was pending, text is the command itself
                                    command = text.strip()
                                    print(f"🔍 Using text as command (wake was pending), command: '{command}'")
                            else:
                                command = text.strip()
                                print(f"🔍 Using text as command (no wake word), command: '{command}'")
                        
                        # Normalize common typos and variations
                        command = normalize_command_typos(command)
                        print(f"📝 Extracted command: '{command}'")
                        
                        if pending_command_buffer and command.strip():
                            command = f"{pending_command_buffer.strip()} {command.strip()}".strip()
                            pending_command_buffer = ""
                            print(f"📝 Combined with buffer: '{command}'")

                        if command and command.strip():
                            pending_wake_started_at = None
                            pending_wake_prompted = False
                            cmd_lower_for_followup = command.strip().lower()
                            
                            # Quick check: if command is clearly complete (has action + target), process immediately
                            # This prevents false positives on "incomplete" commands
                            # BUT: For pending wake commands, always process (user already said the command)
                            action_words = ["open", "start", "launch", "create", "write", "play", "set", "run", "execute"]
                            has_action = any(cmd_lower_for_followup.startswith(act + " ") or cmd_lower_for_followup == act for act in action_words)
                            print(f"🔍 Command analysis: has_action={has_action}, cmd='{cmd_lower_for_followup}', was_pending_wake={was_pending_wake}")
                            
                            # Skip incomplete check for pending wake commands - user already said the command
                            # For pending wake commands, ALWAYS process regardless of action words
                            if was_pending_wake:
                                print(f"✅ Processing pending wake command (skipping all checks, user already said command)")
                                # Force has_action to True for pending wake commands so they always process
                                has_action = True
                                print(f"✅ Forced has_action=True for pending wake command")
                            elif not has_action and command_needs_followup(cmd_lower_for_followup):
                                pending_wake_command = True
                                pending_command_buffer = command.strip()
                                pending_wake_started_at = time.time()
                                pending_wake_prompted = False
                                print("⏳ Command sounds incomplete. Waiting for more details...")
                                try:
                                    web_server.emit_listening()
                                except Exception:
                                    pass
                                return

                            # For pending wake commands, if only TTS is speaking (not a real task), process immediately
                            # Otherwise, queue if a real task is running
                            task_running_check = _is_voice_task_running()
                            is_speaking_check = bool(
                                voice_engine and hasattr(voice_engine, "is_speaking") and voice_engine.is_speaking()
                            )
                            
                            if task_running_check:
                                # Real task is running - queue the command
                                with command_queue_lock:
                                    command_queue.append(command.strip())
                                print(f"📥 Command queued while task running: '{command.strip()}'")
                                speak_if_allowed("I'm finishing your previous request. I'll handle that next.")
                                return
                            elif was_pending_wake and is_speaking_check and not task_running_check:
                                # Pending wake command + only TTS speaking (no real task) = process immediately
                                print(f"✅ Processing pending wake command immediately (TTS only, no real task)")
                                print(f"✅ Bypassing queue, processing command now...")
                                import sys
                                sys.stdout.flush()
                                # Continue to process the command below
                            elif is_speaking_check:
                                # TTS is speaking but it's not a pending wake command - still process (TTS will be stopped)
                                print(f"✅ Processing command (TTS will be interrupted)")
                                # Continue to process the command below

                            # This should ALWAYS execute if we reach here
                            command_to_run = command.strip()
                            print(f"🎯 Processing command: '{command_to_run}' (was_pending_wake={was_pending_wake})")
                            print(f"⚡ Starting task execution immediately...")
                            import sys
                            sys.stdout.flush()
                            # Set pending_wake_command immediately so next command doesn't need "Bittu"
                            if auto_listen_after_command:
                                pending_wake_command = True
                                pending_wake_started_at = time.time()
                                pending_wake_prompted = False
                                print(f"🔔 Auto-listen enabled: next command won't need 'Bittu'")
                            try:
                                _start_voice_task(command_to_run)
                                print(f"✅ _start_voice_task called successfully for '{command_to_run}'")
                            except Exception as task_err:
                                print(f"❌ ERROR starting voice task: {task_err}")
                                import traceback
                                traceback.print_exc()
                                # Try to continue listening
                                try:
                                    web_server.emit_listening()
                                except Exception:
                                    pass
                            return
                        else:
                            print(f"⚠️ Command is empty after extraction, setting pending_wake_command")
                            # Wake word only - set pending flag so next utterance is treated as the command
                            pending_wake_command = True
                            pending_wake_started_at = time.time()
                            pending_wake_prompted = False
                            print("🎤 Wake word detected. Waiting for your command...")
                            if voice_wake_ack_enabled:
                                try:
                                    speak_if_allowed(voice_wake_prompt)
                                except Exception:
                                    pass
                            try:
                                web_server.emit_listening()
                            except Exception:
                                pass
                    except Exception as process_err:
                        print(f"❌ CRITICAL ERROR in command processing: {process_err}")
                        import traceback
                        traceback.print_exc()
                        try:
                            web_server.emit_listening()
                        except Exception:
                            pass
                    else:
                        # Wake word only - set pending flag so next utterance is treated as the command
                        pending_wake_command = True
                        pending_wake_started_at = time.time()
                        pending_wake_prompted = False
                        print("🎤 Wake word detected. Waiting for your command...")
                        if voice_wake_ack_enabled:
                            try:
                                speak_if_allowed(voice_wake_prompt)
                            except Exception:
                                pass
                        try:
                            web_server.emit_listening()
                        except Exception:
                            pass
                else:
                    # No wake word detected - ignore (Alexa-like: only responds to wake word)
                    # This ensures continuous listening works properly
                    print(f"⏭️  No wake word detected. Ignoring: '{text}'")
                    try:
                        web_server.emit_listening()
                    except Exception:
                        pass
            except Exception as e:
                # Critical error handling - ensure we don't break the listening loop
                print(f"❌ CRITICAL ERROR in on_voice_text: {e}")
                import traceback
                traceback.print_exc()
                # Always try to continue listening even after error
                try:
                    web_server.emit_listening()
                except Exception:
                    pass
                print("🔄 Continuing to listen despite error...")

        # Create voice engine with callback BEFORE starting
        voice_engine = VoiceAssistant(on_voice_text)
        print("✅ Voice engine created with callback")
        print(f"   Callback function: {voice_engine.on_transcript}")
        
        # Auto-start voice assistant immediately
        show_output("🎙️ Initializing voice assistant...")
        try:
            if voice_engine.start():
                voice_enabled = True
                print("✅ Voice assistant start() returned True")
                
                # Give the listening thread a brief moment to actually start
                import time
                time.sleep(0.3)  # Minimal delay for thread to start
                
                # Verify voice engine is actually running
                if voice_engine.is_running():
                    print("✅ Voice engine thread is running and listening")
                    show_success("🎙️ Voice assistant is listening NOW!")
                    show_output("🎤 Say 'Bittu' followed by your command - I'm listening!")
                else:
                    print("⚠️ WARNING: Voice engine thread is NOT running!")
                    print("   Attempting to restart...")
                    if voice_engine.restart():
                        print("✅ Voice engine restarted successfully")
                        time.sleep(0.2)  # Brief pause after restart
                        if voice_engine.is_running():
                            show_success("🎙️ Voice assistant restarted and listening!")
                        else:
                            show_error("❌ Voice engine restarted but still not running")
                            voice_enabled = False
                    else:
                        print("❌ Failed to restart voice engine")
                        show_error("❌ Voice assistant thread failed to start properly")
                        diag = getattr(voice_engine, 'diagnostics', lambda: 'No diagnostics')()
                        show_output("Voice diagnostics: " + diag)
                        voice_enabled = False
                
                # Don't speak greeting immediately - let listening start first
                # The listening loop will start immediately and won't be blocked by TTS
                if voice_enabled and voice_engine.is_running():
                    show_output("🎤 Voice assistant is listening continuously. Say 'Bittu' followed by your command.")
                    if voice_spoken_greeting_enabled and voice_tts_enabled:
                        # Delay greeting slightly to ensure listening has started
                        # Allow opt-in spoken greeting for those who prefer it
                        def delayed_greeting():
                            time.sleep(1.0)  # Wait for listening loop to start first
                            if voice_engine.is_running():
                                speak_if_allowed(voice_greeting_text)
                                print("🔊 Greeting spoken. Voice assistant is actively listening for commands.")
                        
                        # Run greeting in separate thread so it doesn't block
                        threading.Thread(target=delayed_greeting, daemon=True).start()
                        print("✅ Listening started - greeting will be spoken shortly")
                    else:
                        print("✅ Listening started - no spoken greeting (ready immediately)")
            else:
                show_error("❌ Voice assistant failed to start. You can still use text commands.")
                diag = getattr(voice_engine, 'diagnostics', lambda: 'No diagnostics')()
                show_output("Voice diagnostics: " + diag)
                voice_enabled = False
        except Exception as e:
            show_error(f"❌ Voice assistant initialization failed: {str(e)}")
            import traceback
            traceback.print_exc()
            show_output("You can still use text commands. Type 'help' for assistance.")
            voice_enabled = False
        
        # Final verification - but don't delay if already running
        if voice_enabled:
            if voice_engine.is_running():
                print("✅ FINAL CHECK: Voice engine is running and ready to receive commands")
                print("   You can now say 'Bittu' followed by your command")
            else:
                print("⚠️ FINAL CHECK: Voice engine is NOT running - attempting final restart...")
                if voice_engine.restart():
                    print("✅ Voice engine restarted - should be listening now")
                else:
                    print("❌ CRITICAL: Voice engine failed to start. Check microphone permissions.")
                    diag = getattr(voice_engine, 'diagnostics', lambda: 'No diagnostics')()
                    print("Diagnostics:", diag)

        def print_response(resp: str) -> None:
            # Ensure response is not None or empty
            if not resp:
                resp = "No response generated."
            
            # Display response with appropriate formatting
            if "✅" in resp or "success" in resp.lower():
                show_success(resp)
            elif "❌" in resp or "error" in resp.lower():
                show_error(resp)
            else:
                show_output(resp)
            try:
                web_server.emit_speaking(tts_clean(resp))
                web_server.emit_listening()
            except Exception:
                pass
            llm_label = get_last_llm_label()
            if llm_label:
                print(f"🤖 Model: {llm_label}")

        # Main conversation loop
        while True:
            try:
                # Check if voice assistant is still running and restart if needed
                if voice_enabled and not voice_engine.is_running():
                    print("🔄 Voice assistant stopped, restarting...")
                    if voice_engine.restart():
                        print("✅ Voice assistant restarted successfully")
                    else:
                        print("❌ Failed to restart voice assistant")
                        voice_enabled = False
                
                user_input = get_input()
                
                # Handle special commands
                if user_input.lower() in ["exit", "quit", "bye", "goodbye"]:
                    show_goodbye()
                    try:
                        voice_engine.stop()
                    except Exception:
                        pass
                    break
                elif user_input.lower() in ["help", "h", "?"]:
                    show_help_menu()
                    continue
                elif user_input.lower() in ["voice on", "start voice", "enable voice"]:
                    if voice_enabled:
                        show_success("🎙️ Voice assistant is already enabled and listening!")
                        try:
                            speak_if_allowed("I'm already listening. How can I help you?")
                        except Exception:
                            pass
                    else:
                        ok = False
                        try:
                            ok = voice_engine.start()
                        except Exception:
                            ok = False
                        if ok:
                            voice_enabled = True
                            show_success("🎙️ Voice assistant enabled. Listening…")
                            try:
                                speak_if_allowed("Voice assistant is now active. How can I help you?")
                            except Exception:
                                pass
                            show_output("Voice assistant is now active. How can I help you?")
                        else:
                            diag = getattr(voice_engine, 'diagnostics', lambda: 'No diagnostics')()
                            show_error("❌ Voice setup failed. Ensure microphone access and install PyAudio & SpeechRecognition.\n" + diag)
                            show_output("Opening microphone privacy settings…")
                            try:
                                import os as _os
                                _os.system("start ms-settings:privacy-microphone")
                            except Exception:
                                pass
                    continue
                elif user_input.lower() in ["voice status", "mic status", "voice diagnostics"]:
                    diag = getattr(voice_engine, 'diagnostics', lambda: 'No diagnostics')()
                    show_output(diag)
                    continue
                elif user_input.lower() in ["voice off", "stop voice", "disable voice"]:
                    if voice_enabled:
                        try:
                            voice_engine.stop()
                            voice_enabled = False
                            show_success("🎙️ Voice assistant disabled. You can still use text commands.")
                            try:
                                speak_if_allowed("Voice assistant disabled. You can still type commands.")
                            except Exception:
                                pass
                        except Exception:
                            show_error("❌ Couldn't stop voice assistant.")
                    else:
                        show_output("🎙️ Voice assistant is already disabled.")
                    continue
                elif user_input.lower() in ["clear", "cls"]:
                    from interface.cli_interface import clear_screen
                    clear_screen()
                    show_welcome()
                    continue
                elif user_input.strip() == "":
                    # If alarm is ringing, pressing Enter stops it immediately
                    try:
                        if is_alarm_active():
                            print(stop_alarm_now())
                            continue
                    except Exception:
                        pass
                    if voice_enabled:
                        print("🎤 Voice assistant is listening... Just speak your command!")
                    else:
                        print("💡 Please enter a command or type 'help' for assistance.")
                    continue
                elif user_input.lower().startswith("voice simulate "):
                    simulated = user_input[len("voice simulate "):].strip()
                    if not simulated:
                        show_output("Provide text after 'voice simulate'.")
                        continue
                    show_output(f"🎛️ Simulating voice input: {simulated}")
                    on_voice_text(simulated)
                    continue
                elif user_input.lower() in ["mute responses", "mute voice", "silent mode"]:
                    voice_tts_enabled = False
                    print("🔇 Voice responses muted.")
                    continue
                elif user_input.lower() in ["unmute responses", "voice responses on", "speak again"]:
                    voice_tts_enabled = True
                    print("🔊 Voice responses re-enabled.")
                    continue
                
                # Process the command
                try:
                    web_server.emit_heard(user_input)
                    web_server.emit_processing()
                except Exception:
                    pass
                
                print("⏳ Working on your request...")
                # Process command and get response (same path as voice commands for consistency)
                start_time = time.time()
                try:
                    print(f"🔄 Calling process_command('{user_input}')...")
                    response = process_command(user_input)
                    elapsed = time.time() - start_time
                    print(f"⏱️ process_command completed in {elapsed:.2f}s")
                except Exception as e:
                    elapsed = time.time() - start_time
                    print(f"❌ process_command failed after {elapsed:.2f}s: {e}")
                    import traceback
                    traceback.print_exc()
                    response = f"❌ Error processing command: {str(e)}"
                
                # Ensure response is not None or empty
                if not response:
                    response = "I'm not sure how to respond to that. Could you please rephrase your question?"
                
                # Always print the response to terminal
                print_response(response)
                
                # Always speak the response (if voice is available)
                try:
                    vr = create_voice_response(response, user_input)
                    if vr and vr.strip():
                        print(f"🔊 Preparing to speak: '{vr}'")
                        if voice_engine and hasattr(voice_engine, 'speak'):
                            speak_if_allowed(vr)
                            print(f"✅ TTS called successfully: '{vr}'")
                        else:
                            print("❌ ERROR: voice_engine.speak() not available!")
                except Exception as e:
                    print(f"❌ ERROR speaking response: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Announce ready for next command
                announce_ready(user_input, response)
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                show_error(f"An unexpected error occurred: {str(e)}")
                print("💡 Try again or type 'help' for assistance.")
                
    except Exception as e:
        show_error(f"Failed to start assistant: {str(e)}")
        print("💡 Make sure all dependencies are installed: pip install -r requirements.txt")

if __name__ == "__main__":
    main()
