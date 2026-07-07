import asyncio
import time
from typing import Optional
from loguru import logger

from backend.services.path_handlers._shared import (
    _slow_executor, _fast_executor,
    _RESOURCE_AWARE, _save_to_experience_pool,
)
from backend.services.path_handlers.experience_path import fetch_experience
from backend.services.path_handlers.knowledge_path import fetch_knowledge
from backend.services.path_handlers.ollama_path import (
    fetch_ollama_all, fetch_ollama_response, diagnose_ollama_status,
)
from backend.services.path_handlers.external_api_path import (
    fetch_external_api, fetch_external_learning,
)
from backend.services.path_handlers.rule_path import fetch_rule
from backend.services.path_handlers.fact_path import fetch_fact_assertions
from backend.services.path_handlers.tool_path import (
    fetch_tool_results, query_needs_tools,
)
from infrastructure.database_manager import DatabaseManager


def _emit(event_type: str, data: dict) -> str:
    import json
    return f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False)}\n\n"


async def _background_collect(task, query: str, task_name: str):
    try:
        result = await task
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and item.get("response"):
                    _save_to_experience_pool(query, item["response"], success=True, intent_type="background_collect", model_name="ollama")
                    logger.info(f"🔄 后台收集: {task_name}推理完成，已存入经验池")
        elif isinstance(result, dict) and result.get("response"):
            _save_to_experience_pool(query, result["response"], success=True, intent_type="background_collect", model_name="external")
            logger.info(f"🔄 后台收集: {task_name}推理完成，已存入经验池")
    except Exception as e:
        logger.debug(f"后台收集异常: {e}")


async def execute_parallel_paths(
    user_input: str,
    intent_type: str,
    conversation_context: str,
    truth_insights: str,
    methodology: dict,
    start_time: float,
):
    logger.info(f"🚀 进入阶段3: 多策略并行尝试, intent={intent_type}, strategy={methodology['strategy']}")

    max_paths = 9
    resource_mode = "normal"
    if _RESOURCE_AWARE:
        try:
            from core.resource_awareness.adaptive_governor import get_adaptive_governor
            from core.resource_awareness.health_monitor import get_health_monitor
            governor = get_adaptive_governor()
            monitor = get_health_monitor()
            max_paths = governor.get_parallel_path_count(9)
            resource_mode = monitor.get_mode_value()
            if max_paths < 9:
                logger.info(f"⚖️ 资源感知：{resource_mode}模式，并行路径 9→{max_paths}")
                yield _emit("step", {"phase": "资源感知", "status": "info", "detail": f"当前{resource_mode}模式，并行路径调整为{max_paths}"})
        except Exception:
            pass

    yield _emit("step", {"phase": "多策略并行", "status": "running", "detail": f"策略：{methodology['strategy']}，{max_paths}路径同时出击..."})

    world_model_hint = None
    try:
        from core.world_model import get_world_model
        wm = get_world_model()
        pre_enactment = wm.pre_enact(
            {"intent": intent_type, "query": user_input[:50]},
            ["rule_reasoning", "ollama_model", "experience_retrieval", "knowledge_search"],
            intent_type
        )
        if pre_enactment.get("has_high_confidence") and pre_enactment.get("recommendation"):
            rec = pre_enactment["recommendation"]
            world_model_hint = rec.get("action", "")
            logger.info(f"世界模型预演: 推荐={world_model_hint} 置信度={rec.get('confidence',0):.2f}")
    except Exception:
        pass

    candidates = []

    rule_result = fetch_rule(user_input, intent_type)
    if rule_result and rule_result.get("response"):
        candidates.append(rule_result)

    exp_task = asyncio.create_task(fetch_experience(user_input))
    know_task = asyncio.create_task(fetch_knowledge(user_input))
    ollama_task = None
    if max_paths >= 3:
        try:
            from infrastructure.hardware_monitor import get_gpu_throttle
            throttle = get_gpu_throttle()
            if throttle["level"] in ("warm", "hot", "critical"):
                logger.info(f"Ollama节流: {throttle['message']}")
                yield _emit("step", {"phase": "GPU节流", "status": "info", "detail": f"{throttle['message']}，先走外部API，Ollama延迟{throttle['delay_seconds']}秒补位"})
                async def _delayed_ollama():
                    await asyncio.sleep(throttle["delay_seconds"])
                    return await fetch_ollama_all(user_input, conversation_context=conversation_context, truth_insights=truth_insights)
                ollama_task = asyncio.create_task(_delayed_ollama())
            else:
                ollama_task = asyncio.create_task(fetch_ollama_all(user_input, conversation_context=conversation_context, truth_insights=truth_insights))
        except Exception:
            ollama_task = asyncio.create_task(fetch_ollama_all(user_input, conversation_context=conversation_context, truth_insights=truth_insights))
    ext_task = None
    if max_paths >= 4:
        ext_task = asyncio.create_task(fetch_external_api(user_input, conversation_context=conversation_context, truth_insights=truth_insights))
    ext_learn_task = None
    if max_paths >= 5:
        ext_learn_task = asyncio.create_task(fetch_external_learning(user_input, conversation_context))
    fact_task = asyncio.create_task(fetch_fact_assertions(user_input))
    self_reason_task = None
    if max_paths >= 6:
        from backend.services.path_handlers._shared import _check_vector_available, _fast_executor
        self_reason_task = asyncio.create_task(_self_reason_impl(user_input, conversation_context, truth_insights))
    tool_task = None
    _tool_intent = intent_type == "code" or query_needs_tools(user_input)
    if _tool_intent or max_paths >= 7:
        tool_task = asyncio.create_task(fetch_tool_results(user_input, intent_type, tool_intent=_tool_intent))

    logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] 开始gather快速路径...")
    fast_results = await asyncio.gather(exp_task, know_task, fact_task, return_exceptions=True)
    logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] gather快速路径完成")
    fast_count = 0
    for r in fast_results:
        if isinstance(r, dict) and r.get("response"):
            candidates.append(r)
            fast_count += 1

    yield _emit("step", {"phase": "多策略并行", "status": "progress", "detail": f"快速路径已返回{fast_count+1}个结果，模型+外部+自推理并行中..."})

    ollama_got = False
    ext_got = False
    ext_learn_got = False
    self_reason_got = False
    heartbeat_sec = 0
    ollama_diagnosed_dead = False
    tool_calls_log = []

    pending_tasks = {}
    if ollama_task: pending_tasks[ollama_task] = "本地模型"
    if ext_task: pending_tasks[ext_task] = "外部模型"
    if ext_learn_task: pending_tasks[ext_learn_task] = "外部学习"
    if self_reason_task: pending_tasks[self_reason_task] = "自我推理"
    if tool_task: pending_tasks[tool_task] = "工具调用"
    pending_set = set(pending_tasks.keys())

    while pending_set:
        logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] asyncio.wait开始, pending={[pending_tasks.get(t,'?') for t in pending_set]}")
        done, pending_set = await asyncio.wait(pending_set, timeout=5.0, return_when=asyncio.FIRST_COMPLETED)
        logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] asyncio.wait返回, done={len(done)}, pending={len(pending_set)}")
        for d in done:
            task_name = pending_tasks.get(d, "未知")
            try:
                result = d.result()
                if isinstance(result, list):
                    for item in result:
                        if isinstance(item, dict) and item.get("response"):
                            candidates.append(item)
                            if "工具" in item.get("source", "") or item.get("source", "") in ("file_reader", "project_scanner", "code_indexer", "dependency_analyzer"):
                                tool_calls_log.append({"tool": item.get("source", ""), "quality": item.get("quality", 0)})
                            if "Ollama" in item.get("source", ""):
                                _save_to_experience_pool(user_input, item["response"], success=True, intent_type="ollama_candidate", model_name="ollama")
                                ollama_got = True
                elif isinstance(result, dict) and result.get("response"):
                    candidates.append(result)
                    if "Ollama" in result.get("source", ""):
                        _save_to_experience_pool(user_input, result["response"], success=True, intent_type="ollama_candidate", model_name="ollama")
                        ollama_got = True
                    elif "外部学习" in result.get("source", ""):
                        ext_learn_got = True
                    elif "自我推理" in result.get("source", ""):
                        self_reason_got = True
                    else:
                        _save_to_experience_pool(user_input, result["response"], success=True, intent_type="external_api", model_name="deepseek")
                        ext_got = True
                yield _emit("step", {"phase": task_name, "status": "done", "detail": f"{task_name}返回结果 ✅"})
            except Exception as e:
                logger.debug(f"{task_name}异常: {e}")
                yield _emit("step", {"phase": task_name, "status": "done", "detail": f"{task_name}异常"})

        if not pending_set:
            break

        heartbeat_sec += 3

        if heartbeat_sec >= 90:
            logger.warning(f"⏱️ 8路径并行等待超时({heartbeat_sec}秒)，用已有{len(candidates)}个候选继续")
            yield _emit("step", {"phase": "智能调度", "status": "done",
                "detail": f"等待超时({heartbeat_sec}秒)，用已有{len(candidates)}个候选继续"})
            for t in pending_set:
                t.cancel()
            pending_set = set()
            break

        still_waiting = [pending_tasks[t] for t in pending_set if t in pending_tasks]
        logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] 轮询: candidates={len(candidates)}, high_q={sum(1 for c in candidates if c.get('quality', 0) >= 60 and len(c.get('response', '')) > 50)}, waiting={still_waiting}")

        high_q = sum(1 for c in candidates if c.get("quality", 0) >= 60 and len(c.get("response", "")) > 50)
        has_model_result = any(c.get("source", "") in ["Ollama", "DeepSeek", "OpenAI", "外部模型"] or "模型" in c.get("source", "") for c in candidates)
        has_search_result = any("搜索" in c.get("source", "") or "学习" in c.get("source", "") or "外部" in c.get("source", "") for c in candidates if c.get("quality", 0) >= 60)

        if high_q >= 2 and heartbeat_sec >= 5:
            if _tool_intent and tool_task and not tool_task.done():
                pass
            else:
                waiting_names = '+'.join(still_waiting)
                yield _emit("step", {"phase": "智能调度", "status": "done",
                    "detail": f"已有{high_q}条高质量候选，先综合输出，慢路径({waiting_names})后台补充"})
                for t in list(pending_set):
                    asyncio.ensure_future(_background_collect(t, user_input, pending_tasks.get(t, "未知路径")))
                    pending_set.discard(t)
                break

        if high_q >= 1 and has_model_result and heartbeat_sec >= 5:
            if _tool_intent and tool_task and not tool_task.done():
                pass
            else:
                waiting_names = '+'.join(still_waiting)
                yield _emit("step", {"phase": "智能调度", "status": "done",
                    "detail": f"已有模型结果+{high_q}条候选，先综合输出，慢路径({waiting_names})后台补充"})
                for t in list(pending_set):
                    asyncio.ensure_future(_background_collect(t, user_input, pending_tasks.get(t, "未知路径")))
                    pending_set.discard(t)
                break

        if high_q >= 2 and has_search_result and heartbeat_sec >= 8:
            if _tool_intent and tool_task and not tool_task.done():
                pass
            else:
                waiting_names = '+'.join(still_waiting)
                yield _emit("step", {"phase": "智能调度", "status": "done",
                    "detail": f"已有{high_q}条高质量搜索候选(无模型结果)，先综合输出，模型后台补充"})
                for t in list(pending_set):
                    asyncio.ensure_future(_background_collect(t, user_input, pending_tasks.get(t, "未知路径")))
                    pending_set.discard(t)
                break

        if high_q >= 1 and has_search_result and heartbeat_sec >= 15:
            if _tool_intent and tool_task and not tool_task.done():
                pass
            else:
                waiting_names = '+'.join(still_waiting)
                yield _emit("step", {"phase": "智能调度", "status": "done",
                    "detail": f"模型未响应，已有{high_q}条搜索候选，先综合输出"})
                for t in list(pending_set):
                    asyncio.ensure_future(_background_collect(t, user_input, pending_tasks.get(t, "未知路径")))
                    pending_set.discard(t)
                break

        ollama_still_pending = ollama_task in pending_set and not ollama_task.done()

        if ollama_still_pending and heartbeat_sec >= 20:
            diagnosis = await diagnose_ollama_status()
            ollama_status = diagnosis["status"]

            if ollama_status == "alive":
                if high_q >= 2:
                    yield _emit("step", {"phase": "智能调度", "status": "done",
                        "detail": f"模型推理中(状态正常)，已有{high_q}条高质量候选，先综合输出，模型结果后台补充"})
                    if ollama_task in pending_set:
                        asyncio.ensure_future(_background_collect(ollama_task, user_input, "本地模型"))
                        pending_set.discard(ollama_task)
                else:
                    yield _emit("step", {"phase": "多路并行", "status": "progress",
                        "detail": f"本地模型正在推理(已{heartbeat_sec}秒，诊断: {'; '.join(diagnosis['evidence'][:2])})，已收集{len(candidates)}个候选"})

            elif ollama_status == "stuck":
                yield _emit("step", {"phase": "智能调度", "status": "progress",
                    "detail": f"本地模型推理{heartbeat_sec}秒，诊断: {'; '.join(diagnosis['evidence'][:3])}，启动替代推理..."})
                try:
                    alt_result = await fetch_ollama_response(user_input, conversation_context=conversation_context, truth_insights=truth_insights)
                    if alt_result and alt_result.get("response"):
                        candidates.append(alt_result)
                        _save_to_experience_pool(user_input, alt_result["response"], success=True, intent_type="ollama_retry", model_name="ollama")
                        ollama_got = True
                        yield _emit("step", {"phase": "替代推理", "status": "done", "detail": "替代推理成功 ✅"})
                except Exception:
                    pass
                if ollama_task in pending_set:
                    pending_set.discard(ollama_task)

            elif ollama_status == "dead":
                ollama_diagnosed_dead = True
                yield _emit("step", {"phase": "智能调度", "status": "done",
                    "detail": f"本地模型不可达(诊断: {'; '.join(diagnosis['evidence'][:2])})，使用{len(candidates)}条已有候选综合"})
                if ollama_task in pending_set:
                    pending_set.discard(ollama_task)
        else:
            yield _emit("step", {"phase": "多路并行", "status": "progress",
                "detail": f"已等待{heartbeat_sec}秒，仍在等待: {'+'.join(still_waiting)}，已收集{len(candidates)}个候选"})

    if ollama_got:
        try:
            from core.module_health import module_health
            module_health.record_success("ollama")
        except Exception:
            pass
    if ext_got:
        try:
            from core.module_health import module_health
            module_health.record_success("external_api")
        except Exception:
            pass
    if ollama_diagnosed_dead:
        try:
            from core.module_health import module_health
            module_health.record_failure("ollama", "diagnosed_dead")
        except Exception:
            pass

    sources_got = set()
    for c in candidates:
        src = c.get("source", "")
        if src.startswith("Ollama"):
            sources_got.add("本地模型")
        elif src in ["DeepSeek", "OpenAI"]:
            sources_got.add("外部模型")
        elif src == "经验池":
            sources_got.add("经验池")
        elif src == "知识库":
            sources_got.add("知识库")
        elif src == "规则推理":
            sources_got.add("规则推理")
        elif "外部学习" in src:
            sources_got.add("外部学习")
        elif "事实锚点" in src:
            sources_got.add("事实锚点")
        elif "自我推理" in src:
            sources_got.add("自我推理")

    yield _emit("step", {"phase": "多策略并行", "status": "done", "detail": f"共获取{len(candidates)}个候选结果（{len(sources_got)}条路径：{'+'.join(sources_got)}）"})

    path_contributions = {}
    total_quality = 0
    for c in candidates:
        src = c.get("source", "未知")
        q = c.get("quality", 50)
        resp_len = len(c.get("response", ""))
        if resp_len > 30:
            path_contributions[src] = path_contributions.get(src, 0) + q
            total_quality += q
    path_percentages = {}
    if total_quality > 0:
        for src, q in sorted(path_contributions.items(), key=lambda x: -x[1]):
            pct = q / total_quality * 100
            path_percentages[src] = round(pct, 1)
    if path_percentages:
        contrib_str = " | ".join(f"{k}:{v}%" for k, v in path_percentages.items())
        yield _emit("step", {"phase": "路径贡献", "status": "done", "detail": f"有效信息占比 → {contrib_str}"})

    try:
        from core.beam_search import beam_search_engine
        if beam_search_engine.should_trigger(candidates):
            yield _emit("step", {"phase": "树搜索扩展", "status": "running", "detail": "候选质量不足，启动beam search扩展..."})
            async def _beam_fetch(q, ctx=""):
                try:
                    return await fetch_ollama_all(q, conversation_context=ctx)
                except Exception:
                    return {"response": "", "source": "beam_search_failed", "quality": 0}
            candidates = await beam_search_engine.search(
                original_query=user_input,
                candidates=candidates,
                fetch_func=_beam_fetch,
                conversation_context=conversation_context,
            )
            yield _emit("step", {"phase": "树搜索扩展", "status": "done", "detail": f"扩展后{len(candidates)}个候选"})
    except Exception as e:
        logger.debug(f"Beam search跳过: {e}")

    yield candidates


async def _self_reason_impl(query: str, conversation_context: str = "", truth_insights: str = "") -> Optional[dict]:

    from backend.services.path_handlers._shared import _check_vector_available, _fast_executor
    try:
        knowledge_parts = []
        try:
            if _check_vector_available():
                from infrastructure.vector_retriever import vector_retriever
                if vector_retriever.is_available():
                    loop = asyncio.get_running_loop()
                    similar = await asyncio.wait_for(
                        loop.run_in_executor(_fast_executor, lambda: vector_retriever.search(query, top_k=3, threshold=0.5)),
                        timeout=5
                    )
                    for s in similar:
                        knowledge_parts.append(f"[经验] {s.get('text', '')[:200]}")
        except Exception:
            pass
        try:
            loop = asyncio.get_running_loop()
            def _query_rules():
                db = DatabaseManager.get("data/learning_rules.db")
                rows = db.query("SELECT rule_text, confidence FROM learning_rules WHERE status='active' AND rule_text LIKE ? ORDER BY confidence DESC LIMIT 3", (f"%{query[:10]}%",))
                return rows
            rows = await asyncio.wait_for(loop.run_in_executor(_fast_executor, _query_rules), timeout=3)
            for row in rows:
                knowledge_parts.append(f"[规则 conf={row[1]:.2f}] {row[0][:200]}")
        except Exception:
            pass
        try:
            loop = asyncio.get_running_loop()
            def _query_truths():
                db = DatabaseManager.get("data/truths.db")
                rows = db.query("SELECT content FROM truths WHERE content LIKE ? LIMIT 2", (f"%{query[:8]}%",))
                return rows
            rows = await asyncio.wait_for(loop.run_in_executor(_fast_executor, _query_truths), timeout=3)
            for row in rows:
                knowledge_parts.append(f"[真谛] {row[0][:200]}")
        except Exception:
            pass
        if knowledge_parts:
            reasoning = f"关于「{query}」，基于已有知识的推理：\n\n" + "\n".join(knowledge_parts)
            return {"source": "自我推理", "response": reasoning, "quality": 55}
    except Exception as e:
        logger.debug(f"自我推理异常: {e}")
    return None