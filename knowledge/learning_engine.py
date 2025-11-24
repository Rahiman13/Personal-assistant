# knowledge/learning_engine.py
"""Pattern recognition and learning algorithms"""
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import Counter
from knowledge.memory_db import MemoryDB

class LearningEngine:
    """Analyzes experiences and learns patterns"""
    
    def __init__(self, memory_db: MemoryDB):
        self.memory_db = memory_db
        self.db = memory_db  # Alias for compatibility
        self._last_command = None
        self._last_command_time = None
    
    def analyze_command(self, command: str, success: bool, response_text: str = "",
                       context: Optional[Dict] = None) -> Dict:
        """Analyze a command and extract learning opportunities"""
        context = context or {}
        timestamp = datetime.now()
        
        # Extract context
        hour = timestamp.hour
        day_of_week = timestamp.strftime("%A")
        
        # Update context
        context.update({
            "hour": hour,
            "day_of_week": day_of_week,
            "time_of_day": self._get_time_of_day(hour)
        })
        
        # Learn command associations
        if self._last_command:
            time_delta = None
            if self._last_command_time:
                time_delta = (timestamp - self._last_command_time).total_seconds()
            self.db.record_association(self._last_command, command, time_delta)
        
        # Detect patterns
        self._detect_patterns(command, success, context)
        
        # Update last command
        self._last_command = command.lower().strip()
        self._last_command_time = timestamp
        
        return {
            "learned": True,
            "context": context
        }
    
    def _detect_patterns(self, command: str, success: bool, context: Dict):
        """Detect various types of patterns"""
        cmd_lower = command.lower().strip()
        hour = context.get("hour", 0)
        time_of_day = context.get("time_of_day", "unknown")
        
        # Time-based pattern
        if success:
            pattern_data = {
                "command": cmd_lower,
                "hour": hour,
                "time_of_day": time_of_day,
                "day_of_week": context.get("day_of_week")
            }
            confidence = 0.4  # Start with low confidence
            self.db.save_pattern("time_based", pattern_data, frequency=1, confidence=confidence)
        
        # Command abbreviation pattern (if user shortens over time)
        if len(cmd_lower.split()) <= 3:
            # Check if there's a longer version of this command
            experiences = self.db.get_experiences(limit=50, command_filter=cmd_lower.split()[0] if cmd_lower.split() else "")
            if len(experiences) > 5:
                # Pattern: user is using shorter version consistently
                pattern_data = {
                    "short_command": cmd_lower,
                    "base_action": cmd_lower.split()[0] if cmd_lower.split() else cmd_lower
                }
                self.db.save_pattern("abbreviation", pattern_data, frequency=1, confidence=0.3)
    
    def suggest_command(self, partial_command: str, context: Optional[Dict] = None) -> List[str]:
        """Suggest commands based on partial input and history"""
        suggestions = []
        partial_lower = partial_command.lower().strip()
        
        # Get frequent commands that match
        frequent = self.db.get_command_frequency(limit=50)
        for item in frequent:
            cmd = item["command"]
            if partial_lower in cmd.lower() or cmd.lower().startswith(partial_lower):
                suggestions.append(cmd)
                if len(suggestions) >= 5:
                    break
        
        # Get associations
        if partial_command:
            associations = self.db.get_associations(partial_command, limit=3)
            for assoc in associations:
                if assoc["associated_command"] not in suggestions:
                    suggestions.append(assoc["associated_command"])
        
        return suggestions[:5]
    
    def get_time_based_suggestion(self, hour: Optional[int] = None) -> Optional[str]:
        """Get suggestion based on current time"""
        if hour is None:
            hour = datetime.now().hour
        
        patterns = self.db.get_time_based_patterns(hour=hour)
        
        if patterns:
            # Return most frequent command at this hour
            return patterns[0]["command"]
        return None
    
    def learn_from_feedback(self, command: str, feedback: str, correction: Optional[str] = None):
        """Learn from user feedback or corrections"""
        cmd_lower = command.lower().strip()
        
        # Negative feedback
        if "wrong" in feedback.lower() or "incorrect" in feedback.lower() or "no" in feedback.lower():
            # Lower confidence for this command pattern
            experiences = self.db.get_experiences(limit=10, command_filter=cmd_lower)
            if experiences:
                # Mark related experiences as needing review
                self.db.save_preference(
                    "command_correction",
                    cmd_lower,
                    f"Feedback: {feedback}",
                    confidence=0.2,
                    learned_from="user_feedback"
                )
        
        # Positive feedback
        if "correct" in feedback.lower() or "yes" in feedback.lower() or "good" in feedback.lower():
            self.db.save_preference(
                "command_validation",
                cmd_lower,
                "Confirmed correct",
                confidence=0.9,
                learned_from="user_feedback"
            )
        
        # Correction provided
        if correction:
            self.db.save_preference(
                "command_correction",
                cmd_lower,
                correction,
                confidence=0.8,
                learned_from="user_correction"
            )
    
    def predict_next_command(self, current_command: str) -> Optional[str]:
        """Predict what user might want next based on current command"""
        associations = self.db.get_associations(current_command, limit=1)
        if associations:
            return associations[0]["associated_command"]
        return None
    
    def get_personalized_response(self, command: str) -> Optional[str]:
        """Get personalized response based on learned preferences"""
        cmd_lower = command.lower().strip()
        
        # Check for learned preferences
        pref = self.db.get_preference("command_style", cmd_lower)
        if pref and pref["confidence"] > 0.6:
            return pref["value"]
        
        return None
    
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
    
    def analyze_user_habits(self) -> Dict:
        """Analyze overall user habits and return insights"""
        habits = {
            "most_common_commands": self.db.get_command_frequency(limit=10),
            "time_patterns": self.db.get_time_based_patterns(),
            "preferences": self.db.get_all_preferences()
        }
        return habits
    
    def should_auto_suggest(self, time_since_last_command: float) -> bool:
        """Determine if we should proactively suggest commands"""
        # Suggest if it's been a while and we have time-based patterns
        if time_since_last_command > 300:  # 5 minutes
            hour = datetime.now().hour
            patterns = self.db.get_time_based_patterns(hour=hour)
            if patterns and patterns[0]["frequency"] >= 3:
                return True
        return False

