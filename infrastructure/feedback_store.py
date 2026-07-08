import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from loguru import logger
from infrastructure.database_manager import DatabaseManager

class FeedbackStore:
    MAX_ENTRIES = 10000
    MAX_FIELD_LEN = 5000
    
    def __init__(self, filepath: str = "feedback.db"):
        filename = Path(filepath).name
        if not filename.endswith('.db'):
            filename = filename.rsplit('.', 1)[0] + '.db'
        
        self.filepath = Path("data/feedback") / filename
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        
        self._lock = threading.Lock()
        self._init_db()
        
        logger.info(f"反馈存储已初始化: {self.filepath}")
    
    def _init_db(self):
        db = DatabaseManager.get(str(self.filepath))
        conn = db._get_conn()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_input TEXT,
                assistant_response TEXT,
                score INTEGER
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON feedback(timestamp)')
    
    def add_feedback(self, user_input: str, assistant_response: str, score: int) -> bool:
        if not isinstance(score, int) or score not in (-1, 0, 1):
            logger.warning(f"无效评分: {score}")
            return False
        
        user_input = str(user_input)[:self.MAX_FIELD_LEN]
        assistant_response = str(assistant_response)[:self.MAX_FIELD_LEN]
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "assistant_response": assistant_response,
            "score": score
        }
        
        with self._lock:
            try:
                db = DatabaseManager.get(str(self.filepath))
                conn = db._get_conn()
                conn.execute('''
                    INSERT INTO feedback (timestamp, user_input, assistant_response, score)
                    VALUES (?, ?, ?, ?)
                ''', (entry["timestamp"], entry["user_input"], entry["assistant_response"], entry["score"]))
                
                cursor = conn.execute('SELECT COUNT(*) FROM feedback')
                count = cursor.fetchone()[0]
                
                if count > self.MAX_ENTRIES:
                    conn.execute('''
                        DELETE FROM feedback 
                        WHERE id IN (
                            SELECT id FROM feedback 
                            ORDER BY timestamp ASC 
                            LIMIT ?
                        )
                    ''', (count - self.MAX_ENTRIES,))
                
                logger.info(f"已记录反馈评分: {score}")
                return True
                
            except Exception as e:
                logger.error(f"保存反馈失败: {e}")
                return False
    
    def get_feedback(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        with self._lock:
            db = DatabaseManager.get(str(self.filepath))
            conn = db._get_conn()
            cursor = conn.execute('''
                SELECT timestamp, user_input, assistant_response, score
                FROM feedback
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            return [
                {
                    "timestamp": row[0],
                    "user_input": row[1],
                    "assistant_response": row[2],
                    "score": row[3]
                }
                for row in cursor.fetchall()
            ]
    
    def get_stats(self) -> Dict:
        with self._lock:
            db = DatabaseManager.get(str(self.filepath))
            conn = db._get_conn()
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN score > 0 THEN 1 ELSE 0 END) as positive,
                    SUM(CASE WHEN score < 0 THEN 1 ELSE 0 END) as negative
                FROM feedback
            ''')
            row = cursor.fetchone()
            
            total = row[0] if row[0] else 0
            return {
                "total": total,
                "positive": row[1] if row[1] else 0,
                "negative": row[2] if row[2] else 0,
                "satisfaction_rate": (row[1] / total * 100) if total > 0 else 0
            }
    
    def clear_old_feedback(self, days: int = 30) -> int:
        cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff = cutoff.replace(day=cutoff.day - days)
        cutoff_str = cutoff.isoformat()
        
        with self._lock:
            db = DatabaseManager.get(str(self.filepath))
            conn = db._get_conn()
            cursor = conn.execute('DELETE FROM feedback WHERE timestamp < ?', (cutoff_str,))
            deleted = cursor.rowcount
            
            if deleted > 0:
                logger.info(f"已清理 {deleted} 条旧反馈")
            
            return deleted
