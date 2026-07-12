"""智能经验池 - 支持重要性评分、时效衰减、主动遗忘"""
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger
from infrastructure.config_manager import config
from infrastructure.database_manager import DatabaseManager


class SmartExperiencePool:
    """智能经验池"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.get("memory.long_term.db_path", "data/experience_pool.db")
        self._init_db()
        
        self.decay_rate = config.get("experience.decay_rate", 0.01)
        self.importance_threshold = config.get("experience.importance_threshold", 0.3)
        self.max_experiences = config.get("memory.long_term.max_experiences", 10000)
        self.cleanup_interval = config.get("experience.cleanup_interval", 100)
        self.add_count = 0
    
    def _init_db(self):
        db = DatabaseManager.get(self.db_path)
        db.execute('''CREATE TABLE IF NOT EXISTS experiences (
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
                importance REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0
            )''', commit=True)
        
        for column, definition in [
            ("importance", "REAL DEFAULT 0.5"),
            ("access_count", "INTEGER DEFAULT 0")
        ]:
            try:
                db.execute(f'ALTER TABLE experiences ADD COLUMN {column} {definition}', commit=True)
            except Exception:
                pass
        
        db.execute('CREATE INDEX IF NOT EXISTS idx_intent ON experiences(intent_type)', commit=True)
        db.execute('CREATE INDEX IF NOT EXISTS idx_score ON experiences(quality_score)', commit=True)
        db.execute('CREATE INDEX IF NOT EXISTS idx_importance ON experiences(importance)', commit=True)
        db.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON experiences(timestamp)', commit=True)
    
    def add_experience(self, intent_type: str, raw_input: str, plan: str,
                       model_name: str, quality_score: int, user_feedback: int,
                       success: bool, duration: float):
        importance = self._calculate_importance(
            quality_score=quality_score, user_feedback=user_feedback,
            success=success, duration=duration, intent_type=intent_type
        )
        
        db = DatabaseManager.get(self.db_path)
        db.execute('''INSERT INTO experiences 
            (timestamp, intent_type, raw_input, plan, model_name,
             quality_score, user_feedback, success, duration, importance, access_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)''',
            (datetime.now().isoformat(), intent_type, raw_input, plan,
             model_name, quality_score, user_feedback, success, duration, importance),
            commit=True)
        
        logger.debug(f"经验已存储: {intent_type}, 质量{quality_score}, 重要性{importance:.3f}")
        self.add_count += 1
        
        if self.add_count % self.cleanup_interval == 0:
            self._auto_cleanup()
    
    def _calculate_importance(self, quality_score: int, user_feedback: int,
                             success: bool, duration: float, intent_type: str) -> float:
        quality_weight = quality_score / 100.0
        feedback_weight = (user_feedback + 1) / 2 if user_feedback is not None else 0.5
        success_weight = 1.0 if success else 0.3
        frequency = self._get_task_frequency(intent_type)
        frequency_weight = min(frequency / 10.0, 1.0)
        efficiency_weight = max(0, 1 - (duration / 30.0))
        
        return (0.35 * quality_weight + 0.25 * feedback_weight + 0.15 * success_weight
                + 0.15 * frequency_weight + 0.10 * efficiency_weight)
    
    def _get_task_frequency(self, intent_type: str) -> int:
        db = DatabaseManager.get(self.db_path)
        row = db.query_one('SELECT COUNT(*) FROM experiences WHERE intent_type = ?', (intent_type,))
        return row[0] if row else 0
    
    def _auto_cleanup(self):
        logger.info("开始自动清理经验池...")
        deleted = self._delete_low_importance()
        trimmed = self._trim_to_max_size()
        logger.info(f"清理完成: 删除{deleted}条, 裁剪{trimmed}条")
    
    def _delete_low_importance(self) -> int:
        db = DatabaseManager.get(self.db_path)
        cur = db.execute('DELETE FROM experiences WHERE importance < ?',
                         (self.importance_threshold,), commit=True)
        deleted = cur.rowcount
        cur = db.execute('''DELETE FROM experiences 
            WHERE success = 0 
              AND (user_feedback IS NULL OR user_feedback <= 0)
              AND id NOT IN (
                  SELECT id FROM experiences WHERE success = 0 
                  ORDER BY timestamp DESC LIMIT 100
              )''', commit=True)
        deleted += cur.rowcount
        return deleted
    
    def _trim_to_max_size(self) -> int:
        db = DatabaseManager.get(self.db_path)
        row = db.query_one('SELECT COUNT(*) FROM experiences')
        total = row[0] if row else 0
        if total > self.max_experiences:
            excess = total - self.max_experiences
            db.execute('''DELETE FROM experiences WHERE id IN (
                SELECT id FROM experiences ORDER BY importance ASC, timestamp ASC LIMIT ?
            )''', (excess,), commit=True)
            return excess
        return 0
    
    def get_high_quality_experiences(self, intent_type: str = None, 
                                     min_quality: int = 70, limit: int = 100):
        query = 'SELECT id, intent_type, raw_input, plan, model_name, quality_score, user_feedback, importance FROM experiences WHERE quality_score >= ?'
        params = [min_quality]
        if intent_type:
            query += ' AND intent_type = ?'
            params.append(intent_type)
        query += ' ORDER BY importance DESC, quality_score DESC LIMIT ?'
        params.append(limit)
        
        db = DatabaseManager.get(self.db_path)
        rows = db.query(query, params)
        for row in rows:
            try:
                db.execute('UPDATE experiences SET access_count = access_count + 1 WHERE id = ?', (row[0],), commit=True)
            except Exception:
                pass
        return [dict(r) for r in rows]
    
    def get_failed_experiences(self, intent_type: str = None, limit: int = 50):
        query = 'SELECT intent_type, raw_input, plan, model_name, quality_score, user_feedback FROM experiences WHERE quality_score < 50 AND (user_feedback IS NULL OR user_feedback <= 0)'
        params = []
        if intent_type:
            query += ' AND intent_type = ?'
            params.append(intent_type)
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        db = DatabaseManager.get(self.db_path)
        rows = db.query(query, params)
        return [dict(r) for r in rows]
    
    def get_statistics(self) -> Dict:
        db = DatabaseManager.get(self.db_path)
        total = db.query_one('SELECT COUNT(*) FROM experiences')[0]
        by_type_rows = db.query('SELECT intent_type, COUNT(*) as count, AVG(quality_score) as avg_quality FROM experiences GROUP BY intent_type')
        by_type = {row[0]: {"count": row[1], "avg_quality": row[2]} for row in by_type_rows}
        avg_importance = db.query_one('SELECT AVG(importance) FROM experiences')[0] or 0
        high_quality = db.query_one('SELECT COUNT(*) FROM experiences WHERE quality_score >= 70')[0]
        success_rate = db.query_one('SELECT AVG(CASE WHEN success THEN 1.0 ELSE 0 END) FROM experiences')[0] or 0
        
        return {
            "total": total, "by_intent_type": by_type, "avg_importance": avg_importance,
            "high_quality_ratio": high_quality / total if total > 0 else 0,
            "success_rate": success_rate, "max_capacity": self.max_experiences,
            "utilization": total / self.max_experiences if self.max_experiences > 0 else 0
        }
    
    def manual_cleanup(self):
        self._auto_cleanup()


ExperiencePool = SmartExperiencePool
