import asyncio
import concurrent.futures
import time
from loguru import logger

_slow_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="slow_op")
_fast_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="fast_op")

_ollama_semaphore = None
_ollama_last_inference_time = 0
_INFERENCE_COOLDOWN_SECONDS = 3
_MAX_RESPONSE_CHARS = 6000


def _get_ollama_semaphore():
    global _ollama_semaphore
    if _ollama_semaphore is None:
        _ollama_semaphore = asyncio.Semaphore(1)
    return _ollama_semaphore

try:
    from core.resource_awareness.adaptive_governor import get_adaptive_governor
    from core.resource_awareness.health_monitor import get_health_monitor
    _RESOURCE_AWARE = True
except ImportError:
    _RESOURCE_AWARE = False

try:
    from core.input_processor import get_input_processor
    _INPUT_PROCESSOR_AVAILABLE = True
except ImportError:
    _INPUT_PROCESSOR_AVAILABLE = False

try:
    from core.spirit_core import spirit_core
    SPIRIT_CORE_AVAILABLE = True
except ImportError:
    SPIRIT_CORE_AVAILABLE = False

_VECTOR_AVAILABLE = None


def _check_vector_available() -> bool:
    global _VECTOR_AVAILABLE
    if _VECTOR_AVAILABLE is not None:
        return _VECTOR_AVAILABLE
    try:
        from infrastructure.vector_retriever import vector_retriever
        _VECTOR_AVAILABLE = vector_retriever is not None
    except Exception:
        _VECTOR_AVAILABLE = False
    return _VECTOR_AVAILABLE


async def _run_sync(func, *args, timeout=30, phase="", **kwargs):
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(_fast_executor, lambda: func(*args, **kwargs)),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        if phase:
            logger.warning(f"路径超时: {phase} ({timeout}秒)")
        raise


async def _run_slow(func, *args, timeout=90, phase="", **kwargs):
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(_slow_executor, lambda: func(*args, **kwargs)),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        if phase:
            logger.warning(f"慢路径超时: {phase} ({timeout}秒)")
        raise


def _save_to_experience_pool(query: str, response: str, success: bool = True, intent_type: str = "default",
                              quality_score: int = 80, duration: float = 0.0, model_name: str = "unknown"):
    try:
        try:
            from core.ethics.safe_learning import learn_safely
            safety = learn_safely(response, source=f"experience_pool/{model_name}", metadata={"query": query, "intent_type": intent_type})
            if not safety.get("accepted", True):
                logger.warning(f"学习内容未通过价值对齐检查: {safety.get('issues', [])}")
                quality_score = min(quality_score, 40)
        except Exception:
            pass

        from infrastructure.experience_pool import get_experience_pool
        ep = get_experience_pool()
        ep.add_experience(
            intent_type=intent_type, raw_input=query, plan="",
            model_name=model_name, quality_score=quality_score,
            user_feedback=0, success=success, duration=duration,
            response=response
        )
    except Exception as e:
        logger.error(f"经验存储失败: {e}")