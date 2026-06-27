import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from loguru import logger

class ExperiencePool:
    def __init__(self, db_path: str = "experience_pool.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS experiences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    intent_type TEXT,
                    raw_input TEXT,
                    plan TEXT,
                    model_name TEXT,
                    quality_score INTEGER,
                    user_feedback INTEGER,
                    success BOOLEAN,
                    duration REAL,
                    response TEXT
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_intent ON experiences(intent_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_score ON experiences(quality_score)')
            
            cursor = conn.execute("PRAGMA table_info(experiences)")
            columns = [row[1] for row in cursor.fetchall()]
            
            required_columns = {
                "response": "TEXT",
                "success": "BOOLEAN",
                "duration": "REAL"
            }
            
            for col, col_type in required_columns.items():
                if col not in columns:
                    try:
                        conn.execute(f"ALTER TABLE experiences ADD COLUMN {col} {col_type}")
                        logger.info(f"  ✓ 添加字段: {col}")
                    except Exception as e:
                        logger.warning(f"  ⚠ 添加字段 {col} 失败: {e}")
            
            conn.commit()

    def add_experience(self, intent_type: str, raw_input: str, plan: str,
                       model_name: str, quality_score: int, user_feedback: int,
                       success: bool, duration: float, response: str = "") -> int:
        """添加经验并返回ID"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute('''
                INSERT INTO experiences (timestamp, intent_type, raw_input, plan, model_name,
                                         quality_score, user_feedback, success, duration, response)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (datetime.now().isoformat(), intent_type, raw_input, plan,
                  model_name, quality_score, user_feedback, success, duration, response))
            
            experience_id = cur.lastrowid
        
        logger.debug(f"经验已存储: {intent_type}, 质量 {quality_score}, ID {experience_id}")
        return experience_id
    
    def update_feedback(self, experience_id: int, feedback: int):
        """更新经验的用户反馈"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE experiences
                SET user_feedback = ?
                WHERE id = ?
            ''', (feedback, experience_id))
        
        logger.debug(f"更新经验反馈: ID {experience_id}, 反馈 {feedback}")
    
    def get_last_experience_id(self, model_name: str, intent_type: str) -> Optional[int]:
        """获取最近一次经验的ID"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute('''
                SELECT id FROM experiences
                WHERE model_name = ? AND intent_type = ?
                ORDER BY timestamp DESC LIMIT 1
            ''', (model_name, intent_type))
            
            row = cur.fetchone()
            return row[0] if row else None

    def get_high_quality_experiences(self, intent_type: str = None, min_quality: int = 70, limit: int = 100):
        """获取高质量经验用于归纳"""
        query = '''
            SELECT intent_type, raw_input, plan, model_name, quality_score, user_feedback
            FROM experiences
            WHERE quality_score >= ?
        '''
        params = [min_quality]
        if intent_type:
            query += ' AND intent_type = ?'
            params.append(intent_type)
        query += ' ORDER BY quality_score DESC LIMIT ?'
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(query, params)
            return [dict(row) for row in cur.fetchall()]

    def get_failed_experiences(self, intent_type: str = None, limit: int = 50):
        """获取失败经验（质量<50且无正面反馈）"""
        query = '''
            SELECT intent_type, raw_input, plan, model_name, quality_score, user_feedback
            FROM experiences
            WHERE quality_score < 50 AND (user_feedback IS NULL OR user_feedback <= 0)
        '''
        params = []
        if intent_type:
            query += ' AND intent_type = ?'
            params.append(intent_type)
        query += ' ORDER BY quality_score ASC LIMIT ?'
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
