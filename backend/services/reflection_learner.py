import asyncio
import time
from loguru import logger

from backend.services.input_preprocessor import feature_enabled as _feature_enabled
from backend.services.orchestrator_helpers import alchemize_error as _alchemize_error
from backend.services.path_handlers._shared import _run_sync, _save_to_experience_pool


async def run_reflection_learning(
    user_input: str, final_response: str, attempts: list, failed_steps: list,
    intent_type: str, start_time: float, candidates: list, comparison: list,
    best: dict, fitness_score, confidence: float,
    cp, cognitive_perception, cognitive_validation,
    bypass_result_l2l3, essence_gate_result, tool_calls_log: list,
) -> dict:
    events = []
    learning_outcomes = []
    reflection = ""
    final_response_override = None

    events.append({"type": "step", "data": {"phase": "反思学习", "status": "running", "detail": "从本次交互中学习，微调系统基因..."}})

    bypass_side_effects_done = bool(bypass_result_l2l3 and bypass_result_l2l3.success)
    if cp and cognitive_perception:
        if not bypass_side_effects_done:
            try:
                _conv_id = f"conv_{int(time.time())}"
                cp._trigger_async_evolution(
                    _conv_id, user_input,
                    final_response or "", cognitive_perception,
                    cognitive_validation
                )
                logger.debug("L5进化层已异步触发")
            except Exception as e:
                logger.warning(f"L5进化层触发跳过: {e}")
        else:
            logger.debug("L5进化层: 旁路已包含副作用，跳过手动触发")

        try:
            if hasattr(cp, 'l5') and cp.l5:
                _l5_status = cp.l5.get_evolution_status()
                _l5_genes = _l5_status.get("genes", {})
                _l5_skills_count = _l5_status.get("skills_count", 0)

                if _l5_genes:
                    from core.task_queue import task_queue, gene_pool
                    _synced_genes = 0
                    for _gid, _ginfo in _l5_genes.items():
                        if isinstance(_ginfo, dict) and "value" in _ginfo:
                            try:
                                _old_val = gene_pool.get(_gid)
                                _new_val = _ginfo["value"]
                                _delta = _new_val - _old_val
                                if abs(_delta) > 0.001:
                                    gene_pool.mutate(_gid, _delta, trigger="l5_evolution_sync")
                                    _synced_genes += 1
                            except Exception:
                                logger.warning("操作降级跳过")
                    if _synced_genes > 0:
                        logger.info(f"L5→基因池同步: {_synced_genes}个基因已通过mutate()写入gene_pool")
                        learning_outcomes.append({"name": "L5基因同步", "success": True, "count": _synced_genes})

                if _l5_skills_count > 0 and hasattr(cp.l5, 'skills'):
                    from core.skill_emergence import skill_emergence
                    _synced_skills = 0
                    for _skill in cp.l5.skills:
                        if isinstance(_skill, dict) and _skill.get("name"):
                            try:
                                skill_emergence._create_skill(
                                    skill_name=_skill["name"],
                                    skill_type=_skill.get("type", "evolved"),
                                    trigger=_skill.get("pattern", _skill.get("trigger", "")),
                                    solution_path=_skill.get("solution", str(_skill.get("name", "")))
                                )
                                _synced_skills += 1
                            except Exception:
                                logger.warning("操作降级跳过")
                    if _synced_skills > 0:
                        logger.info(f"L5→技能库同步: {_synced_skills}个技能已写入skill_emergence")
                        learning_outcomes.append({"name": "L5技能同步", "success": True, "count": _synced_skills})
        except Exception as e:
            logger.warning(f"进化岛结果反馈跳过: {e}")

        try:
            if bypass_side_effects_done and bypass_result_l2l3.introspection:
                cognitive_introspection = bypass_result_l2l3.introspection
                logger.debug("L6内省层: 使用旁路内省结果")
            else:
                cognitive_introspection = cp._get_introspection()
                if cognitive_introspection:
                    logger.debug("L6内省层: 获取到内省报告")
        except Exception as e:
            logger.warning(f"L6内省层跳过: {e}")

        if not bypass_side_effects_done:
            try:
                cp._save_memory(user_input, final_response or "", cognitive_perception, cognitive_validation)
                logger.debug("认知记忆已保存")
            except Exception as e:
                logger.warning(f"认知记忆保存跳过: {e}")
            try:
                cp._update_relationship(user_input, final_response or "", cognitive_perception, cognitive_validation)
                logger.debug("认知关系模型已更新")
            except Exception as e:
                logger.warning(f"认知关系模型更新跳过: {e}")
            try:
                cp._submit_signals(cognitive_perception, cognitive_validation)
                logger.debug("认知信号已提交")
            except Exception as e:
                logger.warning(f"认知信号提交跳过: {e}")
            try:
                from core.presence.signal_integration import submit_success_pattern, submit_error_pattern
                if overall_success:
                    submit_success_pattern(f"查询成功: {user_input[:50]}", source="reflection")
                else:
                    submit_error_pattern(f"查询失败: {user_input[:50]}", source="reflection")
            except Exception:
                pass
        else:
            logger.debug("认知副作用(记忆/关系/信号): 旁路已包含，跳过")

    try:
        from backend.services.reflection_service import reflect_and_learn
        reflection = await _run_sync(reflect_and_learn, user_input, final_response, attempts, start_time, comparison if candidates else [], timeout=5, phase="反思学习")
    except asyncio.TimeoutError:
        logger.warning("反思学习超时(5秒)")
        reflection = "反思学习超时，跳过"
        events.append({"type": "step", "data": {"phase": "反思学习", "status": "timeout", "detail": "反思学习超时，跳过"}})
    except Exception as e:
        logger.error(f"反思学习异常: {e}")
        _alchemize_error(e, context={"user_input": user_input[:50]}, phase="reflection_learning")
        reflection = "反思学习异常，跳过"

    try:
        from core.cognition.experience_abstractor import ExperienceAbstractor
        _abstraction_steps = [{"action": a[0], "result_preview": str(a[2])[:100] if len(a) > 2 else "", "success": a[1]} for a in attempts]
        _abstraction_result = ExperienceAbstractor.abstract(
            user_query=user_input,
            intent_type=intent_type,
            steps=_abstraction_steps,
            final_success=any(a[1] for a in attempts),
            failure_reason=str(failed_steps[0][2])[:200] if failed_steps and len(failed_steps[0]) > 2 else "",
        )
        ExperienceAbstractor.settle_to_skill_db(_abstraction_result, user_input, intent_type)
        if _abstraction_result.get("key_insights"):
            reflection += f"; 🧬 抽象:{_abstraction_result['key_insights'][0][:60]}"
            learning_outcomes.append({"name": "经验抽象", "success": True, "insights": len(_abstraction_result.get("key_insights", []))})
        try:
            from core.feedback.knowledge_validator import KnowledgeValidator
            _kv = KnowledgeValidator()
            _kv_result = _kv.validate(
                content=final_response[:500] if final_response else "",
                source="experience_abstractor",
                signals=[{"type": "success" if overall_success else "failure", "confidence": confidence or 0.5}],
            )
            if not _kv_result.passed:
                logger.warning(f"知识验证未通过: {_kv_result.issues[:2]}")
            elif _kv_result.score >= 0.7:
                learning_outcomes.append({"name": "知识验证", "success": True, "score": round(_kv_result.score, 2)})
        except Exception as e:
            logger.debug(f"知识验证跳过: {e}")
    except Exception as e:
        logger.warning(f"经验抽象跳过: {e}")

    overall_success = any(a[1] for a in attempts)
    try:
        from core.task_queue import task_queue, gene_pool
        task_queue.notify_user_interaction()
        gene_pool.learn_from_interaction(
            elapsed=time.time() - start_time,
            success=overall_success,
            model_used=best.get("source", "") if best else ""
        )
        if failed_steps and overall_success:
            gene_pool.mutate("caution_threshold", 0.02, "partial_failure")
            gene_pool.mutate("self_doubt_frequency", 0.01, "partial_failure")
            reflection += f"; 🧬 基因已微调(部分失败: {len(failed_steps)}步)"
        else:
            reflection += "; 🧬 基因已微调"
        learning_outcomes.append({"name": "基因微调", "success": True})
    except Exception as e:
        logger.error(f"基因微调异常: {e}")

    try:
        from core.learning.error_alchemy import ErrorAlchemy
        _alchemy = ErrorAlchemy()
        _failed_steps = [a for a in attempts if not a[1]]
        for _step_name, _step_success, _step_detail in _failed_steps[:5]:
            _fake_err = Exception(f"Step '{_step_name}' failed: {_step_detail}")
            _err_id = _alchemy.record_error(_fake_err, context={
                "user_input": user_input[:100],
                "step": _step_name,
                "detail": _step_detail[:200],
                "intent_type": intent_type,
            })
            _result = _alchemy.alchemize(_err_id)
            if _result.gold_extracted:
                logger.info(f"错误炼金: 从'{_step_name}'中提炼出{len(_result.patterns_found)}个学习信号")
        if hasattr(_result, 'patterns_found') and _result.patterns_found:
            reflection += f"; 🔮 错误炼金提取{len(_result.patterns_found)}个信号({','.join(_result.patterns_found[:3])})"
            learning_outcomes.append({"name": "错误炼金", "success": True, "signals": len(_result.patterns_found)})
    except Exception as e:
        logger.warning(f"错误炼金跳过: {e}")

    meta_learning_strategy = None
    try:
        from core.learning.meta_learning import MetaLearner, EvaluationMetric
        _meta = MetaLearner()
        _meta_context = {
            "task_type": intent_type,
            "recent_accuracy": sum(1 for a in attempts if a[1]) / max(len(attempts), 1),
            "complexity": len(user_input) / 100,
        }
        _recommendations = _meta.recommend_strategy(_meta_context)
        if _recommendations:
            _top_rec = _recommendations[0]
            meta_learning_strategy = _top_rec.strategy
            logger.info(f"元学习推荐: {_top_rec.strategy.name} (置信度{_top_rec.confidence:.2f}, 原因:{_top_rec.reason})")
            for _rec in _recommendations[:2]:
                _perf_score = 0.7 if overall_success else 0.3
                _meta.evaluate_strategy(
                    _rec.strategy.strategy_id,
                    EvaluationMetric.ACCURACY,
                    _perf_score,
                    context=_meta_context
                )
            reflection += f"; 📚 元学习推荐:{_recommendations[0].strategy.name}"
            learning_outcomes.append({"name": "元学习", "success": True, "strategy": str(_recommendations[0].strategy.name)})
    except Exception as e:
        logger.warning(f"元学习跳过: {e}")

    if meta_learning_strategy:
        try:
            from core.task_queue import gene_pool
            _s_type = meta_learning_strategy.type.value if hasattr(meta_learning_strategy.type, 'value') else str(meta_learning_strategy.type)
            if _s_type == "memorization":
                gene_pool.mutate("learning_rate", 0.02, trigger="meta_memorization")
            elif _s_type == "understanding":
                gene_pool.mutate("depth_preference", 0.02, trigger="meta_understanding")
                gene_pool.mutate("learning_rate", -0.01, trigger="meta_understanding")
            elif _s_type == "application":
                gene_pool.mutate("retry_aggression", 0.02, trigger="meta_application")
            elif _s_type == "evaluation":
                gene_pool.mutate("self_doubt_frequency", 0.02, trigger="meta_evaluation")
            logger.warning(f"元学习策略指导基因微调: {_s_type}")
        except Exception as e:
            logger.warning(f"元学习策略微调跳过: {e}")

    if intent_type in ("complex_query", "code") and fitness_score is not None and hasattr(fitness_score, 'final_score') and fitness_score.final_score < 50:
        try:
            from core.agents.coordinator import agent_coordinator
            agent_result = await asyncio.wait_for(
                agent_coordinator.collaborate(user_input, context={"attempts": [a[0] for a in attempts]}),
                timeout=60,
            )
            if agent_result.get("quality", 0) > fitness_score.final_score * 100:
                final_response_override = agent_result.get("response", final_response)
                reflection += f"; Agent协作提升(迭代{agent_result.get('iterations', 0)}次,质量{agent_result.get('quality', 0):.0f})"
                events.append({"type": "step", "data": {"phase": "Agent协作", "status": "done", "detail": f"多Agent闭环完成,质量提升至{agent_result.get('quality', 0):.0f}"}})
        except asyncio.TimeoutError:
            logger.debug("Agent协作超时,跳过")
        except Exception as e:
            logger.error(f"Agent协作异常: {e}")

    try:
        from infrastructure.dual_speed_evolution import dual_speed_evolution
        fitness_val = fitness_score if isinstance(fitness_score, (int, float)) else 0.0
        dual_speed_evolution.run_fast_loop(
            question=user_input, response=final_response,
            fitness_score=fitness_val, intent_type=intent_type,
        )
    except Exception as e:
        logger.error(f"双速进化快循环异常: {e}")

    if _feature_enabled("path_weight_matrix"):
        try:
            from core.path_weight_manager import path_weight_manager
            from backend.services.response_aggregator import _SOURCE_TO_WEIGHT_KEY
            for src, success, detail in attempts:
                path_name = _SOURCE_TO_WEIGHT_KEY.get(src, src)
                if path_name in path_weight_manager._paths:
                    conf = 0.5
                    if "置信度" in detail:
                        try:
                            conf = float(detail.split("置信度")[-1].split("%")[0]) / 100
                        except (ValueError, IndexError):
                            pass
                    path_weight_manager.update_weight(path_name, success, conf,
                                                        resource_pressure=path_weight_manager.compute_resource_pressure())
        except Exception as e:
            logger.warning(f"路径权重批量更新跳过: {e}")

    try:
        from backend.services.reflection_service import try_solidify_to_gene_pool
        gene_result = await _run_sync(try_solidify_to_gene_pool, user_input, final_response, attempts, comparison, timeout=10, phase="基因固化")
        if gene_result:
            reflection += f"; {gene_result}"
    except Exception as e:
        logger.error(f"知识固化异常: {e}")

    if overall_success and len(attempts) >= 3:
        try:
            from infrastructure.induction import InductionEngine
            _induction = InductionEngine()
            _induction_result = _induction.induct_from_experience(
                query=user_input, response=final_response, intent_type=intent_type,
                success=overall_success, attempts_summary=[{"name": a[0], "success": a[1]} for a in attempts[:5]],
            )
            if _induction_result and _induction_result.get("rules_generated", 0) > 0:
                logger.info(f"归纳学习: 生成{_induction_result['rules_generated']}条规则")
                reflection += f"; 🔍 归纳:{_induction_result['rules_generated']}条规则"
                learning_outcomes.append({"name": "归纳学习", "success": True, "rules": _induction_result["rules_generated"]})
        except Exception as e:
            logger.debug(f"归纳学习跳过: {e}")

    try:
        from infrastructure.fact_store import fact_store
        if overall_success and final_response and len(final_response) > 50:
            fact_count = await _run_sync(fact_store.extract_and_store, user_input, final_response, source="chat_auto", timeout=10, phase="事实提取")
            if fact_count > 0:
                reflection += f"; 📚 事实提取{fact_count}条三元组"
    except Exception as e:
        logger.error(f"事实提取异常: {e}")

    try:
        from core.knowledge_quality_evaluator import KnowledgeQualityEvaluator
        _kqe = KnowledgeQualityEvaluator()
        _quality = _kqe.evaluate(user_input[:200], final_response[:500] if final_response else "")
        if hasattr(_quality, 'overall_score') and _quality.overall_score < 0.4:
            logger.warning(f"知识质量低: {_quality.reasons[:2] if _quality.reasons else ''}")
            reflection += f"; 📉 知识质量:{_quality.overall_score:.2f}"
    except Exception:
        pass

    try:
        from core.ethics import learn_safely
        _safety_result = learn_safely(
            content=final_response[:500] if final_response else "",
            source="reflection_learning",
            metadata={"intent_type": intent_type, "confidence": confidence or 0.5, "user_input": user_input[:100]},
        )
        if _safety_result and not _safety_result.get("success", True):
            _alignment = _safety_result.get("alignment", {})
            logger.warning(f"🛡️ 安全学习层拦截: status={_alignment.get('status')}, issues={_alignment.get('issues', [])[:2]}")
            reflection += f"; 🛡️ 安全拦截:{len(_alignment.get('issues', []))}项"
        elif _safety_result and _safety_result.get("success"):
            _alignment = _safety_result.get("alignment", {})
            if _alignment.get("status") == "partial":
                logger.info(f"🛡️ 安全学习层部分通过: issues={_alignment.get('issues', [])[:2]}")
    except Exception as e:
        logger.debug(f"安全学习层跳过: {e}")

    try:
        from core.learning.feedback_loop import LearningFeedbackLoop, Feedback, FeedbackType
        _feedback_loop = LearningFeedbackLoop()
        _knowledge_id = f"knowledge_{int(time.time())}_{hash(user_input[:50]) % 10000}"
        _feedback_loop.register_knowledge(
            _knowledge_id,
            knowledge={"query": user_input[:100], "response": final_response[:200] if final_response else "", "intent": intent_type},
            initial_confidence=confidence if confidence else 0.5,
        )
        _expected = user_input[:100]
        _actual = final_response[:200] if final_response else ""
        _feedback = Feedback(
            type=FeedbackType.POSITIVE if overall_success else FeedbackType.NEGATIVE,
            knowledge_id=_knowledge_id,
            expected_outcome=_expected,
            actual_outcome=_actual,
            context={"intent_type": intent_type, "attempts_count": len(attempts)},
            confidence=confidence if confidence else 0.5,
            reason="自动验证" if overall_success else "交互失败",
        )
        _loop_result = _feedback_loop.validate(_feedback)
        if _loop_result.should_refine:
            reflection += f"; 🔄 反馈闭环: 知识需精炼(准确度={_loop_result.accuracy:.0%})"
        elif _loop_result.validated:
            reflection += f"; ✅ 反馈闭环: 知识已验证(准确度={_loop_result.accuracy:.0%})"
        learning_outcomes.append({"name": "学习反馈闭环", "success": _loop_result.validated, "accuracy": _loop_result.accuracy})
    except Exception as e:
        logger.warning(f"学习反馈闭环跳过: {e}")

    try:
        from core.learning.incremental_perception import IncrementalPerception, Signal, SignalType
        _ip = IncrementalPerception()
        _signal = Signal(
            type=SignalType.SUCCESS if overall_success else SignalType.FAILURE,
            content={"query": user_input[:100], "intent": intent_type, "attempts_count": len(attempts)},
            context={"confidence": confidence if confidence else 0.5, "best_source": best.get("source", "") if best else ""},
            strength=confidence if confidence else 0.5,
            source="chat_orchestrator",
        )
        _perception_result = _ip.perceive(_signal)
        if _perception_result.patterns_detected:
            reflection += f"; 👁️ 增量感知: 检测到{len(_perception_result.patterns_detected)}个模式"
            learning_outcomes.append({"name": "增量感知", "success": True, "patterns": len(_perception_result.patterns_detected)})
    except Exception as e:
        logger.warning(f"增量感知跳过: {e}")

    try:
        from core.learning.knowledge_weaver import KnowledgeWeaver, NodeType, ConnectionType
        _kw = KnowledgeWeaver()
        if final_response and len(final_response) > 50:
            _node_id = _kw.add_node(
                content={"query": user_input[:100], "response": final_response[:200], "intent": intent_type},
                node_type=NodeType.EXPERIENCE,
                metadata={"confidence": confidence if confidence else 0.5, "success": overall_success},
            )
            if best and best.get("source"):
                _src_node_id = _kw.add_node(
                    content=best["source"],
                    node_type=NodeType.RULE,
                    metadata={"quality": best.get("score", 0)},
                )
                _kw.connect(_src_node_id, _node_id, ConnectionType.APPLIES_TO, strength=confidence if confidence else 0.5, evidence=user_input[:50])
            if _kw.nodes:
                reflection += f"; 🕸️ 知识编织: {len(_kw.nodes)}节点"
                learning_outcomes.append({"name": "知识编织", "success": True, "nodes": len(_kw.nodes)})
    except Exception as e:
        logger.warning(f"知识编织跳过: {e}")

    try:
        from core.cognition.conflict_resolver import conflict_resolver
        if final_response and len(final_response) > 50:
            _cr_nodes = {}
            _cr_nodes[f"new_{int(time.time())}"] = {
                "content": final_response[:200],
                "confidence": confidence if confidence else 0.5,
                "source": best.get("source", "unknown") if best else "unknown",
                "keywords": list(set(user_input.lower().split()[:8])),
                "quality_score": int((confidence if confidence else 0.5) * 100),
            }
            try:
                from core.knowledge_graph import get_knowledge_graph
                _kg = get_knowledge_graph()
                _existing = _kg.search(user_input[:50], top_k=3)
                for _i, _ex in enumerate(_existing):
                    if isinstance(_ex, dict):
                        _cr_nodes[f"existing_{_i}"] = {
                            "content": str(_ex.get("content", ""))[:200],
                            "confidence": _ex.get("importance", 0.5),
                            "source": _ex.get("source", "knowledge_graph"),
                            "keywords": list(set(str(_ex.get("content", "")).lower().split()[:8])),
                            "quality_score": int(_ex.get("importance", 0.5) * 100),
                        }
            except Exception:
                pass
            if len(_cr_nodes) >= 2:
                _conflicts = conflict_resolver.detect_conflicts(_cr_nodes)
                if _conflicts:
                    _resolved = conflict_resolver.resolve_conflicts(_conflicts, _cr_nodes)
                    reflection += f"; ⚖️ 冲突检测: {len(_conflicts)}个冲突, 解决{_resolved}个"
                    learning_outcomes.append({"name": "知识冲突解决", "success": True, "conflicts": len(_conflicts), "resolved": _resolved})
                    logger.info(f"知识冲突检测: {len(_conflicts)}个冲突, 解决{_resolved}个")
    except Exception as e:
        logger.debug(f"知识冲突检测跳过: {e}")

    try:
        pipeline = get_reflection_pipeline()
        if pipeline:
            execution_context = {
                "query": user_input,
                "plan": str(essence_gate_result) if essence_gate_result else "",
                "tool_calls": tool_calls_log,
                "final_answer": final_response,
                "confidence": confidence,
                "model_used": best.get("source", "") if best else "",
                "duration_ms": int((time.time() - start_time) * 1000),
                "extra": {"intent": intent_type, "attempts": [(a[0], a[1]) for a in attempts]}
            }
            asyncio.create_task(pipeline.process(execution_context))
    except Exception as e:
        logger.warning(f"反思管道触发跳过: {e}")

    try:
        from core.spirit_core import spirit_core as _spirit_core_reflect
        _failed_steps = [a for a in attempts if not a[1]]
        if _failed_steps:
            lessons = _spirit_core_reflect.get_lessons_for_reflection()
            if lessons:
                lesson_summary = str(lessons)[:200]
                reflection += f"; 精神教训: {lesson_summary}"
        violations = _spirit_core_reflect.get_violations_for_analysis()
        if violations:
            reflection += f"; 违规记录: {len(violations)}条"
    except Exception as e:
        logger.warning(f"精神内核联动跳过: {e}")

    if learning_outcomes:
        _learned = [o for o in learning_outcomes if o.get("success")]
        _failed = [o for o in learning_outcomes if not o.get("success")]
        logger.info(f"📖 反思学习汇总: {len(_learned)}/{len(learning_outcomes)}成功, "
                     f"学得={len(_learned)}项, 失败={len(_failed)}项")
        events.append({"type": "step", "data": {"phase": "反思学习", "status": "done",
                              "detail": f"学习了{len(_learned)}项, {len(_failed)}项跳过"}})

    return {
        "reflection": reflection,
        "learning_outcomes": learning_outcomes,
        "final_response_override": final_response_override,
        "events": events,
    }