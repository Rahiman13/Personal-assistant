# skills/open_apps.py
import os
import json
import webbrowser
import subprocess
import platform

def handle(command):
    command_lower = command.lower()
    
    # If user says 'open <site>' without specifying a browser, try known site aliases
    site_url = _extract_site_only(command_lower)
    if site_url:
        webbrowser.open(site_url)
        return f"Opening {site_url}"

    # Pattern: "open <site> in <browser>"
    url, target_browser = _extract_site_and_browser(command_lower)
    if url:
        return _open_url_in_browser(url, target_browser)
    
    # Web applications
    if "youtube" in command_lower:
        webbrowser.open("https://youtube.com")
        return "Opening YouTube"
    elif "google" in command_lower or "chrome" in command_lower:
        return _open_browser_app("chrome")
    elif "gmail" in command_lower:
        webbrowser.open("https://gmail.com")
        return "Opening Gmail"
    elif "github" in command_lower:
        webbrowser.open("https://github.com")
        return "Opening GitHub"
    elif "stackoverflow" in command_lower or "stack overflow" in command_lower:
        webbrowser.open("https://stackoverflow.com")
        return "Opening Stack Overflow"
    elif "reddit" in command_lower:
        webbrowser.open("https://reddit.com")
        return "Opening Reddit"
    elif "netflix" in command_lower:
        webbrowser.open("https://netflix.com")
        return "Opening Netflix"
    elif "spotify" in command_lower:
        webbrowser.open("https://open.spotify.com")
        return "Opening Spotify"
    
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
        return "Opening Calculator"
    elif "file explorer" in command_lower or "explorer" in command_lower:
        if platform.system() == "Windows":
            os.system("explorer")
        else:
            subprocess.run(["nautilus"], check=False)
        return "Opening File Explorer"
    elif "task manager" in command_lower:
        if platform.system() == "Windows":
            os.system("taskmgr")
        else:
            subprocess.run(["gnome-system-monitor"], check=False)
        return "Opening Task Manager"
    elif "control panel" in command_lower:
        if platform.system() == "Windows":
            os.system("control")
        else:
            subprocess.run(["gnome-control-center"], check=False)
        return "Opening Control Panel"
    elif "settings" in command_lower:
        if platform.system() == "Windows":
            os.system("start ms-settings:")
        else:
            subprocess.run(["gnome-control-center"], check=False)
        return "Opening Settings"
    elif "microsoft store" in command_lower or command_lower.strip() == "open store" or " app store" in command_lower:
        if platform.system() == "Windows":
            os.system("start ms-windows-store:")
            return "Opening Microsoft Store"
        else:
            return "Microsoft Store is only available on Windows"
    elif "edge" in command_lower or "microsoft edge" in command_lower:
        return _open_browser_app("edge")
    
    # Development tools
    elif "vs code" in command_lower or "vscode" in command_lower or "code" in command_lower:
        return open_vs_code()
    elif "pycharm" in command_lower:
        try:
            subprocess.run(["pycharm"], check=False)
            return "Opening PyCharm"
        except:
            return "PyCharm not found. Make sure it's installed and in PATH"
    elif "sublime" in command_lower:
        try:
            subprocess.run(["subl"], check=False)
            return "Opening Sublime Text"
        except:
            return "Sublime Text not found. Make sure it's installed and in PATH"
    elif "atom" in command_lower:
        try:
            subprocess.run(["atom"], check=False)
            return "Opening Atom"
        except:
            return "Atom not found. Make sure it's installed and in PATH"
    
    # System utilities
    elif "terminal" in command_lower or "cmd" in command_lower or "command prompt" in command_lower:
        if platform.system() == "Windows":
            os.system("cmd")
        else:
            subprocess.run(["gnome-terminal"], check=False)
        return "Opening Terminal"
    elif "powershell" in command_lower:
        if platform.system() == "Windows":
            os.system("powershell")
        else:
            return "PowerShell is only available on Windows"
        return "Opening PowerShell"
    
    # Games and entertainment
    elif "steam" in command_lower:
        try:
            subprocess.run(["steam"], check=False)
            return "Opening Steam"
        except:
            return "Steam not found. Make sure it's installed"
    elif "discord" in command_lower:
        try:
            subprocess.run(["discord"], check=False)
            return "Opening Discord"
        except:
            return "Discord not found. Make sure it's installed"
    
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
            return "Opening Microsoft Word"
        except:
            return "Word not found"
    elif "excel" in command_lower:
        try:
            if platform.system() == "Windows":
                os.system("start excel")
            else:
                subprocess.run(["libreoffice", "--calc"], check=False)
            return "Opening Microsoft Excel"
        except:
            return "Excel not found"
    elif "powerpoint" in command_lower or "power point" in command_lower:
        try:
            if platform.system() == "Windows":
                os.system("start powerpnt")
            else:
                subprocess.run(["libreoffice", "--impress"], check=False)
            return "Opening Microsoft PowerPoint"
        except:
            return "PowerPoint not found"
    
    # Default response with suggestions or targeted unknown message
    else:
        # If user asked to open something unrecognized, try Windows Start menu apps
        unknown = _extract_unknown_target(command_lower)
        if unknown:
            if platform.system() == "Windows":
                launched_msg = _open_windows_app_by_name(unknown)
                if launched_msg:
                    return launched_msg
            # Fallback guidance if not launched
            return (
                f"Couldn't find app or website '{unknown}'. "
                f"Try 'open {unknown} in chrome' or 'help install {unknown}'."
            )
        return """I can open many applications! Here are some examples:

Web Apps: YouTube, Google, Gmail, GitHub, Stack Overflow, Reddit, Netflix, Spotify
Development: VS Code, Postman, IntelliJ, Eclipse, Android Studio, PyCharm, Sublime Text, Atom
System: Notepad, Calculator, File Explorer, Task Manager, Settings, Terminal
Entertainment: Steam, Discord
Office: Word, Excel, PowerPoint
Tools: Git Bash, Docker, Node.js, npm, yarn
Design: Figma, Sketch

Try: 'open [application name]' or 'launch [application name]'
If an app doesn't open, try: 'help install [app name]' for installation help"""

# -------------------------- helpers ---------------------------
def _extract_site_only(cmd: str):
    """Return URL if pattern 'open <site>' matches a known alias like facebook/gmail/etc."""
    import re
    m = re.search(r"\bopen\s+(.+)$", cmd)
    if not m:
        return None
    site_raw = m.group(1).strip()
    # Avoid collisions with app names we handle elsewhere
    blocked = [
        "notepad", "calculator", "calc", "file explorer", "explorer", "task manager",
        "control panel", "settings", "terminal", "cmd", "command prompt", "powershell",
        "vs code", "vscode", "code", "pycharm", "sublime", "atom", "steam", "discord",
        "postman", "intellij", "idea", "eclipse", "android studio", "xcode", "figma",
        "sketch", "docker", "git", "git bash", "node", "nodejs", "npm", "yarn",
        "word", "excel", "powerpoint", "power point", "microsoft edge", "edge", "chrome",
        "google", "firefox", "microsoft store", "store"
    ]
    if site_raw in blocked:
        return None
    alias_to_domain = {
        "facebook": "https://www.facebook.com",
        "fb": "https://www.facebook.com",
        "instagram": "https://www.instagram.com",
        "insta": "https://www.instagram.com",
        "twitter": "https://twitter.com",
        "x": "https://twitter.com",
        "linkedin": "https://www.linkedin.com",
        "whatsapp": "https://web.whatsapp.com",
        "gmail": "https://mail.google.com",
        "youtube": "https://www.youtube.com",
        "github": "https://github.com",
        "stackoverflow": "https://stackoverflow.com",
        "stack overflow": "https://stackoverflow.com",
        "reddit": "https://www.reddit.com",
        "netflix": "https://www.netflix.com",
        "spotify": "https://open.spotify.com",
        "google": "https://www.google.com",
    }
    key = site_raw.lower()
    if key in alias_to_domain:
        return alias_to_domain[key]
    # If looks like a domain
    if "." in site_raw:
        if not site_raw.startswith("http"):
            return f"https://{site_raw}"
        return site_raw
    return None
def _open_browser_app(browser: str) -> str:
    browser = browser.lower()
    if browser == "chrome":
        if platform.system() == "Windows":
            os.system("start chrome")
        else:
            subprocess.run(["google-chrome"], check=False)
        return "Opening Google Chrome"
    if browser == "edge":
        if platform.system() == "Windows":
            os.system("start msedge")
            return "Opening Microsoft Edge"
        else:
            return "Microsoft Edge opening is only implemented for Windows"
    if browser == "firefox":
        if platform.system() == "Windows":
            os.system("start firefox")
        else:
            subprocess.run(["firefox"], check=False)
        return "Opening Firefox"
    return "Unsupported browser requested"


def _extract_site_and_browser(cmd: str):
    import re
    m = re.search(r"\bopen\s+(.+?)\s+in\s+(chrome|edge|firefox)\b", cmd)
    if not m:
        return None, None
    site_raw = m.group(1).strip()
    browser = m.group(2).lower()
    alias_to_domain = {
        "facebook": "https://www.facebook.com",
        "fb": "https://www.facebook.com",
        "instagram": "https://www.instagram.com",
        "insta": "https://www.instagram.com",
        "twitter": "https://twitter.com",
        "x": "https://twitter.com",
        "linkedin": "https://www.linkedin.com",
        "whatsapp": "https://web.whatsapp.com",
        "gmail": "https://mail.google.com",
        "youtube": "https://www.youtube.com",
        "github": "https://github.com",
        "stackoverflow": "https://stackoverflow.com",
        "stack overflow": "https://stackoverflow.com",
        "reddit": "https://www.reddit.com",
        "netflix": "https://www.netflix.com",
        "spotify": "https://open.spotify.com",
        "google": "https://www.google.com",
    }
    url = None
    key = site_raw.lower()
    if key in alias_to_domain:
        url = alias_to_domain[key]
    else:
        if "." in site_raw:
            if not site_raw.startswith("http"):
                url = f"https://{site_raw}"
            else:
                url = site_raw
        else:
            from urllib.parse import quote_plus
            q = quote_plus(site_raw)
            url = f"https://www.google.com/search?q={q}"
    return url, browser


def _open_url_in_browser(url: str, browser: str) -> str:
    if browser == "chrome":
        if platform.system() == "Windows":
            os.system(f"start chrome \"{url}\"")
        else:
            subprocess.run(["google-chrome", url], check=False)
        return f"Opening in Chrome: {url}"
    if browser == "edge":
        if platform.system() == "Windows":
            os.system(f"start msedge \"{url}\"")
            return f"Opening in Microsoft Edge: {url}"
        else:
            return "Microsoft Edge opening is only implemented for Windows"
    if browser == "firefox":
        if platform.system() == "Windows":
            os.system(f"start firefox \"{url}\"")
        else:
            subprocess.run(["firefox", url], check=False)
        return f"Opening in Firefox: {url}"
    webbrowser.open(url)
    return f"Opening: {url}"


def _extract_unknown_target(cmd: str):
    """If the command starts with 'open ...' but wasn't recognized, extract the name."""
    import re
    m = re.search(r"\bopen\s+(.+)$", cmd)
    if not m:
        return None
    target = m.group(1).strip()
    # Remove trailing guidance like 'please'
    target = target.replace('please', '').strip()
    # If it contains ' in <browser>', strip that part
    m2 = re.search(r"(.+?)\s+in\s+(chrome|edge|firefox)\b", target)
    if m2:
        target = m2.group(1).strip()
    # Avoid empty or obviously generic tokens
    if not target or target in ["app", "application", "website", "site"]:
        return None
    return target

def _open_windows_app_by_name(query: str) -> str | None:
    """Attempt to open a Windows Store/UWP or Start menu app by display name.
    Uses PowerShell Get-StartApps to find AppIDs, then launches via shell:AppsFolder.
    Returns a user message if launched, else None.
    """
    try:
        # Build a PowerShell filter that matches display names containing all tokens (case-insensitive)
        tokens = [t for t in query.replace('"', ' ').replace("'", " ").split() if t]
        if not tokens:
            return None
        # Create a -like filter chain in PowerShell
        # Example: Where-Object { $_.Name -like '*foo*' -and $_.Name -like '*bar*' }
        like_parts = " -and ".join([f"$_.Name -like '*{t}*'" for t in tokens])
        ps = (
            f"$apps = Get-StartApps | Where-Object {{ $_.Name -and ({like_parts}) }}; "
            "$apps | Select-Object Name, AppID | Sort-Object -Property Name | ConvertTo-Json -Depth 3"
        )
        res = subprocess.run([
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps
        ], capture_output=True, text=True, timeout=6)
        if res.returncode != 0:
            return None
        stdout = res.stdout.strip()
        if not stdout:
            # Try a broader single like with the raw query
            q = query.strip()
            ps2 = (
                f"$apps = Get-StartApps | Where-Object {{ $_.Name -and ($_.Name -like '*{q}*') }}; "
                "$apps | Select-Object Name, AppID | Sort-Object -Property Name | ConvertTo-Json -Depth 3"
            )
            res2 = subprocess.run([
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps2
            ], capture_output=True, text=True, timeout=6)
            if res2.returncode != 0 or not res2.stdout.strip():
                # As a last resort, try to start by name (classic win32 in PATH)
                try:
                    subprocess.run([query], shell=True, check=False)
                    return f"Opening {query}"
                except Exception:
                    return None
            stdout = res2.stdout.strip()

        # Parse JSON (may be an object or array)
        try:
            data = json.loads(stdout)
        except Exception:
            return None

        candidates = []
        if isinstance(data, dict) and 'AppID' in data:
            candidates = [data]
        elif isinstance(data, list):
            candidates = data
        else:
            candidates = []

        if not candidates:
            # Fallback: enumerate AppsFolder via powershell COM automation
            try:
                ps_enum = (
                    "$sh = New-Object -ComObject Shell.Application;"
                    "$apps = $sh.Namespace('shell:AppsFolder').Items() | ForEach-Object { $_ } | ForEach-Object { $_.Name, $_.Path } | ConvertTo-Json -Depth 3"
                )
                resE = subprocess.run([
                    "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_enum
                ], capture_output=True, text=True, timeout=10)
                dataE = None
                if resE.returncode == 0 and resE.stdout.strip():
                    try:
                        dataE = json.loads(resE.stdout)
                    except Exception:
                        dataE = None
                pairs = []
                if isinstance(dataE, list):
                    # The list alternates [Name, Path, Name, Path, ...]
                    for i in range(0, len(dataE) - 1, 2):
                        nameVal = dataE[i]
                        pathVal = dataE[i + 1]
                        pairs.append({"Name": nameVal, "AppID": pathVal})
                # Filter by tokens
                if pairs:
                    def ok(item):
                        nm = (str(item.get('Name') or '')).lower()
                        return all(t.lower() in nm for t in tokens)
                    filtered = [p for p in pairs if ok(p)]
                    if filtered:
                        candidates = filtered
                if not candidates:
                    return None
            except Exception:
                return None

        # Rank: exact name match first, then token coverage length
        qlower = query.lower()
        def score(item):
            name = (item.get('Name') or '').lower()
            exact = 1 if name == qlower else 0
            coverage = sum(1 for t in tokens if t.lower() in name)
            return (exact, coverage, -len(name))

        best = sorted(candidates, key=score, reverse=True)[0]
        appid = best.get('AppID')
        name = best.get('Name') or query
        if not appid:
            return None
        # Launch via shell:AppsFolder AppID
        try:
            subprocess.run([
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-Command", f"Start-Process \"shell:AppsFolder\\{appid}\""
            ], capture_output=True, text=True, timeout=5)
            return f"Opening {name}"
        except Exception:
            return None
    except Exception:
        return None

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
                    return "Opening VS Code"
            else:
                subprocess.run([path], check=False)
                return "Opening VS Code"
        except:
            continue
    
    return "VS Code not found. Try installing it from: https://code.visualstudio.com/"

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
                    return "Opening Postman"
            else:
                subprocess.run([path], check=False)
                return "Opening Postman"
        except:
            continue
    
    return "Postman not found. Try installing it from: https://www.postman.com/downloads/"

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
                    return "Opening IntelliJ IDEA"
            elif path.startswith("C:\\"):
                if os.path.exists(path):
                    subprocess.run([path], check=False)
                    return "Opening IntelliJ IDEA"
            else:
                subprocess.run([path], check=False)
                return "Opening IntelliJ IDEA"
        except:
            continue
    
    return "IntelliJ IDEA not found. Try installing it from: https://www.jetbrains.com/idea/"

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
                    return "Opening Eclipse"
            elif path.startswith("C:\\"):
                if os.path.exists(path):
                    subprocess.run([path], check=False)
                    return "Opening Eclipse"
            else:
                subprocess.run([path], check=False)
                return "Opening Eclipse"
        except:
            continue
    
    return "Eclipse not found. Try installing it from: https://www.eclipse.org/downloads/"

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
                    return "Opening Android Studio"
            else:
                subprocess.run([path], check=False)
                return "Opening Android Studio"
        except:
            continue
    
    return "Android Studio not found. Try installing it from: https://developer.android.com/studio"

def open_xcode():
    """Open Xcode (macOS only)"""
    if platform.system() != "Darwin":
        return "Xcode is only available on macOS"
    
    try:
        subprocess.run(["open", "-a", "Xcode"], check=False)
        return "Opening Xcode"
    except:
        return "Xcode not found. Install it from the Mac App Store"

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
                    return "Opening Figma"
            else:
                subprocess.run([path], check=False)
                return "Opening Figma"
        except:
            continue
    
    return "Figma not found. Try installing it from: https://www.figma.com/downloads/"

def open_sketch():
    """Open Sketch (macOS only)"""
    if platform.system() != "Darwin":
        return "Sketch is only available on macOS"
    
    try:
        subprocess.run(["open", "-a", "Sketch"], check=False)
        return "Opening Sketch"
    except:
        return "Sketch not found. Install it from: https://www.sketch.com/"

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
                    return "Opening Docker Desktop"
            else:
                subprocess.run([path], check=False)
                return "Opening Docker Desktop"
        except:
            continue
    
    return "Docker Desktop not found. Try installing it from: https://www.docker.com/products/docker-desktop"

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
                    return "Opening Git Bash"
            else:
                subprocess.run([path], check=False)
                return "Opening Git Bash"
        except:
            continue
    
    return "Git Bash not found. Try installing Git from: https://git-scm.com/"

def open_node():
    """Open Node.js REPL"""
    try:
        subprocess.run(["node"], check=False)
        return "Opening Node.js REPL"
    except:
        return "Node.js not found. Try installing it from: https://nodejs.org/"

def open_npm():
    """Open npm help"""
    try:
        subprocess.run(["npm", "--help"], check=False)
        return "Showing npm help"
    except:
        return "npm not found. Try installing Node.js from: https://nodejs.org/"

def open_yarn():
    """Open yarn help"""
    try:
        subprocess.run(["yarn", "--help"], check=False)
        return "Showing yarn help"
    except:
        return "yarn not found. Try installing it with: npm install -g yarn"
