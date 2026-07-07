"""
经验池 - 智能管理版本
支持重要性评分、时效衰减、主动遗忘
"""
import sqlite3
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
        self.db_path = db_path or config.get("memory.long_term.db_path", "experience_pool.db")
        self._init_db()
        
        # 配置参数
        self.decay_rate = config.get("experience.decay_rate", 0.01)  # 时效衰减率
        self.importance_threshold = config.get("experience.importance_threshold", 0.3)  # 重要性阈值
        self.max_experiences = config.get("memory.long_term.max_experiences", 10000)
        self.cleanup_interval = config.get("experience.cleanup_interval", 100)  # 每100次添加清理一次
        
        self.add_count = 0
    
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
                    importance REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0
                )
            ''')
            
            # 添加缺失的列
            for column, definition in [
                ("importance", "REAL DEFAULT 0.5"),
                ("access_count", "INTEGER DEFAULT 0")
            ]:
                try:
                    conn.execute(f'ALTER TABLE experiences ADD COLUMN {column} {definition}')
                except sqlite3.OperationalError:
                    pass
            
            # 索引
            conn.execute('CREATE INDEX IF NOT EXISTS idx_intent ON experiences(intent_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_score ON experiences(quality_score)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_importance ON experiences(importance)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON experiences(timestamp)')
    
    def add_experience(self, intent_type: str, raw_input: str, plan: str,
                       model_name: str, quality_score: int, user_feedback: int,
                       success: bool, duration: float):
        """添加经验(带重要性评估)"""
        # 计算重要性
        importance = self._calculate_importance(
            quality_score=quality_score,
            user_feedback=user_feedback,
            success=success,
            duration=duration,
            intent_type=intent_type
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO experiences 
                (timestamp, intent_type, raw_input, plan, model_name,
                 quality_score, user_feedback, success, duration, importance, access_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            ''', (datetime.now().isoformat(), intent_type, raw_input, plan,
                  model_name, quality_score, user_feedback, success, duration, importance))
        
        logger.debug(f"经验已存储: {intent_type}, 质量{quality_score}, 重要性{importance:.3f}")
        
        self.add_count += 1
        
        # 定期清理
        if self.add_count % self.cleanup_interval == 0:
            self._auto_cleanup()
    
    def _calculate_importance(self, quality_score: int, user_feedback: int,
                             success: bool, duration: float, intent_type: str) -> float:
        """计算经验重要性"""
        # 1. 质量分数 (0-1)
        quality_weight = quality_score / 100.0
        
        # 2. 用户反馈 (-1到1,归一化到0-1)
        feedback_weight = (user_feedback + 1) / 2 if user_feedback is not None else 0.5
        
        # 3. 成功标志
        success_weight = 1.0 if success else 0.3
        
        # 4. 任务频率(高频任务更重要)
        frequency = self._get_task_frequency(intent_type)
        frequency_weight = min(frequency / 10.0, 1.0)  # 最多10次归一化
        
        # 5. 效率(快速响应更重要)
        efficiency_weight = max(0, 1 - (duration / 30.0))  # 30秒为基准
        
        # 综合重要性
        importance = (
            0.35 * quality_weight +
            0.25 * feedback_weight +
            0.15 * success_weight +
            0.15 * frequency_weight +
            0.10 * efficiency_weight
        )
        
        return importance
    
    def _get_task_frequency(self, intent_type: str) -> int:
        """获取任务频率"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                'SELECT COUNT(*) FROM experiences WHERE intent_type = ?',
                (intent_type,)
            )
            return cur.fetchone()[0]
    
    def _auto_cleanup(self):
        """自动清理低价值经验"""
        logger.info("开始自动清理经验池...")
        
        # 1. 更新时效衰减
        self._apply_time_decay()
        
        # 2. 删除低重要性经验
        deleted = self._delete_low_importance()
        
        # 3. 压缩相似经验
        compressed = self._compress_similar_experiences()
        
        # 4. 限制总数
        trimmed = self._trim_to_max_size()
        
        logger.info(f"清理完成: 删除{deleted}条, 压缩{compressed}条, 裁剪{trimmed}条")
    
    def _apply_time_decay(self):
        """应用时效衰减"""
        with sqlite3.connect(self.db_path) as conn:
            # 获取所有经验
            cur = conn.execute('SELECT id, timestamp, importance FROM experiences')
            experiences = cur.fetchall()
            
            now = datetime.now()
            for exp_id, timestamp_str, importance in experiences:
                # 计算年龄(小时)
                timestamp = datetime.fromisoformat(timestamp_str)
                age_hours = (now - timestamp).total_seconds() / 3600
                
                # 时效衰减
                decay_factor = math.exp(-self.decay_rate * age_hours)
                new_importance = importance * decay_factor
                
                # 更新
                conn.execute(
                    'UPDATE experiences SET importance = ? WHERE id = ?',
                    (new_importance, exp_id)
                )
    
    def _delete_low_importance(self) -> int:
        """删除低重要性经验"""
        with sqlite3.connect(self.db_path) as conn:
            # 删除重要性低于阈值的经验
            cur = conn.execute(
                'DELETE FROM experiences WHERE importance < ?',
                (self.importance_threshold,)
            )
            deleted = cur.rowcount
            
            # 删除失败且无反馈的旧经验(保留最近100条用于学习)
            cur = conn.execute('''
                DELETE FROM experiences 
                WHERE success = 0 
                  AND (user_feedback IS NULL OR user_feedback <= 0)
                  AND id NOT IN (
                      SELECT id FROM experiences 
                      WHERE success = 0 
                      ORDER BY timestamp DESC LIMIT 100
                  )
            ''')
            deleted += cur.rowcount
            
            return deleted
    
    def _compress_similar_experiences(self) -> int:
        """压缩相似经验"""
        # 简化实现:合并相同intent_type和model的成功经验
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute('''
                SELECT intent_type, model_name, COUNT(*) as count
                FROM experiences
                WHERE success = 1 AND quality_score >= 70
                GROUP BY intent_type, model_name
                HAVING count > 5
            ''')
            
            compressed = 0
            for intent_type, model_name, count in cur.fetchall():
                # 保留最好的3条,删除其他的
                conn.execute('''
                    DELETE FROM experiences
                    WHERE intent_type = ? 
                      AND model_name = ?
                      AND success = 1
                      AND quality_score >= 70
                      AND id NOT IN (
                          SELECT id FROM experiences
                          WHERE intent_type = ? AND model_name = ? AND success = 1
                          ORDER BY quality_score DESC LIMIT 3
                      )
                ''', (intent_type, model_name, intent_type, model_name))
                
                compressed += conn.total_changes
            
            return compressed
    
    def _trim_to_max_size(self) -> int:
        """裁剪到最大数量"""
        with sqlite3.connect(self.db_path) as conn:
            # 获取总数
            cur = conn.execute('SELECT COUNT(*) FROM experiences')
            total = cur.fetchone()[0]
            
            if total > self.max_experiences:
                # 删除最不重要的经验
                excess = total - self.max_experiences
                conn.execute('''
                    DELETE FROM experiences
                    WHERE id IN (
                        SELECT id FROM experiences
                        ORDER BY importance ASC, timestamp ASC
                        LIMIT ?
                    )
                ''', (excess,))
                
                return excess
            
            return 0
    
    def get_high_quality_experiences(self, intent_type: str = None, 
                                     min_quality: int = 70, limit: int = 100):
        """获取高质量经验"""
        query = '''
            SELECT intent_type, raw_input, plan, model_name, quality_score, user_feedback, importance
            FROM experiences
            WHERE quality_score >= ?
        '''
        params = [min_quality]
        
        if intent_type:
            query += ' AND intent_type = ?'
            params.append(intent_type)
        
        query += ' ORDER BY importance DESC, quality_score DESC LIMIT ?'
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(query, params)
            
            # 更新访问计数
            for row in cur.fetchall():
                conn.execute(
                    'UPDATE experiences SET access_count = access_count + 1 WHERE id = ?',
                    (row['id'],)
                )
            
            return [dict(row) for row in cur.fetchall()]
    
    def get_failed_experiences(self, intent_type: str = None, limit: int = 50):
        """获取失败经验"""
        query = '''
            SELECT intent_type, raw_input, plan, model_name, quality_score, user_feedback
            FROM experiences
            WHERE quality_score < 50 AND (user_feedback IS NULL OR user_feedback <= 0)
        '''
        params = []
        
        if intent_type:
            query += ' AND intent_type = ?'
            params.append(intent_type)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(query, params)
            return [dict(row) for row in cur.fetchall()]
    
    def get_statistics(self) -> Dict:
        """获取经验池统计"""
        with sqlite3.connect(self.db_path) as conn:
            # 总数
            cur = conn.execute('SELECT COUNT(*) FROM experiences')
            total = cur.fetchone()[0]
            
            # 按意图类型
            cur = conn.execute('''
                SELECT intent_type, COUNT(*) as count, AVG(quality_score) as avg_quality
                FROM experiences
                GROUP BY intent_type
            ''')
            by_type = {row[0]: {"count": row[1], "avg_quality": row[2]} for row in cur.fetchall()}
            
            # 平均重要性
            cur = conn.execute('SELECT AVG(importance) FROM experiences')
            avg_importance = cur.fetchone()[0] or 0
            
            # 高质量比例
            cur = conn.execute('SELECT COUNT(*) FROM experiences WHERE quality_score >= 70')
            high_quality = cur.fetchone()[0]
            
            # 成功率
            cur = conn.execute('SELECT AVG(CASE WHEN success THEN 1.0 ELSE 0 END) FROM experiences')
            success_rate = cur.fetchone()[0] or 0
        
        return {
            "total": total,
            "by_intent_type": by_type,
            "avg_importance": avg_importance,
            "high_quality_ratio": high_quality / total if total > 0 else 0,
            "success_rate": success_rate,
            "max_capacity": self.max_experiences,
            "utilization": total / self.max_experiences if self.max_experiences > 0 else 0
        }
    
    def manual_cleanup(self):
        """手动触发清理"""
        self._auto_cleanup()


# 向后兼容
ExperiencePool = SmartExperiencePool