"""
流式聊天处理 - 多路并行、无固定超时、结果对比择优

核心改进：
- 多路并行获取结果（经验池 + 知识库 + Ollama + 规则），不串行等待
- 不设固定超时，外部调用等它自然返回或异常
- 结果到齐后对比择优，自我验证
- 持久化任务队列：后台任务存SQLite，服务重启不丢失，失败自动重试
- 模型分级仲裁：评估用快模型，推理用强模型
- 基因库固化：高质量回复自动升级为永久知识

编排逻辑已迁移至 backend/services/chat_orchestrator.py
本文件保留向后兼容的导入入口
"""
from backend.services.chat_orchestrator import (
    chat_stream,
    _emit,
    _build_uncertainty_note,
    _build_conversation_context,
    _get_stereo_memory_context,
    _self_reason,
    _background_collect,
    _reflect_and_learn,
    _background_deep_thinking,
    _solve_history_query,
    _generate_meaningful_fallback,
    _try_solidify_to_gene_pool,
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
