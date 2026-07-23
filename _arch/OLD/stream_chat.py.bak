"""
流式聊天接口 - 实时返回思考过程
"""
import asyncio
import json
import time
from typing import AsyncGenerator
from loguru import logger

async def stream_chat_with_thinking(
    user_input: str,
    planner,
    intent_parser,
    adapters,
    selected_model: str = "auto"
) -> AsyncGenerator[str, None]:
    """
    流式聊天，实时返回思考过程
    
    Yields:
        JSON格式的思考过程和结果
    """
    
    def emit(event: str, data: dict) -> str:
        """格式化为SSE事件"""
        return f"data: {json.dumps({'event': event, **data}, ensure_ascii=False)}\n\n"
    
    # 1. 开始思考
    yield emit("thinking", {
        "stage": "start",
        "message": "🧠 开始分析您的问题..."
    })
    
    await asyncio.sleep(0.1)
    
    # 2. 意图识别
    yield emit("thinking", {
        "stage": "intent",
        "message": "🔍 正在识别意图..."
    })
    
    try:
        intent = intent_parser.parse(user_input)
        yield emit("thinking", {
            "stage": "intent",
            "message": f"✅ 识别意图: {intent.type} (置信度: {intent.confidence:.0%})",
            "data": {
                "intent": intent.type,
                "confidence": intent.confidence
            }
        })
    except Exception as e:
        yield emit("thinking", {
            "stage": "intent",
            "message": f"⚠️ 意图识别失败，使用默认: {e}"
        })
        intent = None
    
    await asyncio.sleep(0.1)
    
    # 3. 知识检索
    yield emit("thinking", {
        "stage": "knowledge",
        "message": "📚 正在检索知识库..."
    })
    
    knowledge_result = None
    try:
        from core.learning import enhanced_learner
        knowledge_result = enhanced_learner.retrieve_knowledge(user_input)
        if knowledge_result:
            yield emit("thinking", {
                "stage": "knowledge",
                "message": f"✅ 找到相关知识 (置信度: {knowledge_result.get('confidence', 0):.0%})"
            })
        else:
            yield emit("thinking", {
                "stage": "knowledge",
                "message": "ℹ️ 知识库中未找到直接匹配"
            })
    except Exception as e:
        yield emit("thinking", {
            "stage": "knowledge",
            "message": f"⚠️ 知识检索失败: {e}"
        })
    
    await asyncio.sleep(0.1)
    
    # 4. 选择模型
    yield emit("thinking", {
        "stage": "model",
        "message": f"🤖 选择模型: {selected_model}"
    })
    
    # 5. 调用模型
    yield emit("thinking", {
        "stage": "inference",
        "message": "💭 正在生成回答..."
    })
    
    response = None
    start_time = time.time()
    
    try:
        # 调用planner生成响应
        if planner:
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, 
                    planner.plan, 
                    intent
                ),
                timeout=30.0
            )
        
        elapsed = time.time() - start_time
        
        if response:
            yield emit("thinking", {
                "stage": "inference",
                "message": f"✅ 生成完成 (耗时: {elapsed:.1f}秒)"
            })
        else:
            yield emit("thinking", {
                "stage": "inference",
                "message": "⚠️ 模型未返回结果，尝试备用方案..."
            })
            
    except asyncio.TimeoutError:
        yield emit("thinking", {
            "stage": "inference",
            "message": "⏱️ 模型响应超时，使用默认回答"
        })
        response = "抱歉，处理超时了。请稍后重试或简化问题。"
        
    except Exception as e:
        yield emit("thinking", {
            "stage": "inference",
            "message": f"⚠️ 模型调用失败: {e}"
        })
        response = f"处理时遇到问题: {e}"
    
    # 6. 返回最终结果
    yield emit("complete", {
        "response": str(response) if response else "未能生成有效回答",
        "intent": intent.type if intent else "unknown",
        "elapsed": time.time() - start_time
    })