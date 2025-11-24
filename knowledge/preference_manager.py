# knowledge/preference_manager.py
"""Manages user preferences and personalization"""
from typing import Dict, List, Optional
from knowledge.memory_db import MemoryDB

class PreferenceManager:
    """Handles user preferences and personalization"""
    
    def __init__(self, memory_db: MemoryDB):
        self.memory_db = memory_db
        self.db = memory_db  # Alias for compatibility
    
    def get_app_preference(self, app_name: str) -> Optional[str]:
        """Get user's preference for how to open an app"""
        pref = self.db.get_preference("app_preference", app_name.lower())
        if pref and pref["confidence"] > 0.5:
            return pref["value"]
        return None
    
    def learn_app_preference(self, app_name: str, method: str, confidence: float = 0.7):
        """Learn how user prefers to open an app"""
        self.db.save_preference(
            "app_preference",
            app_name.lower(),
            method,
            confidence=confidence,
            learned_from="usage_pattern"
        )
    
    def get_command_variant(self, base_command: str) -> Optional[str]:
        """Get user's preferred variant of a command"""
        pref = self.db.get_preference("command_variant", base_command.lower())
        if pref and pref["confidence"] > 0.6:
            return pref["value"]
        return None
    
    def learn_command_variant(self, base_command: str, variant: str):
        """Learn user's preferred command variant"""
        # Check if this variant is used frequently
        experiences = self.db.get_experiences(limit=50, command_filter=variant)
        frequency = len(experiences)
        
        confidence = min(0.9, 0.5 + (frequency * 0.05))
        
        self.db.save_preference(
            "command_variant",
            base_command.lower(),
            variant,
            confidence=confidence,
            learned_from="frequency"
        )
    
    def get_response_style(self) -> Dict:
        """Get user's preferred response style"""
        prefs = self.db.get_all_preferences("response_style")
        style = {
            "verbosity": "normal",
            "use_emoji": True,
            "confirmation": True
        }
        
        for pref in prefs:
            if pref["confidence"] > 0.6:
                style[pref["key"]] = pref["value"]
        
        return style
    
    def learn_response_preference(self, key: str, value: str):
        """Learn user's response preferences"""
        self.db.save_preference(
            "response_style",
            key,
            value,
            confidence=0.7,
            learned_from="explicit"
        )
    
    def get_all_preferences(self) -> Dict[str, List[Dict]]:
        """Get all learned preferences organized by type"""
        all_prefs = self.db.get_all_preferences()
        
        organized = {}
        for pref in all_prefs:
            ptype = pref["preference_type"]
            if ptype not in organized:
                organized[ptype] = []
            organized[ptype].append(pref)
        
        return organized
    
    def apply_preferences_to_command(self, command: str) -> str:
        """Apply learned preferences to modify a command"""
        cmd_lower = command.lower().strip()
        
        # Check for command variants
        base_action = cmd_lower.split()[0] if cmd_lower.split() else cmd_lower
        variant = self.get_command_variant(base_action)
        if variant:
            # Replace base with preferred variant
            if cmd_lower.startswith(base_action):
                return cmd_lower.replace(base_action, variant, 1)
        
        return command
    
    def should_remember(self, command: str) -> bool:
        """Determine if we should explicitly remember this command"""
        # Remember if it's a new command or important action
        experiences = self.db.get_experiences(limit=10, command_filter=command)
        
        if len(experiences) == 0:
            return True  # New command
        
        # Remember if it's a system-changing action
        important_keywords = ["shutdown", "restart", "lock", "delete", "create"]
        if any(kw in command.lower() for kw in important_keywords):
            return True
        
        return False

