"""
模型统计库 - 增强版
支持成本跟踪、多目标优化、完全数据驱动的路由决策
"""
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger
from infrastructure.config_manager import config


class EnhancedModelStats:
    """增强的模型统计库"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.get("stats.db_path", "model_stats.db")
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            # 主性能表
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
                    output_tokens INTEGER,
                    cost REAL DEFAULT 0.0
                )
            ''')
            
            # 添加缺失的列
            for column, definition in [
                ("quality_score", "INTEGER"),
                ("cost", "REAL DEFAULT 0.0")
            ]:
                try:
                    conn.execute(f'ALTER TABLE model_performance ADD COLUMN {column} {definition}')
                except sqlite3.OperationalError:
                    pass
            
            # 索引
            conn.execute('CREATE INDEX IF NOT EXISTS idx_model_task ON model_performance(model_name, task_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON model_performance(timestamp)')
            
            # 模型成本配置表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS model_cost_config (
                    model_name TEXT PRIMARY KEY,
                    cost_per_1k_tokens REAL,
                    description TEXT
                )
            ''')
    
    def record_call(self, model_name: str, task_type: str, duration: float, success: bool,
                    user_feedback: int = None, input_tokens: int = 0, output_tokens: int = 0,
                    quality_score: int = 0, cost: float = 0.0):
        """记录模型调用"""
        # 自动计算成本(如果未提供)
        if cost == 0.0:
            cost = self._calculate_cost(model_name, input_tokens, output_tokens)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO model_performance 
                (model_name, task_type, duration, success, user_feedback, quality_score, timestamp, input_tokens, output_tokens, cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (model_name, task_type, duration, success, user_feedback, quality_score,
                  datetime.now().isoformat(), input_tokens, output_tokens, cost))
        
        logger.debug(f"记录调用: {model_name}, {task_type}, 耗时{duration:.2f}s, 质量{quality_score}, 成本${cost:.4f}")
    
    def _calculate_cost(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """计算调用成本"""
        # 从配置获取成本
        cost_per_1k = self._get_model_cost_config(model_name)
        
        total_tokens = input_tokens + output_tokens
        cost = (total_tokens / 1000.0) * cost_per_1k
        
        return cost
    
    def _get_model_cost_config(self, model_name: str) -> float:
        """获取模型成本配置"""
        # 硬编码的成本(可移到配置文件)
        cost_map = {
            "gpt-4o-mini": 0.00015,
            "deepseek-chat": 0.00014,
            "deepseek-coder": 0.00014,
            "mindchat": 0.0,  # 本地模型免费
            "qwen2.5-coder:1.5b": 0.0,
        }
        
        # 检查数据库配置
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                'SELECT cost_per_1k_tokens FROM model_cost_config WHERE model_name = ?',
                (model_name,)
            )
            row = cur.fetchone()
            if row:
                return row[0]
        
        return cost_map.get(model_name, 0.0)
    
    def get_model_score(self, model_name: str, task_type: str) -> dict:
        """获取模型评分"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute('''
                SELECT
                    COUNT(*) as total,
                    AVG(CASE WHEN success THEN 1.0 ELSE 0 END) as success_rate,
                    AVG(duration) as avg_duration,
                    AVG(CASE WHEN user_feedback IS NOT NULL THEN user_feedback ELSE 0 END) as avg_feedback,
                    AVG(quality_score) as avg_quality,
                    AVG(cost) as avg_cost
                FROM model_performance
                WHERE model_name = ? AND task_type = ?
            ''', (model_name, task_type))
            
            row = cur.fetchone()
            if row and row[0] > 0:
                return {
                    "total": row[0],
                    "success_rate": row[1],
                    "avg_duration": row[2],
                    "avg_feedback": row[3],
                    "avg_quality": row[4],
                    "avg_cost": row[5]
                }
            else:
                return {
                    "total": 0,
                    "success_rate": 0.5,
                    "avg_duration": 10.0,
                    "avg_feedback": 0,
                    "avg_quality": 50,
                    "avg_cost": 0.0
                }
    
    def get_best_model_for_task(self, task_type: str, 
                                 constraints: Dict = None,
                                 weights: Dict = None) -> Optional[str]:
        """
        获取任务的最佳模型(完全数据驱动)
        
        Args:
            task_type: 任务类型
            constraints: 约束条件 {
                "max_cost": 最大成本,
                "max_duration": 最大时长,
                "min_quality": 最低质量,
                "min_success_rate": 最低成功率
            }
            weights: 权重配置 {
                "quality": 质量权重,
                "speed": 速度权重,
                "cost": 成本权重,
                "success": 成功率权重
            }
        """
        # 默认权重
        if weights is None:
            weights = {
                "quality": 0.4,
                "speed": 0.3,
                "cost": 0.2,
                "success": 0.1
            }
        
        # 默认约束
        if constraints is None:
            constraints = {}
        
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute('''
                SELECT 
                    model_name,
                    COUNT(*) as total,
                    AVG(CASE WHEN success THEN 1.0 ELSE 0 END) as success_rate,
                    AVG(duration) as avg_duration,
                    AVG(CASE WHEN user_feedback IS NOT NULL THEN user_feedback ELSE 0 END) as avg_feedback,
                    AVG(quality_score) as avg_quality,
                    AVG(cost) as avg_cost
                FROM model_performance
                WHERE task_type = ?
                GROUP BY model_name
                HAVING COUNT(*) >= 3  -- 至少3次调用才纳入考虑
            ''', (task_type,))
            
            candidates = []
            for row in cur.fetchall():
                model, total, success_rate, avg_duration, avg_feedback, avg_quality, avg_cost = row
                
                # 检查约束
                if not self._check_constraints(
                    success_rate, avg_duration, avg_quality, avg_cost, constraints
                ):
                    continue
                
                # 计算综合评分
                score = self._calculate_composite_score(
                    success_rate, avg_duration, avg_quality, avg_cost, avg_feedback, weights
                )
                
                candidates.append((model, score, {
                    "success_rate": success_rate,
                    "avg_duration": avg_duration,
                    "avg_quality": avg_quality,
                    "avg_cost": avg_cost
                }))
            
            if candidates:
                # 按评分排序
                candidates.sort(key=lambda x: x[1], reverse=True)
                best_model = candidates[0][0]
                logger.info(
                    f"数据驱动选择模型: {best_model} (评分: {candidates[0][1]:.3f}, "
                    f"质量: {candidates[0][2]['avg_quality']:.1f}, "
                    f"速度: {candidates[0][2]['avg_duration']:.2f}s)"
                )
                return best_model
        
        return None
    
    def _check_constraints(self, success_rate: float, avg_duration: float, 
                          avg_quality: float, avg_cost: float, 
                          constraints: Dict) -> bool:
        """检查约束条件"""
        if "min_success_rate" in constraints and success_rate < constraints["min_success_rate"]:
            return False
        
        if "max_duration" in constraints and avg_duration > constraints["max_duration"]:
            return False
        
        if "min_quality" in constraints and avg_quality < constraints["min_quality"]:
            return False
        
        if "max_cost" in constraints and avg_cost > constraints["max_cost"]:
            return False
        
        return True
    
    def _calculate_composite_score(self, success_rate: float, avg_duration: float,
                                   avg_quality: float, avg_cost: float,
                                   avg_feedback: float, weights: Dict) -> float:
        """计算综合评分"""
        # 归一化
        norm_quality = avg_quality / 100.0
        norm_speed = max(0, 1 - (avg_duration / 60.0))  # 60秒为基准
        norm_cost = max(0, 1 - (avg_cost * 100))  # 成本越低越好
        norm_success = success_rate
        
        # 反馈权重
        norm_feedback = (avg_feedback + 1) / 2 if avg_feedback != 0 else 0.5
        
        # 综合评分
        score = (
            weights["quality"] * (0.7 * norm_quality + 0.3 * norm_feedback) +
            weights["speed"] * norm_speed +
            weights["cost"] * norm_cost +
            weights["success"] * norm_success
        )
        
        return score
    
    def update_last_feedback(self, model_name: str, task_type: str, feedback: int):
        """更新最近调用的反馈"""
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
        
        logger.debug(f"更新反馈: {model_name}, {task_type}, 反馈{feedback}")
    
    def get_model_ranking(self, task_type: str = None, limit: int = 10) -> List[Dict]:
        """获取模型排名"""
        with sqlite3.connect(self.db_path) as conn:
            if task_type:
                cur = conn.execute('''
                    SELECT 
                        model_name,
                        COUNT(*) as total,
                        AVG(quality_score) as avg_quality,
                        AVG(duration) as avg_duration,
                        AVG(cost) as avg_cost,
                        AVG(CASE WHEN success THEN 1.0 ELSE 0 END) as success_rate
                    FROM model_performance
                    WHERE task_type = ?
                    GROUP BY model_name
                    ORDER BY avg_quality DESC
                    LIMIT ?
                ''', (task_type, limit))
            else:
                cur = conn.execute('''
                    SELECT 
                        model_name,
                        COUNT(*) as total,
                        AVG(quality_score) as avg_quality,
                        AVG(duration) as avg_duration,
                        AVG(cost) as avg_cost,
                        AVG(CASE WHEN success THEN 1.0 ELSE 0 END) as success_rate
                    FROM model_performance
                    GROUP BY model_name
                    ORDER BY avg_quality DESC
                    LIMIT ?
                ''', (limit,))
            
            ranking = []
            for row in cur.fetchall():
                ranking.append({
                    "model": row[0],
                    "total_calls": row[1],
                    "avg_quality": row[2],
                    "avg_duration": row[3],
                    "avg_cost": row[4],
                    "success_rate": row[5]
                })
            
            return ranking
    
    def get_statistics_summary(self) -> Dict:
        """获取统计摘要"""
        with sqlite3.connect(self.db_path) as conn:
            # 总调用数
            cur = conn.execute('SELECT COUNT(*) FROM model_performance')
            total_calls = cur.fetchone()[0]
            
            # 模型数量
            cur = conn.execute('SELECT COUNT(DISTINCT model_name) FROM model_performance')
            total_models = cur.fetchone()[0]
            
            # 平均质量
            cur = conn.execute('SELECT AVG(quality_score) FROM model_performance')
            avg_quality = cur.fetchone()[0] or 0
            
            # 总成本
            cur = conn.execute('SELECT SUM(cost) FROM model_performance')
            total_cost = cur.fetchone()[0] or 0
            
            # 成功率
            cur = conn.execute('SELECT AVG(CASE WHEN success THEN 1.0 ELSE 0 END) FROM model_performance')
            success_rate = cur.fetchone()[0] or 0
        
        return {
            "total_calls": total_calls,
            "total_models": total_models,
            "avg_quality": avg_quality,
            "total_cost": total_cost,
            "success_rate": success_rate
        }


# 向后兼容
ModelStats = EnhancedModelStats