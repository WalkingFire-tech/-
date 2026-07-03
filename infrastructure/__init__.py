"""
基础设施层

包含：
- config_manager: 配置管理
- experience_pool: 经验池
- reflection_pipeline: 反思管道
- quick_reflex: 快速反射（T0）
"""

__all__ = [
    "ConfigManager",
    "config",
    "ExperiencePool",
    "ReflectionPipeline",
    "get_reflection_pipeline",
    "QuickReflexEngine",
]


def __getattr__(name):
    if name == "ConfigManager":
        from infrastructure.config_manager import ConfigManager
        return ConfigManager
    elif name == "config":
        from infrastructure.config_manager import config
        return config
    elif name == "ExperiencePool":
        from infrastructure.experience_pool import ExperiencePool
        return ExperiencePool
    elif name == "ReflectionPipeline":
        from infrastructure.reflection_pipeline import ReflectionPipeline
        return ReflectionPipeline
    elif name == "get_reflection_pipeline":
        from infrastructure.reflection_pipeline import get_reflection_pipeline
        return get_reflection_pipeline
    elif name == "QuickReflexEngine":
        from infrastructure.quick_reflex import QuickReflexEngine
        return QuickReflexEngine
    raise AttributeError(f"module 'infrastructure' has no attribute {name}")