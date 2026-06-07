"""
事件常量定义 - 统一管理所有事件名称
避免事件名称分散,便于维护
"""


class Events:
    """系统事件常量"""
    
    # 用户交互事件
    USER_INPUT = "user_input"
    PLAN_EXECUTED = "plan_executed"
    CONFIG_UPDATED = "config_updated"
    RELOAD_CONFIG = "reload_config"
    
    # CLI命令事件
    CMD_OPTIMIZE = "cmd.optimize"
    CMD_INDUCTION = "cmd.induction"
    CMD_CONFLICT_DETECT = "cmd.conflict.detect"
    CMD_CONFLICT_RESOLVE = "cmd.conflict.resolve"
    CMD_TOOLS_ANALYZE = "cmd.tools.analyze"
    
    # 学习事件
    LOW_CONFIDENCE = "low_confidence"
    TASK_FAILED = "task_failed"
    CLARIFICATION_NEEDED = "clarification_needed"
    
    # 文件事件
    FILE_AUTO_PROCESSED = "file_auto_processed"