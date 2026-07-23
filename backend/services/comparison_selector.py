"""
阶段4：对比择优 — 从多策略并行结果中选择最优响应

提取自 chat_orchestrator.py，包含：
- relevance filter（相关性过滤）
- 对比择优（_compare_and_select）
- ToolBuilder观察学习
- 贡献度归因（SHAP风格）
- 动态概率场初始化
- 世界模型反事实推理
"""
import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from backend.services.input_preprocessor import (
    get_intent_domain_keywords as _get_intent_domain_keywords,
    compute_relevance as _compute_relevance,
    feature_enabled as _feature_enabled,
)
from backend.services.orchestrator_helpers import (
    alchemize_error as _alchemize_error,
    emit as _emit,
)
from backend.services.path_handlers._shared import SPIRIT_CORE_AVAILABLE


async def compare_and_select(
    candidates: List[Dict],
    user_input: str,
    intent_type: str,
    confidence: float,
    cbnr_context: str,
    truth_insights: str,
    start_time: float,
    _compare_and_select,
    _dim_orch=None,
    event_sink=None,
    response_style: str = "",
    methodology: dict = None,
) -> Dict[str, Any]:
    """
    阶段4：对比择优

    Returns:
        {
            "best": dict or None,
            "comparison": list,
            "final_response": str or None,
            "attempts": list (appended),
            "path_percentages": dict,
            "events": list,
        }
    """
    events = []
    attempts = []
    path_percentages = {}

    def _emit_s(event_type: str, data: dict):
        if event_sink is not None:
            event_sink.emit(event_type, data)
        return (event_type, data)

    if not candidates:
        events.append(_emit_s("step", {"phase": "对比择优", "status": "done", "detail": "无有效候选结果"}))
        return {
            "best": None, "comparison": [], "final_response": None,
            "attempts": attempts, "path_percentages": path_percentages, "events": events,
        }

    _domain_keywords = _get_intent_domain_keywords(intent_type, user_input)
    for c in candidates:
        c["_relevance"] = _compute_relevance(c.get("response", ""), _domain_keywords)
    _before_cnt = len(candidates)
    _filtered = [c for c in candidates if c["_relevance"] > 0.12]
    if _filtered:
        candidates = _filtered
    else:
        candidates = sorted(candidates, key=lambda c: c.get("_relevance", 0), reverse=True)[:3]
    for c in candidates:
        c["quality"] = int(c.get("quality", 30) * 0.6 + c["_relevance"] * 40)

    if methodology and methodology.get("presence_mode"):
        for c in candidates:
            src = c.get("source", "")
            if "自我推理" in src:
                c["quality"] = min(100, int(c.get("quality", 30) * 1.5))
            elif "Ollama" in src or "本地模型" in src:
                c["quality"] = int(c.get("quality", 30) * 0.5)
            elif "外部" in src or "搜索" in src or "DeepSeek" in src:
                c["quality"] = int(c.get("quality", 30) * 0.3)
        logger.info(f"🪞 在场模式择优: 自我推理×1.5, Ollama×0.5, 外部×0.3")

    logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] 进入阶段4: 对比择优, {len(candidates)}个候选")
    for i, c in enumerate(candidates):
        logger.warning(f"[ORCH_DIAG] 候选{i}: source={c.get('source')}, quality={c.get('quality')}, resp_len={len(c.get('response',''))}, resp_preview={c.get('response','')[:80]}")
    events.append(_emit_s("step", {"phase": "对比择优", "status": "running", "detail": f"对{len(candidates)}个结果评分对比..."}))

    best, comparison = _compare_and_select(candidates, user_input, cbnr_ctx=cbnr_context, response_style=response_style)

    if best:
        final_response = best["response"]
        for c in comparison:
            src = c["source"]
            sc = c["score"]
            attempts.append((src, sc >= 60, f"评分{sc:.0f}"))
        events.append(_emit_s("step", {"phase": "对比择优", "status": "done", "detail": f"最优来源: {best['source']} (评分{comparison[0]['score']:.0f})，共{len(comparison)}个候选"}))

        try:
            from core.learning.tool_builder import ToolSelfBuilder
            tb = ToolSelfBuilder()
            for c in comparison:
                if c.get("score", 0) >= 60:
                    tb.record_success(c["source"], user_input, c.get("response", "")[:200])
        except Exception as e:
            logger.warning(f"ToolBuilder观察跳过: {e}")
            _alchemize_error(e, context={"user_input": user_input[:50]}, phase="tool_builder_observe")

        if _feature_enabled("path_weight_matrix"):
            try:
                from core.contrib_attributor import contrib_attributor
                from core.path_weight_manager import path_weight_manager
                attrib = contrib_attributor.compute_contributions(
                    candidates, final_response, best["source"], user_input
                )
                for src, score in attrib.get("contributions", {}).items():
                    unc_info = (attrib.get("retrieval_uncertainties") or {}).get(src)
                    uncertainty = unc_info.get("retrieval_entropy") if unc_info else None
                    from backend.services.response_aggregator import _SOURCE_TO_WEIGHT_KEY
                    weight_key = _SOURCE_TO_WEIGHT_KEY.get(src, src)
                    path_weight_manager.update_weight(weight_key, True, score, uncertainty=uncertainty,
                                                        resource_pressure=path_weight_manager.compute_resource_pressure())
                if attrib.get("contributions"):
                    contrib_str = " | ".join(f"{k}:{float(v):.0%}" for k, v in list(attrib["contributions"].items())[:5] if v is not None)
                    unc_str = ""
                    if attrib.get("retrieval_uncertainties"):
                        unc_dims = len(attrib["retrieval_uncertainties"])
                        unc_str = f" | 不确定性维度:{unc_dims}"
                    events.append(_emit_s("step", {"phase": "贡献归因", "status": "done", "detail": f"贡献度: {contrib_str}{unc_str}"}))
            except Exception as e:
                logger.warning(f"贡献归因跳过: {e}")
                _alchemize_error(e, context={"user_input": user_input[:50]}, phase="contrib_attribution")

        if _feature_enabled("path_weight_matrix"):
            try:
                from core.dynamic_probability_field import dynamic_probability_field
                from core.path_weight_manager import path_weight_manager
                prob_dist = dynamic_probability_field.initialize(candidates, path_weight_manager.get_weights())
                if prob_dist.get("top"):
                    action = dynamic_probability_field.get_uncertainty_action()
                    action_hint = ""
                    if action["depth"] == "deep":
                        action_hint = " | 建议深度探索"
                    elif action["depth"] == "moderate":
                        action_hint = f" | {action.get('uncertainty_label', '')}"
                    events.append(_emit_s("step", {"phase": "概率场", "status": "done",
                        "detail": f"概率分布: top={prob_dist['top']['source']}({float(prob_dist['top']['probability']):.0%}) 熵={prob_dist['entropy']:.2f}{action_hint}"}))
            except Exception as e:
                logger.warning(f"概率场初始化跳过: {e}")
                _alchemize_error(e, context={"user_input": user_input[:50]}, phase="probability_field")

        try:
            from core.world_model import get_world_model
            wm = get_world_model()
            if best and len(candidates) >= 2:
                actual_source = best.get("source", "")
                alt_source = ""
                for c in candidates:
                    src = c.get("source", "")
                    if src != actual_source:
                        alt_source = src
                        break
                if alt_source:
                    cf = wm.counterfactual(
                        {"intent": intent_type, "query": user_input[:50]},
                        actual_source, alt_source, intent_type
                    )
                    if cf.get("would_have_been_better"):
                        logger.info(f"世界模型反事实: 选择'{actual_source}'不如'{alt_source}'，差异={cf['advantage']:.3f}")
                    wm.save_counterfactual(
                        intent_type, actual_source, alt_source,
                        cf["actual"]["score"], cf["counterfactual"]["score"],
                        cf["would_have_been_better"], cf["lesson"]
                    )
            if best:
                wm.auto_verify(
                    wm._hash_state({"intent": intent_type, "query": user_input[:50]}, intent_type),
                    {"outcome": "success" if best.get("score", 0) >= 60 else "failure", "source": best.get("source", "")}
                )
        except Exception as e:
            logger.warning(f"世界模型反事实推理跳过: {e}")
            _alchemize_error(e, context={"user_input": user_input[:50]}, phase="world_model_counterfactual")
    else:
        events.append(_emit_s("step", {"phase": "对比择优", "status": "done", "detail": "无有效候选结果"}))

    if _dim_orch:
        try:
            from core.cognition.dimension_orchestrator import CognitiveDimension
            _dim_orch.update_dimension(CognitiveDimension.CAUSAL, confidence, f"best_source={best.get('source','') if best else 'none'}")
        except Exception:
            pass

    return {
        "best": best,
        "comparison": comparison,
        "final_response": final_response if best else None,
        "attempts": attempts,
        "path_percentages": path_percentages,
        "events": events,
    }