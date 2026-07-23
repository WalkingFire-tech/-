
# AUTO-GENERATED HOOK for core\capability_creation\solvers\system_diagnosis.py
# 生成时间: 2026-07-24T02:51:22.908176
# 人工审核后移动到合适位置

try:
    from core.capability_creation.solvers.system_diagnosis import SystemDiagnosis
    _system_diagnosis_available = True
except ImportError:
    _system_diagnosis_available = False
    logger.warning("system_diagnosis 模块加载失败")

def try_system_diagnosis(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _system_diagnosis_available:
        return None
    try:
        instance = SystemDiagnosis()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "system_diagnosis"}
    except Exception as e:
        logger.warning(f"system_diagnosis 执行失败: {e}")
        return None
