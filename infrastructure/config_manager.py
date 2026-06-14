"""
配置管理模块
使用YAML配置文件,支持环境变量覆盖
"""
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from loguru import logger

MAX_CONFIG_SIZE = 1024 * 1024  # 1MB


class ModelConfig(BaseModel):
    enabled: bool = True
    description: str = ""
    temperature: float = 0.7
    max_tokens: int = 512


class RoutingConfig(BaseModel):
    preferred: list = []
    fallback: str = "mindchat"


class Settings(BaseSettings):
    config_file: str = "config/settings.yaml"
    
    class Config:
        env_prefix = "CAMPFIRE_"


class ConfigManager:
    _instance = None
    _config: Dict[str, Any] = {}
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._config = {}
                    cls._initialized = True
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        config_path = self._find_config_file()
        
        if not config_path or not config_path.exists():
            logger.warning(f"配置文件不存在，使用默认配置")
            with self._lock:
                self._config = self._get_default_config()
        else:
            try:
                file_size = config_path.stat().st_size
                if file_size > MAX_CONFIG_SIZE:
                    raise ValueError(f"配置文件过大({file_size}字节)，超过限制{MAX_CONFIG_SIZE}字节")
                
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = yaml.safe_load(f) or {}
                
                with self._lock:
                    self._config = loaded_config
                
                logger.info(f"配置文件加载成功: {config_path} (大小: {file_size}字节)")
            except Exception as e:
                logger.error(f"配置文件加载失败: {e}, 使用默认配置")
                with self._lock:
                    self._config = self._get_default_config()
        
        self._apply_env_overrides()
    
    def _find_config_file(self) -> Optional[Path]:
        settings = Settings()
        config_file = settings.config_file
        
        project_root = Path(__file__).parent.parent
        allowed_paths = [
            project_root / config_file,
            project_root / "config" / "settings.yaml",
        ]
        
        for path in allowed_paths:
            if path.exists():
                try:
                    resolved = path.resolve()
                    if resolved.is_relative_to(project_root.resolve()):
                        return path
                    else:
                        logger.warning(f"配置路径越权: {path}")
                except (OSError, RuntimeError) as e:
                    logger.warning(f"路径解析失败: {path} - {e}")
        
        return None
    
    def _get_config_path(self) -> str:
        config_path = self._find_config_file()
        return str(config_path) if config_path else "config/settings.yaml"
    
    def _get_default_config(self) -> Dict[str, Any]:
        return {
            "models": {
                "local": {
                    "ollama_base_url": "http://localhost:11434",
                    "default_timeout": 120,
                    "retry_times": 3,
                    "retry_delay": 2,
                    "available": {
                        "mindchat": {"enabled": True, "temperature": 0.7, "max_tokens": 512},
                        "qwen2.5-coder:1.5b": {"enabled": True, "temperature": 0.5, "max_tokens": 1024},
                    }
                },
                "remote": {
                    "enabled": True,
                    "timeout": 60,
                    "retry_times": 2,
                    "retry_delay": 3,
                }
            },
            "routing": {
                "task_model_mapping": {
                    "code": {"preferred": ["code_light", "remote_gpt4"], "fallback": "mindchat"},
                    "chat": {"preferred": ["mindchat", "remote_gpt4"], "fallback": "code_light"},
                    "question": {"preferred": ["mindchat", "remote_gpt4"], "fallback": "code_light"},
                    "calculation": {"preferred": ["remote_gpt4", "code_light"], "fallback": "mindchat"},
                    "memory": {"preferred": ["mindchat", "remote_gpt4"], "fallback": "code_light"},
                }
            },
            "memory": {
                "short_term": {"max_rounds": 5, "file_path": "campfire_log.txt"},
                "long_term": {"db_path": "experience_pool.db"}
            },
            "stats": {"db_path": "model_stats.db"},
            "audit": {"enabled": True},
            "sandbox": {"enabled": True, "timeout": 15},
            "calculation": {
                "pi": {
                    "use_predefined": True,
                    "predefined_value": "3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679"
                }
            }
        }
    
    def _apply_env_overrides(self):
        if os.getenv("OLLAMA_BASE_URL"):
            self._config.setdefault("models", {}).setdefault("local", {})["ollama_base_url"] = os.getenv("OLLAMA_BASE_URL")
        
        if os.getenv("OPENAI_API_KEY"):
            self._config.setdefault("models", {}).setdefault("remote", {})["enabled"] = True
        
        if os.getenv("CAMPFIRE_TIMEOUT"):
            try:
                timeout = int(os.getenv("CAMPFIRE_TIMEOUT"))
                self._config.setdefault("models", {}).setdefault("local", {})["default_timeout"] = timeout
            except ValueError:
                pass
    
    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            config_copy = self._config.copy()
        
        keys = key.split('.')
        value = config_copy
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        local_models = self.get("models.local.available", {})
        if model_name in local_models:
            return local_models[model_name]
        return {"enabled": False, "temperature": 0.7, "max_tokens": 512}
    
    def get_routing_config(self, task_type: str) -> RoutingConfig:
        mapping = self.get(f"routing.task_model_mapping.{task_type}", {})
        return RoutingConfig(
            preferred=mapping.get("preferred", []),
            fallback=mapping.get("fallback", "mindchat")
        )
    
    def is_model_enabled(self, model_name: str) -> bool:
        config = self.get_model_config(model_name)
        return config.get("enabled", False)
    
    def get_retry_config(self, is_remote: bool = False) -> Dict[str, int]:
        if is_remote:
            return {
                "times": self.get("models.remote.retry_times", 2),
                "delay": self.get("models.remote.retry_delay", 3)
            }
        return {
            "times": self.get("models.local.retry_times", 3),
            "delay": self.get("models.local.retry_delay", 2)
        }
    
    def reload(self, new_config: Dict[str, Any] = None):
        """重新加载配置"""
        with self._lock:
            old_config = self._config.copy()
            
            if new_config:
                self._config.update(new_config)
            else:
                temp_config = self._config.copy()
                self._load_config_unlocked()
            
            logger.info("配置已重新加载")
    
    def _load_config_unlocked(self):
        """内部方法：不加锁的配置加载"""
        config_path = self._find_config_file()
        
        if not config_path or not config_path.exists():
            self._config = self._get_default_config()
        else:
            try:
                file_size = config_path.stat().st_size
                if file_size > MAX_CONFIG_SIZE:
                    raise ValueError(f"配置文件过大({file_size}字节)")
                
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception as e:
                logger.error(f"配置加载失败: {e}")
                self._config = self._get_default_config()
        
        self._apply_env_overrides_unlocked()
    
    def _apply_env_overrides_unlocked(self):
        """内部方法：不加锁的环境变量覆盖"""
        if os.getenv("OLLAMA_BASE_URL"):
            self._config.setdefault("models", {}).setdefault("local", {})["ollama_base_url"] = os.getenv("OLLAMA_BASE_URL")
        
        if os.getenv("OPENAI_API_KEY"):
            self._config.setdefault("models", {}).setdefault("remote", {})["enabled"] = True
        
        if os.getenv("CAMPFIRE_TIMEOUT"):
            try:
                timeout = int(os.getenv("CAMPFIRE_TIMEOUT"))
                self._config.setdefault("models", {}).setdefault("local", {})["default_timeout"] = timeout
            except ValueError:
                pass


config = ConfigManager()