import asyncio
import time
import json
import threading as _th
from loguru import logger

from backend.services.auto_fix_service import run_persistent_solve as _run_persistent_solve, never_give_up_response as _never_give_up_response
from backend.services.input_preprocessor import feature_enabled as _feature_enabled
from backend.services.orchestrator_helpers import (
    is_goal_achieved as _is_goal_achieved,
    get_self_model_safe as _get_self_model,
)
from backend.services.path_handlers._shared import (
    _slow_executor, _save_to_experience_pool, _MAX_RESPONSE_CHARS, SPIRIT_CORE_AVAILABLE,
)
from backend.services.path_handlers.ollama_path import fetch_ollama_response as _fetch_ollama_response
from core.ports.adapters import get_storage_port


async def assemble_and_emit(
    user_input: str, final_response: str, attempts: list,
    intent_type: str, route: str, confidence: float,
    methodology: dict, fitness_score, candidates: list,
    comparison: list, best: dict, path_percentages: dict,
    cbnr_context: dict, _l1_normalized: dict,
    content_understanding: dict, companion_layers: dict,
    conversation_context: str, truth_insights: str,
    start_time: float, _chat_session_id: str,
    cp, _cognitive_perception: dict, _cognitive_learning: dict,
    _cognitive_integration: dict, _cognitive_validation: dict,
    _cognitive_introspection, _emit,
):
    events = []
    elapsed = time.time() - start_time

    if not final_response:
        try:
            ollama_result = await _fetch_ollama_response(user_input, conversation_context=conversation_context, truth_insights="")
            if ollama_result and ollama_result.get("response") and len(ollama_result["response"]) > 20:
                final_response = ollama_result["response"]
                attempts.append(("终极保护-动态", True, "模型实时生成"))
            else:
                attempts.append(("终极保护-动态", False, "模型无有效回复"))
        except Exception as _e:
            logger.warning(f"终极保护-动态推理异常: {_e}")
            attempts.append(("终极保护-动态", False, f"模型异常: {str(_e)[:40]}"))

        if not final_response:
            try:
                events.append({"type": "step", "data": {"phase": "终极持续求解", "status": "running", "detail": "终极保护启动持续求解引擎..."}})
                final_response, _ps_ok2 = await _run_persistent_solve(
                    user_input, attempts, conversation_context,
                    "", intent_type, "终极持续求解", _emit)
                if not _ps_ok2:
                    final_response = final_response or _never_give_up_response(user_input, attempts)
            except Exception as _pse2:
                logger.warning(f"终极持续求解异常: {_pse2}")
                final_response = _never_give_up_response(user_input, attempts)
                attempts.append(("终极持续求解", False, f"异常: {str(_pse2)[:40]}"))

    _save_to_experience_pool(
        user_input, final_response,
        success=any(a[1] for a in attempts),
        intent_type=intent_type,
        quality_score=int(fitness_score.final_score) if fitness_score else (80 if any(a[1] for a in attempts) else 40),
        duration=elapsed,
        model_name=best.get("source", "unknown") if best else "unknown"
    )

    try:
        from core.presence.existence_layer import get_existence_layer
        _el = get_existence_layer()
        if hasattr(_el, 'record_interaction'):
            _quality = int(fitness_score.final_score) if fitness_score else (80 if any(a[1] for a in attempts) else 40)
            _el.record_interaction(quality_score=_quality, user_feedback=0)
    except Exception:
        pass

    try:
        from core.trajectory_evolution import trajectory_store
        traj_steps = []
        for a in attempts:
            traj_steps.append({
                "phase": a[0] if len(a) > 0 else "",
                "success": a[1] if len(a) > 1 else False,
                "detail": a[2] if len(a) > 2 else "",
                "duration_ms": 0
            })
        traj_decisions = []
        if route == "slow" and candidates:
            best_src = comparison[0]["source"] if comparison else ""
            traj_decisions.append({"type": "path_selection", "chosen": best_src, "reason": "highest_score"})
        if path_percentages:
            traj_decisions.append({"type": "path_contribution", "distribution": path_percentages})
        traj_outcome = {
            "quality_score": int(fitness_score.final_score) if fitness_score else (80 if any(a[1] for a in attempts) else 40),
            "confidence": confidence,
            "duration": elapsed,
            "response_length": len(final_response) if final_response else 0,
            "success": any(a[1] for a in attempts)
        }
        traj_fitness = trajectory_store.evaluate_trajectory(traj_steps, traj_outcome)
        trajectory_store.store_trajectory(
            query=user_input,
            steps=traj_steps,
            decisions=traj_decisions,
            outcome=traj_outcome,
            intent_type=intent_type,
            route=route,
            fitness_score=traj_fitness,
            duration=elapsed,
            source="live"
        )
    except Exception as e:
        logger.warning(f"轨迹存储跳过: {e}")

    token_summary = {}
    for c in candidates:
        if isinstance(c, dict) and "tokens" in c:
            src = c.get("source", "未知")
            tk = c["tokens"]
            if tk.get("total_tokens", 0) > 0:
                token_summary[src] = tk

    try:
        from core.alignment_guard import get_alignment_guard
        guard = get_alignment_guard()
        guard.check_response_alignment(user_input, final_response or "", "chat_stream")
    except Exception:
        logger.warning("操作降级跳过")

    try:
        from core.cbnr.hub import get_cbnr_hub
        _cbnr_hub = get_cbnr_hub()
        _l2_output = {
            "topic": cbnr_context.get("l2_topic", ""),
            "entities": cbnr_context.get("l2_entities", []),
            "causal_chain": cbnr_context.get("l2_causal_chain", []),
            "counterfactuals": cbnr_context.get("l2_counterfactuals", []),
            "resolution_mode": cbnr_context.get("l2_conflict_mode", "unknown"),
        }
        _l3_result = _cbnr_hub.process_l3(_l1_normalized, _l2_output)
        cbnr_context["l3_reuse_rate"] = _l3_result.state_reuse_rate
        cbnr_context["l3_search_tree_size"] = _l3_result.search_tree_size
        cbnr_context["l3_fallback_used"] = _l3_result.fallback_used
        cbnr_context["l3_has_experience_base"] = _l3_result.new_state.get("_has_experience_base", False)
        logger.warning(f"CBNR L3: 复用率={_l3_result.state_reuse_rate:.1%}, 搜索树={_l3_result.search_tree_size}")
        try:
            _cbnr_hub.finalize_distributed()
        except Exception:
            logger.warning("操作降级跳过")
    except Exception as e:
        logger.warning(f"CBNR L3跳过: {e}")

    if final_response and len(final_response) > _MAX_RESPONSE_CHARS:
        logger.warning(f"响应过长({len(final_response)}字符)，截断至{_MAX_RESPONSE_CHARS}(GPU过热保护)")
        final_response = final_response[:_MAX_RESPONSE_CHARS] + "\n\n[回复已截断以保护GPU，避免过热断电]"

    try:
        if SPIRIT_CORE_AVAILABLE and final_response:
            from core.spirit_core import spirit_core as _spirit_core
            validation = _spirit_core.validate_response(final_response, context={"query": user_input, "content_understanding": content_understanding if content_understanding else {}})
            companion_layers = {
                "L1_paradigm_match": validation.get("checks", {}).get("meaningful", False),
                "L2_boundary_awareness": validation.get("checks", {}).get("pursue_essence", False),
                "L3_silence_allowed": validation.get("checks", {}).get("state_sync", False),
                "L4_success_archive": validation.get("checks", {}).get("failure_direction", False),
                "L5_self_alignment": validation.get("checks", {}).get("honest_when_lost", False),
                "spirit_score": validation.get("score", 0),
            }
    except Exception:
        logger.warning("操作降级跳过")

    if final_response and confidence is not None and confidence < 0.5:
        quality_hint = "\n\n💡 **我的思考**：我对这个回答的把握不太高。如果你觉得不够深入，可以试试：换个角度提问、补充更多背景、或者把问题拆成更小的部分——这样我能给你更有价值的视角。"
        if len(final_response) < 500:
            final_response += quality_hint

    try:
        _sm = _get_self_model()
        if _sm and final_response and user_input:
            _quality = _sm.detect_interaction_quality(
                user_input, final_response, confidence or 0.5, attempts
            )
            if _quality["should_proactively_improve"] and _quality["suggestions"]:
                _best_suggestion = _quality["suggestions"][0]
                if _best_suggestion not in final_response:
                    final_response += f"\n\n💡 {_best_suggestion}"
    except Exception:
        pass

    try:
        _sm_learn = _get_self_model()
        if _sm_learn and final_response:
            _rl = _sm_learn.snapshot().get("recent_learning", [])
            if _rl:
                _latest = _rl[-1]
                _learn_summary = _latest.get("summary", "")
                _learn_src = _latest.get("source", "")
                if _learn_summary and _learn_src == "L2_learning":
                    _growth_line = f"\n\n🌱 **我学到了**：{_learn_summary[:120]}"
                    if _growth_line not in final_response and "我学到了" not in final_response:
                        final_response += _growth_line
    except Exception:
        pass

    if final_response and not _is_goal_achieved(user_input, final_response, intent_type, attempts):
        logger.info(f"🔄 目标未达成检测: 回复是半成品，启动持续求解...")
        events.append({"type": "step", "data": {"phase": "目标达成检查", "status": "running", "detail": "检测到回复未真正解决问题，启动持续求解..."}})
        _original_response = final_response
        try:
            _ti = truth_insights if truth_insights else ""
            ps_resp3, ps_ok3 = await _run_persistent_solve(
                user_input, attempts, conversation_context,
                _ti, intent_type, "目标达成求解", _emit)
            if ps_ok3 and ps_resp3 and len(ps_resp3) > len(_original_response) * 0.5:
                final_response = ps_resp3
                events.append({"type": "step", "data": {"phase": "目标达成检查", "status": "done", "detail": "✅ 持续求解成功，目标达成"}})
            else:
                if ps_resp3 and len(ps_resp3) > len(_original_response):
                    final_response = ps_resp3
                else:
                    final_response = _original_response
                events.append({"type": "step", "data": {"phase": "目标达成检查", "status": "done", "detail": "⚠️ 持续求解未改善，保留原始回复"}})
        except Exception as _pse3:
            logger.warning(f"目标达成求解异常: {_pse3}")
            final_response = _original_response
            attempts.append(("目标达成求解", False, f"异常: {str(_pse3)[:40]}"))

    result_payload = {
        "response": final_response,
        "attempts": attempts,
        "intent": intent_type,
        "confidence": confidence,
        "route": route,
        "elapsed": round(elapsed, 1),
        "spirit_compliant": SPIRIT_CORE_AVAILABLE,
        "candidates": comparison if candidates else [],
        "path_contributions": path_percentages if path_percentages else {},
        "token_usage": token_summary,
        "cbnr": cbnr_context if cbnr_context else {},
        "session_id": _chat_session_id or "",
        "companion_layers": companion_layers,
        "cognitive_layers": {
            "L1_perception": {k: v for k, v in _cognitive_perception.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))} if _cognitive_perception and isinstance(_cognitive_perception, dict) else {},
            "L2_learning": {k: v for k, v in _cognitive_learning.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))} if _cognitive_learning and isinstance(_cognitive_learning, dict) else {},
            "L3_integration": {k: v for k, v in _cognitive_integration.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))} if _cognitive_integration and isinstance(_cognitive_integration, dict) else {},
            "L4_validation": {k: v for k, v in _cognitive_validation.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))} if _cognitive_validation and isinstance(_cognitive_validation, dict) else {},
            "L5_evolution_triggered": cp is not None and _cognitive_perception is not None,
            "L6_introspection": str(_cognitive_introspection)[:500] if _cognitive_introspection else {},
        } if cp else {},
    }

    try:
        _sm = _get_self_model()
        if _sm:
            result_payload["behavioral_directive"] = _sm.get_behavioral_directive()
    except Exception:
        pass

    try:
        from infrastructure.hardware_monitor import set_ollama_cooldown
        set_ollama_cooldown(3.0)
    except Exception:
        logger.warning("操作降级跳过")

    if _chat_session_id and final_response:
        try:
            from infrastructure.chat_history import get_chat_history
            _ch = get_chat_history()
            _cbnr_sum = ""
            try:
                if cbnr_context:
                    _cbnr_sum = json.dumps(cbnr_context, ensure_ascii=False)[:500]
            except Exception:
                logger.warning("操作降级跳过")
            _ch.add_message(
                _chat_session_id, "assistant", final_response,
                intent=intent_type, route=route, confidence=confidence,
                elapsed=round(elapsed, 1), cbnr_summary=_cbnr_sum
            )
        except Exception as e:
            logger.warning(f"对话历史写入assistant跳过: {e}")

    return {
        "final_response": final_response,
        "attempts": attempts,
        "companion_layers": companion_layers,
        "cbnr_context": cbnr_context,
        "result_payload": result_payload,
        "events": events,
        "elapsed": elapsed,
    }


async def run_background_phase(
    user_input: str, final_response: str, confidence: float,
    start_time: float, _emit, session_id: str = "", intent_type: str = "unknown",
):
    events = []

    events.append({"type": "step", "data": {"phase": "后台处理", "status": "running", "detail": "响应已发送，后台继续深度处理..."}})

    _bg_tasks = []
    _bg_completed = set()
    _bg_lock = _th.Lock()

    def _bg_done(name):
        with _bg_lock:
            _bg_completed.add(name)

    try:
        from core.knowledge_gap_detector import gap_detector
        has_gap, reason, issues = gap_detector.detect_knowledge_gap(
            user_input, final_response, confidence=confidence
        )
        if has_gap:
            async def _bg_auto_evolution():
                try:
                    from core.auto_learning_evolution import auto_evolution
                    evolution_result = await asyncio.get_running_loop().run_in_executor(
                        _slow_executor,
                        lambda: auto_evolution.process_query_with_evolution(
                            user_input, final_response, confidence=confidence
                        )
                    )
                    if evolution_result and evolution_result.get('corrected'):
                        logger.info(f"🧬 自动学习进化修正: {reason}")
                    logger.info("🧬 后台自动学习进化完成")
                except Exception as e:
                    logger.warning(f"后台自动学习进化异常: {e}")
                _bg_done("auto_evolution")

            task = asyncio.create_task(_bg_auto_evolution())
            _bg_tasks.append(task)
    except Exception as e:
        logger.warning(f"自动学习进化跳过: {e}")

    try:
        from core.presence.self_assessment import get_self_assessment
        _sa = get_self_assessment()
        _sa.assess_conversation(
            conversation_id=session_id or "unknown",
            user_input=user_input,
            system_response=final_response,
            context={"confidence": confidence, "intent": intent_type},
        )
        logger.debug(f"适应度评估完成: score={_sa.current_assessment.overall_score:.2f}" if _sa.current_assessment else "适应度评估跳过")
    except Exception as e:
        logger.debug(f"适应度评估跳过: {e}")

    try:
        from core.layers.l5_evolution import get_l5_evolution
        _l5 = get_l5_evolution()
        _l5_experience = {
            "user_input": user_input,
            "response": final_response,
            "validation_result": {"status": "pass" if confidence >= 0.5 else "partial", "confidence": confidence},
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "conversation_id": session_id or "unknown",
        }
        try:
            from core.layers.l2_learning import get_l2_learning
            _l2 = get_l2_learning()
            _l2_status = _l2.get_learning_status()
            _l2_stats = _l2_status.get("stats", {})
            _l5_experience["learning_result"] = {
                "knowledge_gained": _l2_stats.get("total_knowledge_gained", 0),
                "avg_knowledge_quality": _l2_stats.get("avg_knowledge_quality", 0),
                "knowledge_reuse_rate": 0.0,
            }
        except Exception:
            _l5_experience["learning_result"] = {"knowledge_gained": 0}
        _l5.record_experience(_l5_experience)
        logger.debug("L5经验记录完成(后台)")
    except Exception as e:
        logger.debug(f"L5经验记录跳过: {e}")

    if _bg_tasks:
        wait_start = time.time()
        while time.time() - wait_start < 15:
            with _bg_lock:
                done_count = len(_bg_completed)
            if done_count >= len(_bg_tasks):
                events.append({"type": "step", "data": {"phase": "后台处理", "status": "done", "detail": f"后台任务全部完成 ({done_count}/{len(_bg_tasks)})"}})
                break
            events.append({"type": "step", "data": {"phase": "后台处理", "status": "progress", "detail": f"后台学习中... ({done_count}/{len(_bg_tasks)})"}})
            await asyncio.sleep(2.0)
        else:
            events.append({"type": "step", "data": {"phase": "后台处理", "status": "done", "detail": f"后台任务部分完成 ({len(_bg_completed)}/{len(_bg_tasks)})"}})

    for t in _bg_tasks:
        if not t.done():
            t.cancel()

    logger.info(f"✅ SSE完整闭环: {user_input[:30]} -> {time.time()-start_time:.1f}秒")

    return {"events": events}


async def background_deep_thinking(query: str, context: dict, intent_type: str):
    try:
        logger.info(f"🧠 后台深度思考: {query[:30]}...")
        from core.metacognitive_executor import MetacognitiveExecutor
        executor = MetacognitiveExecutor()
        exec_result = await executor.execute_with_full_metacognition(user_query=query, context=context)
        result = exec_result.get("final_result", "")
        if result and len(result) > 20:
            _save_to_experience_pool(query, result, success=True, intent_type="background_thinking", model_name="ollama")
            logger.info(f"✅ 后台思考完成: {len(result)}字")
    except Exception as e:
        logger.error(f"❌ 后台思考失败: {e}")


async def solve_history_query(query: str) -> str:
    try:
        db = get_storage_port("data/experience_pool.db")
        rows = db.query("SELECT raw_input, response FROM experiences ORDER BY timestamp DESC LIMIT 10")
        if rows:
            history_text = "\n".join([f"- {r[0][:30]}... → {r[1][:50]}..." for r in rows[:5]])
            return f"📜 最近的历史记录：\n{history_text}\n\n（完整历史功能开发中）"
        else:
            return "暂无历史记录。开始和我对话吧！"
    except Exception:
        return "历史记录功能正在初始化，请稍后再试。"