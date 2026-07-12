import asyncio
import json
from typing import Optional
from loguru import logger
from infrastructure.database_manager import DatabaseManager

from backend.services.path_handlers._shared import (
    _fast_executor,
    _RESOURCE_AWARE,
    _check_vector_available,
)

try:
    from core.resource_awareness.health_monitor import get_health_monitor
except ImportError:
    get_health_monitor = None

try:
    from core.services.cognitive_planner import get_cognitive_planner, CognitivePlanner
    _COGNITIVE_PLANNER_AVAILABLE = True
except ImportError:
    _COGNITIVE_PLANNER_AVAILABLE = False

try:
    from core.self.model import get_self_model
    _SELF_MODEL_AVAILABLE = True
except ImportError:
    _SELF_MODEL_AVAILABLE = False


def get_cognitive_planner_safe():
    if not _COGNITIVE_PLANNER_AVAILABLE:
        return None
    try:
        return get_cognitive_planner()
    except Exception:
        return None


def get_self_model_safe():
    if not _SELF_MODEL_AVAILABLE:
        return None
    try:
        return get_self_model()
    except Exception:
        return None


class SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return str(obj)
        except Exception:
            return f"<{type(obj).__name__}>"


def emit(event_type: str, data: dict) -> str:
    if event_type == "result" and _RESOURCE_AWARE:
        try:
            if get_health_monitor:
                get_health_monitor().unregister_query()
        except Exception:
            logger.warning("操作降级跳过")
    return f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False, cls=SafeEncoder)}\n\n"


def build_uncertainty_note(query: str, response: str, attempts: list, prob_field, action: dict) -> str:
    entropy = prob_field._entropy if prob_field._candidates else 0
    candidates = prob_field._candidates if prob_field._candidates else {}

    verified_sources = []
    unverified_areas = []

    for name, result in attempts:
        if isinstance(result, bool) and result:
            if name in ("自我验证", "本质推理", "多源交叉验证", "代码验证", "科学免责"):
                verified_sources.append(name)
        if isinstance(result, bool) and not result:
            if name in ("自我验证", "本质推理", "多源交叉验证"):
                unverified_areas.append(name)

    source_names = []
    for cid, cinfo in candidates.items():
        src = cinfo.get("source", "")
        if src and src not in source_names:
            source_names.append(src)

    top_prob = 0.0
    if candidates:
        top_prob = max((c.get("probability", 0) for c in candidates.values()), default=0)

    lines = []
    lines.append("\n\n---")

    if top_prob >= 0.5 and verified_sources:
        confidence_desc = "主要结论经过了验证" if len(verified_sources) >= 2 else "核心观点有一定依据"
        lines.append(f"💡 {confidence_desc}——")
        for v in verified_sources[:3]:
            v_label = {"自我验证": "逻辑自洽检查", "本质推理": "第一性原理推演",
                       "多源交叉验证": "多来源比对", "代码验证": "代码语法验证",
                       "科学免责": "科学事实标注"}.get(v, v)
            lines.append(f"  ✓ {v_label}")
    else:
        lines.append("💡 这个回答我斟酌了一下——")

    if unverified_areas:
        lines.append("但以下方面我还没完全确认：")
        for u in unverified_areas[:2]:
            u_label = {"自我验证": "逻辑链条的完整性", "本质推理": "底层假设的可靠性",
                       "多源交叉验证": "不同来源的一致性"}.get(u, u)
            lines.append(f"  ✗ {u_label}")

    if source_names:
        sources_str = "、".join(source_names[:4])
        lines.append(f"参考来源：{sources_str}")

    if entropy > 0.85:
        lines.append("如果你有相关领域的经验，欢迎指正——我对这个话题的了解确实有限。")
    elif entropy > 0.7:
        specific_hint = ""
        q_lower = query.lower()
        if any(kw in q_lower for kw in ["代码", "编程", "函数", "api", "实现"]):
            specific_hint = "建议在实际环境中跑一遍确认。"
        elif any(kw in q_lower for kw in ["为什么", "原理", "机制", "本质"]):
            specific_hint = "如果需要更深入的推导，可以继续追问。"
        elif any(kw in q_lower for kw in ["多少", "什么时候", "哪个", "谁"]):
            specific_hint = "具体数据建议核对最新资料。"
        else:
            specific_hint = "关键细节建议再确认一下。"
        lines.append(specific_hint)

    lines.append("---")
    return "\n".join(lines)


def build_conversation_context(history: list) -> str:
    if not history:
        return ""
    parts = []
    for msg in history[-10:]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if not content:
            continue
        if "---\n⚠️" in content:
            content = content.split("---\n⚠️")[0].strip()
        if role == "user":
            parts.append(f"用户：{content[:300]}")
        elif role == "assistant":
            parts.append(f"助手：{content[:300]}")
    if not parts:
        return ""
    return "\n".join(parts)


def get_stereo_memory_context(query: str) -> str:
    try:
        from core.memory.stereo_memory import get_stereo_memory, MemoryType
        sm = get_stereo_memory()
        results = sm.search(query=query, limit=3)
        if not results:
            return ""
        parts = []
        for mem in results:
            content_str = str(mem.content)[:200] if mem.content else ""
            if content_str and len(content_str) > 20:
                emotion = mem.self_dimension.emotional_state
                confidence = mem.self_dimension.confidence
                parts.append(f"[记忆:{emotion} 置信度{confidence:.0%}] {content_str}")
        return "\n".join(parts) if parts else ""
    except Exception as e:
        logger.warning(f"立体记忆检索跳过: {e}")
        return ""


async def self_reason(query: str, conversation_context: str = "", truth_insights: str = "") -> Optional[dict]:
    """
    自我推理引擎 v2 — 本质推理+真谛类推驱动

    升级点：
    1. 真谛类推：用truth_accumulator.analogize()做跨域类推
    2. 本质推理：用essence_reasoner做第一性原理推理
    3. 知识聚合：经验+规则+真谛+本质推理综合
    4. 质量提升：从55→70+，高质量时无需调API
    """
    try:
        knowledge_parts = []
        quality_score = 50
        reasoning_depth = 0

        try:
            if _check_vector_available():
                from infrastructure.vector_retriever import vector_retriever
                if vector_retriever.is_available():
                    loop = asyncio.get_running_loop()
                    similar = await asyncio.wait_for(
                        loop.run_in_executor(_fast_executor, lambda: vector_retriever.search(query, top_k=5, threshold=0.4)),
                        timeout=5
                    )
                    for s in similar:
                        score = s.get('score', 0)
                        knowledge_parts.append(f"[经验 sim={score:.2f}] {s.get('text', '')[:250]}")
                        if score > 0.7:
                            quality_score += 5
                    reasoning_depth += 1
        except Exception:
            logger.warning("操作降级跳过")

        try:
            loop = asyncio.get_running_loop()
            def _query_rules():
                db = DatabaseManager.get("data/learning_rules.db")
                rows = db.query("SELECT rule_text, confidence FROM learning_rules WHERE status='active' AND rule_text LIKE ? ORDER BY confidence DESC LIMIT 5", (f"%{query[:10]}%",))
                return [(r[0], r[1]) for r in rows]
            rows = await asyncio.wait_for(loop.run_in_executor(_fast_executor, _query_rules), timeout=3)
            for row in rows:
                knowledge_parts.append(f"[规则 conf={row[1]:.2f}] {row[0][:250]}")
                if row[1] > 0.8:
                    quality_score += 3
            reasoning_depth += 1
        except Exception:
            logger.warning("操作降级跳过")

        analogy_insights = []
        try:
            from core.truth_accumulator import truth_accumulator
            loop = asyncio.get_running_loop()
            analogies = await asyncio.wait_for(
                loop.run_in_executor(_fast_executor, lambda: truth_accumulator.analogize(query)),
                timeout=5
            )
            for a in analogies[:4]:
                insight_text = f"[真谛类推 {a['level']}] {a['name']}：{a['statement'][:200]}"
                if a.get('relevance', 0) > 0.5:
                    insight_text += f" (相关度{a['relevance']:.0%})"
                    quality_score += 5
                analogy_insights.append(insight_text)
            if analogies:
                reasoning_depth += 1
                quality_score += 3
        except Exception:
            logger.warning("操作降级跳过")

        essence_result = None
        try:
            from core.essence_reasoner import essence_reasoner
            loop = asyncio.get_running_loop()
            essence_result = await asyncio.wait_for(
                loop.run_in_executor(_fast_executor, lambda: essence_reasoner.reason(query, "")),
                timeout=10
            )
            if essence_result:
                reasoning_depth += 2
                quality_score += 8
                if essence_result.get("passed"):
                    quality_score += 5
                if essence_result.get("confidence", 0) > 0.7:
                    quality_score += 5
                if essence_result.get("facts"):
                    for fact in essence_result.get("facts", [])[:3]:
                        knowledge_parts.append(f"[本质事实] {str(fact)[:200]}")
                if essence_result.get("reasoning_chain"):
                    knowledge_parts.append(f"[推理链] {essence_result['reasoning_chain'][:300]}")
                if essence_result.get("verdict"):
                    knowledge_parts.append(f"[本质判断] {essence_result['verdict'][:200]}")
        except Exception:
            logger.warning("操作降级跳过")

        if truth_insights:
            knowledge_parts.append(f"[注入真谛] {truth_insights[:300]}")
            quality_score += 3

        all_parts = knowledge_parts + analogy_insights
        if not all_parts:
            return None

        reasoning_sections = []

        if analogy_insights:
            reasoning_sections.append("【真谛类推推理】")
            reasoning_sections.extend(analogy_insights)
            reasoning_sections.append("")

        if knowledge_parts:
            reasoning_sections.append("【知识推理】")
            reasoning_sections.extend(knowledge_parts)
            reasoning_sections.append("")

        if essence_result and essence_result.get("passed"):
            reasoning_sections.append(f"【本质推理结论】置信度{essence_result.get('confidence', 0):.0%}，推理自洽 ✅")
        elif essence_result and not essence_result.get("passed"):
            issues = essence_result.get("issues", [])
            reasoning_sections.append(f"【本质推理】发现{len(issues)}个自洽性问题，推理需谨慎 ⚠️")

        reasoning_sections.append("")
        reasoning_sections.append(f"[推理深度={reasoning_depth} | 质量分={quality_score}]")

        reasoning = f"关于「{query}」，基于本质推理与真谛类推的综合推理：\n\n" + "\n".join(reasoning_sections)

        quality_score = min(quality_score, 85)

        try:
            from backend.services.path_handlers.tool_path import query_needs_tools
            if query_needs_tools(query):
                quality_score = min(quality_score, 40)
                logger.info(f"自我推理: 操作类问题'{query[:30]}'降权 quality={quality_score}")
        except Exception:
            logger.warning("操作降级跳过")

        return {"source": "自我推理", "response": reasoning, "quality": quality_score}
    except Exception as e:
        logger.error(f"自我推理异常: {e}")
    return None


async def background_collect(task, query: str, task_name: str):
    try:
        result = await task
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and item.get("response"):
                    try:
                        from backend.services.path_handlers._shared import _save_to_experience_pool
                        _save_to_experience_pool(query, item["response"], success=True, intent_type="background_collect", model_name="ollama")
                    except Exception:
                        logger.warning("操作降级跳过")
                    logger.info(f"🔄 后台收集: {task_name}推理完成，已存入经验池")
        elif isinstance(result, dict) and result.get("response"):
            try:
                from backend.services.path_handlers._shared import _save_to_experience_pool
                _save_to_experience_pool(query, result["response"], success=True, intent_type="background_collect", model_name="external")
            except Exception:
                logger.warning("操作降级跳过")
            logger.info(f"🔄 后台收集: {task_name}推理完成，已存入经验池")
    except Exception as e:
        logger.error(f"后台收集异常: {e}")


_error_alchemy_instance = None

def alchemize_error(error: Exception, context: dict = None, phase: str = "unknown"):
    """错误炼金辅助函数：将异常交给ErrorAlchemy提炼学习信号

    在chat_orchestrator的关键except块中调用此函数，
    而非在每个except块中重复import+record+alchemize三步。
    """
    global _error_alchemy_instance
    try:
        if _error_alchemy_instance is None:
            from core.learning.error_alchemy import ErrorAlchemy
            _error_alchemy_instance = ErrorAlchemy()
        err_id = _error_alchemy_instance.record_error(error, context={
            **(context or {}),
            "phase": phase,
        })
        result = _error_alchemy_instance.alchemize(err_id)
        if result.gold_extracted:
            logger.info(f"🔮 错误炼金[{phase}]: 从'{type(error).__name__}'中提炼{result.lessons_learned}个学习信号({','.join(result.patterns_found)})")
            return result
    except Exception:
        logger.warning("操作降级跳过")
    return None