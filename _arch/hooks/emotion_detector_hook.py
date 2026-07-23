
# AUTO-GENERATED HOOK for core\perception\emotion_detector.py
# 生成时间: 2026-07-24T02:51:23.009057
# 人工审核后移动到合适位置

try:
    from core.perception.emotion_detector import EmotionDetector
    _emotion_detector_available = True
except ImportError:
    _emotion_detector_available = False
    logger.warning("emotion_detector 模块加载失败")

def try_emotion_detector(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not _emotion_detector_available:
        return None
    try:
        instance = EmotionDetector()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {"status": "loaded", "module": "emotion_detector"}
    except Exception as e:
        logger.warning(f"emotion_detector 执行失败: {e}")
        return None
