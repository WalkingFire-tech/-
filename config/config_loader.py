"""
配置加载器
从YAML文件加载适应度评估配置
"""
import os
from typing import Dict, Any

try:
    import yaml
except ImportError:
    yaml = None


class ConfigLoader:
    """加载并管理配置文件"""
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load(self, config_path: str = "config/fitness_config.yaml") -> Dict[str, Any]:
        """加载YAML配置文件"""
        if self._config is not None:
            return self._config
        
        if not os.path.exists(config_path):
            # 返回默认配置
            self._config = self._get_default_config()
            return self._config
        
        if yaml is None:
            # 没有yaml库，返回默认配置
            self._config = self._get_default_config()
            return self._config
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            return self._config
        except Exception:
            self._config = self._get_default_config()
            return self._config
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            'fitness': {
                'objective_weight': 0.6,
                'subjective_weight': 0.4,
                'objective_threshold': 30.0,
                'total_threshold': 50.0,
                'use_legacy': False,
                'enable_shadow': True,
                'default_score': 50.0
            }
        }
    
    def get_fitness_config(self) -> Dict:
        """获取适应度相关配置"""
        config = self.load()
        return config.get('fitness', {})
    
    def should_use_legacy(self) -> bool:
        """是否使用旧版适应度函数"""
        return self.get_fitness_config().get('use_legacy', False)
    
    def should_enable_shadow(self) -> bool:
        """是否启用影子模式"""
        return self.get_fitness_config().get('enable_shadow', False)
    
    def get_objective_weight(self) -> float:
        """获取客观分权重"""
        return self.get_fitness_config().get('objective_weight', 0.6)
    
    def get_subjective_weight(self) -> float:
        """获取主观分权重"""
        return self.get_fitness_config().get('subjective_weight', 0.4)
    
    def get_objective_threshold(self) -> float:
        """获取客观分阈值"""
        return self.get_fitness_config().get('objective_threshold', 30.0)
    
    def get_total_threshold(self) -> float:
        """获取总分阈值"""
        return self.get_fitness_config().get('total_threshold', 50.0)
    
    def reload(self):
        """重新加载配置"""
        self._config = None
        return self.load()


config_loader = ConfigLoader()