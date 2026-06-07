import sqlite3
from datetime import datetime
from loguru import logger

class ModelStats:
    def __init__(self, db_path: str = "model_stats.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
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
            # 添加 quality_score 列（如果表已存在但缺少该列）
            try:
                conn.execute('ALTER TABLE model_performance ADD COLUMN quality_score INTEGER')
            except sqlite3.OperationalError:
                pass
            conn.execute('CREATE INDEX IF NOT EXISTS idx_model_task ON model_performance(model_name, task_type)')

    def record_call(self, model_name: str, task_type: str, duration: float, success: bool,
                    user_feedback: int = None, input_tokens: int = 0, output_tokens: int = 0,
                    quality_score: int = 0):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO model_performance (model_name, task_type, duration, success, user_feedback, quality_score, timestamp, input_tokens, output_tokens)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (model_name, task_type, duration, success, user_feedback, quality_score,
                  datetime.now().isoformat(), input_tokens, output_tokens))
        logger.debug(f"记录调用: {model_name}, {task_type}, 耗时 {duration:.2f}s, 质量 {quality_score}")

    def get_model_score(self, model_name: str, task_type: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute('''
                SELECT
                    COUNT(*) as total,
                    AVG(CASE WHEN success THEN 1.0 ELSE 0 END) as success_rate,
                    AVG(duration) as avg_duration,
                    AVG(CASE WHEN user_feedback IS NOT NULL THEN user_feedback ELSE 0 END) as avg_feedback,
                    AVG(quality_score) as avg_quality
                FROM model_performance
                WHERE model_name = ? AND task_type = ?
            ''', (model_name, task_type))
            row = cur.fetchone()
            if row and row[0] > 0:
                return {"total": row[0], "success_rate": row[1], "avg_duration": row[2],
                        "avg_feedback": row[3], "avg_quality": row[4]}
            else:
                return {"total": 0, "success_rate": 0.5, "avg_duration": 10.0, "avg_feedback": 0, "avg_quality": 50}

    def get_best_model_for_task(self, task_type: str, speed_weight=0.3, quality_weight=0.7) -> str:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute('''
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
            for row in cur.fetchall():
                model, success_rate, avg_duration, avg_feedback, avg_quality = row
                norm_success = success_rate
                norm_feedback = (avg_feedback + 1) / 2 if avg_feedback is not None else 0.5
                norm_quality = avg_quality / 100.0 if avg_quality else 0.5
                norm_speed = max(0, 1 - (avg_duration / 60.0))
                # 综合质量：反馈+自动评分
                combined_quality = 0.5 * norm_feedback + 0.5 * norm_quality
                score = quality_weight * combined_quality + speed_weight * norm_speed
                candidates.append((score, model))
            if candidates:
                candidates.sort(reverse=True)
                return candidates[0][1]
        return None

    def update_last_feedback(self, model_name: str, task_type: str, feedback: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE model_performance
                SET user_feedback = ?
                WHERE id = (
                    SELECT id FROM model_performance
                    WHERE model_name = ? AND task_type = ?
                    ORDER BY timestamp DESC LIMIT 1
                )
            ''', (feedback, model_name, task_type))
        logger.debug(f"更新最近反馈: {model_name}, {task_type}, 反馈 {feedback}")
