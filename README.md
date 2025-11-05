# Personal AI Assistant

A powerful command-line personal assistant built with Python that works like ChatGPT and can help you with various tasks including opening apps, coding, file operations, and more.

## Features

### 🌐 **Application Management**
- **Web Apps**: YouTube, Google, Gmail, GitHub, Stack Overflow, Reddit, Netflix, Spotify
- **Development Tools**: VS Code, PyCharm, Sublime Text, Atom, Terminal
- **System Utilities**: Notepad, Calculator, File Explorer, Task Manager, Settings
- **Office Apps**: Word, Excel, PowerPoint
- **Entertainment**: Steam, Discord

### 🌤️ **Weather & Information**
- Get current weather for any city worldwide
- Free weather service (wttr.in) with OpenWeatherMap fallback

### ⏰ **Productivity**
- Set timed reminders for tasks
- Conversation memory and context awareness
- Smart command recognition

### 💻 **Coding & Development**
- Create Python, HTML, CSS, JavaScript, JSON files with templates
- Run Python scripts
- Install Python packages
- Code review and formatting
- Generate requirements.txt files

### 📁 **File Operations**
- Create files and folders
- Navigate directories
- List directory contents
- Execute system commands safely

### 💬 **AI Conversation**
- ChatGPT-like conversation with memory
- Context-aware responses
- Fallback responses when API is unavailable

### 🖥️ **System Controls (Windows)**
- Timers: "set a timer for 1 minute", "timer 10s"
- Restart: "restart now", "reboot now"
- Shutdown: "shutdown now"
- Sleep: "sleep now"
- Lock: "lock screen"
- Log off: "log off now"

Safety notes:
- Destructive actions (shutdown/restart/logoff) require confirmation using "now" (or force flags). Example: `restart now`.
- Sleep/lock may depend on system policies. On some systems, sleep requires hibernation to be enabled.

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Keys**:
   - Copy `env_template.txt` to `.env`
   - Add your API keys:
     - `OPENAI_API_KEY`: Get from https://platform.openai.com/api-keys
     - `OPENWEATHER_API_KEY`: Get from https://openweathermap.org/api

3. **Run the Assistant**:
   ```bash
   python main.py
   ```

## Usage Examples

### 🌐 **Opening Applications**
- `open youtube` - Opens YouTube in your browser
- `launch vs code` - Opens VS Code
- `start calculator` - Opens Calculator
- `run terminal` - Opens Terminal

### 🌤️ **Weather Information**
- `weather in London` - Gets weather for London
- `weather in New York` - Gets weather for New York

### ⏰ **Reminders**
- `remind me to call mom in 30 minutes` - Sets a reminder
- `remind me to check email in 1 hour` - Sets a reminder

### 📁 **File Operations**
- `create file test.txt` - Creates a new file
- `create folder myfolder` - Creates a new folder
- `list files` - Shows files in current directory
- `cd Documents` - Navigates to Documents folder

### 💻 **Coding & Development**
- `create Python script` - Creates a Python file with template
- `create HTML file` - Creates an HTML file with template
- `create CSS file` - Creates a CSS file with template
- `create JavaScript file` - Creates a JS file with template
- `run python script.py` - Executes a Python script
- `install package requests` - Installs Python packages
- `review code script.py` - Reviews code for improvements

### 💬 **General Commands**
- `help` - Shows available commands
- `what can you do` - Shows capabilities
- `clear` - Clears the screen
- `exit` or `quit` - Exits the assistant
- Ask me anything! - General conversation and questions

## Project Structure

```
personal assistant/
├── core/
│   └── brain.py              # Enhanced command processing with intent recognition
├── interface/
│   └── cli_interface.py      # Enhanced CLI with better formatting
├── knowledge/
│   └── llm_connector.py      # Enhanced LLM with conversation memory
├── skills/
│   ├── open_apps.py          # Expanded app opening (50+ applications)
│   ├── weather_info.py       # Weather API integration
│   ├── reminder_manager.py   # Reminder system
│   └── coding_assistant.py   # NEW: Coding and development tools
├── main.py                   # Enhanced entry point
├── test_assistant.py         # NEW: Test suite
├── requirements.txt          # Updated dependencies
└── env_template.txt          # Environment variables template
```

## Advanced Features

### 🧠 **Smart Command Recognition**
- Natural language processing for commands
- Context-aware responses
- Multiple ways to express the same command

### 💾 **Conversation Memory**
- Remembers previous conversation context
- Maintains conversation history
- Context-aware AI responses

### 🛡️ **Safety Features**
- Safe system command execution with timeouts
- Error handling and graceful fallbacks
- Input validation and sanitization

### 🎨 **Enhanced User Experience**
- Beautiful CLI interface with emojis and formatting
- Loading indicators for long operations
- Success/error message formatting
- Interactive help system

## Notes

- The reminder system uses threading to avoid blocking the main application
- Weather functionality works with free service (wttr.in) and optional OpenWeather API key
- AI responses work with OpenAI API key or fallback to local responses
- All file operations are performed in the current working directory
- The assistant runs in a loop until you type 'exit' or 'quit'
- Test the assistant with: `python test_assistant.py`
