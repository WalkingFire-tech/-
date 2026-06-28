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
from loguru import logger

try:
    from core.spirit_core import spirit_core, ensure_spirit_compliance
    SPIRIT_CORE_AVAILABLE = True
    logger.info("✅ 精神内核已加载")
except ImportError as e:
    logger.warning(f"⚠️ 精神内核未加载: {e}")
    SPIRIT_CORE_AVAILABLE = False


def _get_available_ollama_model() -> str:
    """获取可用的Ollama模型"""
    try:
        import requests
        tags = requests.get("http://localhost:11434/api/tags", timeout=2)
        available = [m["name"] for m in tags.json().get("models", [])]
    except Exception:
        return None
    
    model_priority = ["qwen2.5:7b", "qwen2.5-coder:7b", "gemma-4-12B:latest", "deepcoder:latest"]
    for m in model_priority:
        for a in available:
            if m in a or a.startswith(m.split(":")[0]):
                return a
    return available[0] if available else None


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
                None, lambda: dispatcher.dispatch(user_query=user_input, context=context)
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
    
    # ========== 策略2：简单意图直接回复 ==========
    if intent_type == "greeting":
        final_response = "你好！我是联盟拓荒者智能体系统，很高兴为你服务。我可以帮助你完成各种任务，包括代码生成、问题解答、数据分析等。"
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
    
    # ========== 策略3：深度认知处理（不设超时！） ==========
    # 超时=放弃，这违背永不放弃精神！
    # 改为：先尝试快速获取结果，如果慢就先给即时回复
    if not final_response:
        logger.info(f"🔄 开始深度认知处理: intent={intent_type}")
        
        # 3a. 先尝试快速路径（知识库+经验池）
        quick_result = await _quick_solve(user_input, intent_type)
        if quick_result:
            final_response = quick_result
            attempts.append(("快速解答", True, "即时回复"))
        
        # 3b. 启动后台深度思考（不阻塞返回）
        if not final_response or len(final_response) < 50:
            asyncio.create_task(
                _background_deep_thinking(user_input, context, intent_type)
            )
            logger.info("🔄 后台深度思考已启动")
    
    # ========== 策略4：Ollama本地模型（不设超时！） ==========
    if not final_response:
        selected = _get_available_ollama_model()
        if selected:
            try:
                import requests
                logger.info(f"  🤖 使用模型: {selected}")
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: requests.post(
                        "http://localhost:11434/api/generate",
                        json={"model": selected, "prompt": user_input, "stream": False},
                        timeout=60  # 给模型足够时间思考
                    )
                )
                if response.status_code == 200:
                    result = response.json().get("response", "")
                    if result and len(result) > 10:
                        final_response = result
                        attempts.append(("Ollama", True, f"{len(result)}字 ({selected})"))
                        # 存入经验池
                        _save_to_experience_pool(user_input, result)
            except Exception as e:
                attempts.append(("Ollama", False, str(e)[:50]))
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
            cursor.execute("SELECT response FROM experiences WHERE query LIKE ? ORDER BY timestamp DESC LIMIT 1", (f"%{user_input[:20]}%",))
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
        final_response = spirit_core.enforce_on_output(final_response, source="chat_handler")
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
        cursor.execute("SELECT response FROM experiences WHERE query LIKE ? ORDER BY timestamp DESC LIMIT 1", (f"%{query[:20]}%",))
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
        
        exec_result = await executor.execute_with_full_metacognition(
            user_query=query, context=context
        )
        
        result = exec_result.get("final_result", "")
        if result and len(result) > 20:
            # 存入经验池，下次直接使用
            _save_to_experience_pool(query, result)
            logger.info(f"✅ 后台思考完成: {len(result)}字，已存入经验池")
        else:
            logger.info(f"⚠️ 后台思考未获得满意结果")
            
    except Exception as e:
        logger.error(f"❌ 后台思考失败: {e}")


def _save_to_experience_pool(query: str, response: str):
    """存入经验池"""
    try:
        import sqlite3
        from datetime import datetime
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO experiences (query, response, timestamp, intent_type, quality_score) VALUES (?, ?, ?, ?, ?)",
            (query, response, datetime.now().isoformat(), "deep_thinking", 70)
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
        cursor.execute("SELECT query, response FROM experiences ORDER BY timestamp DESC LIMIT 10")
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
    """生成智能回复"""
    query_lower = query.lower()
    
    if any(kw in query_lower for kw in ["代码", "编程", "写代码", "函数"]):
        return f"""我理解你需要代码方面的帮助。关于"{query}"，我可以：

1. **代码生成** - 请告诉我具体需求
2. **代码解释** - 请提供代码，我会解释原理
3. **代码优化** - 请提供代码，我给出建议

请告诉我更具体的需求。"""
    
    if any(kw in query_lower for kw in ["什么是", "是什么", "介绍"]):
        topic = query.replace("什么是", "").replace("是什么", "").strip()
        return f"关于'{topic}'，我正在学习相关知识。请稍后重试，或尝试更具体的问题。"
    
    if any(kw in query_lower for kw in ["如何", "怎么", "怎样"]):
        return f"关于'{query}'，这是一个很好的问题。请告诉我更具体的场景，我会给出详细指导。"
    
    return f"我收到了你的问题：'{query}'。虽然暂时无法给出完整答案，但我会记住并继续学习。请尝试换个方式提问，或稍后重试。"


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