"""
适应度评估配置
支持新旧版本切换和影子模式
"""
from typing import Dict, Any
from datetime import datetime
import json

class FitnessConfig:
    """适应度评估配置"""
    
    # 是否使用旧版适应度函数（回滚开关）
    USE_LEGACY_FITNESS: bool = False
    
    # 是否启用影子模式（新旧同时运行）
    SHADOW_MODE_ENABLED: bool = True
    
    # 影子模式日志路径
    SHADOW_LOG_PATH: str = "logs/fitness_shadow.jsonl"
    
    # 客观分权重（事实性问题）
    OBJECTIVE_WEIGHT: float = 0.6
    
    # 主观分权重（事实性问题）
    SUBJECTIVE_WEIGHT: float = 0.4
    
    # 客观分阈值（低于此值触发知识注入）
    OBJECTIVE_THRESHOLD: float = 30.0
    
    # 总分阈值
    TOTAL_THRESHOLD: float = 30.0
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """转为字典"""
        return {
            'USE_LEGACY_FITNESS': cls.USE_LEGACY_FITNESS,
            'SHADOW_MODE_ENABLED': cls.SHADOW_MODE_ENABLED,
            'OBJECTIVE_WEIGHT': cls.OBJECTIVE_WEIGHT,
            'SUBJECTIVE_WEIGHT': cls.SUBJECTIVE_WEIGHT,
            'OBJECTIVE_THRESHOLD': cls.OBJECTIVE_THRESHOLD,
            'TOTAL_THRESHOLD': cls.TOTAL_THRESHOLD,
            'timestamp': datetime.now().isoformat()
        }
    
    @classmethod
    def enable_legacy(cls):
        """切换到旧版"""
        cls.USE_LEGACY_FITNESS = True
        cls.SHADOW_MODE_ENABLED = False
    
    @classmethod
    def enable_new(cls):
        """切换到新版"""
        cls.USE_LEGACY_FITNESS = False
        cls.SHADOW_MODE_ENABLED = False
    
    @classmethod
    def enable_shadow(cls):
        """启用影子模式"""
        cls.USE_LEGACY_FITNESS = False
        cls.SHADOW_MODE_ENABLED = True


class ShadowModeLogger:
    """影子模式日志记录器"""
    
    def __init__(self, log_path: str = FitnessConfig.SHADOW_LOG_PATH):
        self.log_path = log_path
        self._ensure_log_dir()
    
    def _ensure_log_dir(self):
        """确保日志目录存在"""
        from pathlib import Path
        Path(self.log_path).parent.mkdir(parents=True, exist_ok=True)
    
    def log_comparison(
        self,
        question: str,
        legacy_score: float,
        new_score: float,
        objective_score: float,
        subjective_score: float,
        is_factual: bool
    ):
        """记录新旧评分对比"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'question': question[:100],
            'legacy_score': legacy_score,
            'new_score': new_score,
            'objective_score': objective_score,
            'subjective_score': subjective_score,
            'is_factual': is_factual,
            'delta': abs(legacy_score - new_score)
        }
        
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        import os
        if not os.path.exists(self.log_path):
            return {'total': 0}
        
        records = []
        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
        
        if not records:
            return {'total': 0}
        
        deltas = [r['delta'] for r in records]
        factual_count = sum(1 for r in records if r['is_factual'])
        
        return {
            'total': len(records),
            'factual_count': factual_count,
            'avg_delta': sum(deltas) / len(deltas),
            'max_delta': max(deltas),
            'min_delta': min(deltas)
        }


shadow_logger = ShadowModeLogger()