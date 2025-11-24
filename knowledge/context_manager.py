# knowledge/context_manager.py
"""Manages conversation and situational context"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque
from knowledge.memory_db import MemoryDB

class ContextManager:
    """Maintains conversation and situational context"""
    
    def __init__(self, memory_db: MemoryDB, max_context_length: int = 10):
        self.memory_db = memory_db
        self.db = memory_db  # Alias for compatibility
        self.conversation_history: deque = deque(maxlen=max_context_length)
        self.current_session_start = datetime.now()
        self._last_command_time = None
    
    def add_to_context(self, command: str, response: str, success: bool):
        """Add interaction to conversation context"""
        context_entry = {
            "command": command,
            "response": response,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        self.conversation_history.append(context_entry)
        self._last_command_time = datetime.now()
    
    def get_context(self) -> Dict:
        """Get current context information"""
        now = datetime.now()
        hour = now.hour
        
        # Calculate time since last command
        time_since_last = None
        if self._last_command_time:
            time_since_last = (now - self._last_command_time).total_seconds()
        
        # Get recent conversation
        recent_commands = list(self.conversation_history)[-5:]
        
        # Get session duration
        session_duration = (now - self.current_session_start).total_seconds()
        
        return {
            "hour": hour,
            "day_of_week": now.strftime("%A"),
            "time_of_day": self._get_time_of_day(hour),
            "session_duration": session_duration,
            "time_since_last_command": time_since_last,
            "recent_commands": recent_commands,
            "conversation_length": len(self.conversation_history)
        }
    
    def get_relevant_history(self, current_command: str, limit: int = 3) -> List[Dict]:
        """Get relevant conversation history for current command"""
        relevant = []
        cmd_lower = current_command.lower()
        
        # Look for related commands in history
        for entry in self.conversation_history:
            entry_cmd = entry["command"].lower()
            # Check for keyword overlap
            cmd_words = set(cmd_lower.split())
            entry_words = set(entry_cmd.split())
            if cmd_words & entry_words:  # Intersection
                relevant.append(entry)
                if len(relevant) >= limit:
                    break
        
        return relevant
    
    def should_maintain_context(self) -> bool:
        """Determine if we should maintain conversation context"""
        if not self._last_command_time:
            return False
        
        time_since = (datetime.now() - self._last_command_time).total_seconds()
        # Maintain context if last command was within 5 minutes
        return time_since < 300
    
    def get_session_summary(self) -> Dict:
        """Get summary of current session"""
        successful = sum(1 for e in self.conversation_history if e["success"])
        failed = len(self.conversation_history) - successful
        
        return {
            "total_commands": len(self.conversation_history),
            "successful": successful,
            "failed": failed,
            "session_start": self.current_session_start.isoformat(),
            "common_themes": self._detect_session_themes()
        }
    
    def _detect_session_themes(self) -> List[str]:
        """Detect common themes in current session"""
        from collections import Counter
        
        themes = []
        action_words = []
        
        for entry in self.conversation_history:
            cmd = entry["command"].lower()
            words = cmd.split()
            if words:
                action_words.append(words[0])  # First word is usually the action
        
        if action_words:
            counter = Counter(action_words)
            themes = [word for word, count in counter.most_common(3)]
        
        return themes
    
    def _get_time_of_day(self, hour: int) -> str:
        """Categorize time of day"""
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"
    
    def clear_context(self):
        """Clear conversation context (e.g., new session)"""
        self.conversation_history.clear()
        self.current_session_start = datetime.now()
        self._last_command_time = None
    
    def get_contextual_suggestion(self) -> Optional[str]:
        """Get suggestion based on current context"""
        context = self.get_context()
        
        # Suggest based on time
        if context["time_of_day"] == "morning":
            # Check if user typically checks email in morning
            patterns = self.db.get_time_based_patterns(hour=context["hour"])
            if patterns:
                for pattern in patterns:
                    if "email" in pattern["command"].lower() or "gmail" in pattern["command"].lower():
                        if pattern["frequency"] >= 3:
                            return pattern["command"]
        
        # Suggest based on recent commands
        if self.conversation_history:
            last_cmd = self.conversation_history[-1]["command"]
            associations = self.db.get_associations(last_cmd, limit=1)
            if associations:
                return associations[0]["associated_command"]
        
        return None

