#!/usr/bin/env python3
"""
Professional GUI Interface for Personal AI Assistant
Features:
- Brain-like visual structure with animated lights
- Real-time voice status indicators
- Professional and attractive design
- Visual feedback for listening/speaking states
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import time
import math
from typing import Callable, Optional
import queue

class VoiceAssistantGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Bittu - Personal AI Assistant")
        self.root.geometry("1000x700")
        self.root.configure(bg='#0a0a0a')
        
        # Voice states
        self.is_listening = False
        self.is_speaking = False
        self.is_processing = False
        
        # Animation variables
        self.animation_running = False
        self.brain_pulse = 0
        self.light_intensity = 0
        
        # Message queue for thread-safe updates
        self.message_queue = queue.Queue()
        
        # Callbacks
        self.on_voice_command: Optional[Callable[[str], None]] = None
        self.on_voice_toggle: Optional[Callable[[bool], None]] = None
        
        self.setup_ui()
        self.start_animation()
        self.check_queue()
        
    def setup_ui(self):
        """Setup the main UI components"""
        # Main container
        main_frame = tk.Frame(self.root, bg='#0a0a0a')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Header
        self.create_header(main_frame)
        
        # Brain visualization area
        self.create_brain_visualization(main_frame)
        
        # Status and controls
        self.create_status_controls(main_frame)
        
        # Chat area
        self.create_chat_area(main_frame)
        
        # Input area
        self.create_input_area(main_frame)
        
    def create_header(self, parent):
        """Create the header section"""
        header_frame = tk.Frame(parent, bg='#0a0a0a')
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Title
        title_label = tk.Label(
            header_frame,
            text="Bittu - Personal AI Assistant",
            font=('Arial', 24, 'bold'),
            fg='#00ff88',
            bg='#0a0a0a'
        )
        title_label.pack(side=tk.LEFT)
        
        # Status indicator
        self.status_label = tk.Label(
            header_frame,
            text="● Ready",
            font=('Arial', 12),
            fg='#00ff88',
            bg='#0a0a0a'
        )
        self.status_label.pack(side=tk.RIGHT)
        
    def create_brain_visualization(self, parent):
        """Create the brain-like visualization with lights"""
        brain_frame = tk.Frame(parent, bg='#0a0a0a', height=300)
        brain_frame.pack(fill=tk.X, pady=(0, 20))
        brain_frame.pack_propagate(False)
        
        # Canvas for brain visualization
        self.brain_canvas = tk.Canvas(
            brain_frame,
            bg='#0a0a0a',
            highlightthickness=0,
            height=300
        )
        self.brain_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Initialize brain visualization
        self.draw_brain_structure()
        
    def create_status_controls(self, parent):
        """Create status and control buttons"""
        control_frame = tk.Frame(parent, bg='#0a0a0a')
        control_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Voice toggle button
        self.voice_button = tk.Button(
            control_frame,
            text="🎤 Start Voice Assistant",
            font=('Arial', 12, 'bold'),
            bg='#00ff88',
            fg='#000000',
            relief=tk.FLAT,
            padx=20,
            pady=10,
            command=self.toggle_voice
        )
        self.voice_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Clear button
        clear_button = tk.Button(
            control_frame,
            text="🗑️ Clear",
            font=('Arial', 12),
            bg='#ff4444',
            fg='#ffffff',
            relief=tk.FLAT,
            padx=20,
            pady=10,
            command=self.clear_chat
        )
        clear_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Settings button
        settings_button = tk.Button(
            control_frame,
            text="⚙️ Settings",
            font=('Arial', 12),
            bg='#4444ff',
            fg='#ffffff',
            relief=tk.FLAT,
            padx=20,
            pady=10,
            command=self.show_settings
        )
        settings_button.pack(side=tk.LEFT)
        
    def create_chat_area(self, parent):
        """Create the chat display area"""
        chat_frame = tk.Frame(parent, bg='#0a0a0a')
        chat_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Chat display
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            bg='#1a1a1a',
            fg='#ffffff',
            font=('Consolas', 11),
            wrap=tk.WORD,
            state=tk.DISABLED,
            insertbackground='#00ff88'
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for different message types
        self.chat_display.tag_configure('user', foreground='#00ff88', font=('Consolas', 11, 'bold'))
        self.chat_display.tag_configure('assistant', foreground='#88aaff', font=('Consolas', 11))
        self.chat_display.tag_configure('system', foreground='#ffaa00', font=('Consolas', 10, 'italic'))
        self.chat_display.tag_configure('error', foreground='#ff4444', font=('Consolas', 11))
        
    def create_input_area(self, parent):
        """Create the input area"""
        input_frame = tk.Frame(parent, bg='#0a0a0a')
        input_frame.pack(fill=tk.X)
        
        # Text input
        self.text_input = tk.Entry(
            input_frame,
            font=('Arial', 12),
            bg='#1a1a1a',
            fg='#ffffff',
            insertbackground='#00ff88',
            relief=tk.FLAT
        )
        self.text_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.text_input.bind('<Return>', self.send_text_message)
        
        # Send button
        send_button = tk.Button(
            input_frame,
            text="Send",
            font=('Arial', 12, 'bold'),
            bg='#00ff88',
            fg='#000000',
            relief=tk.FLAT,
            padx=20,
            pady=8,
            command=self.send_text_message
        )
        send_button.pack(side=tk.RIGHT)
        
    def draw_brain_structure(self):
        """Draw the brain-like structure with neural network visualization"""
        self.brain_canvas.delete("all")
        
        width = self.brain_canvas.winfo_width()
        height = self.brain_canvas.winfo_height()
        
        if width <= 1 or height <= 1:
            return
            
        center_x = width // 2
        center_y = height // 2
        
        # Draw brain outline
        self.draw_brain_outline(center_x, center_y, width, height)
        
        # Draw neural network nodes
        self.draw_neural_nodes(center_x, center_y, width, height)
        
        # Draw connections
        self.draw_neural_connections(center_x, center_y, width, height)
        
        # Draw status lights
        self.draw_status_lights(center_x, center_y, width, height)
        
    def draw_brain_outline(self, center_x, center_y, width, height):
        """Draw the brain outline"""
        # Main brain shape
        brain_points = [
            center_x - width//3, center_y - height//4,
            center_x - width//4, center_y - height//3,
            center_x + width//4, center_y - height//3,
            center_x + width//3, center_y - height//4,
            center_x + width//3, center_y + height//4,
            center_x + width//4, center_y + height//3,
            center_x - width//4, center_y + height//3,
            center_x - width//3, center_y + height//4
        ]
        
        self.brain_canvas.create_polygon(
            brain_points,
            fill='#1a1a1a',
            outline='#333333',
            width=2
        )
        
    def draw_neural_nodes(self, center_x, center_y, width, height):
        """Draw neural network nodes"""
        node_radius = 8
        nodes = [
            (center_x - width//4, center_y - height//6),
            (center_x, center_y - height//4),
            (center_x + width//4, center_y - height//6),
            (center_x - width//6, center_y),
            (center_x, center_y),
            (center_x + width//6, center_y),
            (center_x - width//4, center_y + height//6),
            (center_x, center_y + height//4),
            (center_x + width//4, center_y + height//6)
        ]
        
        for i, (x, y) in enumerate(nodes):
            # Determine node color based on state
            if self.is_listening:
                color = '#00ff88'  # Green when listening
            elif self.is_speaking:
                color = '#ff8800'  # Orange when speaking
            elif self.is_processing:
                color = '#0088ff'  # Blue when processing
            else:
                color = '#444444'  # Gray when idle
                
            # Add pulsing effect
            pulse = math.sin(self.brain_pulse + i * 0.5) * 0.3 + 0.7
            radius = int(node_radius * pulse)
            
            self.brain_canvas.create_oval(
                x - radius, y - radius,
                x + radius, y + radius,
                fill=color,
                outline='#666666',
                width=1
            )
            
    def draw_neural_connections(self, center_x, center_y, width, height):
        """Draw connections between neural nodes"""
        nodes = [
            (center_x - width//4, center_y - height//6),
            (center_x, center_y - height//4),
            (center_x + width//4, center_y - height//6),
            (center_x - width//6, center_y),
            (center_x, center_y),
            (center_x + width//6, center_y),
            (center_x - width//4, center_y + height//6),
            (center_x, center_y + height//4),
            (center_x + width//4, center_y + height//6)
        ]
        
        # Draw connections
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                x1, y1 = nodes[i]
                x2, y2 = nodes[j]
                
                # Calculate distance
                distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                
                # Only draw connections for nearby nodes
                if distance < width // 3:
                    # Determine connection color and intensity
                    if self.is_listening or self.is_speaking or self.is_processing:
                        intensity = math.sin(self.brain_pulse + i + j) * 0.5 + 0.5
                        if self.is_listening:
                            color = f'#{int(0x00 + intensity * 0xff):02x}{int(0xff - intensity * 0x77):02x}{int(0x88 + intensity * 0x77):02x}'
                        elif self.is_speaking:
                            color = f'#{int(0xff - intensity * 0x77):02x}{int(0x88 + intensity * 0x77):02x}00'
                        else:
                            color = f'#00{int(0x88 + intensity * 0x77):02x}{int(0xff - intensity * 0x77):02x}'
                    else:
                        color = '#333333'
                        
                    self.brain_canvas.create_line(
                        x1, y1, x2, y2,
                        fill=color,
                        width=1
                    )
                    
    def draw_status_lights(self, center_x, center_y, width, height):
        """Draw status indicator lights"""
        # Listening light
        listening_color = '#00ff88' if self.is_listening else '#333333'
        self.brain_canvas.create_oval(
            center_x - width//2 + 20, center_y - height//2 + 20,
            center_x - width//2 + 40, center_y - height//2 + 40,
            fill=listening_color,
            outline='#666666',
            width=2
        )
        self.brain_canvas.create_text(
            center_x - width//2 + 30, center_y - height//2 + 50,
            text="LISTENING",
            fill=listening_color,
            font=('Arial', 8, 'bold')
        )
        
        # Speaking light
        speaking_color = '#ff8800' if self.is_speaking else '#333333'
        self.brain_canvas.create_oval(
            center_x + width//2 - 40, center_y - height//2 + 20,
            center_x + width//2 - 20, center_y - height//2 + 40,
            fill=speaking_color,
            outline='#666666',
            width=2
        )
        self.brain_canvas.create_text(
            center_x + width//2 - 30, center_y - height//2 + 50,
            text="SPEAKING",
            fill=speaking_color,
            font=('Arial', 8, 'bold')
        )
        
        # Processing light
        processing_color = '#0088ff' if self.is_processing else '#333333'
        self.brain_canvas.create_oval(
            center_x - 10, center_y + height//2 - 40,
            center_x + 10, center_y + height//2 - 20,
            fill=processing_color,
            outline='#666666',
            width=2
        )
        self.brain_canvas.create_text(
            center_x, center_y + height//2 - 10,
            text="PROCESSING",
            fill=processing_color,
            font=('Arial', 8, 'bold')
        )
        
    def start_animation(self):
        """Start the animation loop"""
        self.animation_running = True
        self.animate()
        
    def animate(self):
        """Animation loop"""
        if self.animation_running:
            self.brain_pulse += 0.1
            self.draw_brain_structure()
            self.root.after(50, self.animate)  # 20 FPS
            
    def check_queue(self):
        """Check for messages from other threads"""
        try:
            while True:
                message = self.message_queue.get_nowait()
                self.process_message(message)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.check_queue)
            
    def process_message(self, message):
        """Process messages from the queue"""
        msg_type = message.get('type')
        
        if msg_type == 'voice_state':
            self.update_voice_state(message.get('listening', False), 
                                  message.get('speaking', False),
                                  message.get('processing', False))
        elif msg_type == 'chat_message':
            self.add_chat_message(message.get('text', ''), 
                                message.get('sender', 'system'))
        elif msg_type == 'status':
            self.update_status(message.get('text', ''))
            
    def update_voice_state(self, listening=False, speaking=False, processing=False):
        """Update voice state indicators"""
        self.is_listening = listening
        self.is_speaking = speaking
        self.is_processing = processing
        
        # Update status label
        if listening:
            self.status_label.config(text="● Listening", fg='#00ff88')
        elif speaking:
            self.status_label.config(text="● Speaking", fg='#ff8800')
        elif processing:
            self.status_label.config(text="● Processing", fg='#0088ff')
        else:
            self.status_label.config(text="● Ready", fg='#00ff88')
            
    def add_chat_message(self, text, sender='system'):
        """Add a message to the chat display"""
        self.chat_display.config(state=tk.NORMAL)
        
        # Add timestamp
        timestamp = time.strftime("%H:%M:%S")
        self.chat_display.insert(tk.END, f"[{timestamp}] ", 'system')
        
        # Add message with appropriate tag
        if sender == 'user':
            self.chat_display.insert(tk.END, f"You: {text}\n", 'user')
        elif sender == 'assistant':
            self.chat_display.insert(tk.END, f"Bittu: {text}\n", 'assistant')
        else:
            self.chat_display.insert(tk.END, f"{text}\n", 'system')
            
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
        
    def update_status(self, text):
        """Update status message"""
        self.add_chat_message(text, 'system')
        
    def toggle_voice(self):
        """Toggle voice assistant on/off"""
        if self.on_voice_toggle:
            self.on_voice_toggle(not self.is_listening)
            
    def clear_chat(self):
        """Clear the chat display"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state=tk.DISABLED)
        
    def send_text_message(self, event=None):
        """Send a text message"""
        text = self.text_input.get().strip()
        if text:
            self.add_chat_message(text, 'user')
            self.text_input.delete(0, tk.END)
            
            if self.on_voice_command:
                self.on_voice_command(text)
                
    def show_settings(self):
        """Show settings dialog"""
        # Placeholder for settings dialog
        self.add_chat_message("Settings dialog would open here", 'system')
        
    def set_voice_command_callback(self, callback):
        """Set the callback for voice commands"""
        self.on_voice_command = callback
        
    def set_voice_toggle_callback(self, callback):
        """Set the callback for voice toggle"""
        self.on_voice_toggle = callback
        
    def queue_message(self, message):
        """Queue a message for thread-safe processing"""
        self.message_queue.put(message)
        
    def run(self):
        """Start the GUI"""
        self.root.mainloop()
        
    def destroy(self):
        """Destroy the GUI"""
        self.animation_running = False
        self.root.destroy()

if __name__ == "__main__":
    # Test the GUI
    app = VoiceAssistantGUI()
    app.run()
