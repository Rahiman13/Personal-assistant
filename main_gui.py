#!/usr/bin/env python3
"""
Main GUI Application for Personal AI Assistant
Integrates the professional GUI interface with the voice assistant
"""

import sys
import os
import threading
import time
from typing import Optional

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from interface.gui_interface import VoiceAssistantGUI
from core.brain import process_command
from voice import VoiceAssistant

class PersonalAIAssistant:
    def __init__(self):
        self.gui = VoiceAssistantGUI()
        self.voice_engine: Optional[VoiceAssistant] = None
        self.voice_enabled = False
        
        # Setup callbacks
        self.gui.set_voice_command_callback(self.handle_voice_command)
        self.gui.set_voice_toggle_callback(self.toggle_voice_assistant)
        
        # Initialize voice assistant
        self.initialize_voice_assistant()
        
    def initialize_voice_assistant(self):
        """Initialize the voice assistant"""
        try:
            self.voice_engine = VoiceAssistant(self.handle_voice_input)
            self.gui.queue_message({
                'type': 'chat_message',
                'text': 'Voice assistant initialized successfully!',
                'sender': 'system'
            })
        except Exception as e:
            self.gui.queue_message({
                'type': 'chat_message',
                'text': f'Failed to initialize voice assistant: {str(e)}',
                'sender': 'system'
            })
            
    def handle_voice_input(self, text: str):
        """Handle voice input from the voice assistant"""
        self.gui.queue_message({
            'type': 'chat_message',
            'text': f'Heard: {text}',
            'sender': 'system'
        })
        
        # Process the voice command
        self.handle_voice_command(text)
        
    def handle_voice_command(self, text: str):
        """Handle voice commands (both from voice and text input)"""
        if not text.strip():
            return
            
        # Update GUI to show processing
        self.gui.queue_message({
            'type': 'voice_state',
            'processing': True
        })
        
        # Normalization helpers (duplicated lightweight here for GUI)
        def _normalize(s: str) -> str:
            try:
                import re
                s = s.lower()
                s = re.sub(r"[^a-z0-9\s]", " ", s)
                s = re.sub(r"\s+", " ", s).strip()
            except Exception:
                s = s.lower().strip()
            return s

        def _has_wake(s: str) -> bool:
            t = _normalize(s)
            variants = {"bittu", "bitu", "bitto", "beetu", "bithu", "bito", "bittu ji", "hey bittu", "hi bittu", "ok bittu", "okay bittu"}
            if any(v in t for v in variants):
                return True
            # Regex-based fuzzy match
            try:
                import re
                patterns = [
                    r"\bb[iy]tt?u\b",
                    r"^bittu\b",
                    r"\bbittu\s",
                ]
                for p in patterns:
                    if re.search(p, t):
                        return True
            except Exception:
                pass
            # Token match
            tokens = t.split()
            return "bittu" in tokens or any(token.startswith("bitt") for token in tokens)

        def _strip_wake(s: str) -> str:
            t = _normalize(s)
            for w in ["hey", "hi", "ok", "please"]:
                t = t.replace(f"{w} bittu", "bittu").strip()
            return t.replace("bittu", "").strip()

        # Wake word logic - Alexa-like: only respond to wake word
        if _has_wake(text):
            command = _strip_wake(text)
            if command:
                self.gui.queue_message({
                    'type': 'chat_message',
                    'text': f'Processing command: {command}',
                    'sender': 'system'
                })
                self.process_command(command)
            else:
                # Wake word only - brief acknowledgment
                self.gui.queue_message({
                    'type': 'chat_message',
                    'text': "Yes, I'm listening.",
                    'sender': 'assistant'
                })
                self.speak_response("Yes")
                # Reset processing state
                self.gui.queue_message({'type': 'voice_state', 'processing': False})
        else:
            # No wake word - ignore (Alexa-like behavior)
            # This ensures continuous listening works properly
            pass
            
    def process_command(self, command: str):
        """Process a command and provide response"""
        try:
            # Process the command using the brain
            response = process_command(command)
            
            # Display response in GUI
            self.gui.queue_message({
                'type': 'chat_message',
                'text': response,
                'sender': 'assistant'
            })
            
            # Create voice response
            voice_response = self.create_voice_response(response, command)
            
            # Speak the response (no follow-up prompt to avoid interfering with listening)
            self.speak_response(voice_response)
            
        except Exception as e:
            error_msg = f"Error processing command: {str(e)}"
            self.gui.queue_message({
                'type': 'chat_message',
                'text': error_msg,
                'sender': 'system'
            })
        finally:
            # Update GUI to show ready state
            self.gui.queue_message({
                'type': 'voice_state',
                'processing': False
            })
            
    def create_voice_response(self, full_response: str, command: str) -> str:
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
                if "✅" in full_response:
                    return "Done!"
                elif "❌" in full_response:
                    return "Sorry, I couldn't do that"
                else:
                    return "Command completed"
            else:
                # Clean the response for TTS
                import re
                cleaned = re.sub(r"[\u2600-\u27BF\U0001F300-\U0001FAFF]", "", full_response)
                cleaned = cleaned.replace("\n", " ").strip()
                return cleaned[:200]
                
    def speak_response(self, text: str):
        """Speak a response using the voice engine"""
        if self.voice_engine and text.strip():
            # Update GUI to show speaking
            self.gui.queue_message({
                'type': 'voice_state',
                'speaking': True
            })
            
            # Speak in a separate thread to avoid blocking
            def speak_thread():
                try:
                    self.voice_engine.speak(text.strip())
                except Exception as e:
                    print(f"TTS Error: {e}")
                finally:
                    # Update GUI to show not speaking
                    self.gui.queue_message({
                        'type': 'voice_state',
                        'speaking': False
                    })
                    
            threading.Thread(target=speak_thread, daemon=True).start()
            
    def toggle_voice_assistant(self, enable: bool):
        """Toggle the voice assistant on/off"""
        if not self.voice_engine:
            self.gui.queue_message({
                'type': 'chat_message',
                'text': 'Voice assistant not initialized',
                'sender': 'system'
            })
            return
            
        try:
            if enable and not self.voice_enabled:
                # Start voice assistant
                if self.voice_engine.start():
                    self.voice_enabled = True
                    self.gui.queue_message({
                        'type': 'voice_state',
                        'listening': True
                    })
                    self.gui.queue_message({
                        'type': 'chat_message',
                        'text': 'Voice assistant enabled. Say "Bittu" followed by your command.',
                        'sender': 'system'
                    })
                    self.speak_response("Voice assistant enabled. I'm listening for your commands.")
                else:
                    self.gui.queue_message({
                        'type': 'chat_message',
                        'text': 'Failed to start voice assistant',
                        'sender': 'system'
                    })
            elif not enable and self.voice_enabled:
                # Stop voice assistant
                self.voice_engine.stop()
                self.voice_enabled = False
                self.gui.queue_message({
                    'type': 'voice_state',
                    'listening': False
                })
                self.gui.queue_message({
                    'type': 'chat_message',
                    'text': 'Voice assistant disabled',
                    'sender': 'system'
                })
        except Exception as e:
            self.gui.queue_message({
                'type': 'chat_message',
                'text': f'Error toggling voice assistant: {str(e)}',
                'sender': 'system'
            })
            
    def run(self):
        """Run the application"""
        try:
            # Show welcome message
            self.gui.queue_message({
                'type': 'chat_message',
                'text': 'Welcome to Bittu - Personal AI Assistant!',
                'sender': 'system'
            })
            self.gui.queue_message({
                'type': 'chat_message',
                'text': 'Click "Start Voice Assistant" to begin voice interaction, or type commands directly.',
                'sender': 'system'
            })
            
            # Start the GUI
            self.gui.run()
            
        except KeyboardInterrupt:
            print("\nShutting down...")
        except Exception as e:
            print(f"Error running application: {e}")
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Cleanup resources"""
        if self.voice_engine and self.voice_enabled:
            try:
                self.voice_engine.stop()
            except Exception:
                pass
        if self.gui:
            try:
                self.gui.destroy()
            except Exception:
                pass

if __name__ == "__main__":
    app = PersonalAIAssistant()
    app.run()
