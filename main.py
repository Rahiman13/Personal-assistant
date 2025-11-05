# main.py
from interface.cli_interface import (
    get_input, show_output, show_welcome, show_goodbye, 
    show_help_menu, show_error, show_success
)
from core.brain import process_command
from skills.system_controls import is_alarm_active, stop_alarm_now
from voice import VoiceAssistant
from interface import web_server

def main():
    """Main function to run the Personal AI Assistant"""
    try:
        # Show welcome message
        show_welcome()
        
        # Voice assistant state - auto-start enabled
        # Create a temporary callback that will be replaced
        def temp_callback(text: str):
            print(f"⚠️ Temporary callback called with: '{text}' - this should not happen")
        
        voice_engine = VoiceAssistant(temp_callback)
        voice_enabled = False
        
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

        # Auto-start voice assistant
        show_output("🎙️ Initializing voice assistant...")
        try:
            if voice_engine.start():
                voice_enabled = True
                show_success("🎙️ Voice assistant ready!")
                # Personalized greeting
                greeting = "Hi, this is Bittu. I'm listening. Say 'Bittu' followed by your command."
                show_output(greeting)
                show_output("🎤 Voice assistant is listening continuously. Say 'Bittu' followed by your command.")
                # Speak greeting in background (non-blocking)
                voice_engine.speak(greeting)
            else:
                show_error("❌ Voice assistant failed to start. You can still use text commands.")
                diag = getattr(voice_engine, 'diagnostics', lambda: 'No diagnostics')()
                show_output("Voice diagnostics: " + diag)
        except Exception as e:
            show_error(f"❌ Voice assistant initialization failed: {str(e)}")
            show_output("You can still use text commands. Type 'help' for assistance.")

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
            text = normalize_text(s)
            # More accurate wake word detection - check if "bittu" appears as a word
            # Common variants and greetings
            wake_variants = {
                "bittu", "bitu", "bitto", "beetu", "bithu", "bito",
                "bittu ji", "bittuji", "hey bittu", "hi bittu", "ok bittu", "okay bittu"
            }
            # Check for exact matches in variants
            if any(w in text for w in wake_variants):
                return True
            # Regex-based fuzzy match (captures common STT confusions)
            try:
                import re
                patterns = [
                    r"\bb[iy]tt?u\b",      # bittu/bitu variations (word boundary)
                    r"\bb[iy]t+u+\b",      # elongated vowels/consonants
                    r"\bbe+tu+\b",         # beetu/betu
                    r"\bbit+o\b",          # bitto
                    r"^bittu\b",           # Start with bittu
                    r"\bbittu\s",          # bittu followed by space
                ]
                for p in patterns:
                    if re.search(p, text):
                        return True
            except Exception:
                pass
            # Token match - check if bittu is a separate word
            tokens = text.split()
            return "bittu" in tokens or any(t.startswith("bitt") for t in tokens)

        def strip_wake_word(s: str) -> str:
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
            return text
        
        def create_voice_response(full_response: str, command: str) -> str:
            """Create shorter, more natural voice responses"""
            command_lower = command.lower().strip()
            
            # Handle specific commands with short responses
            if "open youtube" in command_lower or "youtube" in command_lower:
                return "Opening YouTube"
            elif "open google" in command_lower or "google" in command_lower:
                return "Opening Google"
            elif "open gmail" in command_lower or "gmail" in command_lower:
                return "Opening Gmail"
            elif "open github" in command_lower or "github" in command_lower:
                return "Opening GitHub"
            elif "open calculator" in command_lower or "calculator" in command_lower:
                return "Opening Calculator"
            elif "open notepad" in command_lower or "notepad" in command_lower:
                return "Opening Notepad"
            elif "open vs code" in command_lower or "code" in command_lower:
                return "Opening VS Code"
            elif "weather" in command_lower:
                # Extract just the weather info, not the full response
                if "temperature" in full_response.lower():
                    import re
                    temp_match = re.search(r'(\d+[°°]?[CF]?)', full_response)
                    if temp_match:
                        return f"Weather: {temp_match.group(1)}"
                return "Getting weather information"
            elif "create" in command_lower and ("file" in command_lower or "script" in command_lower):
                if "python" in command_lower:
                    return "Creating Python script"
                elif "html" in command_lower:
                    return "Creating HTML file"
                elif "css" in command_lower:
                    return "Creating CSS file"
                elif "javascript" in command_lower or "js" in command_lower:
                    return "Creating JavaScript file"
                else:
                    return "Creating file"
            elif "remind" in command_lower or "reminder" in command_lower:
                return "Reminder set"
            elif "help" in command_lower:
                return "Here are the available commands"
            elif "hello" in command_lower or "hi" in command_lower:
                return "Hello! How can I help you?"
            elif "thank" in command_lower:
                return "You're welcome!"
            elif "bye" in command_lower or "goodbye" in command_lower:
                return "Goodbye! Have a great day!"
            else:
                # For other commands, use a shortened version
                if len(full_response) > 100:
                    # Try to extract the key information
                    if "✅" in full_response:
                        return "Done!"
                    elif "❌" in full_response:
                        return "Sorry, I couldn't do that"
                    else:
                        return "Command completed"
                else:
                    return tts_clean(full_response)

        def announce_ready(command_or_text: str, full_response: str | None = None) -> None:
            """After completing a command, set state/UI to indicate ready for next command.
            Don't speak - just update UI to avoid TTS interfering with continuous listening.
            """
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

        def on_voice_text(text: str) -> None:
            nonlocal voice_enabled
            """Handle voice input - simplified Alexa-like behavior: always listen for wake word."""
            try:
                if not text or not text.strip():
                    return
                    
                print(f"\n🎤 Heard: '{text}'")
                try:
                    web_server.emit_heard(text)
                except Exception:
                    pass
                
                # Determine if wake word is present in the utterance
                wake_present = has_wake_word(text)
                print(f"🔍 Wake word detected: {wake_present}")
                
                # Only process if wake word is detected (Alexa-like behavior)
                if wake_present:
                    # Remove wake word and get the command
                    command = strip_wake_word(text)
                    print(f"📝 Extracted command: '{command}'")
                    
                    if command and command.strip():
                        # We have a command with wake word - process it
                        print(f"🎯 Processing command: '{command}'")
                        try:
                            web_server.emit_processing()
                        except Exception:
                            pass
                        
                        try:
                            # Process the command
                            resp = process_command(command)
                            print_response(resp)
                            
                            # Speak the response (non-blocking - runs in separate thread)
                            try:
                                voice_response = create_voice_response(resp, command)
                                try:
                                    web_server.emit_speaking(voice_response)
                                except Exception:
                                    pass
                                # Speak is now non-blocking - returns immediately
                                voice_engine.speak(voice_response)
                                print("🔊 TTS started in background thread")
                            except Exception as e:
                                print(f"⚠️ Error speaking response: {e}")
                                import traceback
                                traceback.print_exc()
                            
                            # Immediately ready for next command (no extra speech)
                            announce_ready(command, resp)
                            print("✅ Command completed. 🎤 Listening for 'bittu'...")
                            print("   (TTS is speaking in background - listening will resume after TTS finishes)")
                            
                            # Verify voice assistant is still running
                            if voice_enabled and not voice_engine.is_running():
                                print("⚠️ Voice assistant stopped! Restarting...")
                                if voice_engine.restart():
                                    print("✅ Voice assistant restarted")
                                else:
                                    print("❌ Failed to restart voice assistant")
                                    voice_enabled = False
                        except Exception as e:
                            print(f"❌ Error processing command: {e}")
                            import traceback
                            traceback.print_exc()
                            # Still announce ready so listening continues
                            try:
                                web_server.emit_listening()
                            except Exception:
                                pass
                    else:
                        # Wake word only - just acknowledge briefly
                        print("🎤 Wake word detected. Waiting for command...")
                        try:
                            # Very brief acknowledgment
                            voice_engine.speak("Yes")
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

        # attach callback now that helper exists
        voice_engine.on_transcript = on_voice_text
        print("✅ Callback attached to voice engine")
        print(f"✅ Callback function: {voice_engine.on_transcript}")
        print("🎤 Voice assistant is ready. Listening for 'bittu'...")
        
        # Verify voice engine is running
        import time
        time.sleep(0.5)  # Give it a moment to start
        if voice_enabled:
            if voice_engine.is_running():
                print("✅ Voice engine thread is running")
            else:
                print("⚠️ WARNING: Voice engine thread is NOT running!")
                print("   Attempting to restart...")
                if voice_engine.restart():
                    print("✅ Voice engine restarted successfully")
                else:
                    print("❌ Failed to restart voice engine")

        def print_response(resp: str) -> None:
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
                            voice_engine.speak("I'm already listening. How can I help you?")
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
                                voice_engine.speak("Voice assistant is now active. How can I help you?")
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
                                voice_engine.speak("Voice assistant disabled. You can still type commands.")
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
                
                # Process the command
                try:
                    web_server.emit_heard(user_input)
                    web_server.emit_processing()
                except Exception:
                    pass
                response = process_command(user_input)
                print_response(response)
                # Speak and announce readiness for typed commands as well
                try:
                    vr = create_voice_response(response, user_input)
                    voice_engine.speak(vr)
                    announce_ready(user_input, response)
                except Exception:
                    pass
                    
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
