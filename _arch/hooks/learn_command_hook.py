
# AUTO-GENERATED HOOK for core\learn_command.py
# 生成时间: 2026-07-24T02:51:22.983688
# 人工审核后移动到合适位置

try:
    from core.learn_command import LearnCommand
    _learn_command_available = True
except ImportError:
    _learn_command_available = False
    logger.warning("learn_command 模块加载失败")

def try_learn_command(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _learn_command_available:
        return None
    try:
        instance = LearnCommand()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "learn_command"}
    except Exception as e:
        logger.warning(f"learn_command 执行失败: {e}")
        return None
