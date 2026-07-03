"""
永不放弃的聊天处理

核心理念：
- 超时不等于放弃！系统正在思考，不应该被中断
- 先给用户即时回复（状态同步），后台继续深度思考
- 思考完成后更新结果到经验池，下次直接使用
- 永不放弃是元能力，刻进底层
"""
import asyncio
import time
import concurrent.futures
from loguru import logger

_slow_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="chat_slow")

try:
    from core.spirit_core import spirit_core, ensure_spirit_compliance
    SPIRIT_CORE_AVAILABLE = True
    logger.info("✅ 精神内核已加载")
except ImportError as e:
    logger.warning(f"⚠️ 精神内核未加载: {e}")
    SPIRIT_CORE_AVAILABLE = False


_OLLAMA_MODEL_CACHE = {"model": None, "timestamp": 0}

def _get_available_ollama_model() -> str:
    """获取可用的Ollama模型（带缓存，60秒过期）"""
    import time as _time
    now = _time.time()
    if _OLLAMA_MODEL_CACHE["model"] and (now - _OLLAMA_MODEL_CACHE["timestamp"]) < 60:
        return _OLLAMA_MODEL_CACHE["model"]
    
    try:
        import requests
        tags = requests.get("http://localhost:11434/api/tags", timeout=2)
        available = [m["name"] for m in tags.json().get("models", [])]
    except Exception:
        return _OLLAMA_MODEL_CACHE["model"]
    
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
    
    return selected


async def chat_never_giveup(user_input: str, context: dict) -> dict:
    """
    永不放弃的聊天处理
    
    核心改变：超时不等于放弃！
    - 系统正在思考，不应该被中断
    - 先给用户即时回复（状态同步）
    - 后台继续深度思考
    - 思考完成后存入经验池，下次直接使用
    """
    
    start_time = time.time()
    attempts = []
    final_response = None
    
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
    
    # ========== 策略1.5：规则匹配与统计 ==========
    try:
        import sqlite3 as _sql
        from infrastructure.rule_matcher import RuleMatcher as _RM
        _INTENT_TYPE_MAP = {
            "greeting": "chat", "confirmation": "chat", "simple_query": "question",
            "complex_query": "code", "learning_trigger": "question",
            "challenge": "verification", "history_query": "memory",
        }
        _mapped_type = _INTENT_TYPE_MAP.get(intent_type, intent_type)
        _rule_ctx = {
            "intent_type": intent_type,
            "intent_type_legacy": _mapped_type,
            "raw_input": user_input,
        }
        _matcher = _RM()
        with _sql.connect("data/learning_rules.db") as _conn:
            _conn.row_factory = _sql.Row
            _cur = _conn.execute(
                "SELECT id, condition, action, status FROM learning_rules WHERE status IN ('active','trial') ORDER BY priority ASC, confidence DESC"
            )
            _active_matched = False
            _trial_matched = False
            for _row in _cur.fetchall():
                try:
                    if _matcher.evaluate_condition(_row["condition"], _rule_ctx):
                        if _row["status"] == "active" and not _active_matched:
                            _conn.execute(
                                "UPDATE learning_rules SET apply_count=apply_count+1, last_applied=? WHERE id=?",
                                (time.time(), _row["id"]),
                            )
                            _active_matched = True
                        elif _row["status"] == "trial" and not _trial_matched:
                            _conn.execute(
                                "UPDATE learning_rules SET apply_count=apply_count+1, last_applied=? WHERE id=? AND status='trial'",
                                (time.time(), _row["id"]),
                            )
                            _trial_matched = True
                        if _active_matched and _trial_matched:
                            break
                except Exception:
                    pass
            _conn.commit()
    except Exception as _e:
        logger.debug(f"规则匹配统计失败: {_e}")

    # ========== 策略2：简单意图直接回复 ==========
    if intent_type == "greeting":
        final_response = "嘿，我在。有什么想聊的，或者遇到了什么问题？我们一起看看。"
        attempts.append(("简单回复", True, "问候语"))
        return {"response": final_response, "attempts": attempts, "intent": intent_type}
    
    elif intent_type == "confirmation":
        final_response = "好的，我明白了。"
        attempts.append(("简单回复", True, "确认"))
        return {"response": final_response, "attempts": attempts, "intent": intent_type}
    
    elif intent_type == "history_query":
        final_response = await _solve_history_query(user_input)
        attempts.append(("历史查询", True, "历史"))
        return {"response": final_response, "attempts": attempts, "intent": intent_type}
    
    # ========== 策略3：深度认知处理（超时不放弃！） ==========
    if not final_response:
        logger.info(f"🔄 开始深度认知处理: intent={intent_type}")
        
        # 3a. 先尝试快速路径（知识库+经验池）
        quick_result = await _quick_solve(user_input, intent_type)
        if quick_result:
            final_response = quick_result
            attempts.append(("快速解答", True, "即时回复"))
        
        # 3b. 无论快速解答是否成功，都启动后台深度思考
        # 快速解答可能不够好，后台思考可以产出更高质量的答案存入经验池
        # 后台深度思考已禁用——fire-and-forget占用_slow_pool线程池导致服务卡死
        # 反思学习由chat_stream.py阶段7的reflection_pipeline负责
        # asyncio.create_task(
        #     _background_deep_thinking(user_input, context, intent_type)
        # )
        logger.debug("后台深度思考已由reflection_pipeline替代")
    
    # ========== 策略4：Ollama本地模型（等待结果，前端120秒超时够用） ==========
    if not final_response:
        selected = _get_available_ollama_model()
        if selected:
            try:
                import requests
                logger.info(f"  🤖 调用Ollama推理: {selected}")
                response = await asyncio.get_event_loop().run_in_executor(
                    _slow_pool,
                    lambda: requests.post(
                        "http://localhost:11434/api/generate",
                        json={"model": selected, "prompt": user_input, "stream": False},
                        timeout=45
                    )
                )
                if response.status_code == 200:
                    result = response.json().get("response", "")
                    if result and len(result) > 10:
                        final_response = result
                        attempts.append(("Ollama", True, f"{len(result)}字 ({selected})"))
                        _save_to_experience_pool(user_input, result, success=True, intent_type="ollama")
                    else:
                        attempts.append(("Ollama", False, "回复过短"))
                else:
                    attempts.append(("Ollama", False, f"HTTP {response.status_code}"))
            except Exception as e:
                logger.warning(f"Ollama推理失败: {e}")
                attempts.append(("Ollama", False, str(e)[:50]))
                # 失败了也启动后台重试
                asyncio.create_task(_background_ollama_thinking(user_input, selected))
        else:
            attempts.append(("Ollama", False, "无可用模型"))
    
    # ========== 策略5：知识库查询 ==========
    if not final_response:
        try:
            import sqlite3
            conn = sqlite3.connect("data/knowledge_store.db")
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM knowledge WHERE content LIKE ? LIMIT 1", (f"%{user_input[:30]}%",))
            row = cursor.fetchone()
            conn.close()
            if row:
                final_response = row[0]
                attempts.append(("知识库", True, "检索成功"))
        except Exception as e:
            attempts.append(("知识库", False, str(e)[:50]))
    
    # ========== 策略6：经验池查询 ==========
    if not final_response:
        try:
            import sqlite3
            conn = sqlite3.connect("data/experience_pool.db")
            cursor = conn.cursor()
            cursor.execute("SELECT response FROM experiences WHERE raw_input LIKE ? ORDER BY timestamp DESC LIMIT 1", (f"%{user_input[:20]}%",))
            row = cursor.fetchone()
            conn.close()
            if row:
                final_response = row[0]
                attempts.append(("经验池", True, "历史经验"))
        except Exception as e:
            attempts.append(("经验池", False, str(e)[:50]))
    
    # ========== 策略7：规则匹配回复 ==========
    if not final_response:
        final_response = _generate_smart_reply(user_input, intent_type)
        attempts.append(("规则匹配", True, "智能回复"))
    
    # ========== 策略8：精神内核强制注入 ==========
    if SPIRIT_CORE_AVAILABLE:
        original_response = final_response
        final_response = spirit_core.enforce_on_output(final_response, source="chat_handler", query=user_input)
        if final_response != original_response:
            attempts.append(("精神内核修正", True, "自动修正敷衍回复"))
        else:
            attempts.append(("精神内核验证", True, "回复符合精神"))
    else:
        if not final_response or len(final_response) < 20:
            final_response = _generate_meaningful_fallback(user_input, attempts)
            attempts.append(("降级保护", True, "基础有意义回复"))
    
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
    """快速解答：先尝试知识库和经验池"""
    # 1. 经验池
    try:
        import sqlite3
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute("SELECT response FROM experiences WHERE raw_input LIKE ? ORDER BY timestamp DESC LIMIT 1", (f"%{query[:20]}%",))
        row = cursor.fetchone()
        conn.close()
        if row and len(row[0]) > 30:
            return row[0]
    except:
        pass
    
    # 2. 知识库
    try:
        import sqlite3
        conn = sqlite3.connect("data/knowledge_store.db")
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM knowledge WHERE content LIKE ? LIMIT 1", (f"%{query[:30]}%",))
        row = cursor.fetchone()
        conn.close()
        if row and len(row[0]) > 30:
            return row[0]
    except:
        pass
    
    return None


async def _background_ollama_thinking(query: str, model: str):
    """后台Ollama思考（超时不放弃！）"""
    try:
        logger.info(f"🤖 后台Ollama思考开始: {query[:30]}... (模型: {model})")
        import requests
        response = await asyncio.get_event_loop().run_in_executor(
            _slow_pool,
            lambda: requests.post(
                "http://localhost:11434/api/generate",
                json={"model": model, "prompt": query, "stream": False},
                timeout=60
            )
        )
        if response.status_code == 200:
            result = response.json().get("response", "")
            if result and len(result) > 10:
                _save_to_experience_pool(query, result, success=True, intent_type="ollama_background")
                logger.info(f"✅ 后台Ollama思考完成: {len(result)}字，已存入经验池")
            else:
                logger.info(f"⚠️ 后台Ollama思考未获得满意结果")
        else:
            logger.warning(f"⚠️ 后台Ollama思考失败: HTTP {response.status_code}")
    except Exception as e:
        logger.error(f"❌ 后台Ollama思考失败: {e}")


async def _background_deep_thinking(query: str, context: dict, intent_type: str):
    """
    后台深度思考（永不放弃！）
    
    核心理念：超时不等于放弃！
    - 系统正在思考，不应该被中断
    - 思考完成后存入经验池
    - 下次遇到同样问题，直接使用
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
            # 存入经验池，下次直接使用
            _save_to_experience_pool(query, result, success=True, intent_type="metacognitive_background")
            logger.info(f"✅ 后台思考完成: {len(result)}字，已存入经验池")
        else:
            logger.info(f"⚠️ 后台思考未获得满意结果")
            
    except Exception as e:
        logger.error(f"❌ 后台思考失败: {e}")


def _save_to_experience_pool(query: str, response: str, success: bool = True, intent_type: str = "deep_thinking", quality_score: int = 70):
    """存入经验池"""
    try:
        import sqlite3
        from datetime import datetime
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO experiences (raw_input, response, timestamp, intent_type, quality_score, success) VALUES (?, ?, ?, ?, ?, ?)",
            (query, response, datetime.now().isoformat(), intent_type, quality_score, 1 if success else 0)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug(f"经验存储失败: {e}")


async def _solve_history_query(query: str) -> str:
    """解决历史查询"""
    try:
        import sqlite3
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute("SELECT raw_input, response FROM experiences ORDER BY timestamp DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()
        
        if rows:
            history_text = "\n".join([f"- {row[0][:30]}... → {row[1][:50]}..." for row in rows[:5]])
            return f"📜 最近的历史记录：\n{history_text}\n\n（完整历史功能开发中）"
        else:
            return "暂无历史记录。开始和我对话吧！"
    except:
        return "历史记录功能正在初始化，请稍后再试。"


def _generate_smart_reply(query: str, intent_type: str) -> str:
    """生成智能回复（不使用敷衍性语言，给出实质性内容）"""
    query_lower = query.lower()
    
    if any(kw in query_lower for kw in ["代码", "编程", "写代码", "函数"]):
        return f"""我理解你需要代码方面的帮助。关于"{query}"，我可以：

1. **代码生成** - 请告诉我具体需求
2. **代码解释** - 请提供代码，我会解释原理
3. **代码优化** - 请提供代码，我给出建议

请告诉我更具体的需求。"""
    
    if any(kw in query_lower for kw in ["认知", "意识", "思维", "智能"]):
        return f"""关于"{query}"，这是一个深刻的哲学与科学问题：

**认知的产生涉及多个层面：**
1. **生物学基础** - 认知源于大脑神经元的连接与活动，约860亿个神经元通过突触形成复杂网络，电化学信号在其中传递与处理信息
2. **感知与输入** - 通过视觉、听觉、触觉等感官接收外界信息，这是认知的起点
3. **信息加工** - 大脑对感知信息进行编码、存储、检索和推理，形成记忆、判断和决策
4. **涌现特性** - 认知不是单个神经元的功能，而是大量简单单元交互后涌现出的复杂特性
5. **学习与适应** - 通过经验不断调整神经连接（神经可塑性），使认知能力持续进化

**关键理论：**
- 具身认知：认知不仅在大脑中，还依赖身体与环境的互动
- 连接主义：认知是神经网络中分布式表征的计算结果
- 预测编码：大脑不断预测输入，用预测误差来更新内部模型

💡 如果你对某个方面特别感兴趣，可以继续深入探讨。"""
    
    if any(kw in query_lower for kw in ["什么是", "是什么", "介绍"]):
        topic = query.replace("什么是", "").replace("是什么", "").replace("介绍一下", "").strip()
        return f"""关于"{topic}"，我目前的理解：

1. **概念层面** - {topic}是一个重要的知识领域
2. **应用层面** - {topic}在实际中有广泛的应用
3. **学习方向** - 可以从基础概念、核心原理、实践案例三个维度深入

💡 建议你尝试更具体的问题，比如"{topic}的核心原理是什么"或"{topic}有哪些典型应用"，这样我能给出更精准的回答。"""
    
    if any(kw in query_lower for kw in ["如何", "怎么", "怎样"]):
        return f"""关于"{query}"，这是一个很好的问题。我的分析：

1. **问题拆解** - 将复杂问题分解为可执行的小步骤
2. **方法选择** - 根据具体场景选择最合适的方案
3. **实践验证** - 通过实际操作来验证和调整

💡 请告诉我更具体的场景和约束条件，我会给出针对性的详细指导。"""
    
    return f"""我收到了你的问题："{query}"

我的初步分析：
1. **问题理解** - 这是一个值得深入探讨的问题
2. **思考方向** - 可以从多个角度来分析和解决
3. **下一步** - 需要更多上下文信息来给出精准回答

💡 你可以：换个方式提问（更具体或更简单）、提供更多背景信息、或者告诉我你最关心的方面。"""


def _generate_meaningful_fallback(query: str, attempts: list) -> str:
    """
    降级保护：生成有意义的基础回复
    
    即使精神内核不可用，也要确保回复有意义
    """
    successful = [a for a in attempts if a[1]]
    failed = [a for a in attempts if not a[1]]
    
    parts = []
    parts.append(f"🎯 关于「{query}」")
    parts.append(f"   我已尝试 {len(attempts)} 种方法")
    
    if successful:
        parts.append(f"   ✅ 成功：{', '.join([a[0] for a in successful])}")
    if failed:
        parts.append(f"   ❌ 失败：{', '.join([a[0] for a in failed])}")
    
    parts.append("\n💡 建议：")
    parts.append("   1. 换个方式提问（更具体或更简单）")
    parts.append("   2. 提供更多背景信息")
    parts.append("   3. 稍后重试")
    
    parts.append("\n🌟 永不放弃：")
    parts.append("   我会记住这个问题，持续学习改进")
    
    return "\n".join(parts)