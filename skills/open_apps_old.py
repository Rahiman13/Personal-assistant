# skills/open_apps.py
import os
import webbrowser
import subprocess
import platform

def handle(command):
    command_lower = command.lower()
    
    # Web applications
    if "youtube" in command_lower:
        webbrowser.open("https://youtube.com")
        return "🎥 Opening YouTube"
    elif "google" in command_lower or "chrome" in command_lower:
        webbrowser.open("https://google.com")
        return "🌐 Opening Google Chrome"
    elif "gmail" in command_lower:
        webbrowser.open("https://gmail.com")
        return "📧 Opening Gmail"
    elif "github" in command_lower:
        webbrowser.open("https://github.com")
        return "🐙 Opening GitHub"
    elif "stackoverflow" in command_lower or "stack overflow" in command_lower:
        webbrowser.open("https://stackoverflow.com")
        return "💻 Opening Stack Overflow"
    elif "reddit" in command_lower:
        webbrowser.open("https://reddit.com")
        return "🔴 Opening Reddit"
    elif "netflix" in command_lower:
        webbrowser.open("https://netflix.com")
        return "🎬 Opening Netflix"
    elif "spotify" in command_lower:
        webbrowser.open("https://open.spotify.com")
        return "🎵 Opening Spotify"
    
    # Desktop applications
    elif "notepad" in command_lower:
        if platform.system() == "Windows":
        os.system("notepad")
        else:
            subprocess.run(["gedit"], check=False)
        return "Opening Notepad"
    elif "calculator" in command_lower or "calc" in command_lower:
        if platform.system() == "Windows":
            os.system("calc")
        else:
            subprocess.run(["gnome-calculator"], check=False)
        return "🧮 Opening Calculator"
    elif "file explorer" in command_lower or "explorer" in command_lower:
        if platform.system() == "Windows":
            os.system("explorer")
        else:
            subprocess.run(["nautilus"], check=False)
        return "📁 Opening File Explorer"
    elif "task manager" in command_lower:
        if platform.system() == "Windows":
            os.system("taskmgr")
        else:
            subprocess.run(["gnome-system-monitor"], check=False)
        return "⚙️ Opening Task Manager"
    elif "control panel" in command_lower:
        if platform.system() == "Windows":
            os.system("control")
        else:
            subprocess.run(["gnome-control-center"], check=False)
        return "⚙️ Opening Control Panel"
    elif "settings" in command_lower:
        if platform.system() == "Windows":
            os.system("ms-settings:")
        else:
            subprocess.run(["gnome-control-center"], check=False)
        return "⚙️ Opening Settings"
    
    # Development tools
    elif "vs code" in command_lower or "vscode" in command_lower or "code" in command_lower:
        return open_vs_code()
    elif "pycharm" in command_lower:
        try:
            subprocess.run(["pycharm"], check=False)
            return "🐍 Opening PyCharm"
        except:
            return "❌ PyCharm not found. Make sure it's installed and in PATH"
    elif "sublime" in command_lower:
        try:
            subprocess.run(["subl"], check=False)
            return "📝 Opening Sublime Text"
        except:
            return "❌ Sublime Text not found. Make sure it's installed and in PATH"
    elif "atom" in command_lower:
        try:
            subprocess.run(["atom"], check=False)
            return "⚛️ Opening Atom"
        except:
            return "❌ Atom not found. Make sure it's installed and in PATH"
    
    # System utilities
    elif "terminal" in command_lower or "cmd" in command_lower or "command prompt" in command_lower:
        if platform.system() == "Windows":
            os.system("cmd")
        else:
            subprocess.run(["gnome-terminal"], check=False)
        return "💻 Opening Terminal"
    elif "powershell" in command_lower:
        if platform.system() == "Windows":
            os.system("powershell")
        else:
            return "❌ PowerShell is only available on Windows"
        return "💻 Opening PowerShell"
    
    # Games and entertainment
    elif "steam" in command_lower:
        try:
            subprocess.run(["steam"], check=False)
            return "🎮 Opening Steam"
        except:
            return "❌ Steam not found. Make sure it's installed"
    elif "discord" in command_lower:
        try:
            subprocess.run(["discord"], check=False)
            return "💬 Opening Discord"
        except:
            return "❌ Discord not found. Make sure it's installed"
    
    # Additional development tools
    elif "postman" in command_lower:
        return open_postman()
    elif "intellij" in command_lower or "idea" in command_lower:
        return open_intellij()
    elif "eclipse" in command_lower:
        return open_eclipse()
    elif "android studio" in command_lower:
        return open_android_studio()
    elif "xcode" in command_lower:
        return open_xcode()
    elif "figma" in command_lower:
        return open_figma()
    elif "sketch" in command_lower:
        return open_sketch()
    elif "docker" in command_lower:
        return open_docker()
    elif "git" in command_lower or "git bash" in command_lower:
        return open_git_bash()
    elif "node" in command_lower or "nodejs" in command_lower:
        return open_node()
    elif "npm" in command_lower:
        return open_npm()
    elif "yarn" in command_lower:
        return open_yarn()
    
    # Office applications
    elif "word" in command_lower:
        try:
            if platform.system() == "Windows":
                os.system("start winword")
            else:
                subprocess.run(["libreoffice", "--writer"], check=False)
            return "📄 Opening Microsoft Word"
        except:
            return "❌ Word not found"
    elif "excel" in command_lower:
        try:
            if platform.system() == "Windows":
                os.system("start excel")
            else:
                subprocess.run(["libreoffice", "--calc"], check=False)
            return "📊 Opening Microsoft Excel"
        except:
            return "❌ Excel not found"
    elif "powerpoint" in command_lower or "power point" in command_lower:
        try:
            if platform.system() == "Windows":
                os.system("start powerpnt")
            else:
                subprocess.run(["libreoffice", "--impress"], check=False)
            return "📊 Opening Microsoft PowerPoint"
        except:
            return "❌ PowerPoint not found"
    
    # Default response with suggestions
    else:
        return """🤖 I can open many applications! Here are some examples:

🌐 Web Apps: YouTube, Google, Gmail, GitHub, Stack Overflow, Reddit, Netflix, Spotify
💻 Development: VS Code, Postman, IntelliJ, Eclipse, Android Studio, PyCharm, Sublime Text, Atom
📝 System: Notepad, Calculator, File Explorer, Task Manager, Settings, Terminal
🎮 Entertainment: Steam, Discord
📄 Office: Word, Excel, PowerPoint
🐙 Tools: Git Bash, Docker, Node.js, npm, yarn
🎨 Design: Figma, Sketch

Try: 'open [application name]' or 'launch [application name]'
💡 If an app doesn't open, try: 'help install [app name]' for installation help"""

# Helper functions for better application detection
def open_vs_code():
    """Open VS Code with multiple detection methods"""
    possible_paths = [
        "code",  # Standard PATH
        "code.cmd",  # Windows
        "C:\\Users\\{}\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe".format(os.getenv('USERNAME', '')),
        "C:\\Program Files\\Microsoft VS Code\\Code.exe",
        "C:\\Program Files (x86)\\Microsoft VS Code\\Code.exe"
    ]
    
    for path in possible_paths:
        try:
            if path.startswith("C:\\"):
                if os.path.exists(path):
                    subprocess.run([path], check=False)
                    return "💻 Opening VS Code"
            else:
                subprocess.run([path], check=False)
                return "💻 Opening VS Code"
        except:
            continue
    
    return "❌ VS Code not found. Try installing it from: https://code.visualstudio.com/"

def open_postman():
    """Open Postman with multiple detection methods"""
    possible_paths = [
        "postman",  # Standard PATH
        "C:\\Users\\{}\\AppData\\Local\\Postman\\Postman.exe".format(os.getenv('USERNAME', '')),
        "C:\\Program Files\\Postman\\Postman.exe",
        "C:\\Program Files (x86)\\Postman\\Postman.exe"
    ]
    
    for path in possible_paths:
        try:
            if path.startswith("C:\\"):
                if os.path.exists(path):
                    subprocess.run([path], check=False)
                    return "📮 Opening Postman"
            else:
                subprocess.run([path], check=False)
                return "📮 Opening Postman"
        except:
            continue
    
    return "❌ Postman not found. Try installing it from: https://www.postman.com/downloads/"

def open_intellij():
    """Open IntelliJ IDEA"""
    possible_paths = [
        "idea",  # Standard PATH
        "C:\\Users\\{}\\AppData\\Local\\JetBrains\\Toolbox\\apps\\IDEA-U\\ch-0\\*\\bin\\idea64.exe".format(os.getenv('USERNAME', '')),
        "C:\\Program Files\\JetBrains\\IntelliJ IDEA Community Edition *\\bin\\idea64.exe",
        "C:\\Program Files\\JetBrains\\IntelliJ IDEA *\\bin\\idea64.exe"
    ]
    
    for path in possible_paths:
        try:
            if "*" in path:
                # Handle wildcard paths
                import glob
                matches = glob.glob(path)
                if matches:
                    subprocess.run([matches[0]], check=False)
                    return "🧠 Opening IntelliJ IDEA"
            elif path.startswith("C:\\"):
                if os.path.exists(path):
                    subprocess.run([path], check=False)
                    return "🧠 Opening IntelliJ IDEA"
            else:
                subprocess.run([path], check=False)
                return "🧠 Opening IntelliJ IDEA"
        except:
            continue
    
    return "❌ IntelliJ IDEA not found. Try installing it from: https://www.jetbrains.com/idea/"

def open_eclipse():
    """Open Eclipse IDE"""
    possible_paths = [
        "eclipse",  # Standard PATH
        "C:\\Users\\{}\\eclipse\\java-*\\eclipse\\eclipse.exe".format(os.getenv('USERNAME', '')),
        "C:\\Program Files\\Eclipse\\eclipse.exe"
    ]
    
    for path in possible_paths:
        try:
            if "*" in path:
                import glob
                matches = glob.glob(path)
                if matches:
                    subprocess.run([matches[0]], check=False)
                    return "🌙 Opening Eclipse"
            elif path.startswith("C:\\"):
                if os.path.exists(path):
                    subprocess.run([path], check=False)
                    return "🌙 Opening Eclipse"
            else:
                subprocess.run([path], check=False)
                return "🌙 Opening Eclipse"
        except:
            continue
    
    return "❌ Eclipse not found. Try installing it from: https://www.eclipse.org/downloads/"

def open_android_studio():
    """Open Android Studio"""
    possible_paths = [
        "studio",  # Standard PATH
        "C:\\Users\\{}\\AppData\\Local\\Android\\Sdk\\tools\\studio.exe".format(os.getenv('USERNAME', '')),
        "C:\\Program Files\\Android\\Android Studio\\bin\\studio64.exe"
    ]
    
    for path in possible_paths:
        try:
            if path.startswith("C:\\"):
                if os.path.exists(path):
                    subprocess.run([path], check=False)
                    return "🤖 Opening Android Studio"
            else:
                subprocess.run([path], check=False)
                return "🤖 Opening Android Studio"
        except:
            continue
    
    return "❌ Android Studio not found. Try installing it from: https://developer.android.com/studio"

def open_xcode():
    """Open Xcode (macOS only)"""
    if platform.system() != "Darwin":
        return "❌ Xcode is only available on macOS"
    
    try:
        subprocess.run(["open", "-a", "Xcode"], check=False)
        return "🍎 Opening Xcode"
    except:
        return "❌ Xcode not found. Install it from the Mac App Store"

def open_figma():
    """Open Figma"""
    possible_paths = [
        "figma",  # Standard PATH
        "C:\\Users\\{}\\AppData\\Local\\Figma\\Figma.exe".format(os.getenv('USERNAME', '')),
        "C:\\Program Files\\Figma\\Figma.exe"
    ]
    
    for path in possible_paths:
        try:
            if path.startswith("C:\\"):
                if os.path.exists(path):
                    subprocess.run([path], check=False)
                    return "🎨 Opening Figma"
            else:
                subprocess.run([path], check=False)
                return "🎨 Opening Figma"
        except:
            continue
    
    return "❌ Figma not found. Try installing it from: https://www.figma.com/downloads/"

def open_sketch():
    """Open Sketch (macOS only)"""
    if platform.system() != "Darwin":
        return "❌ Sketch is only available on macOS"
    
    try:
        subprocess.run(["open", "-a", "Sketch"], check=False)
        return "✏️ Opening Sketch"
    except:
        return "❌ Sketch not found. Install it from: https://www.sketch.com/"

def open_docker():
    """Open Docker Desktop"""
    possible_paths = [
        "docker",  # Standard PATH
        "C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe",
        "C:\\Users\\{}\\AppData\\Local\\Docker\\Docker Desktop.exe".format(os.getenv('USERNAME', ''))
    ]
    
    for path in possible_paths:
        try:
            if path.startswith("C:\\"):
                if os.path.exists(path):
                    subprocess.run([path], check=False)
                    return "🐳 Opening Docker Desktop"
            else:
                subprocess.run([path], check=False)
                return "🐳 Opening Docker Desktop"
        except:
            continue
    
    return "❌ Docker Desktop not found. Try installing it from: https://www.docker.com/products/docker-desktop"

def open_git_bash():
    """Open Git Bash"""
    possible_paths = [
        "git-bash",  # Standard PATH
        "C:\\Program Files\\Git\\git-bash.exe",
        "C:\\Program Files (x86)\\Git\\git-bash.exe"
    ]
    
    for path in possible_paths:
        try:
            if path.startswith("C:\\"):
                if os.path.exists(path):
                    subprocess.run([path], check=False)
                    return "🐙 Opening Git Bash"
            else:
                subprocess.run([path], check=False)
                return "🐙 Opening Git Bash"
        except:
            continue
    
    return "❌ Git Bash not found. Try installing Git from: https://git-scm.com/"

def open_node():
    """Open Node.js REPL"""
    try:
        subprocess.run(["node"], check=False)
        return "🟢 Opening Node.js REPL"
    except:
        return "❌ Node.js not found. Try installing it from: https://nodejs.org/"

def open_npm():
    """Open npm help"""
    try:
        subprocess.run(["npm", "--help"], check=False)
        return "📦 Showing npm help"
    except:
        return "❌ npm not found. Try installing Node.js from: https://nodejs.org/"

def open_yarn():
    """Open yarn help"""
    try:
        subprocess.run(["yarn", "--help"], check=False)
        return "🧶 Showing yarn help"
    except:
        return "❌ yarn not found. Try installing it with: npm install -g yarn"
