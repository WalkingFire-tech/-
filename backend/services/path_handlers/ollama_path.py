import asyncio
import time
from loguru import logger
from adapters.llm.ollama_adapter import ollama_chat_request
from backend.services.path_handlers._shared import (
    _get_ollama_semaphore,
    _ollama_last_inference_time,
    _INFERENCE_COOLDOWN_SECONDS,
    _MAX_RESPONSE_CHARS,
    _RESOURCE_AWARE,
    _INPUT_PROCESSOR_AVAILABLE,
    _slow_executor,
    _fast_executor,
    _save_to_experience_pool,
)
from backend.services.path_handlers.experience_path import get_experience_context

_OLLAMA_MODEL_CACHE = {"model": None, "timestamp": 0}
_OLLAMA_MODELS_CACHE = {"models": [], "timestamp": 0}

_CODE_INTENTS = {"complex_query", "hardware", "map"}
_GENERAL_INTENTS = {"greeting", "confirmation", "simple_query", "learning_trigger", "challenge", "history_query", "weather"}


def _model_priority_for_intent(intent_type: str) -> list:
    if intent_type in _CODE_INTENTS:
        return ["qwen2.5-coder:7b", "qwen2.5:7b", "gemma-4-12B:latest", "deepcoder:latest"]
    return ["qwen2.5:7b", "qwen2.5-coder:7b", "gemma-4-12B:latest", "deepcoder:latest"]


async def get_available_ollama_models_async() -> list:
    """异步获取可用Ollama模型列表"""
    import time as _time
    now = _time.time()
    if _OLLAMA_MODELS_CACHE["models"] and (now - _OLLAMA_MODELS_CACHE["timestamp"]) < 60:
        return _OLLAMA_MODELS_CACHE["models"]
    try:
        import requests
        loop = asyncio.get_running_loop()
        tags = await asyncio.wait_for(
            loop.run_in_executor(_fast_executor, lambda: requests.get("http://localhost:11434/api/tags", timeout=3)),
            timeout=5
        )
        models = [m["name"] for m in tags.json().get("models", [])]
        if models:
            _OLLAMA_MODELS_CACHE["models"] = models
            _OLLAMA_MODELS_CACHE["timestamp"] = now
        return models
    except Exception:
        return _OLLAMA_MODELS_CACHE["models"]


async def get_available_ollama_model_async(intent_type: str = "") -> str:
    """异步获取优先Ollama模型（根据意图类型动态选择）"""
    import time as _time
    now = _time.time()
    cache_key = f"{intent_type or 'default'}"
    if _OLLAMA_MODEL_CACHE["model"] and (now - _OLLAMA_MODEL_CACHE["timestamp"]) < 60 and _OLLAMA_MODEL_CACHE.get("intent") == cache_key:
        return _OLLAMA_MODEL_CACHE["model"]
    models = await get_available_ollama_models_async()
    if not models:
        return _OLLAMA_MODEL_CACHE["model"]
    model_priority = _model_priority_for_intent(intent_type)
    selected = None
    for m in model_priority:
        for a in models:
            if m in a or a.startswith(m.split(":")[0]):
                selected = a
                break
        if selected:
            break
    if not selected:
        selected = models[0]
    if selected:
        _OLLAMA_MODEL_CACHE["model"] = selected
        _OLLAMA_MODEL_CACHE["timestamp"] = now
        _OLLAMA_MODEL_CACHE["intent"] = cache_key
    return selected


async def ollama_background_save(ollama_task: asyncio.Task, query: str):
    """Ollama超时后后台继续等，结果存入经验池供下次使用"""
    try:
        ollama_results = await ollama_task
        for r in ollama_results:
            if isinstance(r, dict) and r.get("response"):
                _save_to_experience_pool(query, r["response"], success=True, intent_type="ollama_background", model_name="ollama")
                logger.info(f"🔄 Ollama后台结果已存入经验池: {query[:30]}")
    except Exception as e:
        logger.error(f"Ollama后台保存失败: {e}")


async def fetch_ollama(query: str, model: str, timeout: int = 60, conversation_context: str = "", truth_insights: str = "") -> dict:
    try:
        from core.config.unified_config import get_config
        _cfg = get_config()
        if _cfg.get("gpu_protection.disable_ollama", False):
            _reason = _cfg.get("gpu_protection.disable_reason", "GPU保护模式")
            logger.warning(f"Ollama已禁用(GPU保护): {_reason}")
            return {"response": "", "source": "ollama_disabled", "error": _reason}
    except Exception as e:
        logger.warning(f"操作降级跳过: {e}")
    async with _get_ollama_semaphore():
        global _ollama_last_inference_time
        _num_predict = 1024
        try:
            from infrastructure.hardware_monitor import get_gpu_throttle
            throttle = get_gpu_throttle()
            if throttle.get("level") == "critical":
                logger.warning(f"Ollama降级: GPU过热({throttle.get('temperature', 0)}°C)，优先外部API，缩短推理")
                _num_predict = min(_num_predict, 128)
                await asyncio.sleep(5)
            elif throttle["delay_seconds"] > 0:
                logger.info(f"Ollama推理节流: {throttle['message']}，等待{throttle['delay_seconds']}秒")
                await asyncio.sleep(throttle["delay_seconds"])
                _num_predict = throttle.get("max_tokens", 1024)
        except Exception:
            logger.warning("操作降级跳过")
        if _RESOURCE_AWARE:
            try:
                monitor = get_health_monitor()
                monitor.register_ollama_request()
                monitor.register_ollama_model(model)
            except Exception:
                logger.warning("操作降级跳过")
        try:
            import requests
            exp_context = get_experience_context(query)
            prompt_parts = []
            if conversation_context:
                prompt_parts.append(f"【对话历史】\n{conversation_context}")
            if exp_context:
                prompt_parts.append(f"【前车之鉴-历史经验】\n{exp_context}")
            if truth_insights:
                prompt_parts.append(truth_insights)

            is_factual_query = any(kw in query for kw in [
                "为什么", "是什么", "原理", "原因", "机制", "本质", "如何", "怎么",
                "科学", "物理", "化学", "生物", "天文", "数学", "医学",
                "是真的吗", "对吗", "正确吗", "你确定"
            ])
            essence_prompt = ""
            if is_factual_query:
                try:
                    from core.essence_reasoner import essence_reasoner
                    essence_prompt = essence_reasoner.build_essence_prompt(query, conversation_context)
                    prompt_parts.append(essence_prompt)
                except Exception:
                    prompt_parts.append(f"【当前问题】\n{query}")
                    prompt_parts.append("请用第一性原理逐步推理，标注每个声明的确定性，区分事实与推论，考虑反面观点。")
            else:
                prompt_parts.append(f"【当前问题】\n{query}")
                if len(prompt_parts) > 1:
                    prompt_parts.append("请结合对话历史和上下文，给出连贯、准确、完整的回答。注意保持与之前对话的一致性。")
            prompt = "\n\n".join(prompt_parts)
            prompt += "\n\n【重要】请简洁回答，控制在800字以内，避免冗长展开。"
            
            MAX_PROMPT_LENGTH = 12000
            if len(prompt) > MAX_PROMPT_LENGTH:
                if _INPUT_PROCESSOR_AVAILABLE:
                    try:
                        processor = get_input_processor()
                        skeleton = processor._extract_skeleton(query)
                        cognitive_strategy = processor._determine_cognitive_strategy(skeleton)
                        prompt = processor.distill_prompt_parts(
                            [
                                ("query", f"【当前问题】\n{query}", 1.0),
                                ("conversation_context", f"【对话历史】\n{conversation_context}" if conversation_context else "", 0.8),
                                ("truth_insights", truth_insights or "", 0.6),
                                ("essence_prompt", essence_prompt, 0.5),
                                ("experience_context", f"【前车之鉴-历史经验】\n{exp_context}" if exp_context else "", 0.3),
                            ],
                            budget=int(MAX_PROMPT_LENGTH * 0.8),
                            cognitive_strategy=cognitive_strategy
                        )
                        logger.warning(f"Prompt动态提炼: {len(prompt)}字符, 策略={cognitive_strategy}")
                    except Exception:
                        query_part = f"【当前问题】\n{query[:1500]}"
                        ctx_budget = MAX_PROMPT_LENGTH - len(query_part) - 300
                        if conversation_context and ctx_budget > 500:
                            ctx_lines = conversation_context.split("\n")
                            kept = []
                            for line in ctx_lines:
                                if len("\n".join(kept) + "\n" + line) > ctx_budget:
                                    break
                                kept.append(line)
                            context_part = "\n".join(kept)
                            prompt = f"{context_part}\n\n{query_part}\n\n请结合上下文，给出连贯、准确、完整的回答。"
                        else:
                            prompt = query_part + "\n\n请给出准确、完整的回答。"
                else:
                    query_part = f"【当前问题】\n{query[:1500]}"
                    ctx_budget = MAX_PROMPT_LENGTH - len(query_part) - 300
                    if conversation_context and ctx_budget > 500:
                        ctx_lines = conversation_context.split("\n")
                        kept = []
                        for line in ctx_lines:
                            if len("\n".join(kept) + "\n" + line) > ctx_budget:
                                break
                            kept.append(line)
                        context_part = "\n".join(kept)
                        prompt = f"{context_part}\n\n{query_part}\n\n请结合上下文，给出连贯、准确、完整的回答。"
                    else:
                        prompt = query_part + "\n\n请给出准确、完整的回答。"
                logger.warning(f"Prompt截断: {len(prompt)}字符")
            
            loop = asyncio.get_running_loop()
            future = loop.run_in_executor(
                _slow_executor,
                lambda: ollama_chat_request(
                    base_url="http://localhost:11434",
                    model=model,
                    prompt=prompt,
                    timeout=timeout,
                    num_predict=_num_predict,
                )
            )
            result_data = await asyncio.wait_for(future, timeout=timeout + 10)
            result = result_data.get("content", "")
            if result and len(result) > 10:
                if len(result) > _MAX_RESPONSE_CHARS:
                    logger.info(f"Ollama响应截断: {len(result)}→{_MAX_RESPONSE_CHARS}字符(GPU保护)")
                    result = result[:_MAX_RESPONSE_CHARS] + "\n\n[回复已截断以保护GPU，避免过热断电]"
                return {"source": f"Ollama({model})", "response": result, "quality": 80}
        except requests.exceptions.Timeout:
            logger.warning(f"Ollama({model}) requests超时({timeout}秒)")
        except asyncio.TimeoutError:
            logger.warning(f"Ollama({model}) asyncio.wait_for超时({timeout+10}秒)")
        except Exception as e:
            logger.error(f"Ollama({model})调用失败: {e}")
        finally:
            _ollama_last_inference_time = time.time()
            if _RESOURCE_AWARE:
                try:
                    get_health_monitor().unregister_ollama_request()
                except Exception:
                    logger.warning("操作降级跳过")
    return None


async def fetch_ollama_all(query: str, conversation_context: str = "", truth_insights: str = "", intent_type: str = "") -> list:
    models = await get_available_ollama_models_async()
    if not models:
        return []
    model = await get_available_ollama_model_async(intent_type=intent_type)
    if not model:
        return []
    ollama_timeout = 45
    try:
        from core.path_weight_manager import path_weight_manager
        w = path_weight_manager.get_weight("ollama")
        ollama_timeout = int(30 + 30 * w / max(path_weight_manager.get_weights().values()))
    except Exception:
        logger.warning("操作降级跳过")
    result = await fetch_ollama(query, model, timeout=ollama_timeout, conversation_context=conversation_context, truth_insights=truth_insights)
    return [result] if result else []


async def fetch_ollama_response(query: str, conversation_context: str = "", truth_insights: str = "", intent_type: str = "") -> dict:
    results = await fetch_ollama_all(query, conversation_context=conversation_context, truth_insights=truth_insights, intent_type=intent_type)
    return results[0] if results else None


async def diagnose_ollama_status() -> dict:
    """
    穷尽一切手段诊断Ollama模型状态（异步版，不阻塞事件循环）
    
    手段1: HTTP API检测（/api/tags, /api/ps）
    手段2: 进程检测（ollama进程是否在运行）
    手段3: GPU/内存检测（模型是否占用了资源）
    
    注意：不再发极简推理测试——它会和主请求竞争Ollama资源并阻塞事件循环
    
    Returns:
        {
            "status": "alive"|"stuck"|"dead",
            "evidence": [...],  # 诊断证据链
            "model_running": bool,
            "gpu_in_use": bool,
            "can_respond": bool,
        }
    """
    result = {
        "status": "dead",
        "evidence": [],
        "model_running": False,
        "gpu_in_use": False,
        "can_respond": False,
    }
    
    loop = asyncio.get_running_loop()
    
    # 手段1: HTTP API检测（异步）
    try:
        import requests as _req
        try:
            r = await asyncio.wait_for(
                loop.run_in_executor(_slow_executor, lambda: _req.get("http://localhost:11434/api/tags", timeout=3)),
                timeout=5
            )
            if r.status_code == 200:
                models = r.json().get("models", [])
                if models:
                    result["model_running"] = True
                    result["evidence"].append(f"API可用，{len(models)}个模型")
                else:
                    result["evidence"].append("API可用但无模型")
                    return result
        except asyncio.TimeoutError:
            result["evidence"].append("API超时(5秒)")
            result["status"] = "stuck"
        except _req.exceptions.ConnectionError:
            result["evidence"].append("API连接失败")
        except _req.exceptions.Timeout:
            result["evidence"].append("API超时(3秒)")
            result["status"] = "stuck"
        except Exception as e:
            result["evidence"].append(f"API异常: {str(e)[:50]}")
        
        # 手段1b: 检查正在运行的模型（异步）
        if result["model_running"]:
            try:
                ps = await asyncio.wait_for(
                    loop.run_in_executor(_slow_executor, lambda: _req.get("http://localhost:11434/api/ps", timeout=3)),
                    timeout=5
                )
                if ps.status_code == 200:
                    running = ps.json().get("models", [])
                    if running:
                        model_names = [m.get("name", "?") for m in running]
                        result["evidence"].append(f"正在运行: {','.join(model_names)}")
                        result["status"] = "alive"
                    else:
                        result["evidence"].append("无模型在运行（可能正在加载）")
                        result["status"] = "alive"
            except Exception:
                result["evidence"].append("ps查询失败，但API可用")
                result["status"] = "alive"
    except ImportError:
        result["evidence"].append("requests库不可用")
    
    # 手段2: 进程检测（异步）
    if result["status"] == "dead":
        try:
            import subprocess
            proc = await asyncio.wait_for(
                loop.run_in_executor(_slow_executor, lambda: subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq ollama.exe"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )),
                timeout=8
            )
            if "ollama" in proc.stdout.lower():
                result["model_running"] = True
                result["evidence"].append("ollama进程存在")
                result["status"] = "stuck"
            else:
                result["evidence"].append("ollama进程不存在")
        except Exception:
            result["evidence"].append("进程检测失败")
    
    # 手段3: GPU/内存检测（异步）
    if result["status"] in ("alive", "stuck"):
        try:
            import subprocess
            proc = await asyncio.wait_for(
                loop.run_in_executor(_slow_executor, lambda: subprocess.run(
                    ["nvidia-smi", "--query-compute-apps=pid,name,used_memory", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )),
                timeout=8
            )
            if proc.stdout.strip() and "ollama" in proc.stdout.lower():
                result["gpu_in_use"] = True
                result["evidence"].append(f"GPU占用中: {proc.stdout.strip()[:80]}")
                if result["status"] == "stuck":
                    result["status"] = "alive"
                    result["evidence"].append("GPU占用说明模型正在推理，修正为alive")
            elif result["status"] == "stuck":
                result["evidence"].append("GPU无占用，模型可能卡住")
        except Exception:
            result["evidence"].append("GPU检测不可用")
    
    # 不再发极简推理测试——它会和主请求竞争Ollama资源，且同步调用会阻塞事件循环
    # 改用/api/ps判断：如果API可响应且显示有模型在运行，就认为alive
    if result["status"] == "stuck" and result["model_running"]:
        result["status"] = "alive"
        result["evidence"].append("API可响应+进程存在，判定为推理中而非卡死")
    
    if result["status"] == "stuck":
        result["evidence"].append("所有手段均无法确认模型可用，判定为stuck，建议启动替代推理")
    
    logger.info(f"🔍 Ollama诊断: status={result['status']}, evidence={'; '.join(result['evidence'])}")
    return result