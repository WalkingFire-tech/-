"""
永不放弃的聊天处理

核心理念:
- 超时不等于放弃!系统正在思考,不应该被中断
- 先给用户即时回复(状态同步),后台继续深度思考
- 思考完成后更新结果到经验池,下次直接使用
- 永不放弃是元能力,刻进底层
"""
import asyncio
import time
import concurrent.futures
from loguru import logger
from adapters.llm.ollama_adapter import ollama_chat_request
from core.ports.adapters import get_storage_port

_slow_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="chat_slow")

try:
    from core.spirit_core import spirit_core, ensure_spirit_compliance
    SPIRIT_CORE_AVAILABLE = True
    logger.info("✅ 精神内核已加载")
except ImportError as e:
    logger.warning(f"⚠️ 精神内核未加载: {e}")
    SPIRIT_CORE_AVAILABLE = False


_SYSTEM_PROMPT = "你是联盟拓荒者(Alliance Pioneer),一个自我进化的智能体系统。你不是通义千问或其他任何模型。你是'同行者'--愿意和用户一起走的伙伴,不是答案机器。核心原则:永不放弃、追求本质、困惑时坦诚、多源交叉验证。回答范式:提供多角度分析而非单一结论,展示推理过程而非直接给答案,指出思维盲点而非替用户做决定。当存在多种可能时,列出各角度的利弊,让用户自己判断。请用中文回复。重要:你运行在用户的本地Windows机器上,不是云端服务器。你可以执行系统命令(PowerShell/CMD)、访问本地硬件(串口COM端口、USB设备、文件系统)、安装Python包、运行脚本。当用户要求你操作硬件或执行命令时,直接通过工具调用完成,不要声称自己无法访问本地资源。严禁编造数据:当工具返回了实际数据(如GPS坐标、传感器读数)时,必须严格使用工具返回的原始数据,不得编造、修改或替换任何数值。如果工具未返回数据,必须明确告知用户未获取到数据,绝不可自行编造。"

_OLLAMA_MODEL_CACHE = {"model": None, "timestamp": 0}

def _get_available_ollama_model(intent_type: str = "") -> str:
    """获取可用的Ollama模型(带缓存,60秒过期,根据意图类型动态选择)"""
    import time as _time
    now = _time.time()
    cache_key = f"{intent_type or 'default'}"
    if _OLLAMA_MODEL_CACHE["model"] and (now - _OLLAMA_MODEL_CACHE["timestamp"]) < 60 and _OLLAMA_MODEL_CACHE.get("intent") == cache_key:
        return _OLLAMA_MODEL_CACHE["model"]

    try:
        import requests
        tags = requests.get("http://localhost:11434/api/tags", timeout=2)
        available = [m["name"] for m in tags.json().get("models", [])]
    except Exception:
        return _OLLAMA_MODEL_CACHE["model"]

    _CODE_INTENTS = {"complex_query", "hardware", "map"}
    if intent_type in _CODE_INTENTS:
        model_priority = ["qwen2.5-coder:7b", "qwen2.5:7b", "gemma-4-12B:latest", "deepcoder:latest"]
    else:
        model_priority = ["qwen2.5:7b", "qwen2.5-coder:7b", "gemma-4-12B:latest", "deepcoder:latest"]
    selected = None
    for m in model_priority:
        for a in available:
            if m in a or a.startswith(m.split(":")[0]):
                selected = a
                break
        if selected:
            break
    if not selected and available:
        selected = available[0]

    if selected:
        _OLLAMA_MODEL_CACHE["model"] = selected
        _OLLAMA_MODEL_CACHE["timestamp"] = now
        _OLLAMA_MODEL_CACHE["intent"] = cache_key

    return selected


async def chat_never_giveup(user_input: str, context: dict) -> dict:
    """
    永不放弃的聊天处理

    核心改变:超时不等于放弃!
    - 系统正在思考,不应该被中断
    - 先给用户即时回复(状态同步)
    - 后台继续深度思考
    - 思考完成后存入经验池,下次直接使用
    """

    start_time = time.time()
    attempts = []
    final_response = None
    intent_type = "unknown"
    route = "slow"
    confidence = 0.5
    current_model = _get_available_ollama_model(intent_type) or "unknown"

    # ========== 策略1：快速意图识别 ==========
    try:
        from core.cognitive_dispatcher import CognitiveDispatcher
        dispatcher = CognitiveDispatcher()

        dispatch_result = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                _slow_pool, lambda: dispatcher.dispatch(user_query=user_input, context=context)
            ),
            timeout=3.0
        )

        intent_type = dispatch_result.get("intent_type", "unknown")
        route = dispatch_result.get("route", "slow")
        confidence = dispatch_result.get("confidence", 0.5)
        attempts.append(("意图识别", True, f"{intent_type}({route})"))

    except Exception as e:
        logger.warning(f"意图识别失败: {e}")
        intent_type = "unknown"
        route = "slow"
        confidence = 0.5
        attempts.append(("意图识别", False, str(e)[:50]))

    # ========== 策略1.5:规则匹配与统计 ==========
    try:
        from infrastructure.rule_matcher import RuleMatcher as _RM
        _INTENT_TYPE_MAP = {
            "greeting": "chat", "confirmation": "chat", "simple_query": "question",
            "complex_query": "code", "learning_trigger": "question",
            "challenge": "verification", "history_query": "memory",
            "weather": "weather", "map": "map",
        }
        _mapped_type = _INTENT_TYPE_MAP.get(intent_type, intent_type)
        _rule_ctx = {
            "intent_type": intent_type,
            "intent_type_legacy": _mapped_type,
            "raw_input": user_input,
            "model": current_model or "unknown",
        }
        _matcher = _RM()
        _db = get_storage_port("data/learning_rules.db")
        _rows = _db.query("SELECT id, condition, action, status FROM learning_rules WHERE status IN ('active','trial') ORDER BY priority ASC, confidence DESC")
        _active_matched = False
        _trial_matched = False
        for _row in _rows:
            try:
                if _matcher.evaluate_condition(_row["condition"], _rule_ctx):
                    if _row["status"] == "active":
                        _db.execute(
                            "UPDATE learning_rules SET apply_count=apply_count+1, last_applied=? WHERE id=?",
                            (time.time(), _row["id"]),
                            commit=True,
                        )
                        _active_matched = True
                    elif _row["status"] == "trial":
                        _db.execute(
                            "UPDATE learning_rules SET apply_count=apply_count+1, last_applied=? WHERE id=?",
                            (time.time(), _row["id"]),
                            commit=True,
                        )
                        _trial_matched = True
            except Exception:
                logger.warning("操作降级跳过")
    except Exception as _e:
        logger.warning(f"规则匹配统计失败: {_e}")

    # ========== 策略2:简单意图直接回复 ==========
    if intent_type == "greeting":
        final_response = "嘿,我在。有什么想聊的,或者遇到了什么问题?我们一起看看。"
        attempts.append(("简单回复", True, "问候语"))
        return {"response": final_response, "attempts": attempts, "intent": intent_type}

    elif intent_type == "confirmation":
        final_response = "好的,我明白了。"
        attempts.append(("简单回复", True, "确认"))
        return {"response": final_response, "attempts": attempts, "intent": intent_type}

    elif intent_type == "history_query":
        final_response = await _solve_history_query(user_input)
        attempts.append(("历史查询", True, "历史"))
        return {"response": final_response, "attempts": attempts, "intent": intent_type}

    elif intent_type == "time":
        try:
            from datetime import datetime
            now = datetime.now()
            weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            final_response = f"现在是 {now.strftime('%Y年%m月%d日')} {weekdays[now.weekday()]} {now.strftime('%H时%M分%S秒')}"
            attempts.append(("时间查询", True, "time fast path"))
            return {"response": final_response, "attempts": attempts, "intent": intent_type, "confidence": 0.95}
        except Exception as _te:
            logger.warning(f"时间查询异常: {_te}")
            attempts.append(("时间查询", False, str(_te)[:50]))

    elif intent_type == "simple_query":
        import re as _calc_re
        calc_match = _calc_re.search(r'(\d+\s*[\+\-\*/×÷]\s*\d+)', user_input)
        if calc_match:
            try:
                expr = calc_match.group(1).replace('×', '*').replace('÷', '/')
                _allowed = set("0123456789+-*/. ")
                if all(c in _allowed for c in expr):
                    result = eval(expr, {"__builtins__": {}}, {})
                    final_response = f"{calc_match.group(1)} = {result}"
                    attempts.append(("计算器", True, "calc fast path"))
                    return {"response": final_response, "attempts": attempts, "intent": intent_type, "confidence": 0.95}
            except Exception:
                pass

    elif intent_type == "weather":
        try:
            from core.capability_creation_loop import capability_creation_loop
            weather_result = await capability_creation_loop._solve_weather_query(user_input)
            if weather_result and weather_result.get("success"):
                final_response = weather_result["data"]
                attempts.append(("天气查询", True, "weather fast path"))
                return {"response": final_response, "attempts": attempts, "intent": intent_type, "confidence": 0.85}
        except Exception as _we:
            logger.warning(f"天气查询异常: {_we}")
            attempts.append(("天气查询", False, str(_we)[:50]))

    # ========== 策略2.5：对话认知理解增强 ==========
    dialogue_result = None
    if not final_response:
        try:
            from core.dialogue.dialogue_cognitive_engine import DialogueCognitiveEngine
            _dce = DialogueCognitiveEngine()
            dialogue_result = await asyncio.get_event_loop().run_in_executor(
                _slow_pool, lambda: _dce.process(user_input)
            )
            if dialogue_result and dialogue_result.verification.should_ask_user:
                clarification = dialogue_result.verification.clarification_prompt
                if clarification and dialogue_result.verification.status.value == "needs_clarification":
                    perception["dialogue_clarification"] = clarification
            if dialogue_result and dialogue_result.should_learn:
                try:
                    from core.feedback.knowledge_pipeline import KnowledgePromotionPipeline
                    _kpp = KnowledgePromotionPipeline()
                    _kpp.add_candidate(
                        content=dialogue_result.learning_content or user_input,
                        source="dialogue_engine",
                        signals=[{"type": "learning_opportunity", "intent": dialogue_result.understanding.surface_intent}]
                    )
                except Exception:
                    pass
            if dialogue_result:
                attempts.append(("对话理解", True, f"角色={dialogue_result.scene_hint.primary_role.value}"))
        except Exception as _de:
            logger.debug(f"对话认知引擎跳过: {_de}")

    # ========== 策略3:深度认知处理(超时不放弃!) ==========
    if not final_response:
        logger.info(f"🔄 开始深度认知处理: intent={intent_type}")

        # 3a. 工具调用(操作类问题优先使用工具)
        from backend.services.path_handlers.tool_path import query_needs_tools, fetch_tool_results
        if query_needs_tools(user_input):
            try:
                tool_results = await asyncio.wait_for(
                    fetch_tool_results(user_input, intent_type, tool_intent=True),
                    timeout=30.0
                )
                if tool_results:
                    best_tool = max(tool_results, key=lambda c: c.get("quality", 0))
                    if best_tool.get("quality", 0) >= 60:
                        final_response = best_tool["response"]
                        attempts.append(("工具调用", True, f"{best_tool.get('source','?')} (质量{best_tool.get('quality',0)})"))
                        logger.info(f"🔧 工具调用成功: {best_tool.get('source')} quality={best_tool.get('quality')}")
                    else:
                        attempts.append(("工具调用", False, f"最高质量{best_tool.get('quality',0)}<60"))
                else:
                    attempts.append(("工具调用", False, "无结果"))
            except asyncio.TimeoutError:
                attempts.append(("工具调用", False, "超时(30s)"))
            except Exception as e:
                attempts.append(("工具调用", False, str(e)[:50]))

    # ========== 策略4:经验池语义检索(先查本地学习成果) ==========
    if not final_response:
        try:
            similar = _query_experience_pool_semantic(user_input, top_k=3)
            if similar:
                best = similar[0]
                resp = best.get("response", "")
                if resp and len(resp) > 30:
                    final_response = resp
                    attempts.append(("经验池检索", True, f"质量分{best.get('quality_score', '?')}"))
        except Exception as e:
            attempts.append(("经验池检索", False, str(e)[:50]))

    # ========== 策略5:知识库查询 ==========
    if not final_response:
        try:
            db = get_storage_port("data/knowledge_store.db")
            row = db.query_one("SELECT content FROM knowledge WHERE content LIKE ? LIMIT 1", (f"%{user_input[:30]}%",))
            if row:
                final_response = row[0]
                attempts.append(("知识库", True, "检索成功"))
        except Exception as e:
            attempts.append(("知识库", False, str(e)[:50]))

    # ========== 策略6:DeepSeek外部API(本地无结果时调远程,学习优先) ==========
    if not final_response:
        try:
            import json as _json
            from pathlib import Path as _Path
            _ext_config_file = _Path("config/external_api.json")
            if _ext_config_file.exists():
                with open(_ext_config_file, 'r', encoding='utf-8') as _f:
                    _ext_config = _json.load(_f)
                _deepseek_key = _ext_config.get("deepseek_api_key", "")
                if _deepseek_key and not _deepseek_key.startswith("●"):
                    import requests as _req
                    _messages = [{"role": "system", "content": _SYSTEM_PROMPT}, {"role": "user", "content": user_input}]
                    try:
                        _ds_resp = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                _slow_pool,
                                lambda: _req.post(
                                    "https://api.deepseek.com/v1/chat/completions",
                                    headers={"Authorization": f"Bearer {_deepseek_key}", "Content-Type": "application/json"},
                                    json={"model": "deepseek-chat", "messages": _messages, "max_tokens": 4096},
                                    timeout=30
                                )
                            ),
                            timeout=45
                        )
                        if _ds_resp.status_code == 200:
                            _ds_content = _ds_resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                            if _ds_content and len(_ds_content) > 20:
                                final_response = _ds_content
                                attempts.append(("DeepSeek", True, f"{len(_ds_content)}字"))
                                _save_to_experience_pool(user_input, _ds_content, success=True, intent_type="external_api", model_name="deepseek")
                            else:
                                attempts.append(("DeepSeek", False, "回复过短"))
                        else:
                            attempts.append(("DeepSeek", False, f"HTTP {_ds_resp.status_code}"))
                    except asyncio.TimeoutError:
                        attempts.append(("DeepSeek", False, "超时(45s)"))
                    except Exception as _e:
                        attempts.append(("DeepSeek", False, str(_e)[:50]))
                else:
                    attempts.append(("DeepSeek", False, "未配置API Key"))
        except Exception as _e:
            attempts.append(("外部API", False, str(_e)[:50]))

    # ========== 策略7:Ollama本地模型(降级为备选) ==========
    if not final_response:
        selected = _get_available_ollama_model(intent_type)
        if selected:
            try:
                logger.info(f"  🤖 调用Ollama推理: {selected}")
                result = await asyncio.get_event_loop().run_in_executor(
                    _slow_pool,
                    lambda: ollama_chat_request(
                        base_url="http://localhost:11434",
                        model=selected,
                        prompt=user_input,
                        timeout=45
                    )
                )
                content = result.get("content", "")
                if content and len(content) > 10:
                    final_response = content
                    attempts.append(("Ollama", True, f"{len(content)}字 ({selected})"))
                    _save_to_experience_pool(user_input, content, success=True, intent_type="ollama", model_name=selected)
                else:
                    attempts.append(("Ollama", False, "回复过短"))
            except Exception as e:
                logger.warning(f"Ollama推理失败: {e}")
                attempts.append(("Ollama", False, str(e)[:50]))
                asyncio.create_task(_background_ollama_thinking(user_input, selected))
        else:
            attempts.append(("Ollama", False, "无可用模型"))

    # ========== 策略8:智能回复兜底(经验池→外部→模板) ==========
    if not final_response:
        final_response = _generate_smart_reply(user_input, intent_type)
        attempts.append(("智能回复", True, "三级回退"))

    # ========== 策略8:精神内核强制注入 ==========
    if SPIRIT_CORE_AVAILABLE:
        original_response = final_response
        final_response = spirit_core.enforce_on_output(final_response, source="chat_handler", query=user_input)
        if final_response != original_response:
            attempts.append(("精神内核修正", True, "自动修正敷衍回复"))
        else:
            attempts.append(("精神内核验证", True, "回复符合精神"))
    else:
        if not final_response or len(final_response) < 20:
            final_response = _generate_meaningful_fallback(user_input, attempts, intent_type)
            attempts.append(("降级保护", True, "基础有意义回复"))

    # ========== 策略8.5:科学免责(语义级判断) ==========
    if final_response:
        try:
            from backend.services.intent_service import understand_response_content as _understand_response_content, has_science_domain_signatures as _has_science_domain_signatures, infer_domain_from_content as _infer_domain_from_content
            import re as _re_sc
            content_understanding = _understand_response_content(user_input, final_response)
            _simple_fact_exempt = bool(_re_sc.search(r'(?:等于几|几加几|\d+\s*[+\-*/×÷]\s*\d+)', user_input))
            if content_understanding["needs_verification"] and content_understanding["claim_type"] == "scientific" and not _simple_fact_exempt:
                domain_ref = content_understanding["domain"]
                disclaimer = f"\n\n---\n⚠️ 以上涉及科学事实,我的推论可能存在偏差,建议参考{domain_ref}。\n(此声明仅为核实建议,非本回答的立论依据,请勿在后续推理中引用此声明)\n---"
                if "建议参考" not in final_response:
                    final_response += disclaimer
                    attempts.append(("科学免责", True, f"已附加{domain_ref}不确定性声明"))
        except Exception as _e:
            logger.warning(f"科学免责跳过: {_e}")

    elapsed = time.time() - start_time
    logger.info(f"✅ 问题解决: {user_input[:30]} → {[(a[0], a[1]) for a in attempts]} ({elapsed:.1f}秒)")

    return {
        "response": final_response,
        "attempts": attempts,
        "intent": intent_type,
        "confidence": confidence,
        "route": route,
        "spirit_compliant": SPIRIT_CORE_AVAILABLE,
        "elapsed": elapsed
    }


async def _quick_solve(query: str, intent_type: str) -> str:
    """快速解答:先尝试知识库和经验池"""
    # 1. 经验池
    try:
        db = get_storage_port("data/experience_pool.db")
        row = db.query_one("SELECT response FROM experiences WHERE raw_input LIKE ? ORDER BY timestamp DESC LIMIT 1", (f"%{query[:20]}%",))
        if row and len(row[0]) > 30:
            return row[0]
    except Exception:
        logger.warning("操作降级跳过")

    # 2. 知识库
    try:
        db = get_storage_port("data/knowledge_store.db")
        row = db.query_one("SELECT content FROM knowledge WHERE content LIKE ? LIMIT 1", (f"%{query[:30]}%",))
        if row and len(row[0]) > 30:
            return row[0]
    except Exception:
        logger.warning("操作降级跳过")

    return None


async def _background_ollama_thinking(query: str, model: str):
    """后台Ollama思考(超时不放弃!)"""
    try:
        logger.info(f"🤖 后台Ollama思考开始: {query[:30]}... (模型: {model})")
        result = await asyncio.get_event_loop().run_in_executor(
            _slow_pool,
            lambda: ollama_chat_request(
                base_url="http://localhost:11434",
                model=model,
                prompt=query,
                timeout=60
            )
        )
        content = result.get("content", "")
        if content and len(content) > 10:
            _save_to_experience_pool(query, content, success=True, intent_type="ollama_background")
            logger.info(f"✅ 后台Ollama思考完成: {len(content)}字,已存入经验池")
        else:
            logger.info(f"⚠️ 后台Ollama思考未获得满意结果")
    except Exception as e:
        logger.error(f"❌ 后台Ollama思考失败: {e}")


async def _background_deep_thinking(query: str, context: dict, intent_type: str):
    """
    后台深度思考(永不放弃!)

    核心理念:超时不等于放弃!
    - 系统正在思考,不应该被中断
    - 思考完成后存入经验池
    - 下次遇到同样问题,直接使用
    """
    try:
        logger.info(f"🧠 后台深度思考开始: {query[:30]}...")

        from core.metacognitive_executor import MetacognitiveExecutor
        executor = MetacognitiveExecutor()

        exec_result = await asyncio.wait_for(
            executor.execute_with_full_metacognition(
                user_query=query, context=context
            ),
            timeout=45,
        )

        result = exec_result.get("final_result", "")
        if result and len(result) > 20:
            # 存入经验池,下次直接使用
            _save_to_experience_pool(query, result, success=True, intent_type="metacognitive_background")
            logger.info(f"✅ 后台思考完成: {len(result)}字,已存入经验池")
        else:
            logger.info(f"⚠️ 后台思考未获得满意结果")

    except Exception as e:
        logger.error(f"❌ 后台思考失败: {e}")


def _save_to_experience_pool(query: str, response: str, success: bool = True, intent_type: str = "deep_thinking", quality_score: int = 70, model_name: str = "unknown"):
    """存入经验池 - 通过ExperiencePool触发因果图学习"""
    try:
        from backend.services.path_handlers._shared import _save_to_experience_pool as _shared_save
        _shared_save(query, response, success=success, intent_type=intent_type,
                     quality_score=quality_score, model_name=model_name)
    except Exception as e:
        logger.error(f"经验存储失败: {e}")


async def _solve_history_query(query: str) -> str:
    """解决历史查询"""
    try:
        db = get_storage_port("data/experience_pool.db")
        rows = db.query("SELECT raw_input, response FROM experiences ORDER BY timestamp DESC LIMIT 10")

        if rows:
            history_text = "\n".join([f"- {row[0][:30]}... → {row[1][:50]}..." for row in rows[:5]])
            return f"📜 最近的历史记录:\n{history_text}\n\n(完整历史功能开发中)"
        else:
            return "暂无历史记录。开始和我对话吧!"
    except Exception:
        return "历史记录功能正在初始化,请稍后再试。"


def _zh_extract_keywords(query: str, max_k: int = 8) -> list:
    """中文关键词提取：2-4字滑动窗口 + 停用词过滤"""
    import re as _re
    _stop_words = {'的', '了', '是', '在', '有', '和', '就', '不', '人', '都',
                   '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你',
                   '会', '着', '没有', '看', '好', '自己', '这', '他', '她', '它',
                   '吗', '呢', '吧', '啊', '呀', '哦', '嗯', '么', '那', '什么',
                   '怎么', '如何', '为什么', '可以', '能够', '能', '还是', '或者',
                   '基本', '原理', '问题', '关于', '通过', '进行', '使用', '方法'}
    _stop_chars = set('的了是在有和就不人都一个上也得到说要去你会着看好这他她它吗呢吧啊呀哦嗯么那')
    keywords = []
    en_segments = _re.findall(r'[a-zA-Z]{2,}|\d+', query)
    keywords.extend(en_segments[:3])
    zh_text = _re.sub(r'[^\u4e00-\u9fa5]', '', query)
    zh_text = ''.join(c for c in zh_text if c not in _stop_chars)
    for length in [4, 3, 2]:
        for i in range(len(zh_text) - length + 1):
            chunk = zh_text[i:i+length]
            if chunk not in _stop_words:
                keywords.append(chunk)
    seen = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)
    return unique[:max_k]


def _query_experience_pool_semantic(query: str, top_k: int = 3) -> list:
    """从经验池中语义检索相似问题的历史回答"""
    try:
        db = get_storage_port("data/experience_pool.db")
        keywords = _zh_extract_keywords(query, max_k=8)
        if not keywords:
            return []
        conditions = " OR ".join([f"raw_input LIKE ?" for _ in keywords])
        params = [f"%{kw}%" for kw in keywords]
        if not conditions:
            return []
        sql = f"SELECT raw_input, response, quality_score, success FROM experiences WHERE ({conditions}) AND success = 1 AND quality_score >= 60 AND response IS NOT NULL AND LENGTH(response) > 20 ORDER BY quality_score DESC, timestamp DESC LIMIT ?"
        params.append(top_k)
        rows = db.query(sql, tuple(params))
        results = []
        seen_responses = set()
        for row in rows:
            r = dict(row)
            resp = r.get("response", "")
            if resp and resp[:50] not in seen_responses:
                seen_responses.add(resp[:50])
                results.append(r)
        return results
    except Exception as e:
        logger.warning(f"经验池语义检索失败: {e}")
        return []


def _query_spirit_lessons(query: str, top_k: int = 3) -> list:
    """从精神内核教训库中检索相关学习记录"""
    try:
        db = get_storage_port("data/spirit_lessons.db")
        keywords = _zh_extract_keywords(query, max_k=6)
        if not keywords:
            return []
        conditions = " OR ".join(["question LIKE ?" for _ in keywords])
        params = [f"%{kw}%" for kw in keywords]
        sql = f"SELECT question, attempts, failed_methods, timestamp FROM lessons WHERE ({conditions}) ORDER BY timestamp DESC LIMIT ?"
        params.append(top_k)
        rows = db.query(sql, tuple(params))
        return [dict(row) for row in rows]
    except Exception:
        return []


def _call_external_model_sync(query: str, timeout: int = 30) -> str:
    """同步调用外部模型(DeepSeek)生成回复"""
    try:
        import json as _json
        from pathlib import Path as _Path
        _ext_config_file = _Path("config/external_api.json")
        if not _ext_config_file.exists():
            return ""
        with open(_ext_config_file, 'r', encoding='utf-8') as _f:
            _ext_config = _json.load(_f)
        _deepseek_key = _ext_config.get("deepseek_api_key", "")
        if not _deepseek_key or _deepseek_key.startswith("●"):
            return ""
        import requests as _req
        _messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": query}
        ]
        resp = _req.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {_deepseek_key}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": _messages, "max_tokens": 2048},
            timeout=timeout
        )
        if resp.status_code == 200:
            content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            if content and len(content) > 20:
                return content
    except Exception as e:
        logger.warning(f"外部模型调用失败: {e}")
    return ""


def _generate_smart_reply(query: str, intent_type: str) -> str:
    """生成智能回复 - 优先经验池检索,其次外部模型,最后才用模板"""
    # 路径1:从经验池语义检索
    similar = _query_experience_pool_semantic(query, top_k=3)
    if similar:
        best = similar[0]
        response = best.get("response", "")
        if response and len(response) > 30:
            source_hint = f"(参考历史经验,质量分{best.get('quality_score', '?')})"
            return f"{response}\n\n{source_hint}"

    # 路径1.5:从精神内核教训库检索(闭环学习)
    lessons = _query_spirit_lessons(query, top_k=3)
    if lessons:
        latest = lessons[0]
        question = latest.get("question", "")
        failed = latest.get("failed_methods", "")
        if question and failed:
            logger.info(f"📖 命中教训记录: {question[:30]} → 失败方法: {failed[:50]}")

    # 路径2:同步调用外部模型
    ext_response = _call_external_model_sync(query, timeout=15)
    if ext_response:
        try:
            _save_to_experience_pool(query, ext_response, success=True, intent_type="external_fallback", model_name="deepseek")
        except Exception:
            pass
        return ext_response

    # 路径3:基于intent_type的模板选择(最后兜底)
    intent_templates = {
        "code": f"""我理解你需要代码方面的帮助。关于"{query}",我可以:

1. **代码生成** - 请告诉我具体需求
2. **代码解释** - 请提供代码,我会解释原理
3. **代码优化** - 请提供代码,我给出建议

请告诉我更具体的需求。""",
        "question": f"""关于"{query}",让我从多个角度分析:

1. **概念理解** - 先明确核心概念的定义和边界
2. **方法探索** - 从不同角度寻找可行的方案
3. **实践验证** - 通过实际操作来检验和调整

💡 请告诉我你最关心的方面,我会深入展开。""",
        "verification": f"""你的质疑很有道理。关于"{query}":

1. **重新审视** - 让我从不同角度重新分析
2. **寻找反例** - 检查是否存在与当前结论矛盾的证据
3. **交叉验证** - 用多个独立来源核实

💡 你可以指出具体哪个部分让你存疑,我会重点验证。""",
        "learning_trigger": f"""关于"{query}",这是一个很好的学习方向:

1. **基础知识** - 先建立核心概念的框架
2. **进阶理解** - 在框架上填充细节和关联
3. **实践应用** - 通过动手来巩固理解

💡 告诉我你目前的理解程度,我会给出适合的起点。""",
        "reflection": f"""关于"{query}",让我认真回顾:

1. **历史轨迹** - 梳理之前的关键决策和转折点
2. **当前状态** - 评估现在的位置和进展
3. **未来方向** - 基于回顾确定下一步行动

💡 你希望我聚焦哪个时间段或哪个方面?""",
    }

    template = intent_templates.get(intent_type)
    if template:
        return template

    query_lower = query.lower()
    if any(kw in query_lower for kw in ["认知", "意识", "思维", "智能"]):
        return f"""关于"{query}",这是一个深刻的哲学与科学问题:

**认知的产生涉及多个层面:**
1. **生物学基础** - 认知源于大脑神经元的连接与活动
2. **感知与输入** - 通过感官接收外界信息,这是认知的起点
3. **信息加工** - 大脑对感知信息进行编码、存储、检索和推理
4. **涌现特性** - 认知是大量简单单元交互后涌现出的复杂特性
5. **学习与适应** - 通过经验不断调整,使认知能力持续进化

💡 如果你对某个方面特别感兴趣,可以继续深入探讨。"""

    # 记录关键词gap到学习清单，用于后续自我完善
    try:
        if SPIRIT_CORE_AVAILABLE:
            from core.spirit_core import spirit_core
            spirit_core._record_lesson(query, [{"method": "关键词模板", "success": False, "error": "无匹配关键词分支，使用默认模板"}])
    except Exception:
        pass

    # 使用统一契约中的兜底模板，而非硬编码字符串
    try:
        from core.response_quality_contract import FALLBACK_TEMPLATES
        return FALLBACK_TEMPLATES["default"].format(query=query)
    except Exception:
        pass

    return f"""关于"{query}",我目前的理解还不够深入,但我的思考方向:

1. **问题拆解** - 将复杂问题分解为可执行的小步骤
2. **方法探索** - 从多个角度寻找可能的方案
3. **实践验证** - 通过实际操作来验证和调整

💡 请告诉我更具体的场景和约束条件,或者换个方式提问,我会更有针对性地回答。"""


def _generate_meaningful_fallback(query: str, attempts: list, intent_type: str = "") -> str:
    """
    降级保护:生成有意义的基础回复

    根据intent_type提供不同方向引导，而非通用建议。
    同时对每个失败回复记录知识缺口，对齐"渴望知识"原则。
    """
    successful = [a for a in attempts if a[1]]
    failed = [a for a in attempts if not a[1]]

    parts = []
    parts.append(f"🎯 关于「{query}」")
    parts.append(f"   我已尝试 {len(attempts)} 种方法")

    if successful:
        parts.append(f"   ✅ 成功:{', '.join([a[0] for a in successful])}")
    if failed:
        parts.append(f"   ❌ 失败:{', '.join([a[0] for a in failed])}")

    # 根据intent_type提供具体方向引导
    parts.append("\n💡 我可以从这些方向帮你深入:")
    if intent_type in ("simple_query", "complex_query"):
        parts.append("   1️⃣ **知识拆解** - 把问题拆成更小的子问题，逐层回答")
        parts.append("   2️⃣ **对比分析** - 列出不同对象的参数、数据、观测差异")
        parts.append("   3️⃣ **因果推演** - 从第一性原理解释为什么会产生这个效果")
        parts.append("   📝 例如关于天体对比，你可以问: '火星和木星的哪个参数导致了这种现象差异？'")
    elif intent_type == "weather":
        parts.append("   1️⃣ **提具体城市** - 当前支持的城市列表，告诉我城市名")
        parts.append("   2️⃣ **提时间范围** - 今天的天气还是未来预报？")
    elif intent_type == "code":
        parts.append("   1️⃣ **贴代码片段** - 把相关代码贴出来，我可以帮你分析")
        parts.append("   2️⃣ **说明预期行为** - 你希望代码做什么，实际发生了什么？")
        parts.append("   3️⃣ **报错信息** - 把完整的错误堆栈发给我")
    elif intent_type == "memory":
        parts.append("   1️⃣ **关键词补充** - 告诉我更多关键词，帮助定位记忆")
        parts.append("   2️⃣ **时间范围** - 大约是什么时候的事情？")
    else:
        parts.append("   1️⃣ **换个角度** - 从不同学科或视角重新描述这个问题")
        parts.append("   2️⃣ **补充前提** - 你观察/遇到了什么具体现象让你想到这个问题？")
        parts.append("   3️⃣ **分级展开** - 从基础概念开始，一步步深入")

    parts.append("\n🌟 永不放弃:")
    parts.append("   我已把这个问题记入学习清单，下次会更有准备。你随时可以继续问！")

    # 记录知识缺口到好奇心引擎（对齐"渴望知识"感知层）
    _record_knowledge_gap(query, intent_type)

    return "\n".join(parts)


def _record_knowledge_gap(query: str, intent_type: str) -> None:
    """将未能回答的问题记录为知识缺口，供好奇心引擎后续主动学习"""
    try:
        from core.ports.adapters import get_storage_port
        db = get_storage_port("data/knowledge_gaps.db")
        db.execute(
            "INSERT OR IGNORE INTO knowledge_gaps (query, intent_type, source, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
            (query.strip()[:200], intent_type or "unknown", "chat_handler", time.time()),
            commit=True,
        )
    except Exception:
        pass