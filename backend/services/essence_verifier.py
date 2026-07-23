import asyncio
from loguru import logger

from backend.services.orchestrator_helpers import alchemize_error as _alchemize_error
from backend.services.path_handlers._shared import _run_sync, _save_to_experience_pool
from backend.services.path_handlers.external_api_path import fetch_external_api as _fetch_external_api
from backend.services.path_handlers.knowledge_path import fetch_knowledge as _fetch_knowledge
from backend.services.path_handlers.experience_path import fetch_experience as _fetch_experience



async def verify_essence(
    user_input: str, final_response: str, attempts: list,
    conversation_context: str, truth_insights: str, best: dict,
    fact_context: str,
) -> dict:
    events = []
    essence_passed = True
    essence_confidence = 1.0
    essence_issues = []
    essence_cross_validated = False

    if not final_response:
        return {
            "final_response": final_response, "essence_passed": essence_passed,
            "essence_confidence": essence_confidence, "essence_issues": essence_issues,
            "essence_cross_validated": essence_cross_validated, "events": events,
        }

    events.append({"type": "step", "data": {"phase": "本质推理", "status": "running", "detail": "第一性原理推理→自洽性验证→事实锚点验证→跨域一致性→反向归谬..."}})
    try:
        from core.essence_reasoner import essence_reasoner
        essence_result = await _run_sync(essence_reasoner.reason, user_input, final_response, conversation_context, timeout=15, phase="本质推理")

        fact_verified = True
        fact_issues = []
        try:
            from infrastructure.fact_store import fact_store
            negations = await _run_sync(fact_store.get_negations, user_input, timeout=5, phase="事实锚点验证")
            if negations:
                for neg in negations:
                    neg_claim = f"{neg['subject']}{neg['predicate']}{neg['object']}"
                    if neg_claim in final_response:
                        fact_verified = False
                        fact_issues.append(f"与已纠错事实冲突: {neg_claim}")
        except Exception:
            logger.warning("操作降级跳过")

        if not fact_verified:
            essence_result["passed"] = False
            essence_result["consistency_issues"].extend(fact_issues)
            if essence_result["confidence"] > 0.7:
                essence_result["confidence"] = 0.5
            events.append({"type": "step", "data": {"phase": "事实验证", "status": "done", "detail": f"发现{len(fact_issues)}个事实冲突 ⚠️"}})
        elif fact_context:
            events.append({"type": "step", "data": {"phase": "事实验证", "status": "done", "detail": "事实锚点验证通过 ✅"}})

        if essence_result["passed"]:
            essence_passed = True
            essence_confidence = essence_result["confidence"]
            attempts.append(("本质推理", True, f"{essence_result['verdict']} (置信度{essence_result['confidence']:.0%})"))
            events.append({"type": "step", "data": {"phase": "本质推理", "status": "done", "detail": f"推理自洽 ✅ {essence_result['verdict']}"}})

            if essence_confidence >= 0.7 and len(final_response) > 50:
                try:
                    from core.truth_accumulator import truth_accumulator
                    truth_accumulator._save_truth(
                        name=user_input[:30],
                        level="L1",
                        domain="essence",
                        statement=essence_result.get("verdict", final_response[:200]),
                        source="essence_reasoning",
                    )
                    logger.debug(f"本质洞察→真谛候选: {user_input[:30]} (置信度{essence_confidence:.0%})")
                except Exception:
                    pass

            events.append({"type": "awareness", "data": {
                "essence_verdict": essence_result.get("verdict", "")[:60],
                "essence_confidence": round(essence_confidence, 2),
                "essence_passed": True,
            }})
        else:
            essence_passed = False
            essence_confidence = essence_result["confidence"]
            essence_issues = essence_result.get("consistency_issues", [])
            issues_str = '；'.join(essence_result["consistency_issues"][:3])
            attempts.append(("本质推理", False, f"发现{len(essence_result['consistency_issues'])}个问题：{issues_str[:60]}"))
            events.append({"type": "step", "data": {"phase": "本质推理", "status": "done", "detail": f"发现自洽性问题：{issues_str[:80]}，尝试修正..."}})
            events.append({"type": "awareness", "data": {
                "essence_issues_count": len(essence_result["consistency_issues"]),
                "essence_confidence": round(essence_confidence, 2),
                "essence_passed": False,
            }})

            if essence_result["enhanced_response"] and len(essence_result["enhanced_response"]) > len(final_response):
                final_response = essence_result["enhanced_response"]
                events.append({"type": "step", "data": {"phase": "本质修正", "status": "done", "detail": "已附加推理审视和自洽性提示"}})

            if essence_result["confidence"] < 0.5:
                events.append({"type": "step", "data": {"phase": "多源交叉验证", "status": "running", "detail": "置信度过低，启动多源并行交叉验证..."}})
                multi_sources = []

                ext_result = await _fetch_external_api(user_input, conversation_context=conversation_context, truth_insights=truth_insights)
                if ext_result and ext_result.get("response"):
                    multi_sources.append({"source": ext_result["source"], "response": ext_result["response"]})

                know_result = await _fetch_knowledge(user_input)
                if know_result and know_result.get("response"):
                    multi_sources.append({"source": "知识库", "response": know_result["response"]})

                exp_result = await _fetch_experience(user_input)
                if exp_result and exp_result.get("response"):
                    multi_sources.append({"source": "经验池", "response": exp_result["response"]})

                if len(multi_sources) >= 2:
                    essence_cross_validated = True
                    events.append({"type": "step", "data": {"phase": "多源交叉验证", "status": "progress", "detail": f"收集到{len(multi_sources)}个来源，进行差异萃取..."}})
                    from backend.services.response_aggregator import cross_source_merge as _csm, list_divergences as _ld
                    merged = _csm(user_input, multi_sources, essence_result["consistency_issues"])
                    if merged:
                        final_response = merged
                        _save_to_experience_pool(user_input, merged, success=True, intent_type="multi_source_merge", model_name="merge")
                        attempts.append(("多源交叉验证", True, f"{len(multi_sources)}源融合成功"))
                        events.append({"type": "step", "data": {"phase": "多源交叉验证", "status": "done", "detail": f"多源融合完成 ✅ ({len(multi_sources)}个来源)"}})
                    else:
                        divergence = _ld(user_input, multi_sources)
                        final_response = divergence
                        attempts.append(("多源交叉验证", True, "罗列分歧"))
                        events.append({"type": "step", "data": {"phase": "多源交叉验证", "status": "done", "detail": "多源存在分歧，诚实罗列各方观点"}})
                elif len(multi_sources) == 1:
                    essence_cross_validated = True
                    single = multi_sources[0]
                    recheck = None
                    try:
                        from core.essence_reasoner import essence_reasoner
                        recheck = await _run_sync(essence_reasoner.reason, user_input, single["response"], conversation_context, timeout=30)
                    except Exception:
                        logger.warning("操作降级跳过")
                    if recheck and recheck["confidence"] > essence_result["confidence"]:
                        final_response = single["response"]
                        _save_to_experience_pool(user_input, final_response, success=True, intent_type="single_source", model_name=best.get("source", "unknown") if best else "unknown")
                        attempts.append(("多源交叉验证", True, f"单源({single['source']})置信度提升"))
                        events.append({"type": "step", "data": {"phase": "多源交叉验证", "status": "done", "detail": f"单源验证通过 ({single['source']})"}})
                    else:
                        attempts.append(("多源交叉验证", False, "单源未改善"))
                        events.append({"type": "step", "data": {"phase": "多源交叉验证", "status": "done", "detail": "单源验证未改善，保留修正后回答"}})
                else:
                    events.append({"type": "step", "data": {"phase": "多源交叉验证", "status": "done", "detail": "无可用外部来源，保留修正后回答"}})
    except ImportError:
        events.append({"type": "step", "data": {"phase": "本质推理", "status": "done", "detail": "本质推理器未安装，跳过"}})
    except asyncio.TimeoutError:
        logger.warning("本质推理超时(15秒)")
        events.append({"type": "step", "data": {"phase": "本质推理", "status": "timeout", "detail": "本质推理超时，跳过验证继续"}})
    except Exception as e:
        logger.error(f"本质推理异常: {e}")
        _alchemize_error(e, context={"user_input": user_input[:50]}, phase="essence_reasoning")
        events.append({"type": "step", "data": {"phase": "本质推理", "status": "done", "detail": "本质推理异常，继续后续验证"}})

    return {
        "final_response": final_response, "essence_passed": essence_passed,
        "essence_confidence": essence_confidence, "essence_issues": essence_issues,
        "essence_cross_validated": essence_cross_validated, "events": events,
    }