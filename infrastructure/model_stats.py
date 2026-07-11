import sqlite3
from datetime import datetime
from loguru import logger
from infrastructure.database_manager import DatabaseManager

class ModelStats:
    def __init__(self, db_path: str = "model_stats.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS model_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT,
                task_type TEXT,
                duration REAL,
                success BOOLEAN,
                user_feedback INTEGER,
                quality_score INTEGER,
                timestamp TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER
            )
        ''')
        try:
            db.execute('ALTER TABLE model_performance ADD COLUMN quality_score INTEGER', commit=True)
        except sqlite3.OperationalError:
            pass
        db.execute('CREATE INDEX IF NOT EXISTS idx_model_task ON model_performance(model_name, task_type)', commit=True)

    def record_call(self, model_name: str, task_type: str, duration: float, success: bool,
                    user_feedback: int = None, input_tokens: int = 0, output_tokens: int = 0,
                    quality_score: int = 0):
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            INSERT INTO model_performance (model_name, task_type, duration, success, user_feedback, quality_score, timestamp, input_tokens, output_tokens)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (model_name, task_type, duration, success, user_feedback, quality_score,
              datetime.now().isoformat(), input_tokens, output_tokens), commit=True)
        logger.debug(f"记录调用: {model_name}, {task_type}, 耗时 {duration:.2f}s, 质量 {quality_score}")

    def get_model_score(self, model_name: str, task_type: str) -> dict:
        db = DatabaseManager.get(self.db_path)
        row = db.query_one('''
            SELECT
                COUNT(*) as total,
                AVG(CASE WHEN success THEN 1.0 ELSE 0 END) as success_rate,
                AVG(duration) as avg_duration,
                AVG(CASE WHEN user_feedback IS NOT NULL THEN user_feedback ELSE 0 END) as avg_feedback,
                AVG(quality_score) as avg_quality
            FROM model_performance
            WHERE model_name = ? AND task_type = ?
        ''', (model_name, task_type))
        if row and row[0] > 0:
            return {"total": row[0], "success_rate": row[1], "avg_duration": row[2],
                    "avg_feedback": row[3], "avg_quality": row[4]}
        else:
            return {"total": 0, "success_rate": 0.5, "avg_duration": 10.0, "avg_feedback": 0, "avg_quality": 50}

    def get_best_model_for_task(self, task_type: str, weights: dict = None, 
                                speed_weight=0.3, quality_weight=0.7) -> str:
        """获取最佳模型
        
        Args:
            task_type: 任务类型
            weights: 权重字典 {'quality': x, 'speed': y, 'cost': z}
            speed_weight: 速度权重(旧参数,保持兼容)
            quality_weight: 质量权重(旧参数,保持兼容)
        """
        # 处理新旧参数兼容
        if weights:
            quality_weight = weights.get('quality', 0.5)
            speed_weight = weights.get('speed', 0.3)
            cost_weight = weights.get('cost', 0.2)
        else:
            cost_weight = 0.0
        
        db = DatabaseManager.get(self.db_path)
        rows = db.query('''
            SELECT model_name,
                   AVG(CASE WHEN success THEN 1.0 ELSE 0 END) as success_rate,
                   AVG(duration) as avg_duration,
                   AVG(CASE WHEN user_feedback IS NOT NULL THEN user_feedback ELSE 0 END) as avg_feedback,
                   AVG(quality_score) as avg_quality
            FROM model_performance
            WHERE task_type = ?
            GROUP BY model_name
        ''', (task_type,))
        candidates = []
        for row in rows:
            model, success_rate, avg_duration, avg_feedback, avg_quality = row
            norm_success = success_rate if success_rate else 0.5
            norm_feedback = (avg_feedback + 1) / 2 if avg_feedback is not None else 0.5
            norm_quality = avg_quality / 100.0 if avg_quality else 0.5
            norm_speed = max(0, 1 - (avg_duration / 60.0)) if avg_duration else 0.5
            # 综合质量：反馈+自动评分
            combined_quality = 0.5 * norm_feedback + 0.5 * norm_quality
            score = quality_weight * combined_quality + speed_weight * norm_speed + cost_weight * 0.5
            candidates.append((score, model))
        if candidates:
            candidates.sort(reverse=True)
            return candidates[0][1]
        return None

    def update_last_feedback(self, model_name: str, task_type: str, feedback: int):
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            UPDATE model_performance
            SET user_feedback = ?
            WHERE id = (
                SELECT id FROM model_performance
                WHERE model_name = ? AND task_type = ?
                ORDER BY timestamp DESC LIMIT 1
            )
        ''', (feedback, model_name, task_type), commit=True)
        logger.debug(f"更新最近反馈: {model_name}, {task_type}, 反馈 {feedback}")
    
    def get_all_model_stats(self) -> dict:
        """获取所有模型的统计信息"""
        db = DatabaseManager.get(self.db_path)
        rows = db.query('''
            SELECT model_name,
                   COUNT(*) as total_calls,
                   SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count,
                   AVG(duration) as avg_duration,
                   AVG(CASE WHEN user_feedback IS NOT NULL THEN user_feedback ELSE 0 END) as avg_feedback,
                   AVG(quality_score) as avg_quality
            FROM model_performance
            GROUP BY model_name
        ''')
        
        result = {}
        for row in rows:
            model_name, total_calls, success_count, avg_duration, avg_feedback, avg_quality = row
            result[model_name] = {
                "total_calls": total_calls,
                "success_count": success_count,
                "success_rate": success_count / total_calls if total_calls > 0 else 0,
                "avg_duration": avg_duration,
                "avg_feedback": avg_feedback,
                "avg_quality": avg_quality
            }
        
        return result
