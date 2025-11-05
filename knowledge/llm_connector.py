import os
import json
import datetime
import time
from dotenv import load_dotenv

load_dotenv()

# Global conversation memory
conversation_history = []
MAX_HISTORY = 10  # Keep last 10 exchanges
_llm_blocked_until: float | None = None  # epoch seconds; set after 429
_last_error: str | None = None

def ask_gpt(prompt):
    """
    Enhanced LLM connector with conversation memory and context awareness
    """
    global conversation_history
    prompt_lower = prompt.lower().strip()
    
    # Add current prompt to history
    conversation_history.append({"role": "user", "content": prompt, "timestamp": datetime.datetime.now().isoformat()})
    
    # Enhanced free responses with more context
    free_responses = {
        "hello": "Hello! I'm your personal AI assistant. How can I help you today?",
        "hi": "Hi there! I'm here to assist you. What would you like to do?",
        "how are you": "I'm doing great! I'm here and ready to help you with various tasks.",
        "what can you do": get_capabilities_response(),
        "help": get_help_response(),
        "capabilities": get_capabilities_response(),
        "time": "I don't have access to real-time clock, but you can check your system time or ask me to remind you about something!",
        "date": "I don't have access to the current date, but you can check your system calendar!",
        "weather": "To get weather information, try: 'weather in [city name]'",
        "thank you": "You're welcome! I'm happy to help.",
        "thanks": "You're welcome! Feel free to ask me anything else.",
        "bye": "Goodbye! Have a great day!",
        "goodbye": "Goodbye! Take care!",
        "who are you": "I'm your personal AI assistant! I can help you with tasks like opening apps, checking weather, setting reminders, coding, and much more.",
        "what's your name": "I'm your personal AI assistant! You can call me Assistant or whatever you prefer.",
        "clear memory": "clear_memory_command",
        "clear history": "clear_memory_command",
    }
    
    # Check for exact matches first
    if prompt_lower in free_responses:
        response = free_responses[prompt_lower]
        if response == "clear_memory_command":
            response = clear_conversation_memory()
        conversation_history.append({"role": "assistant", "content": response, "timestamp": datetime.datetime.now().isoformat()})
        return response
    
    # Check for partial matches
    for key, response in free_responses.items():
        if key in prompt_lower:
            conversation_history.append({"role": "assistant", "content": response, "timestamp": datetime.datetime.now().isoformat()})
            return response
    
    # Try OpenAI if API key is available (and not blocked by recent 429)
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    api_org = os.getenv("OPENAI_ORG")
    model = os.getenv("OPENAI_MODEL") or "gpt-3.5-turbo"
    global _llm_blocked_until, _last_error
    now = time.time()
    if os.getenv("OPENAI_FORCE_OFFLINE") == "1":
        return _offline_fallback(prompt)
    if _llm_blocked_until and now < _llm_blocked_until:
        return _offline_fallback(prompt)
    if api_key and api_key != "your_openai_api_key_here":
        try:
            from openai import OpenAI
            client_kwargs = {"api_key": api_key}
            if api_base:
                client_kwargs["base_url"] = api_base
            if api_org:
                client_kwargs["organization"] = api_org
            client = OpenAI(**client_kwargs)

            messages = [{"role": "system", "content": get_system_prompt()}]
            recent_history = conversation_history[-10:]
            for msg in recent_history:
                if msg["role"] in ["user", "assistant"]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )

            ai_response = response.choices[0].message.content.strip()
            conversation_history.append({"role": "assistant", "content": ai_response, "timestamp": datetime.datetime.now().isoformat()})
            if len(conversation_history) > MAX_HISTORY * 2:
                conversation_history = conversation_history[-MAX_HISTORY * 2:]
            _last_error = None
            return ai_response
        except Exception as e:
            msg = str(e)
            _last_error = msg
            # Cooldown on 429 errors to prevent repeated spam
            if "429" in msg or "insufficient_quota" in msg or "quota" in msg.lower():
                _llm_blocked_until = time.time() + 600  # 10 minutes
            return _offline_fallback(prompt)
    
    # Enhanced fallback responses with context
    fallback_responses = [
        f"I understand you're asking about: '{prompt}'. While I don't have a specific answer for that, I can help you with opening applications, checking weather, setting reminders, coding tasks, or answering general questions.",
        f"That's an interesting question about '{prompt}'. I'm designed to help with practical tasks like opening apps, weather info, reminders, and coding. Feel free to ask me about those!",
        f"I'm not sure about '{prompt}', but I can definitely help you with opening applications, getting weather updates, setting reminders, or coding tasks. What would you like to try?",
        f"'{prompt}' is an interesting topic! While I may not have specific information about that, I can help you with many other tasks. Try asking me to open apps, check weather, or help with coding!",
    ]
    
    import random
    response = random.choice(fallback_responses)
    conversation_history.append({"role": "assistant", "content": response, "timestamp": datetime.datetime.now().isoformat()})
    return response


def _offline_fallback(prompt: str) -> str:
    # Minimal offline answers for common dev/CS topics to avoid LLM 429 noise
    p = prompt.lower().strip()
    offline_qa = {
        "oops": "OOP (Object-Oriented Programming) is a paradigm based on objects and classes, supporting encapsulation, inheritance, polymorphism, and abstraction.",
        "polymorphism": "Polymorphism lets different types respond to the same interface (method) in type-specific ways—e.g., method overriding.",
        "inheritance": "Inheritance lets a class derive from another, reusing and extending behavior.",
        "encapsulation": "Encapsulation bundles data and methods, exposing a minimal public interface and hiding implementation details.",
        "abstraction": "Abstraction focuses on essential characteristics, hiding unnecessary details behind clear interfaces.",
    }
    for k, v in offline_qa.items():
        if k in p:
            return v
    # Otherwise show friendly message without large error
    return (
        "I'm currently offline for AI answers. I can still help with apps, system controls, files, timers, and more. "
        "You can set OPENAI_API_KEY and restart to enable full AI answers."
    )


def get_llm_status() -> str:
    key = os.getenv("OPENAI_API_KEY")
    masked = (key[:3] + "..." + key[-4:]) if key and key != "your_openai_api_key_here" else "(not set)"
    base = os.getenv("OPENAI_API_BASE") or "(default)"
    model = os.getenv("OPENAI_MODEL") or "gpt-3.5-turbo"
    org = os.getenv("OPENAI_ORG") or "(none)"
    cooldown = 0
    if _llm_blocked_until:
        cooldown = max(0, int(_llm_blocked_until - time.time()))
    status = [
        f"API Key: {masked}",
        f"Base URL: {base}",
        f"Model: {model}",
        f"Org: {org}",
        f"Cooldown (s): {cooldown}",
    ]
    if _last_error:
        status.append(f"Last error: {_last_error}")
    return "\n".join(status)


def set_offline_mode(enable: bool) -> str:
    global _llm_blocked_until
    if enable:
        os.environ["OPENAI_FORCE_OFFLINE"] = "1"
        _llm_blocked_until = time.time() + 3600  # 1 hour convenience
        return "LLM offline mode enabled."
    else:
        if "OPENAI_FORCE_OFFLINE" in os.environ:
            del os.environ["OPENAI_FORCE_OFFLINE"]
        _llm_blocked_until = None
        return "LLM offline mode disabled."

def get_system_prompt():
    """Get the system prompt for the AI assistant"""
    return """You are a helpful personal AI assistant with the following capabilities:

1. **Application Management**: Open web apps (YouTube, Google, Gmail, GitHub, etc.), desktop apps (VS Code, Notepad, Calculator, etc.), and system utilities
2. **Weather Information**: Get current weather for any city
3. **Reminders**: Set timed reminders for tasks
4. **File Operations**: Create files, folders, navigate directories, list files
5. **System Commands**: Execute system commands safely
6. **Coding Assistance**: Help with file creation, Python scripts, and basic coding tasks
7. **General Conversation**: Answer questions and provide helpful information

You should be helpful, friendly, and focus on practical assistance. Always prioritize user safety when executing system commands."""

def get_capabilities_response():
    """Get a comprehensive capabilities response"""
    return """🤖 **Personal AI Assistant Capabilities**

🌐 **Web & Apps**: Open YouTube, Google, Gmail, GitHub, Stack Overflow, Reddit, Netflix, Spotify
💻 **Development**: VS Code, PyCharm, Sublime Text, Atom, Terminal
📝 **System Tools**: Notepad, Calculator, File Explorer, Task Manager, Settings
🎮 **Entertainment**: Steam, Discord
📄 **Office**: Word, Excel, PowerPoint

🌤️ **Weather**: Get current weather for any city
⏰ **Reminders**: Set timed reminders for tasks
📁 **File Operations**: Create files/folders, navigate directories, list files
💻 **Coding**: Create Python scripts, help with file operations
⚙️ **System Commands**: Execute safe system commands
💬 **Conversation**: Answer questions and provide assistance

Try commands like:
- 'open youtube' or 'launch vs code'
- 'weather in London' 
- 'remind me to call mom in 30 minutes'
- 'create file test.txt' or 'list files'
- 'run python --version'"""

def get_help_response():
    """Get a comprehensive help response"""
    return """🆘 **Help - Available Commands**

**🌐 Opening Applications:**
- `open youtube` - Open YouTube
- `launch vs code` - Open VS Code
- `start calculator` - Open Calculator
- `run terminal` - Open Terminal

**🌤️ Weather:**
- `weather in London` - Get weather for London
- `weather in New York` - Get weather for New York

**⏰ Reminders:**
- `remind me to call mom in 30 minutes`
- `remind me to check email in 1 hour`

**📁 File Operations:**
- `create file filename.txt` - Create a new file
- `create folder myfolder` - Create a new folder
- `list files` - Show files in current directory
- `cd Documents` - Navigate to Documents folder

**💻 Coding & System:**
- `create Python script` - Create a Python file
- `run dir` - Execute system command
- `execute python --version` - Check Python version

**💬 General:**
- Ask me anything! I can help with questions and conversation
- Type `exit` or `quit` to close the assistant"""

def clear_conversation_memory():
    """Clear the conversation memory"""
    global conversation_history
    conversation_history = []
    return "✅ Conversation memory cleared! Starting fresh."

def get_conversation_history():
    """Get the current conversation history"""
    if not conversation_history:
        return "No conversation history yet."
    
    history_text = "📝 **Recent Conversation:**\n"
    for i, msg in enumerate(conversation_history[-6:], 1):  # Show last 6 messages
        role = "🧑 You" if msg["role"] == "user" else "🤖 Assistant"
        history_text += f"{i}. {role}: {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}\n"
    
    return history_text
