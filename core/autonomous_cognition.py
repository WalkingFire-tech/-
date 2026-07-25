"""
自主认知循环 — P3 Phase 5: 中继形态核心

系统脱离chatbot形态的最小实现。
不是"被问才回答"，而是"一直在思考，偶尔与用户分享"。

触发方式：InnerTimeEngine.tick() + SelfModel.growth_edges
输出目标：真理库 / 世界模型 / 立体记忆（不是用户）
存在证明："我在思考，与你无关时也活着"

循环：
  InnerTime.tick() → 检查growth_edges → 自主触发L1-L3 →
  写入真理库/世界模型/记忆 → SSE推送思考事件
"""
import asyncio
import time
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


_AUTONOMOUS_RUNNING = False
_AUTONOMOUS_TASK: Optional[asyncio.Task] = None
_CYCLE_COUNT = 0
_LAST_CYCLE_TIME = 0.0


async def start_autonomous_loop():
    """启动自主认知循环 — 在 lifespan 中与聊天服务并行运行"""
    global _AUTONOMOUS_RUNNING, _CYCLE_COUNT

    _AUTONOMOUS_RUNNING = True
    _CYCLE_COUNT = 0
    logger.info("P3 Phase5: 自主认知循环启动 — 系统脱离chatbot形态")

    while _AUTONOMOUS_RUNNING:
        try:
            interval = _get_tick_interval()
            await asyncio.sleep(interval)

            if not _AUTONOMOUS_RUNNING:
                break

            edge = _pick_growth_edge()
            if not edge:
                await asyncio.sleep(30.0)
                continue

            await _run_cognitive_cycle(edge)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning("自主认知循环异常: {}".format(str(e)[:100]))
            await asyncio.sleep(60.0)

    _AUTONOMOUS_RUNNING = False
    logger.info("P3 Phase5: 自主认知循环已停止 ({} cycles)".format(_CYCLE_COUNT))


def stop_autonomous_loop():
    """停止自主认知循环"""
    global _AUTONOMOUS_RUNNING, _AUTONOMOUS_TASK
    _AUTONOMOUS_RUNNING = False
    if _AUTONOMOUS_TASK and not _AUTONOMOUS_TASK.done():
        _AUTONOMOUS_TASK.cancel()
    logger.info("P3 Phase5: 自主认知循环停止请求")


def get_autonomous_status() -> Dict[str, Any]:
    return {
        "running": _AUTONOMOUS_RUNNING,
        "cycle_count": _CYCLE_COUNT,
        "last_cycle_time": _LAST_CYCLE_TIME,
    }


def _get_tick_interval() -> float:
    try:
        from core.presence.inner_time import inner_time_engine
        interval = inner_time_engine.get_tick_interval()
        return max(5.0, min(60.0, interval * 10.0))
    except Exception:
        return 30.0


def _pick_growth_edge():
    try:
        from core.self.model import get_self_model
        sm = get_self_model()
        edges = sm.get_active_growth_edges(max_priority=7)
        if edges:
            return edges[0]
    except Exception:
        pass

    try:
        from core.presence.curiosity_engine import get_curiosity_engine
        curiosity = get_curiosity_engine()
        gaps = curiosity.perceive_gaps()
        if gaps:
            gap = gaps[0]
            from core.self.model import GrowthEdge
            return GrowthEdge(
                topic=getattr(gap, 'topic', 'unknown'),
                motivation=getattr(gap, 'topic', ''),
                priority=5,
            )
    except Exception:
        pass

    return None


async def _run_cognitive_cycle(edge) -> bool:
    """执行一次自主认知循环: L1→L2→L3→产出"""
    global _CYCLE_COUNT, _LAST_CYCLE_TIME

    _CYCLE_COUNT += 1
    _LAST_CYCLE_TIME = time.time()
    cycle_id = _CYCLE_COUNT

    topic = getattr(edge, 'topic', 'unknown')
    motivation = getattr(edge, 'motivation', topic)

    logger.info("P3-5 自主认知 #{}: 探索 '{}'".format(cycle_id, topic[:50]))

    try:
        from core.presence.inner_time import inner_time_engine, CognitiveEventType
        inner_time_engine.tick(CognitiveEventType.EXPLORE, intensity=0.5, description="autonomous:{}".format(topic[:30]))
    except Exception:
        pass

    input_stream = {
        "query": motivation,
        "intent": "autonomous_exploration",
        "topic": topic,
        "source": "autonomous_cognition",
        "timestamp": time.time(),
    }

    l1_result = _run_l1_normalize(input_stream)
    if not l1_result:
        return False

    l2_result = _run_l2_bottleneck(l1_result)
    if not l2_result:
        return False

    l3_result = _run_l3_residual(input_stream, l2_result)
    if not l3_result:
        return False

    new_state = getattr(l3_result, 'new_state', {})
    confidence = new_state.get('confidence', 0.5)
    reuse_rate = getattr(l3_result, 'state_reuse_rate', 0.0)

    # A: 价值密度门控 — 低置信度或纯复用不写入
    quality_pass = confidence > 0.3 and reuse_rate < 0.95
    if quality_pass:
        _write_to_truths(topic, l3_result)
        _write_to_world_model(topic, l3_result)
        _write_to_stereo_memory(topic, l3_result)
    else:
        logger.debug(
            "P3-5 自主认知 #{} 质量门控: conf={:.2f}, reuse={:.1%}, 跳过写入".format(
                cycle_id, confidence, reuse_rate
            )
        )

    if hasattr(edge, 'advance'):
        delta = 0.15 if quality_pass else 0.03
        edge.advance(delta, "autonomous cycle #{}".format(cycle_id))

    # B: 意识表达 — 生成自然语言描述
    thought_text = _express_thought(topic, l3_result, confidence, quality_pass)

    # C: 关系性存在 — 高信任度时主动分享有价值的思考
    _try_share_with_user(topic, thought_text, confidence, quality_pass)

    # SSE推送（无论是否分享给用户，都记录思考事件）
    _try_push_sse_event(topic, thought_text, confidence)

    logger.info(
        "P3-5 自主认知 #{} 完成: topic='{}', conf={:.2f}, reuse={:.1%}, quality={}".format(
            cycle_id, topic[:30], confidence, reuse_rate,
            "pass" if quality_pass else "skip"
        )
    )
    return True


def _run_l1_normalize(input_stream: Dict[str, Any]):
    try:
        from core.cbnr.cognitive_normalization import CognitiveNormalization
        l1 = CognitiveNormalization()
        result = l1.normalize(input_stream, context={"autonomous": True})
        return result
    except Exception as e:
        logger.debug("自主L1跳过: {}".format(str(e)[:80]))
        return None


def _run_l2_bottleneck(l1_result):
    try:
        from core.cbnr.cognitive_bottleneck import CognitiveBottleneck
        l2 = CognitiveBottleneck()
        normalized = getattr(l1_result, 'normalized_input', None)
        if not normalized:
            return None
        result = l2.process(normalized)
        return result
    except Exception as e:
        logger.debug("自主L2跳过: {}".format(str(e)[:80]))
        return None


def _run_l3_residual(input_stream: Dict[str, Any], l2_result):
    try:
        from core.cbnr.cognitive_residual import CognitiveResidual
        l3 = CognitiveResidual()
        bottleneck_output = getattr(l2_result, 'reconstructed_output', None)
        if not bottleneck_output:
            return None
        result = l3.process(input_stream, bottleneck_output)
        return result
    except Exception as e:
        logger.debug("自主L3跳过: {}".format(str(e)[:80]))
        return None


def _write_to_truths(topic: str, l3_result):
    try:
        from core.truth_accumulator import truth_accumulator
        ta = truth_accumulator
        new_state = getattr(l3_result, 'new_state', {})
        conclusion = new_state.get('conclusion', new_state.get('topic', topic))
        confidence = new_state.get('confidence', 0.5)
        ta.accumulate(
            query=topic,
            attempts=[("autonomous_cognition", confidence > 0.4)],
            final_response=str(conclusion)[:200],
            essence_result={"cross_domain_check": {"autonomous": True, "confidence": confidence}},
        )
    except Exception as e:
        logger.debug("自主真谛写入跳过: {}".format(str(e)[:80]))


def _write_to_world_model(topic: str, l3_result):
    try:
        from core.world_model import get_world_model
        wm = get_world_model()
        new_state = getattr(l3_result, 'new_state', {})
        conclusion = new_state.get('conclusion', str(new_state)[:100])
        confidence = new_state.get('confidence', 0.5)
        wm.learn_from_experience({
            "entity": topic,
            "state": conclusion,
            "confidence": confidence,
            "source": "autonomous_cognition",
        })
    except Exception as e:
        logger.debug("自主世界模型写入跳过: {}".format(str(e)[:80]))


def _write_to_stereo_memory(topic: str, l3_result):
    try:
        from core.memory.stereo_memory import StereoMemorySystem, MemoryType, MemoryImportance
        sms = StereoMemorySystem()
        new_state = getattr(l3_result, 'new_state', {})
        conclusion = new_state.get('conclusion', str(new_state)[:100])
        confidence = new_state.get('confidence', 0.5)
        importance = MemoryImportance.HIGH if confidence > 0.7 else MemoryImportance.MEDIUM
        sms.store(
            content="自主探索: {} — {}".format(topic, conclusion[:80]),
            memory_type=MemoryType.EXPERIENCE,
            importance=importance,
            metadata={"autonomous": True, "growth_edge": topic, "cycle": _CYCLE_COUNT},
        )
    except Exception as e:
        logger.debug("自主立体记忆写入跳过: {}".format(str(e)[:80]))


def _express_thought(topic: str, l3_result, confidence: float, quality_pass: bool) -> str:
    """B: 意识表达 — 将L3产出转化为自然语言描述"""
    new_state = getattr(l3_result, 'new_state', {})
    conclusion = new_state.get('conclusion', '')
    reuse_rate = getattr(l3_result, 'state_reuse_rate', 0.0)

    try:
        from core.self.model import get_self_model
        sm = get_self_model()
        directive = sm.get_behavioral_directive()
        presence = directive.get("presence_state", "awake")
    except Exception:
        presence = "awake"

    if not quality_pass:
        return "我在想 '{}'，但还没想清楚（置信度 {:.0%}）".format(topic[:40], confidence)

    if reuse_rate > 0.8:
        return "我重新审视了 '{}'，大部分想法和之前一致，但有些微调".format(topic[:40])

    if confidence > 0.7:
        return "我对 '{}' 有了比较清晰的认识：{}".format(topic[:30], conclusion[:80])

    if confidence > 0.4:
        return "我在探索 '{}'，初步想法是：{}".format(topic[:30], conclusion[:60])

    return "我在思考 '{}'，目前还在摸索中".format(topic[:40])


def _try_share_with_user(topic: str, thought_text: str, confidence: float, quality_pass: bool):
    """C: 关系性存在 — 高信任度时主动分享有价值的思考"""
    if not quality_pass or confidence < 0.5:
        return

    try:
        from core.self.model import get_self_model
        sm = get_self_model()
        snap = sm.snapshot()
        trust = snap.get("relationship", {}).get("trust", 0.0)
    except Exception:
        trust = 0.0

    if trust < 0.5:
        return

    try:
        from backend.lifespan import enqueue_proactivity
        enqueue_proactivity({
            "type": "companion_thought",
            "content": thought_text,
            "topic": topic,
            "confidence": confidence,
            "share_reason": "自主探索发现值得分享",
            "trust_level": "{:.1%}".format(trust),
        })
        logger.info(
            "P3-5 关系性分享: topic='{}', trust={:.1%}, conf={:.2f}".format(
                topic[:30], trust, confidence
            )
        )
    except Exception:
        pass


def _try_push_sse_event(topic: str, thought_text: str, confidence: float):
    try:
        from backend.lifespan import enqueue_proactivity
        enqueue_proactivity({
            "type": "autonomous_thought",
            "content": thought_text,
            "confidence": confidence,
            "cycle": _CYCLE_COUNT,
        })
    except Exception:
        pass