# skills/coding_assistant.py
import os
import re
import subprocess
from datetime import datetime

def handle(command):
    """Handle coding-related commands"""
    command_lower = command.lower()
    
    if "create python script" in command_lower or "create py file" in command_lower:
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
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(template)
        return f"✅ Created Python script: {filename}\n💡 Template includes main function and proper structure"
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
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(template)
        return f"✅ Created HTML file: {filename}\n💡 Template includes responsive design and modern styling"
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
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(template)
        return f"✅ Created CSS file: {filename}\n💡 Template includes modern CSS with utility classes"
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
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(template)
        return f"✅ Created JavaScript file: {filename}\n💡 Template includes modern ES6+ syntax and app structure"
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
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(template)
        return f"✅ Created JSON file: {filename}\n💡 Template includes proper JSON structure with metadata"
    except Exception as e:
        return f"❌ Error creating JSON file: {str(e)}"

def run_python_script(command):
    """Run a Python script"""
    script_name = extract_filename_from_command(command)
    if not script_name:
        return "❌ Please specify a Python script to run. Example: 'run python script.py'"
    
    if not script_name.endswith('.py'):
        script_name += '.py'
    
    if not os.path.exists(script_name):
        return f"❌ Script '{script_name}' not found in current directory"
    
    try:
        result = subprocess.run(['python', script_name], 
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
            with open('requirements.txt', 'w') as f:
                f.write(result.stdout)
            return "✅ Created requirements.txt with all installed packages"
        else:
            return "❌ Failed to get installed packages"
    except Exception as e:
        return f"❌ Error creating requirements file: {str(e)}"

def review_code(command):
    """Provide basic code review suggestions"""
    filename = extract_filename_from_command(command)
    if not filename:
        return "❌ Please specify a file to review. Example: 'review code script.py'"
    
    if not os.path.exists(filename):
        return f"❌ File '{filename}' not found"
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
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
            return f"📝 Code review for {filename}:\n" + "\n".join([f"• {s}" for s in suggestions])
        else:
            return f"✅ Code review for {filename}: No obvious issues found!"
            
    except Exception as e:
        return f"❌ Error reviewing code: {str(e)}"

def format_code(command):
    """Format code using available formatters"""
    filename = extract_filename_from_command(command)
    if not filename:
        return "❌ Please specify a file to format. Example: 'format code script.py'"
    
    if not os.path.exists(filename):
        return f"❌ File '{filename}' not found"
    
    try:
        if filename.endswith('.py'):
            # Try to format Python code
            result = subprocess.run(['python', '-m', 'autopep8', '--in-place', filename], 
                                 capture_output=True, text=True)
            if result.returncode == 0:
                return f"✅ Python code formatted successfully: {filename}"
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

def extract_filename_from_command(command):
    """Extract filename from command"""
    patterns = [
        r'create \w+ file (\S+)',
        r'create \w+ (\S+)',
        r'run python (\S+)',
        r'execute python (\S+)',
        r'review code (\S+)',
        r'format code (\S+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, command.lower())
        if match:
            return match.group(1)
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
