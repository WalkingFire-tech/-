from loguru import logger

from backend.services.auto_fix_service import auto_fix_checkpoint as _auto_fix_checkpoint
from backend.services.path_handlers._shared import _run_sync


async def optimize_fitness(
    user_input: str, final_response: str, attempts: list,
    intent_type: str, route: str, confidence: float,
    methodology: dict, fitness_score, candidates: list, best: dict,
    conversation_context: str, truth_insights: str,
    complexity: float, fetch_ollama_fn, fetch_external_fn,
    fetch_knowledge_fn, fetch_experience_fn, self_reason_fn,
) -> dict:
    events = []

    if final_response:
        try:
            from infrastructure.fitness_evaluator import fitness_evaluator
            fitness_score = await _run_sync(
                fitness_evaluator.evaluate,
                question=user_input,
                response=final_response,
                user_feedback=0,
                intent_type=intent_type,
                timeout=5
            )
            if fitness_score.is_factual_question:
                attempts.append(("适应度评估", True, f"客观{fitness_score.objective_score:.0f}/主观{fitness_score.subjective_score:.0f}→总分{fitness_score.final_score:.0f}"))
                events.append({"type": "step", "data": {"phase": "适应度评估", "status": "done", "detail": f"事实性问题 | 客观分{fitness_score.objective_score:.0f} 主观分{fitness_score.subjective_score:.0f} 总分{fitness_score.final_score:.0f}"}})

                should_inject, inject_reason = fitness_evaluator.should_inject_knowledge(fitness_score)
                if should_inject:
                    events.append({"type": "step", "data": {"phase": "适应度评估", "status": "done", "detail": f"⚠️ 建议知识注入: {inject_reason}"}})
            else:
                events.append({"type": "step", "data": {"phase": "适应度评估", "status": "done", "detail": f"开放性问题 | 主观分{fitness_score.subjective_score:.0f}"}})
        except Exception as e:
            logger.warning(f"适应度评估跳过: {e}")

    try:
        from core.dynamic_probability_field import dynamic_probability_field
        if fitness_score and dynamic_probability_field._candidates:
            ev_type = "quality_boost" if fitness_score.final_score >= 60 else "essence_fail"
            dynamic_probability_field.update({
                "type": ev_type,
                "confidence": fitness_score.final_score / 100.0,
                "source": best.get("source", "") if best else "",
                "content": final_response[:300] if final_response else "",
            })
            dynamic_probability_field.save_snapshot(user_input)
            if best:
                dynamic_probability_field.record_outcome(
                    best.get("source", ""), fitness_score.final_score
                )
    except Exception as e:
        logger.warning(f"概率场更新跳过: {e}")

    if fitness_score and fitness_score.final_score < 60 and fitness_score.final_score >= 20 and final_response and route == "slow":
        events.append({"type": "step", "data": {"phase": "ReAct循环", "status": "running",
            "detail": f"适应度{fitness_score.final_score:.0f}不足60，启动ReAct迭代推理..."}})
        try:
            from core.react_engine import react_engine

            react_enhanced_query = user_input
            try:
                from core.react_enhancer import react_enhancer
                coverage = {}
                if fitness_score:
                    if hasattr(fitness_score, 'factual_score') and fitness_score.factual_score is not None:
                        coverage["factual_accuracy"] = fitness_score.factual_score / 100.0
                    if hasattr(fitness_score, 'subjective_score') and fitness_score.subjective_score is not None:
                        coverage["subjective_quality"] = fitness_score.subjective_score / 100.0
                    if hasattr(fitness_score, 'completeness') and fitness_score.completeness is not None:
                        coverage["completeness"] = fitness_score.completeness / 100.0
                gap = react_enhancer.identify_gap({
                    "query": user_input, "coverage": coverage, "iteration": 0
                })
                if gap.get("severity", 0) > 0.3:
                    react_enhanced_query = react_enhancer.generate_focused_prompt(gap, user_input)
                    events.append({"type": "step", "data": {"phase": "短板聚焦", "status": "done",
                        "detail": f"识别短板: {gap['gap_type']}(严重度{gap['severity']:.2f}), 已注入增强提示"}})
            except Exception as e:
                logger.warning(f"ReactEnhancer跳过: {e}")

            async def _react_fitness(q, r):
                try:
                    from infrastructure.fitness_evaluator import fitness_evaluator
                    return await _run_sync(fitness_evaluator.evaluate, question=q, response=r, timeout=5)
                except Exception:
                    return None

            react_result = await react_engine.run(
                query=react_enhanced_query,
                initial_response=final_response,
                initial_quality=fitness_score.final_score,
                candidates=candidates,
                fitness_score=fitness_score,
                intent_type=intent_type,
                conversation_context=conversation_context,
                truth_insights=truth_insights,
                fetch_ollama_fn=fetch_ollama_fn,
                fetch_external_fn=fetch_external_fn,
                fetch_knowledge_fn=fetch_knowledge_fn,
                fetch_experience_fn=fetch_experience_fn,
                self_reason_fn=self_reason_fn,
                fitness_fn=_react_fitness,
            )

            for it in react_result.iterations:
                status = "改善 ✅" if it.improved else "未显著改善"
                events.append({"type": "step", "data": {"phase": f"ReAct-R{it.iter_num}", "status": "done",
                    "detail": f"策略:{it.action} | {status} | 适应度→{it.quality:.0f}"}})

            if react_result.improved and react_result.final_response:
                final_response = react_result.final_response
                fitness_score_final = react_result.final_quality
                attempts.append(("ReAct循环", True,
                    f"{react_result.total_iterations}次迭代, 适应度{fitness_score.final_score:.0f}→{fitness_score_final:.0f}, 策略:{'+'.join(react_result.strategies_used)}"))
                events.append({"type": "step", "data": {"phase": "ReAct循环", "status": "done",
                    "detail": f"✅ ReAct改善: {react_result.total_iterations}次迭代, 适应度{fitness_score.final_score:.0f}→{fitness_score_final:.0f}"}})
            else:
                attempts.append(("ReAct循环", False, f"{react_result.total_iterations}次迭代未改善"))
                events.append({"type": "step", "data": {"phase": "ReAct循环", "status": "done",
                    "detail": f"ReAct {react_result.total_iterations}次迭代未显著改善，保留当前结果"}})
        except Exception as e:
            logger.error(f"ReAct循环异常: {e}")
            events.append({"type": "step", "data": {"phase": "ReAct循环", "status": "done", "detail": "ReAct循环跳过"}})

    if fitness_score and not fitness_score.is_factual_question and fitness_score.subjective_score >= 40:
        pass
    elif fitness_score and fitness_score.final_score < 20 and final_response and route == "slow":
        events.append({"type": "step", "data": {"phase": "闭环迭代", "status": "running",
            "detail": f"适应度{fitness_score.final_score:.0f}过低，启动闭环迭代..."}})
        try:
            from core.closed_loop_orchestrator import closed_loop_orchestrator, LoopContext, LoopState
            loop_ctx = LoopContext(
                query=user_input,
                conversation_context=conversation_context,
                intent_type=intent_type,
                complexity=complexity,
                confidence=confidence,
                route=route,
                iteration=0,
                candidates=candidates if candidates else [],
                best=best._asdict() if best and hasattr(best, '_asdict') else (best if isinstance(best, dict) else None),
                final_response=final_response,
                attempts=attempts[:],
                fitness_score=fitness_score,
            )
            loop_ctx.evaluation_passed = False
            loop_ctx.evaluation_issues = [f"适应度{fitness_score.final_score:.0f}低于阈值40"]
            loop_ctx.state = LoopState.EXECUTION

            loop_result = await closed_loop_orchestrator.orchestrate_from_context(loop_ctx)

            if loop_result.final_response and len(loop_result.final_response) > len(final_response):
                final_response = loop_result.final_response
                attempts.append(("闭环迭代", True, f"迭代{loop_result.iteration + 1}次改善"))
                events.append({"type": "step", "data": {"phase": "闭环迭代", "status": "done",
                    "detail": f"✅ 闭环迭代改善 (迭代{loop_result.iteration + 1}次)"}})
            else:
                attempts.append(("闭环迭代", False, "迭代未改善"))
                events.append({"type": "step", "data": {"phase": "闭环迭代", "status": "done", "detail": "迭代未显著改善，保留当前结果"}})
        except Exception as e:
            logger.error(f"闭环迭代异常: {e}")
            events.append({"type": "step", "data": {"phase": "闭环迭代", "status": "done", "detail": "闭环迭代跳过"}})

    try:
        _af3 = await _auto_fix_checkpoint(attempts, methodology, user_input, intent_type, "验证迭代后")
        if _af3["fixes_applied"] > 0:
            events.append({"type": "step", "data": {"phase": "自我修复", "status": "done", "detail": f"🔧 验证阶段修复{_af3['fixes_applied']}项，已调整策略"}})
    except Exception:
        pass

    return {
        "final_response": final_response, "fitness_score": fitness_score,
        "attempts": attempts, "events": events,
    }