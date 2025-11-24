# core/brain.py
import re
import os
import subprocess
import time
from skills import open_apps, weather_info, reminder_manager, coding_assistant, system_controls
from skills import automation, code_generator, email_writer
from skills import file_operations
from skills.path_utils import (
    get_base_output_dir,
    resolve_access_path,
    resolve_directory_path,
    resolve_output_path,
)
from knowledge.llm_connector import ask_gpt, get_llm_status, register_context_provider, set_offline_mode
from knowledge.llm_connector import self_test as llm_self_test
from knowledge.llm_connector import get_llm_help
from knowledge.llm_connector import stylize_response
from core.classifier import classify_task, TaskType
from llm.ollama_client import OllamaClient, OllamaClientError

# Initialize learning system
_learning_system = None
_context_manager = None
_preference_manager = None
_command_counter = 0
_AUTO_INSIGHT_INTERVAL = max(0, int(os.getenv("LEARNING_INSIGHT_INTERVAL", "8")))

def _init_learning_system():
    """Initialize learning system components"""
    global _learning_system, _context_manager, _preference_manager
    
    if _learning_system is None:
        try:
            from knowledge.memory_db import MemoryDB
            from knowledge.learning_engine import LearningEngine
            from knowledge.preference_manager import PreferenceManager
            from knowledge.context_manager import ContextManager
            
            memory_db = MemoryDB()
            _learning_system = LearningEngine(memory_db)
            _preference_manager = PreferenceManager(memory_db)
            _context_manager = ContextManager(memory_db)
            register_context_provider(_recent_context_snapshot)
            print("✅ Learning system initialized")
        except Exception as e:
            # Silently fail - learning is optional
            import traceback
            print(f"⚠️ Learning system disabled (non-fatal): {e}")
            traceback.print_exc()
            _learning_system = None
            _preference_manager = None
            _context_manager = None

# Initialize learning system (non-blocking, lazy initialization)
_learning_initialized = False
_general_llm_client: OllamaClient | None = None


def _debug_route(category: str, detail: str = "", task: TaskType | None = None) -> None:
    """Lightweight debug logger to show how commands are classified and routed."""
    try:
        base = f"🧭 Route: {category}"
        if task is not None:
            base += f" | TaskType: {task.value}"
        if detail:
            base += f" | Detail: {detail}"
        print(base)
    except Exception:
        # Never let logging break command handling
        pass

def _ensure_learning_initialized():
    """Lazy initialization of learning system"""
    global _learning_initialized
    if not _learning_initialized:
        try:
            _init_learning_system()
            _learning_initialized = True
        except Exception:
            _learning_initialized = True  # Mark as attempted even if failed
            pass

def _recent_context_snapshot(limit: int = 3):
    """Return the most recent command/response pairs for contextual LLM prompts."""
    if not _context_manager:
        return []
    try:
        context = _context_manager.get_context()
        recent = context.get("recent_commands") or []
        if limit > 0:
            return recent[-limit:]
        return recent
    except Exception:
        return []

def _recent_conversation_text(limit: int = 5) -> str:
    if not _context_manager:
        return "I don't have any recent conversation history yet."
    try:
        recent = list(_context_manager.conversation_history)[-limit:]
        if not recent:
            return "I don't have any recent conversation history yet."
        lines = []
        for entry in recent:
            cmd = entry.get("command", "").strip()
            resp = (entry.get("response", "") or "").strip()
            snippet = resp.replace("\n", " ")[:160]
            lines.append(f"• You: {cmd}\n  Me: {snippet}")
        return "📝 Recent discussion recap:\n" + "\n".join(lines)
    except Exception as exc:
        return f"⚠️ Couldn't fetch recent conversation: {exc}"

def _augment_command_with_context(command: str) -> str:
    """Inject recent command/response pairs so LLMs can answer follow-ups more accurately."""
    snapshots = _recent_context_snapshot()
    if not snapshots:
        return command
    lines = []
    for entry in snapshots:
        cmd = entry.get("command", "").strip()
        resp = (entry.get("response", "") or "").strip()
        if not cmd or not resp:
            continue
        resp_short = resp.replace("\n", " ")[:180]
        lines.append(f"- Previous command: '{cmd}' → Assistant reply: '{resp_short}'")
    if not lines:
        return command
    return (
        f"{command}\n\nRecent context you can reference:\n" +
        "\n".join(lines)
    )

def _ask_with_context(command: str) -> str:
    """Wrapper around ask_gpt that injects recent context for better continuity."""
    contextual_command = _augment_command_with_context(command)
    return ask_gpt(contextual_command)

def _get_general_llm_client() -> OllamaClient:
    """Get (or create) the shared Ollama client for general AI answers."""
    global _general_llm_client
    if _general_llm_client is None:
        _general_llm_client = OllamaClient()
    return _general_llm_client

def _route_ai_agents(command: str) -> str | None:
    """Classify commands and route them to specialized agents."""
    if not command.strip():
        return None

    task = classify_task(command)

    if task == TaskType.CODE_GENERATION:
        return code_generator.handle(command)
    if task == TaskType.EMAIL_WRITING:
        return email_writer.handle(command)
    if task == TaskType.GENERAL_AI:
        return _general_ai_response(command)
    return None

def _needs_special_ai_task(command: str) -> bool:
    """Return True if the command should be handled by a specialized AI agent."""
    task = classify_task(command)
    return task in (TaskType.CODE_GENERATION, TaskType.EMAIL_WRITING)

def _general_ai_response(command: str) -> str | None:
    """Use the default general model for conversational replies with improved intelligence."""
    try:
        client = _get_general_llm_client()
        # Enhanced prompt for better, faster responses
        contextual_command = _augment_command_with_context(command)
        enhanced_prompt = f"""You are Bittu, an intelligent personal AI assistant. Answer the following question clearly, accurately, and comprehensively.

Question: {contextual_command}

Provide a complete, informative answer. If the question asks "what is X" or "explain Y", give a detailed explanation covering:
1. Main definition/concept
2. Key features/characteristics
3. Practical applications or examples (if relevant)
4. Brief context or background (if helpful)

Answer:"""
        
        # Use generate directly for better control - optimized for speed
        response = client.generate(
            prompt=enhanced_prompt,
            system="You are Bittu, a helpful, intelligent personal AI assistant. You provide accurate, comprehensive answers while being concise when needed.",
            temperature=0.2,
            max_tokens=1024
        )
        return response.strip() if response else None
    except OllamaClientError as exc:
        print(f"⚠️ Ollama general model error: {exc}")
        # Fallback to ask_gpt with context
        try:
            return _ask_with_context(command)
        except Exception:
            return None
    except Exception as exc:
        print(f"⚠️ General AI agent error: {exc}")
        # Fallback to ask_gpt
        try:
            return _ask_with_context(command)
        except Exception:
            return None

def _learning_insight() -> str:
    if not _learning_system or _AUTO_INSIGHT_INTERVAL <= 0:
        return ""
    if _command_counter == 0 or (_command_counter % _AUTO_INSIGHT_INTERVAL) != 0:
        return ""
    try:
        habits = _learning_system.analyze_user_habits()
        most_common = habits.get("most_common_commands") or []
        preferences = habits.get("preferences") or []
        pieces = []
        if most_common:
            cmd = most_common[0]
            pieces.append(f"You're often using '{cmd['command']}' ({cmd['frequency']} times).")
        if preferences:
            pref = preferences[0]
            pieces.append(f"I remember you prefer {pref['key']} → {pref['value']}.")
        if not pieces:
            return ""
        return " ".join(pieces)
    except Exception:
        return ""

def process_command(command):
    """Enhanced command processing with better accuracy and intent recognition"""
    command_lower = command.lower().strip()
    original_command = command.strip()
    
    # Classify high-level intent once for debugging / routing visibility
    try:
        task_type = classify_task(original_command)
        print(f"🧠 Intent classifier: {task_type.value} | Command: {original_command}")
    except Exception:
        task_type = None
    
    # Enhanced typo normalization (expanded for better accuracy)
    typo_fixes = {
        "utube": "youtube",
        "u tube": "youtube",
        "you tube": "youtube",
        "yt": "youtube",
        "youtub": "youtube",
        "fb": "facebook",
        "face book": "facebook",
        "gmail": "gmail",
        "g mail": "gmail",
        "google": "google",
        "goo gle": "google",
        "github": "github",
        "git hub": "github",
        "calc": "calculator",
        "calcu": "calculator",
        "notepad": "notepad",
        "note pad": "notepad",
        "vscode": "vs code",
        "vs code": "vs code",
        "visual studio": "vs code",
    }
    for typo, correct in typo_fixes.items():
        if typo in command_lower:
            command = command.replace(typo, correct)
            command_lower = command.lower().strip()
    
    # Enhanced command normalization for better understanding
    # Remove filler words that don't affect meaning
    filler_words = ["please", "can you", "could you", "would you", "kindly", "i want", "i need"]
    for filler in filler_words:
        if command_lower.startswith(filler + " "):
            command = command[len(filler):].strip()
            command_lower = command.lower().strip()
    
    # Apply learned preferences to command
    if _preference_manager:
        try:
            command = _preference_manager.apply_preferences_to_command(command)
            command_lower = command.lower().strip()
        except Exception:
            pass
    
    # Learning system commands
    if command_lower.startswith("learn ") or command_lower.startswith("remember "):
        _debug_route("SYSTEM_LEARNING", "learn/remember command", task_type)
        return handle_learning_command(command)
    elif command_lower in ["show my habits", "my habits", "what do you know about me", "what do you remember about me"]:
        _debug_route("SYSTEM_LEARNING", "show habits", task_type)
        return handle_show_habits()
    elif command_lower in [
        "what did we discuss earlier",
        "what did we talk about",
        "recent conversation",
        "recap conversation",
        "summarize recent discussion"
    ]:
        return _recent_conversation_text()
    elif command_lower.startswith("forget ") or command_lower.startswith("unlearn "):
        return handle_forget_command(command)
    elif command_lower in ["suggestions", "suggest", "what should i do"]:
        return handle_suggestions()
    elif command_lower in ["recent commands", "my recent commands", "what did i just ask", "show recent commands"]:
        return handle_recent_commands()

    # Enhanced intent routing with better pattern matching
    # System command execution should be checked before app opening so 'run ...' works
    if any(keyword in command_lower for keyword in ["run", "execute", "cmd", "command"]):
        _debug_route("SYSTEM", "system command execution", task_type)
        return handle_system_commands(command)
    # Composite actions like "open notepad and type hello"
    composite = handle_composite_actions(command)
    if composite:
        _debug_route("SYSTEM", "composite action", task_type)
        return composite

    # Media/playback intents should route before generic open to capture 'open youtube and play ...'
    if ("play" in command_lower) or command_lower.startswith("play "):
        _debug_route("SYSTEM", "media/playback via open_apps", task_type)
        return open_apps.handle(command)
    # Email writing should be routed to AI agent before automation intercepts 'write' commands
    if classify_task(original_command) == TaskType.EMAIL_WRITING:
        _debug_route("AI_EMAIL", "email writer agent", task_type)
        ai_response = _route_ai_agents(original_command)
        if ai_response:
            return ai_response

    # Specialized AI tasks (code generation, etc.) should run before automation
    if _needs_special_ai_task(original_command):
        _debug_route("AI_SPECIAL", "specialized AI agent (code/email)", task_type)
        ai_response = _route_ai_agents(original_command)
        if ai_response:
            return ai_response

    # Automation: typing, pressing keys, paste, WhatsApp message
    file_mentioned = "file" in command_lower or "folder" in command_lower
    if (not file_mentioned and
        not any(phrase in command_lower for phrase in ["create file", "create a file", "make file", "make a file"]) and
        any(k in command_lower for k in [
            "type ", "write ", "press ", "paste ", "send message", "whatsapp"
        ])):
        _debug_route("SYSTEM_AUTOMATION", "keyboard/mouse automation", task_type)
        return automation.handle(command)
    
    # File location queries (e.g., "where is test.txt created")
    if "where" in command_lower and "file" in command_lower:
        location_response = handle_file_location_query(command)
        if location_response:
            return location_response

    # App opening - execute non-blocking for faster response
    if any(keyword in command_lower for keyword in ["open", "launch", "start"]):
        # Check if it's a question first (e.g., "what is open source?")
        is_question = any(q in command_lower for q in [
            "what is", "what are", "who is", "who are", "how to", "how do", 
            "explain", "tell me about", "define", "meaning of", "what does",
            "why", "when", "where"
        ])
        if not is_question:
            # Non-blocking app opening
            import threading
            result_container = {"response": None}
            def _open_app():
                result_container["response"] = open_apps.handle(command)
            thread = threading.Thread(target=_open_app, daemon=True)
            thread.start()
            thread.join(timeout=0.5)  # Wait max 500ms for response
            if result_container["response"]:
                _debug_route("SYSTEM", "app open (fast response)", task_type)
                return result_container["response"]
            # If still opening, return immediately
            app_name = command_lower.replace("open", "").replace("launch", "").replace("start", "").strip()
            _debug_route("SYSTEM", f"app open (non-blocking): {app_name}", task_type)
            return f"✅ Opening {app_name}..."
        else:
            # It's a question, route to AI
            pass
    elif "weather" in command_lower:
        _debug_route("SYSTEM", "weather handler", task_type)
        return weather_info.handle(command)
    elif "remind" in command_lower:
        _debug_route("SYSTEM", "reminder handler", task_type)
        return reminder_manager.handle(command)
    # Installation help should be routed before coding intents so 'help install vs code' works
    elif "help install" in command_lower or "install help" in command_lower:
        _debug_route("SYSTEM", "installation help", task_type)
        return handle_installation_help(command)
    # LLM status / offline toggles
    elif command_lower in ["llm status", "ai status", "model status"]:
        _debug_route("SYSTEM", "llm status", task_type)
        return get_llm_status()
    elif command_lower in ["go offline", "llm offline", "ai offline"]:
        _debug_route("SYSTEM", "llm offline", task_type)
        return set_offline_mode(True)
    elif command_lower in ["go online", "llm online", "ai online"]:
        _debug_route("SYSTEM", "llm online", task_type)
        return set_offline_mode(False)
    elif command_lower in ["llm test", "ai test", "model test"]:
        _debug_route("SYSTEM", "llm self-test", task_type)
        return llm_self_test()
    elif command_lower in ["llm help", "ai help", "model help"]:
        _debug_route("SYSTEM", "llm help", task_type)
        return get_llm_help()
    # System controls (timer, shutdown, restart, sleep, lock, logoff, wifi/bluetooth)
    elif any(k in command_lower for k in [
        "timer", "timmer", "set timer", "set timmer", "countdown", "alarm in", "set alarm", "remind me in",
        "shutdown", "power off", "turn off", "restart", "reboot", "sleep", "suspend", "lock", "lock screen",
        "logoff", "log out", "sign out", "stop alarm", "stop timer", "stop ringing", "silence alarm", "dismiss alarm",
        "volume", "mute", "unmute", "sound", "increase volume", "decrease volume",
        "brightness", "screen brightness", "display brightness", "increase brightness", "decrease brightness",
        "bluetooth", "bt", "wifi", "wi-fi", "wi fi", "wlan"
    ]):
        _debug_route("SYSTEM", "system controls", task_type)
        return system_controls.handle(command)
    elif "create file" in command_lower and not any(ext in command_lower for ext in ["python", "html", "css", "javascript", "json"]):
        _debug_route("SYSTEM_FILES", "generic create file (coding commands)", task_type)
        return handle_coding_commands(command)
    elif any(keyword in command_lower for keyword in ["create", "write", "code", "generate", "make", "python", "html", "css", "javascript", "json"]):
        _debug_route("AI_CODE", "coding assistant", task_type)
        return coding_assistant.handle(command)
    # File operations - comprehensive file manipulation
    elif any(keyword in command_lower for keyword in [
        "delete file", "remove file", "read file", "show file", "view file",
        "write to file", "append to file", "copy file", "move file", "rename file",
        "search in file", "find in file", "file info", "file size", "file details",
        "delete folder", "remove folder", "create folder", "create directory"
    ]):
        _debug_route("SYSTEM_FILES", "file operations handler", task_type)
        return file_operations.handle(command)
    elif any(keyword in command_lower for keyword in ["list", "show", "dir", "ls"]):
        # Check if it's a detailed list request
        if "detailed" in command_lower or "ls -l" in command_lower:
            _debug_route("SYSTEM_FILES", "detailed list via file_operations", task_type)
            return file_operations.handle(command)
        _debug_route("SYSTEM_FILES", "basic list / show via handle_file_operations", task_type)
        return handle_file_operations(command)
    elif any(keyword in command_lower for keyword in ["cd", "navigate", "go to"]):
        _debug_route("SYSTEM_FILES", "navigation", task_type)
        return handle_navigation(command)
    elif command_lower in ["quit", "exit", "bye", "goodbye"]:
        _debug_route("SYSTEM", "quit/exit", task_type)
        return "Goodbye! Have a great day! 👋"

    # Enhanced question detection - route informational queries to Ollama first
    is_question = any(q in command_lower for q in [
        "what is", "what are", "who is", "who are", "how to", "how do", 
        "explain", "tell me about", "define", "meaning of", "what does",
        "why", "when", "where", "can you explain", "what does", "what do",
        "difference between", "compare", "advantages of", "benefits of"
    ])
    
    if is_question:
        # Prioritize Ollama for questions (faster and more accurate)
        _debug_route("AI_QA", "question detected, routing to AI", task_type)
        ai_response = _route_ai_agents(original_command)
        if ai_response:
            return ai_response
        # Fallback to ask_gpt
        try:
            _debug_route("AI_QA", "question fallback ask_gpt", task_type)
            return _ask_with_context(command)
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    # Try routing to specialized AI agents
    _debug_route("AI_GENERAL", "general AI routing", task_type)
    ai_response = _route_ai_agents(original_command)
    if ai_response:
        return ai_response

    # Final fallback
    try:
        _debug_route("AI_FALLBACK", "final ask_gpt fallback", task_type)
        return _ask_with_context(command)
    except Exception as e:
        return f"❌ Error: {str(e)}"

def handle_coding_commands(command):
    """Handle coding and file creation commands"""
    command_lower = command.lower()
    
    if "create file" in command_lower or "make file" in command_lower:
        # Delegate to coding assistant for richer behavior (supports inline content)
        from skills.coding_assistant import create_generic_file  # lazy import to avoid overhead
        return create_generic_file(command)
    
    elif "create folder" in command_lower or "make directory" in command_lower:
        folder_name = extract_folder_name(command)
        if folder_name:
            try:
                folder_path = resolve_directory_path(folder_name)
                return f"✅ Created folder: {folder_path.name}\n📁 Location: {folder_path}"
            except Exception as e:
                return f"❌ Error creating folder: {str(e)}"
    
    elif "python script" in command_lower or "py file" in command_lower:
        filename = extract_filename(command) or "script.py"
        if not filename.endswith('.py'):
            filename += '.py'
        try:
            output_path = resolve_output_path(filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("#!/usr/bin/env python3\n# Generated by Personal Assistant\n\n")
            return f"✅ Created Python script: {output_path.name}\n📁 Location: {output_path}"
        except Exception as e:
            return f"❌ Error creating Python script: {str(e)}"
    
    return "I can help you create files, folders, and Python scripts. Try: 'create file filename.txt' or 'create Python script'"

def handle_file_operations(command):
    """Handle file listing and directory operations"""
    command_lower = command.lower()
    
    if "list files" in command_lower or "show files" in command_lower or "ls" in command_lower:
        try:
            base_dir = get_base_output_dir()
            files = os.listdir(base_dir)
            if files:
                file_list = "\n".join([f"📄 {f}" for f in sorted(files)])
                return f"📁 Files in sandbox ({base_dir}):\n{file_list}"
            else:
                return f"📁 Sandbox directory ({base_dir}) is empty"
        except Exception as e:
            return f"❌ Error listing files: {str(e)}"
    
    return "I can list files in the current directory. Try: 'list files' or 'show files'"

def handle_file_location_query(command: str) -> str:
    """Provide the absolute path of a requested file if it exists"""
    try:
        from skills.coding_assistant import extract_filename_from_command
        filename = extract_filename_from_command(command)
    except Exception:
        filename = None
    if not filename:
        # Attempt simple fallback: look for last word ending with common extension
        tokens = command.replace("?", "").split()
        for token in reversed(tokens):
            if "." in token:
                filename = token.strip(" ,.")
                break
    if not filename:
        return ""
    file_path = resolve_access_path(filename)
    if file_path.exists():
        return f"📁 File '{file_path.name}' is located at:\n{file_path}"
    else:
        return (
            f"❌ I couldn't find '{file_path.name}' in the sandbox directory "
            f"({get_base_output_dir()})."
        )

def handle_navigation(command):
    """Handle directory navigation"""
    command_lower = command.lower()
    
    if "cd" in command_lower or "navigate" in command_lower:
        # Extract directory path
        path = extract_path(command)
        if path:
            try:
                os.chdir(path)
                return f"✅ Navigated to: {os.getcwd()}"
            except Exception as e:
                return f"❌ Error navigating to {path}: {str(e)}"
    
    return "I can help you navigate directories. Try: 'cd folder_name' or 'navigate to path'"

def handle_composite_actions(command: str) -> str:
    """Handle composite commands like 'open notepad and type hello'"""
    cmd = command.lower().strip()
    if any(phrase in cmd for phrase in ["create file", "create a file", "make file", "make a file"]):
        return ""
    # Don't treat file-creation commands as automation composites
    if "create file" in cmd or "make file" in cmd:
        return ""
    # Normalize some ASR fillers like 'and a type' -> 'and type'
    cmd_norm = cmd.replace("and a type", "and type").replace(" then a type", " then type")

    # Pattern: open notepad ... and (type|write) <text>
    import re as _re
    m = _re.search(r"open\s+(notepad)\b.*?(type|write)\s+['\"]?(.+)$", cmd_norm)
    if m:
        app = m.group(1)
        text = command[m.start(3):m.end(3)]  # preserve original casing from original command
        # Step 1: open app
        open_result = open_apps.handle(f"open {app}")
        # Small delay to allow window to appear
        try:
            time.sleep(0.6)
        except Exception:
            pass
        # Step 2: type text
        type_result = automation.handle(f"type {text}")
        # Merge responses
        return f"{open_result}\n{type_result}"

    # Generic pattern: open <app> and type <text> (we only reliably support notepad for typing)
    m2 = _re.search(r"open\s+([\w\s\-\.]+)\b.*?(type|write)\s+['\"]?(.+)$", cmd_norm)
    if m2 and "notepad" in m2.group(1):
        text = command[m2.start(3):m2.end(3)]
        open_result = open_apps.handle("open notepad")
        try:
            time.sleep(0.6)
        except Exception:
            pass
        type_result = automation.handle(f"type {text}")
        return f"{open_result}\n{type_result}"

    return ""

def handle_system_commands(command):
    """Handle system command execution"""
    command_lower = command.lower()
    
    if "run" in command_lower or "execute" in command_lower:
        # Extract the actual command to run
        cmd = extract_command(command)
        if cmd:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    return f"✅ Command executed successfully:\n{result.stdout}"
                else:
                    return f"❌ Command failed:\n{result.stderr}"
            except subprocess.TimeoutExpired:
                return "❌ Command timed out"
            except Exception as e:
                return f"❌ Error executing command: {str(e)}"
    
    return "I can execute system commands. Try: 'run dir' or 'execute python --version'"

def extract_filename(command):
    """Extract filename from command"""
    patterns = [
        r'create file (\S+)',
        r'make file (\S+)',
        r'file (\S+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, command.lower())
        if match:
            return match.group(1)
    return None

def extract_folder_name(command):
    """Extract folder name from command"""
    patterns = [
        r'create folder (\S+)',
        r'make directory (\S+)',
        r'folder (\S+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, command.lower())
        if match:
            return match.group(1)
    return None

def extract_path(command):
    """Extract path from navigation command"""
    patterns = [
        r'cd (\S+)',
        r'navigate to (\S+)',
        r'go to (\S+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, command.lower())
        if match:
            return match.group(1)
    return None

def extract_command(command):
    """Extract system command to execute"""
    patterns = [
        r'run (.+)',
        r'execute (.+)',
        r'command (.+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, command.lower())
        if match:
            return match.group(1)
    return None

def handle_installation_help(command):
    """Provide installation help for applications"""
    command_lower = command.lower()
    
    installation_guides = {
        "vs code": """💻 **VS Code Installation Help**
1. Download from: https://code.visualstudio.com/
2. Run the installer
3. Add to PATH during installation
4. Restart your terminal/command prompt
5. Try: 'open vs code' again""",
        
        "postman": """📮 **Postman Installation Help**
1. Download from: https://www.postman.com/downloads/
2. Run the installer
3. Launch Postman from Start Menu
4. Try: 'open postman' again""",
        
        "intellij": """🧠 **IntelliJ IDEA Installation Help**
1. Download from: https://www.jetbrains.com/idea/
2. Run the installer
3. Add to PATH if prompted
4. Try: 'open intellij' again""",
        
        "eclipse": """🌙 **Eclipse Installation Help**
1. Download from: https://www.eclipse.org/downloads/
2. Extract to a folder
3. Run eclipse.exe
4. Try: 'open eclipse' again""",
        
        "android studio": """🤖 **Android Studio Installation Help**
1. Download from: https://developer.android.com/studio
2. Run the installer
3. Follow setup wizard
4. Try: 'open android studio' again""",
        
        "figma": """🎨 **Figma Installation Help**
1. Download from: https://www.figma.com/downloads/
2. Run the installer
3. Launch from Start Menu
4. Try: 'open figma' again""",
        
        "docker": """🐳 **Docker Desktop Installation Help**
1. Download from: https://www.docker.com/products/docker-desktop
2. Run the installer
3. Restart your computer
4. Try: 'open docker' again""",
        
        "git": """🐙 **Git Installation Help**
1. Download from: https://git-scm.com/
2. Run the installer
3. Add to PATH during installation
4. Try: 'open git bash' again""",
        
        "node": """🟢 **Node.js Installation Help**
1. Download from: https://nodejs.org/
2. Run the installer
3. Restart your terminal
4. Try: 'open node' again""",
    }
    
    # Extract app name from command
    for app_name, guide in installation_guides.items():
        if app_name in command_lower:
            return guide
    
    # General installation help
    return """🛠️ **Application Installation Help**

I can help you install these popular applications:

💻 **Development Tools:**
• VS Code - Code editor
• Postman - API testing
• IntelliJ IDEA - Java IDE
• Eclipse - Java IDE
• Android Studio - Android development

🎨 **Design Tools:**
• Figma - UI/UX design
• Sketch - Design tool (macOS only)

🐙 **Development Tools:**
• Git - Version control
• Docker - Containerization
• Node.js - JavaScript runtime

**Usage:** 'help install [app name]'
**Example:** 'help install vs code'

💡 Most applications will provide download links and installation instructions!"""

# Learning system handlers
def handle_learning_command(command: str) -> str:
    """Handle learning/remember commands"""
    if not _learning_system or not _preference_manager:
        return "⚠️ Learning system is not available."
    
    cmd_lower = command.lower().strip()
    
    # Extract what to remember
    if "remember" in cmd_lower:
        item = cmd_lower.replace("remember", "").replace("bittu", "").strip()
    elif "learn" in cmd_lower:
        item = cmd_lower.replace("learn", "").replace("bittu", "").strip()
    else:
        return "Usage: 'remember [something]' or 'learn [something]'"
    
    if not item:
        return "What should I remember? Try: 'remember I prefer Chrome'"
    
    # Save as preference
    _preference_manager.db.save_preference(
        "user_memory",
        "general",
        item,
        confidence=0.8,
        learned_from="explicit"
    )
    
    return f"✅ I'll remember: '{item}'"

def handle_show_habits() -> str:
    """Show learned user habits"""
    if not _learning_system:
        return "⚠️ Learning system is not available."
    
    try:
        habits = _learning_system.analyze_user_habits()
        
        result = "📊 **Your Usage Patterns:**\n\n"
        
        # Most common commands
        if habits.get("most_common_commands"):
            result += "🎯 **Most Used Commands:**\n"
            for i, cmd in enumerate(habits["most_common_commands"][:5], 1):
                result += f"{i}. {cmd['command']} (used {cmd['frequency']} times)\n"
            result += "\n"
        
        # Time patterns
        if habits.get("time_patterns"):
            result += "⏰ **Time-Based Patterns:**\n"
            for pattern in habits["time_patterns"][:3]:
                result += f"• {pattern['command']} - Hour {pattern['hour']:02d}:00 ({pattern['frequency']} times)\n"
            result += "\n"
        
        # Preferences
        if habits.get("preferences"):
            result += "💡 **Learned Preferences:**\n"
            for pref in habits["preferences"][:5]:
                result += f"• {pref['key']}: {pref['value']} (confidence: {pref['confidence']:.1%})\n"
        
        if not any([habits.get("most_common_commands"), habits.get("time_patterns"), habits.get("preferences")]):
            result += "I'm still learning about your habits. Keep using me and I'll learn more! 🧠"
        
        return result
    except Exception as e:
        return f"❌ Error showing habits: {str(e)}"

def handle_forget_command(command: str) -> str:
    """Handle forget/unlearn commands"""
    if not _preference_manager:
        return "⚠️ Learning system is not available."
    
    cmd_lower = command.lower().strip()
    item = cmd_lower.replace("forget", "").replace("unlearn", "").replace("bittu", "").strip()
    
    if not item:
        return "What should I forget? Try: 'forget [preference]'"
    
    # Note: Full deletion would require additional DB methods
    # For now, we'll lower confidence
    pref = _preference_manager.db.get_preference("user_memory", item)
    if pref:
        _preference_manager.db.save_preference(
            "user_memory",
            item,
            pref["value"],
            confidence=0.1,  # Lower confidence effectively "forgets"
            learned_from="user_request"
        )
        return f"✅ I'll forget: '{item}'"
    
    return f"⚠️ I don't have '{item}' in my memory."

def handle_suggestions() -> str:
    """Provide contextual suggestions"""
    if not _learning_system or not _context_manager:
        return "⚠️ Learning system is not available."
    
    try:
        suggestions = []
        
        # Time-based suggestion
        time_suggestion = _learning_system.get_time_based_suggestion()
        if time_suggestion:
            suggestions.append(f"⏰ Based on time: '{time_suggestion}'")
        
        # Contextual suggestion (based on your recent commands)
        context_suggestion = _context_manager.get_contextual_suggestion()
        if context_suggestion:
            suggestions.append(f"💡 Based on recent activity: '{context_suggestion}'")
        
        # Most common commands you use
        frequent = _learning_system.db.get_command_frequency(limit=3)
        if frequent:
            suggestions.append(f"🎯 You often use: '{frequent[0]['command']}'")
        
        if suggestions:
            return "💭 **Personalized Suggestions:**\n\n" + "\n".join(suggestions)
        else:
            return "💡 I don't have enough data yet to make suggestions. Keep using me and I'll learn more."
    except Exception as e:
        return f"❌ Error getting suggestions: {str(e)}"


def handle_recent_commands() -> str:
    """Show a short history of your recent commands and results."""
    if not _context_manager:
        return "⚠️ Conversation history is not available yet."
    try:
        history = list(_context_manager.conversation_history)[-5:]
        if not history:
            return "I don't have any recent commands recorded yet."
        lines: list[str] = ["📝 **Your recent commands:**"]
        for idx, entry in enumerate(history, 1):
            status = "✅" if entry.get("success") else "⚠️"
            cmd = str(entry.get("command", ""))[:80]
            resp = str(entry.get("response", ""))[:80]
            lines.append(f"{idx}. {status} `{cmd}` → {resp}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error reading recent commands: {str(e)}"

# Wrapper to log all commands
def process_command_with_learning(command: str) -> str:
    """Process command with learning integration - always returns response"""
    # Ensure learning is initialized (lazy init)
    try:
        _ensure_learning_initialized()
    except Exception:
        pass  # Continue even if learning init fails
    
    if not command or not command.strip():
        return "Please provide a command."
    
    start_time = time.time()
    response = ""
    success = False
    
    # Get context (non-blocking)
    context = {}
    if _context_manager:
        try:
            context = _context_manager.get_context()
        except Exception:
            pass
    
    # Process command (CRITICAL - must always return a response)
    try:
        response = process_command(command)
        if not response:
            response = "Command processed but no response generated."
        success = not (response.startswith("❌") or "error" in response.lower() or "failed" in response.lower())
    except Exception as e:
        response = f"❌ Error processing command: {str(e)}"
        success = False
    
    # Ensure we always have a response
    if not response or not response.strip():
        response = "Command processed."

    global _command_counter
    _command_counter += 1
    insight = _learning_insight()
    if insight:
        response = f"{response}\n\n💡 Insight: {insight}"
    
    response_time = time.time() - start_time

    # Persona-enhance the response if LLM backend is available
    try:
        response = stylize_response(command, response)
    except Exception:
        pass
    
    # Learn from experience (non-blocking, must not interfere with response)
    # This runs AFTER response is ready, so it can't block
    if _learning_system and _context_manager:
        try:
            _learning_system.analyze_command(command, success, response, context)
            _context_manager.add_to_context(command, response, success)
            
            # Log to database
            if hasattr(_learning_system, 'db') and _learning_system.db:
                _learning_system.db.log_experience(
                    command=command,
                    success=success,
                    response_text=str(response)[:500],  # Limit length
                    response_time=response_time,
                    context=context
                )
        except Exception:
            # Learning errors should never prevent response - silently ignore
            pass
    
    return response