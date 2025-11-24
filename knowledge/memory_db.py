# knowledge/memory_db.py
"""Persistent memory storage for AI learning experiences"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

class MemoryDB:
    """SQLite database for storing experiences, preferences, and patterns"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Store in project root
            project_root = Path(__file__).parent.parent
            db_path = str(project_root / "bittu_memory.db")
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
        except Exception as e:
            # If database can't be created, that's okay - learning is optional
            print(f"⚠️ Could not initialize learning database: {e}")
            return
        
        # Experiences table: stores all command interactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                success INTEGER NOT NULL,
                response_text TEXT,
                response_time REAL,
                user_feedback TEXT,
                context_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Preferences table: learned user preferences
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preference_type TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                learned_from TEXT,
                usage_count INTEGER DEFAULT 1,
                last_used TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(preference_type, key)
            )
        """)
        
        # Patterns table: detected behavioral patterns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                confidence REAL DEFAULT 0.5,
                last_seen TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Command associations: links between commands
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS command_associations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command1 TEXT NOT NULL,
                command2 TEXT NOT NULL,
                cooccurrence_count INTEGER DEFAULT 1,
                time_delta REAL,
                last_seen TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def log_experience(self, command: str, success: bool, response_text: str = "",
                      response_time: float = 0.0, context: Optional[Dict] = None,
                      user_feedback: Optional[str] = None) -> int:
        """Log a command experience"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        context_json = json.dumps(context or {})
        timestamp = datetime.now().isoformat()
        
        try:
            cursor.execute("""
                INSERT INTO experiences 
                (command, timestamp, success, response_text, response_time, user_feedback, context_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (command, timestamp, 1 if success else 0, response_text, response_time, 
                  user_feedback, context_json))
            
            experience_id = cursor.lastrowid
            conn.commit()
        except Exception as e:
            experience_id = 0
        finally:
            try:
                conn.close()
            except Exception:
                pass
        return experience_id
    
    def get_experiences(self, limit: int = 100, command_filter: Optional[str] = None) -> List[Dict]:
        """Retrieve recent experiences"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if command_filter:
            cursor.execute("""
                SELECT * FROM experiences 
                WHERE command LIKE ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (f"%{command_filter}%", limit))
        else:
            cursor.execute("""
                SELECT * FROM experiences 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_success_rate(self, command: str) -> float:
        """Get success rate for a specific command pattern"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(success) as successful
            FROM experiences 
            WHERE command LIKE ?
        """, (f"%{command}%",))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] > 0:
            return row[1] / row[0]
        return 0.5  # Default confidence
    
    def save_preference(self, preference_type: str, key: str, value: str,
                       confidence: float = 0.5, learned_from: str = "pattern"):
        """Save or update a user preference"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO preferences (preference_type, key, value, confidence, learned_from, last_used, usage_count)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(preference_type, key) DO UPDATE SET
                value = excluded.value,
                confidence = (confidence + excluded.confidence) / 2,
                usage_count = usage_count + 1,
                last_used = excluded.last_used
        """, (preference_type, key, value, confidence, learned_from, timestamp))
        
        conn.commit()
        conn.close()
    
    def get_preference(self, preference_type: str, key: str) -> Optional[Dict]:
        """Retrieve a preference"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM preferences 
            WHERE preference_type = ? AND key = ?
        """, (preference_type, key))
        
        row = cursor.fetchone()
        conn.close()
        
        return dict(row) if row else None
    
    def get_all_preferences(self, preference_type: Optional[str] = None) -> List[Dict]:
        """Get all preferences, optionally filtered by type"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if preference_type:
            cursor.execute("SELECT * FROM preferences WHERE preference_type = ?", (preference_type,))
        else:
            cursor.execute("SELECT * FROM preferences")
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def save_pattern(self, pattern_type: str, pattern_data: Dict, 
                    frequency: int = 1, confidence: float = 0.5):
        """Save or update a detected pattern"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        pattern_json = json.dumps(pattern_data)
        timestamp = datetime.now().isoformat()
        
        # Check if similar pattern exists
        cursor.execute("""
            SELECT id, frequency FROM patterns 
            WHERE pattern_type = ? AND pattern_data = ?
        """, (pattern_type, pattern_json))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing pattern
            new_freq = existing[1] + frequency
            new_conf = min(0.95, confidence + (existing[1] * 0.01))
            cursor.execute("""
                UPDATE patterns 
                SET frequency = ?, confidence = ?, last_seen = ?
                WHERE id = ?
            """, (new_freq, new_conf, timestamp, existing[0]))
        else:
            # Insert new pattern
            cursor.execute("""
                INSERT INTO patterns (pattern_type, pattern_data, frequency, confidence, last_seen)
                VALUES (?, ?, ?, ?, ?)
            """, (pattern_type, pattern_json, frequency, confidence, timestamp))
        
        conn.commit()
        conn.close()
    
    def get_patterns(self, pattern_type: Optional[str] = None, 
                    min_confidence: float = 0.3) -> List[Dict]:
        """Retrieve patterns, optionally filtered"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if pattern_type:
            cursor.execute("""
                SELECT * FROM patterns 
                WHERE pattern_type = ? AND confidence >= ?
                ORDER BY frequency DESC, confidence DESC
            """, (pattern_type, min_confidence))
        else:
            cursor.execute("""
                SELECT * FROM patterns 
                WHERE confidence >= ?
                ORDER BY frequency DESC, confidence DESC
            """, (min_confidence,))
        
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            d = dict(row)
            d['pattern_data'] = json.loads(d['pattern_data'])
            result.append(d)
        return result
    
    def record_association(self, command1: str, command2: str, time_delta: Optional[float] = None):
        """Record that two commands are often used together"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        # Ensure command1 < command2 for consistency
        if command1 > command2:
            command1, command2 = command2, command1
        
        cursor.execute("""
            INSERT INTO command_associations (command1, command2, cooccurrence_count, time_delta, last_seen)
            VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(command1, command2) DO UPDATE SET
                cooccurrence_count = cooccurrence_count + 1,
                time_delta = CASE 
                    WHEN time_delta IS NULL THEN excluded.time_delta
                    ELSE (time_delta + excluded.time_delta) / 2
                END,
                last_seen = excluded.last_seen
        """, (command1, command2, time_delta, timestamp))
        
        conn.commit()
        conn.close()
    
    def get_associations(self, command: str, limit: int = 5) -> List[Dict]:
        """Get commands frequently associated with given command"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT command2 as associated_command, cooccurrence_count, time_delta
            FROM command_associations 
            WHERE command1 = ?
            UNION
            SELECT command1 as associated_command, cooccurrence_count, time_delta
            FROM command_associations 
            WHERE command2 = ?
            ORDER BY cooccurrence_count DESC
            LIMIT ?
        """, (command, command, limit))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_command_frequency(self, limit: int = 20) -> List[Dict]:
        """Get most frequently used commands"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                command,
                COUNT(*) as frequency,
                AVG(success) as success_rate,
                MAX(timestamp) as last_used
            FROM experiences
            GROUP BY command
            ORDER BY frequency DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "command": row[0],
                "frequency": row[1],
                "success_rate": row[2],
                "last_used": row[3]
            }
            for row in rows
        ]
    
    def get_time_based_patterns(self, hour: Optional[int] = None) -> List[Dict]:
        """Get patterns based on time of day"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT 
                command,
                COUNT(*) as frequency,
                strftime('%H', timestamp) as hour
            FROM experiences
            WHERE success = 1
        """
        
        params = []
        if hour is not None:
            query += " AND strftime('%H', timestamp) = ?"
            params.append(f"{hour:02d}")
        
        query += """
            GROUP BY command, hour
            ORDER BY frequency DESC
            LIMIT 10
        """
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "command": row[0],
                "frequency": row[1],
                "hour": int(row[2])
            }
            for row in rows
        ]

