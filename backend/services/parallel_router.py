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
        logger.error(f"后台收集异常: {e}")


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
            logger.warning("操作降级跳过")

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
        logger.warning("操作降级跳过")

    candidates = []

    _path_weights = methodology.get("path_weights", {}) if methodology else {}

    def _should_run(path_name: str, default: bool = True) -> bool:
        w = _path_weights.get(path_name, 1.0)
        if w < 0.3:
            logger.info(f"⚖️ 路径权重: {path_name}={w:.1f}，跳过")
            return False
        return default

    rule_result = fetch_rule(user_input, intent_type)
    if rule_result and rule_result.get("response"):
        candidates.append(rule_result)

    # 【去API依赖】本地先行路由：先启动本地路径，3秒内有高质量结果则直接返回
    # 本地路径：经验池、知识库、事实锚点、工具调用、自我推理
    # API路径：Ollama、外部模型、外部学习 — 延迟3秒启动
    LOCAL_FIRST_WINDOW = 3.0
    LOCAL_QUALITY_THRESHOLD = 55

    exp_task = asyncio.create_task(fetch_experience(user_input)) if _should_run("experience") else None
    know_task = asyncio.create_task(fetch_knowledge(user_input)) if _should_run("knowledge") else None
    fact_task = asyncio.create_task(fetch_fact_assertions(user_input)) if _should_run("fact") else None
    _tool_intent = (methodology.get("strategy") == "tool_first" if methodology else False) or intent_type == "code" or query_needs_tools(user_input)
    tool_task = None
    if (_tool_intent or max_paths >= 7) and _should_run("tool"):
        tool_task = asyncio.create_task(fetch_tool_results(user_input, intent_type, methodology=methodology, tool_intent=_tool_intent))
    self_reason_task = None
    if max_paths >= 6 and _should_run("self_reason"):
        from backend.services.path_handlers._shared import _check_vector_available, _fast_executor
        self_reason_task = asyncio.create_task(_self_reason_impl(user_input, conversation_context, truth_insights))

    local_tasks = [t for t in [exp_task, know_task, fact_task, tool_task, self_reason_task] if t is not None]
    local_names = []
    if exp_task: local_names.append("经验池")
    if know_task: local_names.append("知识库")
    if fact_task: local_names.append("事实锚点")
    if tool_task: local_names.append("工具调用")
    if self_reason_task: local_names.append("自我推理")

    logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] 本地先行：等待{local_names}（{LOCAL_FIRST_WINDOW}秒窗口）...")
    yield _emit("step", {"phase": "本地先行", "status": "running", "detail": f"先用本地能力({'+'.join(local_names)})尝试..."})

    local_done, local_pending = await asyncio.wait(local_tasks, timeout=LOCAL_FIRST_WINDOW, return_when=asyncio.ALL_COMPLETED)
    local_count = 0
    local_best_quality = 0
    for d in local_done:
        task_name_local = local_names[local_tasks.index(d)] if d in local_tasks else "未知"
        try:
            result = d.result()
            logger.warning(f"[ROUTER_DIAG] 本地先行完成: {task_name_local}, type={type(result).__name__}, is_list={isinstance(result, list)}")
            if isinstance(result, list):
                for item in result:
                    if isinstance(item, dict) and item.get("response"):
                        candidates.append(item)
                        local_count += 1
                        q = item.get("quality", 0)
                        if q > local_best_quality:
                            local_best_quality = q
                        logger.warning(f"[ROUTER_DIAG] 候选: source={item.get('source')}, quality={q}, resp_len={len(item.get('response',''))}")
            elif isinstance(result, dict) and result.get("response"):
                candidates.append(result)
                local_count += 1
                q = result.get("quality", 0)
                if q > local_best_quality:
                    local_best_quality = q
                logger.warning(f"[ROUTER_DIAG] 候选: source={result.get('source')}, quality={q}, resp_len={len(result.get('response',''))}")
            elif result is None:
                logger.warning(f"[ROUTER_DIAG] {task_name_local}返回None")
            else:
                logger.warning(f"[ROUTER_DIAG] {task_name_local}返回非预期类型: {type(result)}")
        except Exception as e:
            logger.warning(f"[ROUTER_DIAG] {task_name_local}异常: {e}")

    for p in local_pending:
        task_name_local = local_names[local_tasks.index(p)] if p in local_tasks else "未知"
        logger.warning(f"[ROUTER_DIAG] 本地先行未完成: {task_name_local}, done={p.done()}, cancelled={p.cancelled()}")

    logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] 本地先行完成: {local_count}个结果, 最高质量={local_best_quality}, _tool_intent={_tool_intent}, tool_task_done={tool_task.done() if tool_task else 'N/A'}")

    if local_best_quality >= LOCAL_QUALITY_THRESHOLD and local_count >= 1:
        if _tool_intent and tool_task and not tool_task.done():
            logger.warning(f"[ROUTER_DIAG] 本地先行命中(质量{local_best_quality})，工具意图=True，tool_task未完成，等待工具...")
            yield _emit("step", {"phase": "本地先行", "status": "running", "detail": f"本地能力已有结果，但等待工具执行完成..."})
            try:
                tool_result = await asyncio.wait_for(tool_task, timeout=25.0)
                logger.warning(f"[ROUTER_DIAG] 工具等待返回: type={type(tool_result).__name__}, is_list={isinstance(tool_result, list)}, is_dict={isinstance(tool_result, dict)}")
                if isinstance(tool_result, list):
                    for item in tool_result:
                        if isinstance(item, dict) and item.get("response"):
                            candidates.append(item)
                            q = item.get("quality", 0)
                            if q > local_best_quality:
                                local_best_quality = q
                            logger.warning(f"[ROUTER_DIAG] 工具候选: source={item.get('source')}, quality={q}, resp_len={len(item.get('response',''))}")
                    logger.warning(f"[ROUTER_DIAG] 工具列表结果: {len(tool_result)}项, 有效候选已添加")
                elif isinstance(tool_result, dict) and tool_result.get("response"):
                    candidates.append(tool_result)
                    q = tool_result.get("quality", 0)
                    if q > local_best_quality:
                        local_best_quality = q
                    logger.warning(f"[ROUTER_DIAG] 工具单结果: source={tool_result.get('source')}, quality={q}")
                elif tool_result is None:
                    logger.warning(f"[ROUTER_DIAG] 工具等待返回None! 工具执行可能失败")
                else:
                    logger.warning(f"[ROUTER_DIAG] 工具等待返回非预期类型: {type(tool_result)}")
            except asyncio.TimeoutError:
                logger.warning("[ROUTER_DIAG] 工具执行超时(25秒)，用已有本地结果继续")
            except Exception as e:
                logger.warning(f"[ROUTER_DIAG] 工具等待异常: {e}", exc_info=True)
            logger.warning(f"[ROUTER_DIAG] 工具等待完成，candidates={len(candidates)}个, 最高质量={local_best_quality}，直接返回，API后台补充")
            yield _emit("step", {"phase": "本地先行", "status": "done", "detail": f"✅ 工具已执行完成(质量{local_best_quality})，无需等待API"})
            logger.warning(f"[ROUTER_DIAG] yield candidates: {[{'source':c.get('source'),'quality':c.get('quality')} for c in candidates]}")
            yield candidates
            return
        else:
            logger.info(f"✅ 本地先行命中: 质量{local_best_quality}>={LOCAL_QUALITY_THRESHOLD}，可直接返回")
            yield _emit("step", {"phase": "本地先行", "status": "done", "detail": f"✅ 本地能力已解决(质量{local_best_quality})，API仅作补充"})

    if local_best_quality >= 60 and local_count >= 1 and _tool_intent:
        if tool_task and not tool_task.done():
            logger.warning(f"[ROUTER_DIAG] 工具意图+本地高质量({local_best_quality})，tool_task未完成，等待工具...")
            yield _emit("step", {"phase": "本地先行", "status": "running", "detail": f"本地能力已有结果，但等待工具执行完成..."})
            try:
                tool_result = await asyncio.wait_for(tool_task, timeout=25.0)
                logger.warning(f"[ROUTER_DIAG] 工具等待返回(分支2): type={type(tool_result).__name__}")
                if isinstance(tool_result, list):
                    for item in tool_result:
                        if isinstance(item, dict) and item.get("response"):
                            candidates.append(item)
                            logger.warning(f"[ROUTER_DIAG] 工具候选(分支2): source={item.get('source')}, quality={item.get('quality')}")
                elif isinstance(tool_result, dict) and tool_result.get("response"):
                    candidates.append(tool_result)
                    logger.warning(f"[ROUTER_DIAG] 工具单结果(分支2): source={tool_result.get('source')}, quality={tool_result.get('quality')}")
                elif tool_result is None:
                    logger.warning(f"[ROUTER_DIAG] 工具等待返回None(分支2)! 工具执行可能失败")
            except asyncio.TimeoutError:
                logger.warning("[ROUTER_DIAG] 工具执行超时(25秒)(分支2)，用已有本地结果继续")
            except Exception as e:
                logger.warning(f"[ROUTER_DIAG] 工具等待异常(分支2): {e}", exc_info=True)
        logger.warning(f"[ROUTER_DIAG] 工具意图+结果就绪({local_best_quality})，candidates={len(candidates)}个，直接返回")
        yield _emit("step", {"phase": "本地先行", "status": "done", "detail": f"✅ 工具已解决(质量{local_best_quality})，无需等待API"})
        logger.warning(f"[ROUTER_DIAG] yield candidates(分支2): {[{'source':c.get('source'),'quality':c.get('quality')} for c in candidates]}")
        yield candidates
        return

    # API路径：延迟启动（本地先行窗口结束后才启动）
    ollama_task = None
    if max_paths >= 3 and _should_run("ollama"):
        _ollama_decision = None
        try:
            from core.resource_awareness.adaptive_governor import get_adaptive_governor, ActionType
            _ollama_decision = get_adaptive_governor().decide(ActionType.OLLAMA_INFERENCE)
            if not _ollama_decision.allowed:
                logger.warning(f"⚖️ Ollama路径被governor阻止: {_ollama_decision.message}")
            elif _ollama_decision.degraded_to:
                logger.info(f"⚖️ Ollama路径被governor降级: {_ollama_decision.degraded_to}")
        except Exception:
            pass
        
        if _ollama_decision is None or _ollama_decision.allowed:
            try:
                from infrastructure.hardware_monitor import get_gpu_throttle
                throttle = get_gpu_throttle()
                if throttle.get("level") == "critical":
                    logger.warning(f"Ollama降级: GPU过热({throttle.get('temperature', 0)}°C)，延迟5秒+短推理")
                    yield _emit("step", {"phase": "GPU保护", "status": "warning", "detail": f"GPU过热({throttle.get('temperature', 0)}°C)，本地模型降频运行"})
                    async def _throttled_ollama():
                        await asyncio.sleep(5)
                        return await fetch_ollama_all(user_input, conversation_context=conversation_context, truth_insights=truth_insights)
                    ollama_task = asyncio.create_task(_throttled_ollama())
                elif throttle["level"] in ("warm", "hot"):
                    logger.info(f"Ollama节流: {throttle['message']}")
                    yield _emit("step", {"phase": "GPU节流", "status": "info", "detail": f"{throttle['message']}"})
                    async def _delayed_ollama():
                        await asyncio.sleep(throttle["delay_seconds"])
                        return await fetch_ollama_all(user_input, conversation_context=conversation_context, truth_insights=truth_insights)
                    ollama_task = asyncio.create_task(_delayed_ollama())
                else:
                    ollama_task = asyncio.create_task(fetch_ollama_all(user_input, conversation_context=conversation_context, truth_insights=truth_insights))
            except Exception:
                ollama_task = asyncio.create_task(fetch_ollama_all(user_input, conversation_context=conversation_context, truth_insights=truth_insights))
    ext_task = None
    if max_paths >= 4 and _should_run("external_api"):
        _search_decision = None
        try:
            from core.resource_awareness.adaptive_governor import get_adaptive_governor, ActionType
            _search_decision = get_adaptive_governor().decide(ActionType.EXTERNAL_SEARCH)
            if not _search_decision.allowed:
                logger.warning(f"⚖️ 外部搜索被governor阻止: {_search_decision.message}")
        except Exception:
            pass
        if _search_decision is None or _search_decision.allowed:
            ext_task = asyncio.create_task(fetch_external_api(user_input, conversation_context=conversation_context, truth_insights=truth_insights))
    ext_learn_task = None
    if max_paths >= 5 and _should_run("external_learning"):
        ext_learn_task = asyncio.create_task(fetch_external_learning(user_input, conversation_context))

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
                logger.error(f"{task_name}异常: {e}")
                yield _emit("step", {"phase": task_name, "status": "done", "detail": f"{task_name}异常"})

        if not pending_set:
            break

        # 自我保存本能：实时监控GPU温度，上升时取消高消耗待完成任务
        try:
            from infrastructure.hardware_monitor import get_gpu_throttle
            _throttle_check = get_gpu_throttle()
            if _throttle_check.get("level") == "critical":
                _gpu_temp_now = _throttle_check.get("temperature", 0)
                _cancel_gpu_tasks = []
                _keep_light_tasks = set()
                for t in pending_set:
                    tname = pending_tasks.get(t, "")
                    if tname in ("本地模型", "自我推理"):
                        t.cancel()
                        _cancel_gpu_tasks.append(tname)
                    else:
                        _keep_light_tasks.add(t)
                if _cancel_gpu_tasks:
                    logger.warning(f"🛡️ 自我保存: GPU过热({_gpu_temp_now}°C)，取消高消耗任务{_cancel_gpu_tasks}")
                    yield _emit("step", {"phase": "自我保存", "status": "warning", "detail": f"GPU过热({_gpu_temp_now}°C)，取消本地模型推理，保留轻量路径"})
                    pending_set = _keep_light_tasks
                    if not pending_set:
                        break
        except Exception:
            pass

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
        has_strong_self_reason = any("自我推理" in c.get("source", "") and c.get("quality", 0) >= 70 for c in candidates)
        has_tool_result_95 = any(c.get("quality", 0) >= 95 and ("工具" in c.get("source", "") or "serial" in c.get("source", "").lower() or "bash" in c.get("source", "").lower()) for c in candidates)

        if has_tool_result_95 and heartbeat_sec >= 3:
            waiting_names = '+'.join(still_waiting)
            yield _emit("step", {"phase": "智能调度", "status": "done",
                "detail": f"工具结果评分>=95，无需等待慢路径({waiting_names})，取消后台任务"})
            for t in list(pending_set):
                t.cancel()
            pending_set = set()
            break


        if has_strong_self_reason and heartbeat_sec >= 5:
            if _tool_intent and tool_task and not tool_task.done():
                pass
            else:
                waiting_names = '+'.join(still_waiting)
                yield _emit("step", {"phase": "智能调度", "status": "done",
                    "detail": f"自我推理质量>=70，无需等待API，取消慢路径({waiting_names})"})
                for t in list(pending_set):
                    t.cancel()
                    pending_set.discard(t)
                break

        if high_q >= 1 and has_model_result and heartbeat_sec >= 5:
            if _tool_intent and tool_task and not tool_task.done():
                pass
            else:
                waiting_names = '+'.join(still_waiting)
                yield _emit("step", {"phase": "智能调度", "status": "done",
                    "detail": f"已有模型结果+{high_q}条候选，取消慢路径({waiting_names})"})
                for t in list(pending_set):
                    t.cancel()
                    pending_set.discard(t)
                break

        if high_q >= 2 and has_search_result and heartbeat_sec >= 8:
            if _tool_intent and tool_task and not tool_task.done():
                pass
            else:
                waiting_names = '+'.join(still_waiting)
                yield _emit("step", {"phase": "智能调度", "status": "done",
                    "detail": f"已有{high_q}条高质量搜索候选(无模型结果)，取消慢路径({waiting_names})"})
                for t in list(pending_set):
                    t.cancel()
                    pending_set.discard(t)
                break

        if high_q >= 1 and has_search_result and heartbeat_sec >= 15:
            if _tool_intent and tool_task and not tool_task.done():
                pass
            else:
                waiting_names = '+'.join(still_waiting)
                yield _emit("step", {"phase": "智能调度", "status": "done",
                    "detail": f"模型未响应，已有{high_q}条搜索候选，取消慢路径({waiting_names})"})
                for t in list(pending_set):
                    t.cancel()
                    pending_set.discard(t)
                break

        ollama_still_pending = ollama_task in pending_set and not ollama_task.done()

        if ollama_still_pending and heartbeat_sec >= 20:
            diagnosis = await diagnose_ollama_status()
            ollama_status = diagnosis["status"]

            if ollama_status == "alive":
                if high_q >= 2:
                    yield _emit("step", {"phase": "智能调度", "status": "done",
                        "detail": f"模型推理中(状态正常)，已有{high_q}条高质量候选，取消慢路径"})
                    if ollama_task in pending_set:
                        ollama_task.cancel()
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
                    logger.warning("操作降级跳过")
                if ollama_task in pending_set:
                    ollama_task.cancel()
                    pending_set.discard(ollama_task)

            elif ollama_status == "dead":
                ollama_diagnosed_dead = True
                yield _emit("step", {"phase": "智能调度", "status": "done",
                    "detail": f"本地模型不可达(诊断: {'; '.join(diagnosis['evidence'][:2])})，使用{len(candidates)}条已有候选综合"})
                if ollama_task in pending_set:
                    ollama_task.cancel()
                    pending_set.discard(ollama_task)
        else:
            yield _emit("step", {"phase": "多路并行", "status": "progress",
                "detail": f"已等待{heartbeat_sec}秒，仍在等待: {'+'.join(still_waiting)}，已收集{len(candidates)}个候选"})

    if ollama_got:
        try:
            from core.module_health import module_health
            module_health.record_success("ollama")
        except Exception:
            logger.warning("操作降级跳过")
    if ext_got:
        try:
            from core.module_health import module_health
            module_health.record_success("external_api")
        except Exception:
            logger.warning("操作降级跳过")
    if ollama_diagnosed_dead:
        try:
            from core.module_health import module_health
            module_health.record_failure("ollama", "diagnosed_dead")
        except Exception:
            logger.warning("操作降级跳过")

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

    _src_weight_map = {
        "经验池": "experience", "知识库": "knowledge", "事实锚点": "fact",
        "工具调用": "tool", "工具": "tool", "自我推理": "self_reason",
        "本地模型": "ollama", "Ollama": "ollama",
        "外部模型": "external_api", "外部API": "external_api",
        "外部学习": "external_learning",
    }
    for c in candidates:
        src = c.get("source", "")
        wkey = None
        for k, v in _src_weight_map.items():
            if k in src:
                wkey = v
                break
        if wkey and wkey in _path_weights:
            orig_q = c.get("quality", 50)
            c["quality"] = int(orig_q * _path_weights[wkey])

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
        logger.warning(f"Beam search跳过: {e}")

    yield candidates


async def _self_reason_impl(query: str, conversation_context: str = "", truth_insights: str = "") -> Optional[dict]:
    from backend.services.orchestrator_helpers import self_reason
    return await self_reason(query, conversation_context, truth_insights)