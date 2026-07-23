
# AUTO-GENERATED HOOK for core\presence\proactivity.py
# 生成时间: 2026-07-24T02:51:23.014058
# 人工审核后移动到合适位置

try:
    from core.presence.proactivity import Proactivity
    _proactivity_available = True
except ImportError:
    _proactivity_available = False
    logger.warning("proactivity 模块加载失败")

def try_proactivity(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _proactivity_available:
        return None
    try:
        instance = Proactivity()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "proactivity"}
    except Exception as e:
        logger.warning(f"proactivity 执行失败: {e}")
        return None
