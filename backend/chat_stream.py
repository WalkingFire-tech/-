"""
流式聊天处理 - 多路并行、无固定超时、结果对比择优

编排逻辑已迁移至 backend/services/chat_orchestrator.py
本文件保留向后兼容的导入入口
"""
from backend.services.chat_orchestrator import chat_stream
from backend.services.orchestrator_helpers import (
    emit as _emit,
    build_uncertainty_note as _build_uncertainty_note,
    build_conversation_context as _build_conversation_context,
    get_stereo_memory_context as _get_stereo_memory_context,
    self_reason as _self_reason,
    background_collect as _background_collect,
)
from backend.services.input_preprocessor import generate_meaningful_fallback as _generate_meaningful_fallback
from backend.services.reflection_service import (
    reflect_and_learn as _reflect_and_learn,
    try_solidify_to_gene_pool as _try_solidify_to_gene_pool,
)
from backend.services.response_assembler import (
    background_deep_thinking as _background_deep_thinking,
    solve_history_query as _solve_history_query,
)

__all__ = [
    "chat_stream",
    "_emit",
    "_build_uncertainty_note",
    "_build_conversation_context",
    "_get_stereo_memory_context",
    "_self_reason",
    "_background_collect",
    "_reflect_and_learn",
    "_background_deep_thinking",
    "_solve_history_query",
    "_generate_meaningful_fallback",
    "_try_solidify_to_gene_pool",
]
