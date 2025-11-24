# interface/cli_interface.py
import os
import sys
from datetime import datetime
try:
    from interface.web_server import emit_log
except Exception:
    def emit_log(_msg: str) -> None:
        return

def get_input():
    """Get user input with enhanced formatting"""
    try:
        # Get current directory for context
        current_dir = os.getcwd()
        dir_name = os.path.basename(current_dir)
        
        # Create a nice prompt
        prompt = f"🧑 You ({dir_name}): "
        return input(prompt)
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except EOFError:
        print("\n👋 Goodbye!")
        sys.exit(0)

def show_output(text):
    """Display assistant output with enhanced formatting"""
    print("\n" + "="*60)
    print("🤖 Assistant:")
    print("-" * 20)
    
    # Format the output nicely
    lines = text.split('\n')
    for line in lines:
        if line.strip():
            print(f"   {line}")
        else:
            print()
    
    print("="*60)
    print()
    try:
        emit_log(text)
    except Exception:
        pass

def show_welcome():
    """Show welcome message with current status"""
    print("\n" + "="*80)
    print("🤖 PERSONAL AI ASSISTANT")
    print("="*80)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Current directory: {os.getcwd()}")
    print("💡 Type 'help' for available commands or 'exit' to quit")
    print("="*80)
    print()

def show_goodbye():
    """Show goodbye message"""
    print("\n" + "="*60)
    print("👋 Thank you for using Personal AI Assistant!")
    msg = f"📅 Session ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    print(msg)
    try:
        emit_log("Session ended")
    except Exception:
        pass
    print("="*60)

def show_error(error_message):
    """Show error messages with formatting"""
    print("\n" + "❌" + "="*58)
    print("🚨 ERROR:")
    print("-" * 10)
    print(f"   {error_message}")
    print("❌" + "="*58)
    print()
    try:
        emit_log(f"ERROR: {error_message}")
    except Exception:
        pass

def show_success(success_message):
    """Show success messages with formatting"""
    print("\n" + "✅" + "="*58)
    print("🎉 SUCCESS:")
    print("-" * 10)
    print(f"   {success_message}")
    print("✅" + "="*58)
    print()
    try:
        emit_log(success_message)
    except Exception:
        pass

def format_code_block(code, language="text"):
    """Format code blocks nicely"""
    print(f"\n💻 {language.upper()} CODE:")
    print("-" * 20)
    lines = code.split('\n')
    for i, line in enumerate(lines, 1):
        print(f"{i:3d}| {line}")
    print("-" * 20)
    try:
        emit_log(f"CODE [{language}]:\n{code}")
    except Exception:
        pass

def show_loading(message="Processing..."):
    """Show loading indicator"""
    import time
    import threading
    
    def loading_animation():
        chars = "|/-\\"
        i = 0
        while not loading_stop:
            print(f"\r⏳ {message} {chars[i % len(chars)]}", end="", flush=True)
            time.sleep(0.1)
            i += 1
    
    loading_stop = False
    loading_thread = threading.Thread(target=loading_animation, daemon=True)
    loading_thread.start()
    
    return loading_stop

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')
    try:
        emit_log("Screen cleared")
    except Exception:
        pass

def show_help_menu():
    """Show interactive help menu"""
    print("\n" + "="*80)
    print("🆘 HELP MENU - Personal AI Assistant")
    print("="*80)
    print()
    print("🌐 OPENING APPLICATIONS:")
    print("   • open youtube          - Open YouTube")
    print("   • launch vs code        - Open VS Code")
    print("   • start calculator      - Open Calculator")
    print("   • run terminal          - Open Terminal")
    print()
    print("🌤️ WEATHER INFORMATION:")
    print("   • weather in London     - Get weather for London")
    print("   • weather in New York   - Get weather for New York")
    print()
    print("⏰ REMINDERS:")
    print("   • remind me to call mom in 30 minutes")
    print("   • remind me to check email in 1 hour")
    print()
    print("📁 FILE OPERATIONS:")
    print("   • create file test.txt  - Create a new file")
    print("   • create folder myfolder - Create a new folder")
    print("   • read file test.txt    - Read file contents")
    print("   • write to file test.txt with text 'content' - Write to file")
    print("   • append to file test.txt with text 'content' - Append to file")
    print("   • delete file test.txt  - Delete a file")
    print("   • copy file source.txt to dest.txt - Copy file")
    print("   • move file old.txt to new.txt - Move/rename file")
    print("   • search in file test.txt for 'text' - Search in file")
    print("   • file info test.txt    - Get file information")
    print("   • list files            - Show files in current directory")
    print("   • list files detailed   - Detailed file listing")
    print("   • cd Documents          - Navigate to Documents folder")
    print()
    print("💻 CODING & SYSTEM:")
    print("   • create Python script  - Create a Python file")
    print("   • run dir               - Execute system command")
    print("   • execute python --version - Check Python version")
    print()
    print("💬 GENERAL:")
    print("   • Ask me anything! I can help with questions and conversation")
    print("   • Type 'exit' or 'quit' to close the assistant")
    print("="*80)
    print()
