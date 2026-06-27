"""
统一配置管理 - 所有组件的配置中心

确保所有组件的配置集中管理，保持一致。
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class UnifiedConfig:
    """
    统一配置管理器
    
    单例模式，所有组件通过此对象获取配置。
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._config: Dict[str, Any] = {}
        self._config_path = Path("config/system_config.json")
        self._load_config()
        
        logger.info("⚙️ 统一配置管理器已初始化")
    
    def _load_config(self):
        """加载配置文件"""
        default_config = {
            "system": {
                "name": "Alliance Pioneer",
                "version": "6.0",
                "description": "A Thinking Companion"
            },
            "layers": {
                "L0": {"enabled": True, "description": "存在层"},
                "L1": {"enabled": True, "description": "感知层"},
                "L2": {"enabled": True, "description": "学习层"},
                "L3": {"enabled": True, "description": "整合层"},
                "L4": {"enabled": True, "description": "校验层"},
                "L5": {"enabled": True, "description": "进化层"},
                "L6": {"enabled": True, "description": "内省层"}
            },
            "presence": {
                "heartbeat_interval": 10,
                "perception_interval": 30,
                "growth_interval": 15,
                "sleep_interval": 300,
                "consolidation_interval": 1800
            },
            "memory": {
                "stereo_memory_db": "data/stereo_memory.db",
                "relationship_db": "data/relationship.db",
                "max_history": 1000,
                "decay_rate": 0.99
            },
            "evolution": {
                "gene_evolution_interval": 7,
                "skill_threshold": 3,
                "reflex_threshold": 3,
                "abstraction_interval": 14
            },
            "proactivity": {
                "level": "moderate",
                "silence_threshold": 600,
                "cooldown_seconds": 300,
                "max_actions_per_hour": 3
            },
            "goals": {
                "default_priority": 5,
                "min_evidence_for_goal": 3,
                "priority_update_interval": 7
            },
            "review": {
                "enabled": True,
                "thresholds": {
                    "understanding": 0.6,
                    "relevance": 0.6,
                    "helpfulness": 0.6,
                    "clarity": 0.5,
                    "empathy": 0.4,
                    "boundary": 0.7
                }
            }
        }
        
        if self._config_path.exists():
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    if loaded:
                        self._config = self._deep_merge(default_config, loaded)
                        logger.info(f"✅ 配置文件已加载: {self._config_path}")
                        return
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}，使用默认配置")
        
        self._config = default_config
        self._save_config()
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """深度合并字典"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _save_config(self):
        """保存配置到文件"""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"保存配置失败: {e}")
    
    def get(self, key: str, default=None) -> Any:
        """获取配置值（支持点号分隔）"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self._save_config()
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()


_unified_config = None


def get_config() -> UnifiedConfig:
    """获取配置单例"""
    global _unified_config
    if _unified_config is None:
        _unified_config = UnifiedConfig()
    return _unified_config