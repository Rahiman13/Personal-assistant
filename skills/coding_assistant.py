# skills/coding_assistant.py
import re
import subprocess
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional

from skills.path_utils import (
    get_base_output_dir,
    resolve_access_path,
    resolve_output_path,
)

def handle(command):
    """Handle coding-related commands"""
    command_lower = command.lower()
    
    if _is_file_write_request(command_lower):
        return create_generic_file(command)
    elif "create python script" in command_lower or "create py file" in command_lower:
        return create_python_script(command)
    elif "create html file" in command_lower or "create html" in command_lower:
        return create_html_file(command)
    elif "create css file" in command_lower or "create css" in command_lower:
        return create_css_file(command)
    elif "create javascript file" in command_lower or "create js file" in command_lower:
        return create_javascript_file(command)
    elif "create json file" in command_lower or "create json" in command_lower:
        return create_json_file(command)
    elif "run python" in command_lower or "execute python" in command_lower:
        return run_python_script(command)
    elif "install package" in command_lower or "pip install" in command_lower:
        return install_python_package(command)
    elif "create requirements" in command_lower or "generate requirements" in command_lower:
        return create_requirements_file()
    elif "code review" in command_lower or "review code" in command_lower:
        return review_code(command)
    elif "format code" in command_lower or "beautify code" in command_lower:
        return format_code(command)
    else:
        return get_coding_help()

def create_generic_file(command):
    """Create (or overwrite) a file, optionally generating content from an instruction."""
    instruction = extract_file_content(command)
    filename = extract_filename_from_command(command) or infer_default_filename(command, instruction)
    if not filename:
        return "❌ Please specify a filename. Example: 'create file notes.txt'"
    
    generated_content = generate_content_from_instruction(
        instruction or command, filename
    )
    content_to_write = (
        generated_content if generated_content is not None
        else (instruction.strip() + "\n" if instruction else "# Created by Personal AI Assistant\n")
    )
    
    try:
        output_path = resolve_output_path(filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content_to_write.rstrip() + "\n")
        
        preview = content_to_write.strip()
        if len(preview) > 160:
            preview = preview[:157] + "..."
        
        summary = "with generated code/content" if generated_content else "with provided content"
        return (
            f"✅ Created file '{output_path.name}' {summary}.\n"
            f"📄 Preview:\n{preview}\n"
            f"📁 Location: {output_path}"
        )
    except Exception as e:
        return f"❌ Error creating file: {str(e)}"

def create_python_script(command):
    """Create a Python script with basic template"""
    filename = extract_filename_from_command(command) or "script.py"
    if not filename.endswith('.py'):
        filename += '.py'
    
    try:
        template = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created by Personal AI Assistant
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

def main():
    """Main function"""
    print("Hello, World!")

if __name__ == "__main__":
    main()
'''
        output_path = resolve_output_path(filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template)
        return (
            f"✅ Created Python script: {output_path.name}\n"
            f"💡 Template includes main function and proper structure\n"
            f"📁 Location: {output_path}"
        )
    except Exception as e:
        return f"❌ Error creating Python script: {str(e)}"

def create_html_file(command):
    """Create an HTML file with basic template"""
    filename = extract_filename_from_command(command) or "index.html"
    if not filename.endswith('.html'):
        filename += '.html'
    
    try:
        template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Web Page</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to My Web Page</h1>
        <p>This page was created by Personal AI Assistant on {datetime.now().strftime('%Y-%m-%d')}</p>
        <p>Start editing this file to create your website!</p>
    </div>
</body>
</html>
'''
        output_path = resolve_output_path(filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template)
        return (
            f"✅ Created HTML file: {output_path.name}\n"
            f"💡 Template includes responsive design and modern styling\n"
            f"📁 Location: {output_path}"
        )
    except Exception as e:
        return f"❌ Error creating HTML file: {str(e)}"

def create_css_file(command):
    """Create a CSS file with basic template"""
    filename = extract_filename_from_command(command) or "style.css"
    if not filename.endswith('.css'):
        filename += '.css'
    
    try:
        template = f'''/* CSS file created by Personal AI Assistant */
/* Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} */

/* Reset and base styles */
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f8f9fa;
}}

/* Container */
.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}}

/* Typography */
h1, h2, h3, h4, h5, h6 {{
    margin-bottom: 1rem;
    color: #2c3e50;
}}

p {{
    margin-bottom: 1rem;
}}

/* Buttons */
.btn {{
    display: inline-block;
    padding: 10px 20px;
    background-color: #007bff;
    color: white;
    text-decoration: none;
    border-radius: 5px;
    transition: background-color 0.3s;
}}

.btn:hover {{
    background-color: #0056b3;
}}

/* Cards */
.card {{
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    margin-bottom: 20px;
}}
'''
        output_path = resolve_output_path(filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template)
        return (
            f"✅ Created CSS file: {output_path.name}\n"
            f"💡 Template includes modern CSS with utility classes\n"
            f"📁 Location: {output_path}"
        )
    except Exception as e:
        return f"❌ Error creating CSS file: {str(e)}"

def create_javascript_file(command):
    """Create a JavaScript file with basic template"""
    filename = extract_filename_from_command(command) or "script.js"
    if not filename.endswith('.js'):
        filename += '.js'
    
    try:
        template = f'''// JavaScript file created by Personal AI Assistant
// Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

// Main application object
const App = {{
    init() {{
        console.log('App initialized');
        this.setupEventListeners();
    }},
    
    setupEventListeners() {{
        // Add your event listeners here
        document.addEventListener('DOMContentLoaded', () => {{
            console.log('DOM loaded');
        }});
    }},
    
    // Utility functions
    utils: {{
        // Add utility functions here
        log(message) {{
            console.log(`[App] ${{message}}`);
        }}
    }}
}};

// Initialize app when DOM is ready
if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', () => App.init());
}} else {{
    App.init();
}}
'''
        output_path = resolve_output_path(filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template)
        return (
            f"✅ Created JavaScript file: {output_path.name}\n"
            f"💡 Template includes modern ES6+ syntax and app structure\n"
            f"📁 Location: {output_path}"
        )
    except Exception as e:
        return f"❌ Error creating JavaScript file: {str(e)}"

def create_json_file(command):
    """Create a JSON file with basic template"""
    filename = extract_filename_from_command(command) or "data.json"
    if not filename.endswith('.json'):
        filename += '.json'
    
    try:
        template = f'''{{
    "created_by": "Personal AI Assistant",
    "created_at": "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    "version": "1.0.0",
    "data": {{
        "example": "This is a sample JSON structure",
        "items": [],
        "settings": {{
            "debug": false,
            "max_items": 100
        }}
    }}
}}'''
        output_path = resolve_output_path(filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template)
        return (
            f"✅ Created JSON file: {output_path.name}\n"
            f"💡 Template includes proper JSON structure with metadata\n"
            f"📁 Location: {output_path}"
        )
    except Exception as e:
        return f"❌ Error creating JSON file: {str(e)}"

def run_python_script(command):
    """Run a Python script"""
    script_name = extract_filename_from_command(command)
    if not script_name:
        return "❌ Please specify a Python script to run. Example: 'run python script.py'"
    
    if not script_name.endswith('.py'):
        script_name += '.py'
    
    script_path = resolve_access_path(script_name)
    if not script_path.exists():
        return f"❌ Script '{script_path.name}' not found in sandbox directory ({get_base_output_dir()})"
    
    try:
        result = subprocess.run(['python', str(script_path)], 
                               capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return f"✅ Python script executed successfully:\n{result.stdout}"
        else:
            return f"❌ Python script failed:\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "❌ Script execution timed out"
    except Exception as e:
        return f"❌ Error running Python script: {str(e)}"

def install_python_package(command):
    """Install a Python package using pip"""
    package_name = extract_package_name(command)
    if not package_name:
        return "❌ Please specify a package name. Example: 'install package requests'"
    
    try:
        result = subprocess.run(['pip', 'install', package_name], 
                               capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return f"✅ Package '{package_name}' installed successfully"
        else:
            return f"❌ Failed to install package '{package_name}':\n{result.stderr}"
    except subprocess.TimeoutExpired:
        return "❌ Package installation timed out"
    except Exception as e:
        return f"❌ Error installing package: {str(e)}"

def create_requirements_file():
    """Create a requirements.txt file from installed packages"""
    try:
        result = subprocess.run(['pip', 'freeze'], capture_output=True, text=True)
        if result.returncode == 0:
            output_path = resolve_output_path('requirements.txt')
            with open(output_path, 'w') as f:
                f.write(result.stdout)
            return f"✅ Created requirements.txt with all installed packages\n📁 Location: {output_path}"
        else:
            return "❌ Failed to get installed packages"
    except Exception as e:
        return f"❌ Error creating requirements file: {str(e)}"

def review_code(command):
    """Provide basic code review suggestions"""
    filename = extract_filename_from_command(command)
    if not filename:
        return "❌ Please specify a file to review. Example: 'review code script.py'"
    
    file_path = resolve_access_path(filename)
    if not file_path.exists():
        return f"❌ File '{file_path.name}' not found in sandbox directory ({get_base_output_dir()})"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        suggestions = []
        
        # Basic code review checks
        if filename.endswith('.py'):
            if 'import' not in content:
                suggestions.append("Consider adding necessary imports")
            if 'def main()' not in content and 'if __name__' not in content:
                suggestions.append("Consider adding a main function and proper entry point")
            if 'print(' in content and 'logging' not in content:
                suggestions.append("Consider using logging instead of print statements for production code")
        
        if len(content.split('\n')) > 100:
            suggestions.append("Consider breaking this into smaller functions or modules")
        
        if not content.strip():
            suggestions.append("File appears to be empty")
        
        if suggestions:
            return (
                f"📝 Code review for {file_path.name}:\n"
                + "\n".join([f"• {s}" for s in suggestions])
                + f"\n📁 Location: {file_path}"
            )
        else:
            return f"✅ Code review for {file_path.name}: No obvious issues found!\n📁 Location: {file_path}"
            
    except Exception as e:
        return f"❌ Error reviewing code: {str(e)}"

def format_code(command):
    """Format code using available formatters"""
    filename = extract_filename_from_command(command)
    if not filename:
        return "❌ Please specify a file to format. Example: 'format code script.py'"
    
    file_path = resolve_access_path(filename)
    if not file_path.exists():
        return f"❌ File '{file_path.name}' not found in sandbox directory ({get_base_output_dir()})"
    
    try:
        if filename.endswith('.py'):
            # Try to format Python code
            result = subprocess.run(['python', '-m', 'autopep8', '--in-place', str(file_path)], 
                                 capture_output=True, text=True)
            if result.returncode == 0:
                return f"✅ Python code formatted successfully: {file_path.name}\n📁 Location: {file_path}"
            else:
                return f"❌ Failed to format Python code. Install autopep8: pip install autopep8"
        else:
            return f"❌ Code formatting not supported for {filename}. Currently supports Python files."
    except Exception as e:
        return f"❌ Error formatting code: {str(e)}"

def get_coding_help():
    """Get help for coding commands"""
    return """💻 **Coding Assistant Help**

**📝 File Creation:**
• `create Python script` - Create a Python file with template
• `create HTML file` - Create an HTML file with template  
• `create CSS file` - Create a CSS file with template
• `create JavaScript file` - Create a JS file with template
• `create JSON file` - Create a JSON file with template

**🚀 Running Code:**
• `run python script.py` - Execute a Python script
• `install package requests` - Install Python packages

**📋 Project Management:**
• `create requirements` - Generate requirements.txt from installed packages

**🔍 Code Quality:**
• `review code script.py` - Get code review suggestions
• `format code script.py` - Format Python code (requires autopep8)

**💡 Tips:**
- All templates include best practices and modern syntax
- Use proper file extensions for better IDE support
- Install packages before running scripts that depend on them"""


def _is_file_write_request(command_lower: str) -> bool:
    """Detect natural phrases requesting file creation + content."""
    if "file" not in command_lower:
        return False

    trigger_phrases = (
        "create a file",
        "create file",
        "make a file",
        "make file",
        "generate a file",
        "generate file",
        "write to file",
        "write into file",
        "write in file",
        "write inside file",
        "in file",
        "into file",
        "add to file",
        "append to file",
    )
    if any(phrase in command_lower for phrase in trigger_phrases):
        return True

    if re.search(r"\bfile\s+(?:named|called)\s+\S+", command_lower):
        return True

    if re.search(r"\bcreate\s+(?:a\s+)?[\w\s.-]*file\b", command_lower):
        return True

    if command_lower.startswith("file "):
        return True

    return False


_STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "with", "about", "on", "of", "to",
    "in", "into", "by", "from", "write", "create", "make", "generate", "file",
    "code", "series", "please", "kindly", "bittu", "assistant"
}


def _slugify_hint(text: str, fallback: str = "notes") -> str:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    filtered = [t for t in tokens if t not in _STOPWORDS]
    if not filtered:
        filtered = tokens
    if not filtered:
        return fallback
    return "_".join(filtered[:4])


def _infer_extension(command_lower: str, instruction_lower: Optional[str]) -> str:
    text = instruction_lower or command_lower
    if any(keyword in text for keyword in ["python", "py ", "function", "script", "fibonacci"]):
        return ".py"
    if any(keyword in text for keyword in ["javascript", " js", "node", "frontend"]):
        return ".js"
    if "typescript" in text or ".tsx" in text:
        return ".tsx"
    if "react" in text or ".jsx" in text:
        return ".jsx"
    if "html" in text:
        return ".html"
    if "css" in text or "style" in text:
        return ".css"
    if "json" in text:
        return ".json"
    if "md" in text or "notes" in text or "summary" in text:
        return ".md"
    return ".txt"


def infer_default_filename(command: str, instruction: Optional[str] = None) -> Optional[str]:
    """Infer a descriptive filename when the user doesn't specify one."""
    text_for_slug = instruction or command
    base = _slugify_hint(text_for_slug, fallback="notes")
    ext = _infer_extension(command.lower(), instruction.lower() if instruction else None)
    return f"{base}{ext}"


def generate_content_from_instruction(instruction: str, filename: str) -> Optional[str]:
    """Create smart content snippets for well-known requests."""
    if not instruction:
        return None
    instruction_lower = instruction.lower()
    extension = Path(filename).suffix.lower()
    stem = Path(filename).stem
    
    if "fibonacci" in instruction_lower:
        if extension in (".py", ".pyw", "") or "python" in instruction_lower:
            return _python_fibonacci_template()
        if extension in (".js", ".jsx", ".ts", ".tsx") or "javascript" in instruction_lower:
            return _js_fibonacci_template()
    
    if (
        "react" in instruction_lower
        or "react" in stem.lower()
        or extension in (".jsx", ".tsx")
    ):
        if extension in (".jsx", ".js"):
            return _react_component_template(stem, is_typescript=False)
        if extension in (".tsx", ".ts"):
            return _react_component_template(stem, is_typescript=True)
        return _react_summary()
    
    if "mern" in instruction_lower or "mern" in stem.lower():
        return _mern_summary()
    
    return None


def _python_fibonacci_template() -> str:
    return textwrap.dedent(
        """\
        \"\"\"Fibonacci sequence utilities.\"\"\"

        from functools import lru_cache


        @lru_cache(maxsize=None)
        def fibonacci(n: int) -> int:
            if n < 0:
                raise ValueError("n must be non-negative")
            if n in (0, 1):
                return n
            return fibonacci(n - 1) + fibonacci(n - 2)


        def generate_series(length: int) -> list[int]:
            return [fibonacci(i) for i in range(length)]


        if __name__ == "__main__":
            series = generate_series(10)
            print("Fibonacci series:", ", ".join(str(num) for num in series))
        """
    ).strip()


def _js_fibonacci_template() -> str:
    return textwrap.dedent(
        """\
        // Fibonacci series generator
        const fibonacci = (n) => {
          if (n < 0) {
            throw new Error("n must be non-negative");
          }
          if (n <= 1) return n;
          let prev = 0;
          let curr = 1;
          for (let i = 2; i <= n; i += 1) {
            [prev, curr] = [curr, prev + curr];
          }
          return curr;
        };

        export const generateSeries = (length = 10) =>
          Array.from({ length }, (_, idx) => fibonacci(idx));

        console.log("Fibonacci series:", generateSeries(10).join(", "));
        """
    ).strip()


def _react_component_template(stem: str, is_typescript: bool) -> str:
    component_name = _derive_component_name(stem)
    if is_typescript:
        template = textwrap.dedent(
            """\
            import { FC, useState } from "react";

            const COMPONENT_NAME: FC = () => {
              const [count, setCount] = useState(0);

              return (
                <main className="app-shell">
                  <header>
                    <h1>COMPONENT_NAME</h1>
                    <p>Starter React component generated by Bittu.</p>
                  </header>

                  <section className="card">
                    <p>Button clicks: {count}</p>
                    <button onClick={() => setCount((value) => value + 1)}>
                      Increment
                    </button>
                  </section>
                </main>
              );
            };

            export default COMPONENT_NAME;
            """
        ).strip()
    else:
        template = textwrap.dedent(
            """\
            import { useState } from "react";

            const COMPONENT_NAME = () => {
              const [count, setCount] = useState(0);

              return (
                <main className="app-shell">
                  <header>
                    <h1>COMPONENT_NAME</h1>
                    <p>Starter React component generated by Bittu.</p>
                  </header>

                  <section className="card">
                    <p>Button clicks: {count}</p>
                    <button onClick={() => setCount((value) => value + 1)}>
                      Increment
                    </button>
                  </section>
                </main>
              );
            };

            export default COMPONENT_NAME;
            """
        ).strip()

    return template.replace("COMPONENT_NAME", component_name)


def _react_summary() -> str:
    return textwrap.dedent(
        """\
        # React Overview

        React is an open-source JavaScript library for building user interfaces.
        Key ideas:
        • Declarative UI components that react to data changes
        • A virtual DOM diffing algorithm for fast rendering
        • One-way data flow that keeps state predictable
        • Rich ecosystem (hooks, router, context, suspense, server components)
        • Works with tooling like Vite, Next.js, Remix, Expo, and React Native

        Typical workflow:
        1. Break the UI into reusable components
        2. Pass data via props; store shared state with hooks or context
        3. Compose components to build complete experiences
        """
    ).strip()


def _mern_summary() -> str:
    return textwrap.dedent(
        """\
        # MERN Stack Cheat Sheet

        **M**ongoDB — Document-oriented database for flexible JSON-like storage.
        **E**xpress.js — Minimal Node.js framework for building APIs and middleware.
        **R**eact — Front-end library focused on modular, state-driven UI.
        **N**ode.js — JavaScript runtime that powers the backend.

        Recommended project structure:
        /client  → React app (Vite or CRA)
        /server  → Express app with routes, controllers, services
        /config  → Environment variables and database connection helpers

        Essential practices:
        • Use Mongoose models + schemas for validation
        • Secure APIs with JWT or session cookies
        • Centralize error handling and logging
        • Split production builds for client/server and deploy separately
        """
    ).strip()


def _derive_component_name(stem: str) -> str:
    candidate = re.sub(r"[^0-9a-zA-Z]+", " ", stem).title().replace(" ", "")
    return candidate or "GeneratedComponent"

def extract_filename_from_command(command):
    """Extract filename from command (preserves original casing)."""
    patterns = [
        r'create\s+(?:a\s+)?file\s+(?:named\s+|called\s+)?([^\s]+)',
        r'create\s+\w+\s+file\s+(?:named\s+|called\s+)?([^\s]+)',
        r'create\s+\w+\s+(?:named\s+|called\s+)?([^\s]+)',
        r'in\s+file\s+(?:named\s+|called\s+)?([^\s]+)',
        r'write\s+to\s+file\s+(?:named\s+|called\s+)?([^\s]+)',
        r'write\s+into\s+file\s+(?:named\s+|called\s+)?([^\s]+)',
        r'file\s+(?:named\s+|called\s+)?([^\s]+)\s+with',
        r'run\s+python\s+([^\s]+)',
        r'execute\s+python\s+([^\s]+)',
        r'review\s+code\s+([^\s]+)',
        r'format\s+code\s+([^\s]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, command, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    
    tokens = command.split()
    for i, token in enumerate(tokens[:-1]):
        if token.lower() == "file":
            return tokens[i + 1]
    
    return None

def extract_file_content(command):
    """Extract inline content specified via 'with content ...'"""
    command_lower = command.lower()
    markers = [
        "with content",
        "with text",
        "containing",
        "content",
        "text",
        "write about",
        "and write about",
        "and write",
        "write in",
        "write into",
        "write to",
        "write",
    ]
    for marker in markers:
        idx = command_lower.find(marker)
        if idx != -1:
            content = command[idx + len(marker):].strip(" :\"'`")
            if not content:
                continue
            # Remove trailing phrases like "in that file" or "into that file"
            content = re.sub(r'\s+(?:in|into|to)\s+(?:that\s+)?file.*$', '', content, flags=re.IGNORECASE)
            # Remove leading filler words
            content = re.sub(r'^(?:about|text|content)\s+', '', content, flags=re.IGNORECASE)
            if content:
                return content
    return None

def extract_package_name(command):
    """Extract package name from install command"""
    patterns = [
        r'install package (\S+)',
        r'pip install (\S+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, command.lower())
        if match:
            return match.group(1)
    return None
