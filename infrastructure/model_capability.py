"""
能力矩阵 - 多维度评估模型能力
为多模型联邦调度提供决策依据
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from loguru import logger
from pathlib import Path
from infrastructure.database_manager import DatabaseManager


class ModelCapability:
    """模型能力矩阵管理器"""
    
    DEFAULT_DIMENSIONS = {
        'reasoning': 0.7,
        'coding': 0.7,
        'math': 0.6,
        'creative': 0.6,
        'knowledge': 0.7,
        'speed': 0.7,
        'context_length': 0.5
    }
    
    TASK_DIMENSION_MAPPING = {
        'code': {'coding': 0.5, 'reasoning': 0.3, 'speed': 0.2},
        'math': {'math': 0.6, 'reasoning': 0.3, 'speed': 0.1},
        'creative': {'creative': 0.6, 'knowledge': 0.3, 'speed': 0.1},
        'analysis': {'reasoning': 0.5, 'knowledge': 0.3, 'speed': 0.2},
        'qa': {'knowledge': 0.6, 'reasoning': 0.3, 'speed': 0.1},
        'default': {'reasoning': 0.4, 'knowledge': 0.3, 'speed': 0.3}
    }
    
    def __init__(self, db_path: str = "data/capability_matrix.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(exist_ok=True)
        self._init_db()
        logger.info("能力矩阵管理器已初始化")
    
    def _init_db(self):
        """初始化数据库"""
        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS model_capabilities (
                model_name TEXT,
                dimension TEXT,
                score REAL,
                sample_count INTEGER,
                last_updated TEXT,
                PRIMARY KEY (model_name, dimension)
            );
            CREATE TABLE IF NOT EXISTS task_dimensions (
                task_type TEXT,
                dimension TEXT,
                weight REAL,
                PRIMARY KEY (task_type, dimension)
            );
        ''')
        
        self._init_default_task_dimensions(db)
    
    def _init_default_task_dimensions(self, db):
        """初始化默认任务维度映射"""
        for task_type, dimensions in self.TASK_DIMENSION_MAPPING.items():
            for dimension, weight in dimensions.items():
                db.execute('''
                    INSERT OR IGNORE INTO task_dimensions
                    (task_type, dimension, weight)
                    VALUES (?, ?, ?)
                ''', (task_type, dimension, weight), commit=True)
    
    def register_model(self, model_name: str, 
                      capabilities: Optional[Dict[str, float]] = None):
        """注册模型能力
        
        Args:
            model_name: 模型名称
            capabilities: 能力评分字典，如 {'coding': 0.9, 'reasoning': 0.8}
        """
        if capabilities is None:
            capabilities = self.DEFAULT_DIMENSIONS.copy()
        
        now = datetime.now().isoformat()
        
        db = DatabaseManager.get(self.db_path)
        for dimension, score in capabilities.items():
            db.execute('''
                INSERT OR REPLACE INTO model_capabilities
                (model_name, dimension, score, sample_count, last_updated)
                VALUES (?, ?, ?, 0, ?)
            ''', (model_name, dimension, score, now), commit=True)
        
        logger.info(f"已注册模型能力: {model_name}, 维度: {len(capabilities)}")
    
    def update_capability(self, model_name: str, dimension: str, 
                         score: float, sample_weight: float = 1.0):
        """更新模型能力（增量学习）
        
        Args:
            model_name: 模型名称
            dimension: 能力维度
            score: 新得分 (0-1)
            sample_weight: 样本权重
        """
        db = DatabaseManager.get(self.db_path)
        row = db.query_one('''
            SELECT score, sample_count FROM model_capabilities
            WHERE model_name = ? AND dimension = ?
        ''', (model_name, dimension))
        
        if row:
            old_score, old_count = row
            new_count = old_count + sample_weight
            new_score = (old_score * old_count + score * sample_weight) / new_count
            
            db.execute('''
                UPDATE model_capabilities
                SET score = ?, sample_count = ?, last_updated = ?
                WHERE model_name = ? AND dimension = ?
            ''', (new_score, new_count, datetime.now().isoformat(),
                  model_name, dimension), commit=True)
        else:
            db.execute('''
                INSERT INTO model_capabilities
                (model_name, dimension, score, sample_count, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', (model_name, dimension, score, sample_weight,
                  datetime.now().isoformat()), commit=True)

    
    def get_model_capability(self, model_name: str) -> Dict[str, float]:
        """获取模型能力画像"""
        db = DatabaseManager.get(self.db_path)
        rows = db.query('''
            SELECT dimension, score FROM model_capabilities
            WHERE model_name = ?
        ''', (model_name,))
        
        capabilities = {}
        for row in rows:
            capabilities[row[0]] = row[1]
        
        if not capabilities:
            return self.DEFAULT_DIMENSIONS.copy()
        
        for dim, default_score in self.DEFAULT_DIMENSIONS.items():
            if dim not in capabilities:
                capabilities[dim] = default_score
        
        return capabilities
    
    def get_task_requirements(self, task_type: str) -> Dict[str, float]:
        """获取任务能力需求"""
        db = DatabaseManager.get(self.db_path)
        rows = db.query('''
            SELECT dimension, weight FROM task_dimensions
            WHERE task_type = ?
        ''', (task_type,))
        
        requirements = {}
        for row in rows:
            requirements[row[0]] = row[1]
        
        if not requirements:
            return self.TASK_DIMENSION_MAPPING.get('default', {}).copy()
        
        return requirements
    
    def score_model_for_task(self, model_name: str, task_type: str) -> float:
        """计算模型对任务的匹配得分
        
        Args:
            model_name: 模型名称
            task_type: 任务类型
        
        Returns:
            匹配得分 (0-1)
        """
        capabilities = self.get_model_capability(model_name)
        requirements = self.get_task_requirements(task_type)
        
        if not requirements:
            return 0.5
        
        total_score = 0.0
        total_weight = 0.0
        
        for dimension, weight in requirements.items():
            capability = capabilities.get(dimension, 0.5)
            total_score += capability * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.5
        
        return total_score / total_weight
    
    def rank_models_for_task(self, task_type: str, 
                            models: Optional[List[str]] = None,
                            available_only: bool = True) -> List[Tuple[str, float]]:
        """为任务排序模型
        
        Args:
            task_type: 任务类型
            models: 候选模型列表，None则使用所有已注册模型
            available_only: 是否只返回可用模型
        
        Returns:
            排序后的(模型名, 得分)列表
        """
        if models is None:
            db = DatabaseManager.get(self.db_path)
            rows = db.query('''
                SELECT DISTINCT model_name FROM model_capabilities
            ''')
            models = [row[0] for row in rows]
        
        # 过滤不可用模型
        if available_only:
            try:
                from infrastructure.model_health_checker import model_health_checker
                models = [m for m in models if model_health_checker.is_available(m)]
            except:
                pass
        
        ranked = []
        for model_name in models:
            score = self.score_model_for_task(model_name, task_type)
            ranked.append((model_name, score))
        
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
    
    def get_top_models(self, task_type: str, top_k: int = 3) -> List[str]:
        """获取任务的最佳模型列表"""
        ranked = self.rank_models_for_task(task_type)
        return [model for model, score in ranked[:top_k]]
    
    def update_from_feedback(self, model_name: str, task_type: str,
                            success: bool, quality_score: float = 0.5):
        """从反馈更新能力（自适应学习率）
        
        Args:
            model_name: 模型名称
            task_type: 任务类型
            success: 是否成功
            quality_score: 质量评分 (0-1)
        """
        requirements = self.get_task_requirements(task_type)
        
        for dimension in requirements.keys():
            current = self.get_model_capability(model_name).get(dimension, 0.5)
            
            db = DatabaseManager.get(self.db_path)
            row = db.query_one('''
                SELECT sample_count FROM model_capabilities
                WHERE model_name = ? AND dimension = ?
            ''', (model_name, dimension))
            
            sample_count = row[0] if row else 0
            
            # 优化：指数衰减学习率，避免初期变化剧烈
            base_lr = 0.05
            decay_rate = 0.95
            lr = base_lr * (decay_rate ** min(sample_count, 20))
            
            if success:
                target = current + 0.1 * (quality_score - 0.5)
            else:
                target = current - 0.2 * (1 - quality_score)
            
            target = max(0.1, min(0.95, target))
            
            new_score = current + lr * (target - current)
            new_score = max(0.1, min(0.95, new_score))
            
            self.update_capability(model_name, dimension, new_score, sample_weight=lr)
    
    def get_capability_matrix(self) -> Dict[str, Dict[str, float]]:
        """获取完整能力矩阵"""
        db = DatabaseManager.get(self.db_path)
        rows = db.query('''
            SELECT model_name, dimension, score FROM model_capabilities
        ''')
        
        matrix = {}
        for row in rows:
            model_name, dimension, score = row
            if model_name not in matrix:
                matrix[model_name] = {}
            matrix[model_name][dimension] = score
        
        return matrix
    
    def get_registered_models(self) -> List[str]:
        """获取所有已注册的模型名称"""
        db = DatabaseManager.get(self.db_path)
        rows = db.query('SELECT DISTINCT model_name FROM model_capabilities')
        return [row[0] for row in rows]
    
    def ensure_model_registered(self, model_name: str, 
                               default_capabilities: Optional[Dict[str, float]] = None):
        """确保模型已注册（若未注册则注册）
        
        Args:
            model_name: 模型名称
            default_capabilities: 默认能力，None则使用DEFAULT_DIMENSIONS
        """
        registered = self.get_registered_models()
        if model_name not in registered:
            caps = default_capabilities or self.DEFAULT_DIMENSIONS.copy()
            self.register_model(model_name, caps)
            logger.info(f"自动注册模型: {model_name}")
    
    def add_dimension(self, dimension: str, default_score: float = 0.5):
        """添加新能力维度"""
        db = DatabaseManager.get(self.db_path)
        models = self.get_registered_models()
        
        for model_name in models:
            db.execute('''
                INSERT OR IGNORE INTO model_capabilities
                (model_name, dimension, score, sample_count, last_updated)
                VALUES (?, ?, ?, 0, ?)
            ''', (model_name, dimension, default_score, datetime.now().isoformat()), commit=True)
        
        logger.info(f"已添加新能力维度: {dimension}, 默认得分: {default_score}")
    
    def apply_decay(self, decay_factor: float = 0.98, days_threshold: int = 7):
        """应用时效衰减
        
        Args:
            decay_factor: 衰减因子（0.98表示每天衰减2%）
            days_threshold: 超过多少天未使用才衰减
        """
        db = DatabaseManager.get(self.db_path)
        rows = db.query('''
            SELECT model_name, dimension, score, last_updated
            FROM model_capabilities
        ''')
        
        for row in rows:
            model_name, dimension, score, last_updated = row
            
            try:
                last_time = datetime.fromisoformat(last_updated)
                days_since = (datetime.now() - last_time).days
                
                if days_since > days_threshold:
                    new_score = score * (decay_factor ** (days_since - days_threshold))
                    new_score = max(0.1, new_score)
                    
                    db.execute('''
                        UPDATE model_capabilities
                        SET score = ?
                        WHERE model_name = ? AND dimension = ?
                    ''', (new_score, model_name, dimension), commit=True)
            
            except Exception as e:
                logger.debug(f"衰减计算失败: {e}")
        

        logger.info(f"已应用时效衰减: 因子={decay_factor}, 阈值={days_threshold}天")
    
    def export_stats(self) -> Dict:
        """导出统计信息"""
        db = DatabaseManager.get(self.db_path)
        row = db.query_one('SELECT COUNT(DISTINCT model_name) FROM model_capabilities')
        model_count = row[0]
        
        row = db.query_one('SELECT COUNT(DISTINCT dimension) FROM model_capabilities')
        dimension_count = row[0]
        
        row = db.query_one('SELECT COUNT(*) FROM task_dimensions')
        task_count = row[0]
        
        return {
            'registered_models': model_count,
            'dimensions': dimension_count,
            'task_types': task_count,
            'matrix_size': model_count * dimension_count
        }


model_capability = ModelCapability()