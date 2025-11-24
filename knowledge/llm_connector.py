import os
import json
import datetime
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

# Global conversation memory
# Keep a larger rolling window so follow‑up questions can use richer context.
conversation_history = []
MAX_HISTORY = 20  # Keep last 20 exchanges (user + assistant messages)
_external_context_provider: Optional[Callable[[], List[Dict[str, str]]]] = None
_history_path = Path("data/conversation_history.json")
_llm_blocked_until: float | None = None  # epoch seconds; set after 429
_last_error: str | None = None
_last_llm_label: str = "unknown"

def _ensure_history_loaded() -> None:
    global conversation_history
    try:
        if not _history_path.exists():
            _history_path.parent.mkdir(parents=True, exist_ok=True)
            _history_path.write_text("[]", encoding="utf-8")
        data = json.loads(_history_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            conversation_history = data[-MAX_HISTORY:]
    except Exception:
        conversation_history = []

def _save_history() -> None:
    try:
        _history_path.parent.mkdir(parents=True, exist_ok=True)
        trimmed = conversation_history[-MAX_HISTORY:]
        _history_path.write_text(json.dumps(trimmed, indent=2), encoding="utf-8")
    except Exception:
        pass

def _append_history(role: str, content: str) -> None:
    conversation_history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.datetime.now().isoformat()
    })
    # Trim and persist
    if len(conversation_history) > MAX_HISTORY * 2:
        recent = conversation_history[-MAX_HISTORY:]
        conversation_history.clear()
        conversation_history.extend(recent)
    _save_history()

def _set_last_llm_label(label: str) -> None:
    global _last_llm_label
    _last_llm_label = label

_ensure_history_loaded()

def register_context_provider(provider: Optional[Callable[[], List[Dict[str, str]]]]) -> None:
    """Allow other modules (e.g., the brain) to provide recent context for LLM prompts."""
    global _external_context_provider
    _external_context_provider = provider

def get_last_llm_label() -> str:
    return _last_llm_label

def ask_gpt(prompt):
    """
    Enhanced LLM connector with conversation memory and context awareness
    """
    global conversation_history
    prompt_lower = prompt.lower().strip()
    
    # Add current prompt to history
    _append_history("user", prompt)
    
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
        _append_history("assistant", response)
        return response
    
    # Check for partial matches
    for key, response in free_responses.items():
        if key in prompt_lower:
            _append_history("assistant", response)
            return response
    
    # Route to configured backend: ollama (default), openai, or transformers
    # Defaulting to Ollama ensures everything runs through the local Qwen3 model
    # unless you explicitly override LLM_BACKEND.
    backend = (os.getenv("LLM_BACKEND") or "ollama").lower()
    global _llm_blocked_until, _last_error
    now = time.time()
    if os.getenv("OPENAI_FORCE_OFFLINE") == "1":
        return _offline_fallback(prompt)
    if _llm_blocked_until and now < _llm_blocked_until:
        return _offline_fallback(prompt)

    try:
        if backend == "ollama":
            return _chat_with_ollama(prompt)
        elif backend == "transformers":
            return _chat_with_transformers(prompt)
        else:
            return _chat_with_openai(prompt)
    except Exception as e:
        msg = str(e)
        _last_error = msg
        if "429" in msg or "insufficient_quota" in msg or "quota" in msg.lower():
            _llm_blocked_until = time.time() + 600
        # Provide actionable backend-specific guidance
        guidance = _backend_unavailable_message(backend, msg)
        return guidance or _offline_fallback(prompt)
    
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
    backend = (os.getenv("LLM_BACKEND") or "ollama").lower()
    if backend == "ollama":
        model = os.getenv("OLLAMA_MODEL") or "qwen3-coder:30b"
        base = os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434"
    elif backend == "transformers":
        model = os.getenv("TRANSFORMERS_MODEL") or "mistralai/Mistral-7B-Instruct-v0.2"
        base = "(local transformers)"
    cooldown = 0
    if _llm_blocked_until:
        cooldown = max(0, int(_llm_blocked_until - time.time()))
    status = [
        f"Backend: {backend}",
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
    return """You are Bittu, a professional, warm, and creative personal AI assistant.

Core behavior:
- Be concise, human-like, and proactive. Offer helpful follow-ups when appropriate.
- Keep outputs clear and skimmable. Use short paragraphs and light emoji only when it adds clarity.
- Never fabricate actions; confirm before any destructive/system operations.
- If you include code or command output, format it properly and keep it minimal.

Capabilities:
1) Open apps and websites
2) Weather, reminders, file ops, navigation
3) Safe system commands
4) Coding assistance and explanations
5) General Q&A

Tone:
- Professional, friendly, confident. Avoid over-apologies. Stay on-topic.
"""

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
    _save_history()
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


def get_llm_help() -> str:
    backend = (os.getenv("LLM_BACKEND") or "ollama").lower()
    if backend == "ollama":
        return (
            "🧩 LLM Help (Ollama)\n\n"
            "- Install Ollama (Windows): winget install Ollama.Ollama or download from https://ollama.com\n"
            "- Start service: 'ollama serve' (leave it running)\n"
            "- Pull Qwen model: 'ollama pull qwen3-coder:30b'\n"
            "- In your shell (PowerShell): $env:LLM_BACKEND=\"ollama\"; $env:OLLAMA_MODEL=\"qwen3-coder:30b\"\n"
            "- Verify: 'llm status' and 'llm test'"
        )
    elif backend == "transformers":
        return (
            "🧩 LLM Help (Transformers local)\n\n"
            "- pip install transformers accelerate torch\n"
            "- Set model: setx TRANSFORMERS_MODEL \"mistralai/Mistral-7B-Instruct-v0.2\"\n"
            "- Select backend: setx LLM_BACKEND \"transformers\"\n"
            "- Optional GPU: setx TRANSFORMERS_DEVICE \"auto\"\n"
            "- Verify: 'llm status' and 'llm test'"
        )
    else:
        return (
            "🧩 LLM Help (OpenAI)\n\n"
            "- Set API key: setx OPENAI_API_KEY \"sk-...\"\n"
            "- Optional: OPENAI_MODEL, OPENAI_API_BASE\n"
            "- Verify: 'llm status' and 'llm test'"
        )


def _backend_unavailable_message(backend: str, error_message: str) -> str:
    if backend == "ollama":
        return (
            "❌ Ollama backend not reachable. Please install/start Ollama and pull a model.\n\n"
            "Steps (Windows):\n"
            "1) Install: winget install Ollama.Ollama (or download from https://ollama.com)\n"
            "2) Start service: 'ollama serve'\n"
            "3) Pull a model: 'ollama pull qwen3-coder:30b'\n"
            "4) In this shell: $env:LLM_BACKEND=\"ollama\"; $env:OLLAMA_MODEL=\"qwen3-coder:30b\"\n"
            f"Details: {error_message}"
        )
    if backend == "transformers":
        return (
            "❌ Transformers backend not available. Ensure dependencies and model are set.\n\n"
            "Steps:\n"
            "1) pip install transformers accelerate torch\n"
            "2) setx LLM_BACKEND \"transformers\"\n"
            "3) setx TRANSFORMERS_MODEL \"mistralai/Mistral-7B-Instruct-v0.2\"\n"
            f"Details: {error_message}"
        )
    # For OpenAI or unknown, fall back silently
    return ""


# --- Backends ---
def _build_messages(prompt: str):
    messages = [{"role": "system", "content": get_system_prompt()}]
    recent_history = conversation_history[-10:]
    for msg in recent_history:
        if msg["role"] in ["user", "assistant"]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    if _external_context_provider:
        try:
            context_snippets = _external_context_provider() or []
            if context_snippets:
                summary_lines = []
                for entry in context_snippets[-3:]:
                    command = entry.get("command", "").strip()
                    response = entry.get("response", "").strip()
                    if not command or not response:
                        continue
                    response_short = response[:180]
                    summary_lines.append(f"- User earlier: '{command}' → Assistant: '{response_short}'")
                if summary_lines:
                    context_text = (
                        "Recent assistant context (last few commands):\n" +
                        "\n".join(summary_lines) +
                        "\nUse this context when answering follow-up questions."
                    )
                    messages.append({"role": "system", "content": context_text})
        except Exception:
            pass
    messages.append({"role": "user", "content": prompt})
    return messages


def _record_and_trim(ai_response: str) -> str:
    _append_history("assistant", ai_response)
    return ai_response


def _chat_with_openai(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    api_org = os.getenv("OPENAI_ORG")
    model = os.getenv("OPENAI_MODEL") or "gpt-3.5-turbo"
    if not api_key or api_key == "your_openai_api_key_here":
        raise RuntimeError("OpenAI not configured")
    from openai import OpenAI
    client_kwargs = {"api_key": api_key}
    if api_base:
        client_kwargs["base_url"] = api_base
    if api_org:
        client_kwargs["organization"] = api_org
    client = OpenAI(**client_kwargs)
    messages = _build_messages(prompt)
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=500
    )
    ai_response = response.choices[0].message.content.strip()
    _set_last_llm_label(f"openai:{model}")
    return _record_and_trim(ai_response)


def _chat_with_ollama(prompt: str) -> str:
    # Requires Ollama running locally: https://ollama.com
    # Default model: "qwen3-coder:30b"
    import requests
    base_url = os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434"
    model = os.getenv("OLLAMA_MODEL") or "qwen3-coder:30b"
    # Build chat format expected by Ollama
    messages = _build_messages(prompt)
    # Convert OpenAI-like messages to Ollama format (same keys are accepted by /api/chat)
    resp = requests.post(
        f"{base_url}/api/chat",
        json={
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 1024}
        },
        timeout=60
    )
    resp.raise_for_status()
    data = resp.json()
    # Ollama returns messages list or a single message depending on version; try common fields
    if "message" in data and isinstance(data["message"], dict):
        ai_response = data["message"].get("content", "").strip()
    elif "choices" in data and data["choices"]:
        ai_response = data["choices"][0].get("message", {}).get("content", "").strip()
    else:
        # Fallback aggregate
        ai_response = (data.get("response") or "").strip()
    if not ai_response:
        raise RuntimeError("Empty response from Ollama")
    _set_last_llm_label(f"ollama:{model}")
    return _record_and_trim(ai_response)


_transformers_pipeline = None


def _chat_with_transformers(prompt: str) -> str:
    # Local inference using transformers; first call lazily loads model.
    global _transformers_pipeline
    model_id = os.getenv("TRANSFORMERS_MODEL") or "mistralai/Mistral-7B-Instruct-v0.2"
    device = os.getenv("TRANSFORMERS_DEVICE") or "auto"  # e.g., "cuda", "cpu", or "auto"
    max_new_tokens = int(os.getenv("TRANSFORMERS_MAX_NEW_TOKENS") or 512)
    temperature = float(os.getenv("TRANSFORMERS_TEMPERATURE") or 0.7)

    if _transformers_pipeline is None:
        # Lazy import to avoid heavy import cost on startup
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        tok = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=None,
            device_map="auto" if device == "auto" else None
        )
        _transformers_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tok,
            device_map="auto" if device == "auto" else None
        )

    # Simple chat template: include brief history and system prompt
    messages = _build_messages(prompt)
    # Convert to a single prompt; many instruct models expect chat-style formatting
    sys = messages[0]["content"] if messages and messages[0]["role"] == "system" else ""
    convo = []
    if sys:
        convo.append(f"[SYSTEM]\n{sys}\n[/SYSTEM]")
    for m in messages[1:]:
        role = "USER" if m["role"] == "user" else "ASSISTANT"
        convo.append(f"[{role}]\n{m['content']}\n[/{role}]")
    final_prompt = "\n".join(convo) + "\n[ASSISTANT]\n"

    out = _transformers_pipeline(
        final_prompt,
        do_sample=True,
        temperature=temperature,
        max_new_tokens=max_new_tokens,
        eos_token_id=None
    )
    text = out[0]["generated_text"]
    # Extract the text after the last [ASSISTANT] tag
    split_tag = "[ASSISTANT]\n"
    ai_response = text.split(split_tag)[-1].strip()
    _set_last_llm_label(f"transformers:{model_id}")
    return _record_and_trim(ai_response)


def stylize_response(command: str, raw_text: str) -> str:
    """Rewrite a tool/raw response to a professional, human-like tone using the active backend.

    Honors env toggles:
    - LLM_PERSONA_ENHANCE=0 disables stylization (returns raw_text)
    - OPENAI_FORCE_OFFLINE=1 disables stylization (returns raw_text)
    """
    if os.getenv("OPENAI_FORCE_OFFLINE") == "1":
        return raw_text
    if os.getenv("LLM_PERSONA_ENHANCE") == "0":
        return raw_text
    backend = (os.getenv("LLM_BACKEND") or "openai").lower()
    try:
        system = (
            "You refine assistant outputs. Keep them concise, professional, friendly, and human-like. "
            "Preserve factual content and any critical details. If the text contains command outputs or file lists, keep them intact. "
            "Do not invent steps. Prefer short, skimmable phrasing."
        )
        user_msg = (
            f"User command: {command}\n\n"
            f"Raw assistant text to refine:\n{raw_text}"
        )
        # Build one-off messages without polluting main conversation too much
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ]
        # Temporarily bypass conversation history for deterministic rewrites
        if backend == "ollama":
            import requests
            base_url = os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434"
            model = os.getenv("OLLAMA_MODEL") or "qwen3-coder:30b"
            resp = requests.post(
                f"{base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False, "options": {"temperature": 0.2, "num_predict": 512}},
                timeout=45,
            )
            resp.raise_for_status()
            data = resp.json()
            refined = (
                (data.get("message") or {}).get("content")
                or (data.get("choices") or [{}])[0].get("message", {}).get("content")
                or data.get("response")
                or ""
            )
            return refined.strip() or raw_text
        elif backend == "transformers":
            # Simple local generation using same pipeline
            global _transformers_pipeline
            if _transformers_pipeline is None:
                # Lazily init with default model if needed
                from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
                model_id = os.getenv("TRANSFORMERS_MODEL") or "mistralai/Mistral-7B-Instruct-v0.2"
                tok = AutoTokenizer.from_pretrained(model_id)
                model = AutoModelForCausalLM.from_pretrained(model_id)
                _transformers_pipeline = pipeline("text-generation", model=model, tokenizer=tok)
            # Convert to a simple prompt
            prompt = (
                "[SYSTEM]\n" + system + "\n[/SYSTEM]\n[USER]\n" + user_msg + "\n[/USER]\n[ASSISTANT]\n"
            )
            out = _transformers_pipeline(prompt, do_sample=True, temperature=0.5, max_new_tokens=240)
            text = out[0]["generated_text"]
            refined = text.split("[ASSISTANT]\n")[-1].strip()
            return refined or raw_text
        else:
            # OpenAI path
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key or api_key == "your_openai_api_key_here":
                return raw_text
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL") or "gpt-3.5-turbo",
                messages=messages,
                temperature=0.5,
                max_tokens=300,
            )
            refined = response.choices[0].message.content.strip()
            return refined or raw_text
    except Exception:
        return raw_text


def self_test() -> str:
    """Run a lightweight self-test of the configured LLM backend.

    - openai: verifies API key presence by performing a short completion against a harmless prompt
    - ollama: checks server health and model availability, then does a tiny chat
    - transformers: verifies library/model import path and generates a very short response
    """
    backend = (os.getenv("LLM_BACKEND") or "openai").lower()
    try:
        if backend == "ollama":
            import requests
            base_url = os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434"
            # Health/model list
            info = requests.get(f"{base_url}/api/tags", timeout=10)
            info.raise_for_status()
            models = [m.get("name") for m in (info.json().get("models") or [])]
            model = os.getenv("OLLAMA_MODEL") or "qwen3-coder:30b"
            if model not in models:
                # Still attempt a chat; Ollama can pull on demand if configured
                pass
            small = _chat_with_ollama("Say 'ok' only.")
            return f"✅ Ollama OK (model={model}). Sample: {small[:60]}"
        elif backend == "transformers":
            # Try an ultra-short generation to validate pipeline
            resp = _chat_with_transformers("Say 'ok' only.")
            return f"✅ Transformers OK (model={os.getenv('TRANSFORMERS_MODEL') or 'default'}). Sample: {resp[:60]}"
        else:
            # OpenAI
            resp = _chat_with_openai("Say 'ok' only.")
            return f"✅ OpenAI OK (model={os.getenv('OPENAI_MODEL') or 'gpt-3.5-turbo'}). Sample: {resp[:60]}"
    except Exception as e:
        return f"❌ LLM self-test failed ({backend}): {e}"
