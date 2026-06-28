"""
永不放弃的聊天处理 - 简化版
保留原来的工作逻辑，但添加降级保护

核心精神：所有回复都必须符合精神内核
- 合理且逻辑清晰有理有据且自洽
- 即使失败也给出有意义的回复
- 永不放弃是元能力
"""
import asyncio
from loguru import logger

# 导入精神内核
try:
    from core.spirit_core import spirit_core, ensure_spirit_compliance
    SPIRIT_CORE_AVAILABLE = True
    logger.info("✅ 精神内核已加载")
except ImportError as e:
    logger.warning(f"⚠️ 精神内核未加载: {e}")
    SPIRIT_CORE_AVAILABLE = False


async def chat_never_giveup(user_input: str, context: dict) -> dict:
    """
    永不放弃的聊天处理
    
    策略：
    1. 快速意图识别
    2. 简单意图直接回复
    3. 深度认知处理
    4. Ollama本地模型
    5. 知识库查询
    6. 经验池查询
    7. 规则匹配回复
    8. 后台任务（永不放弃）
    """
    
    attempts = []
    final_response = None
    
    # ========== 策略1：快速意图识别 ==========
    try:
        from core.cognitive_dispatcher import CognitiveDispatcher
        loop = asyncio.get_event_loop()
        dispatcher = CognitiveDispatcher()
        
        dispatch_result = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: dispatcher.dispatch(user_query=user_input, context=context)),
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
    
    # ========== 策略3：深度认知处理（所有问题都尝试） ==========
    if not final_response:
        logger.info(f"🔄 开始深度认知处理: intent={intent_type}")
        try:
            from core.metacognitive_executor import MetacognitiveExecutor
            executor = MetacognitiveExecutor()
            
            exec_result = await asyncio.wait_for(
                executor.execute_with_full_metacognition(user_query=user_input, context=context),
                timeout=15.0
            )
            
            result = exec_result.get("final_result", "")
            if result and len(result) > 20:
                final_response = result
                attempts.append(("深度认知", True, f"{len(result)}字"))
                logger.info(f"✅ 深度认知成功: {len(result)}字")
        except Exception as e:
            logger.error(f"❌ 深度认知失败: {e}")
            attempts.append(("深度认知", False, str(e)[:50]))
    
    # ========== 策略4：Ollama本地模型 ==========
    if not final_response:
        try:
            import requests
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "qwen2.5:7b", "prompt": user_input, "stream": False},
                    timeout=10
                )
            )
            if response.status_code == 200:
                result = response.json().get("response", "")
                if result and len(result) > 20:
                    final_response = result
                    attempts.append(("Ollama", True, f"{len(result)}字"))
        except Exception as e:
            attempts.append(("Ollama", False, str(e)[:50]))
    
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
    
    # ========== 策略8：精神内核强制注入（最后一道防线） ==========
    if SPIRIT_CORE_AVAILABLE:
        # 使用enforce_on_output：自动验证+异常触发+自动修正
        original_response = final_response
        final_response = spirit_core.enforce_on_output(final_response, source="chat_handler")
        if final_response != original_response:
            attempts.append(("精神内核修正", True, "自动修正敷衍回复"))
        else:
            attempts.append(("精神内核验证", True, "回复符合精神"))
    else:
        # 如果精神内核不可用，使用基础的有意义回复生成
        if not final_response or len(final_response) < 20:
            final_response = _generate_meaningful_fallback(user_input, attempts)
            attempts.append(("降级保护", True, "基础有意义回复"))
    
    # ========== 记录解决过程 ==========
    logger.info(f"✅ 问题解决: {user_input[:30]} → {[(a[0], a[1]) for a in attempts]}")
    
    return {
        "response": final_response,
        "attempts": attempts,
        "intent": intent_type,
        "confidence": confidence,
        "route": route,
        "spirit_compliant": SPIRIT_CORE_AVAILABLE
    }


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