# Continuous Learning System Documentation

## Overview
Bittu now has a complete continuous learning system that learns from every interaction and improves over time.

## Features

### 1. **Memory & Experience Storage**
- All commands are logged to SQLite database (`bittu_memory.db`)
- Tracks: command text, timestamp, success/failure, response time, context
- Persistent storage across sessions

### 2. **Pattern Recognition**
- **Time-based patterns**: Learns when you typically use certain commands
- **Command associations**: Remembers commands you use together
- **Command frequency**: Tracks most used commands
- **Abbreviation learning**: Learns your preferred command shortcuts

### 3. **User Preferences**
- **App preferences**: Remembers how you like to open apps
- **Command variants**: Learns your preferred command phrasing
- **Response style**: Adapts to your communication preferences

### 4. **Context Awareness**
- Maintains conversation history
- Tracks session context
- Time-of-day awareness
- Day-of-week patterns

## Usage Commands

### Learning Commands
- `remember [something]` - Explicitly remember something
  - Example: `remember I prefer Chrome browser`
- `learn [something]` - Same as remember

### Viewing Learned Data
- `show my habits` - View your usage patterns
- `my habits` - Same as above
- `what do you know about me` - Same as above

### Getting Suggestions
- `suggestions` - Get contextual suggestions
- `suggest` - Same as above
- `what should i do` - Same as above

### Forgetting
- `forget [item]` - Lower confidence for a learned item
- `unlearn [item]` - Same as forget

## How It Works

### Automatic Learning
Every command you give is automatically:
1. Logged to the database
2. Analyzed for patterns
3. Used to update preferences
4. Added to conversation context

### Pattern Detection
The system detects:
- **Time patterns**: "User opens YouTube at 6 PM daily"
- **Sequential patterns**: "After opening VS Code, user opens terminal"
- **Command clusters**: Groups of related commands
- **Success patterns**: What works best for you

### Preference Learning
Learns:
- Favorite apps and websites
- Preferred command phrasing
- Response style preferences
- Contextual behaviors

## Database Structure

### Tables
1. **experiences** - All command interactions
2. **preferences** - Learned user preferences
3. **patterns** - Detected behavioral patterns
4. **command_associations** - Links between commands

## Integration

The learning system is automatically integrated:
- All commands go through `process_command_with_learning()`
- Works in both CLI and web UI
- Voice commands are also learned
- No additional setup required

## Example Learning Flow

1. User: `open youtube`
   - System logs: command, time, success
   - Learns: YouTube opening preference

2. User: `open youtube` (again at similar time)
   - System detects: Time-based pattern
   - Increases confidence in pattern

3. User: `open youtube and play believer`
   - System learns: Command association
   - Remembers: "youtube" + "play" combination

4. User: `show my habits`
   - System shows: Most used commands, time patterns, preferences

5. User: `suggestions`
   - System suggests: Based on time and context
   - Example: "Based on time: 'open youtube'"

## Technical Details

### Files Created
- `knowledge/memory_db.py` - Database operations
- `knowledge/learning_engine.py` - Pattern recognition
- `knowledge/preference_manager.py` - Preference handling
- `knowledge/context_manager.py` - Context management

### Integration Points
- `core/brain.py` - Main command processing
- `main.py` - CLI interface
- `interface/web_server.py` - Web interface

### Database Location
- Default: `bittu_memory.db` in project root
- SQLite database (no server required)

## Future Enhancements

Potential additions:
- Machine learning models for prediction
- Advanced clustering algorithms
- Multi-user support
- Export/import learning data
- Privacy controls
- Learning analytics dashboard

## Privacy

- All data stored locally
- No external data sharing
- User can clear learning data
- Database file can be deleted to reset

