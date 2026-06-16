"""测试聊天功能"""
import sys
import asyncio
sys.path.insert(0, '.')

print("=" * 60)
print("  测试聊天功能")
print("=" * 60)

async def test_chat():
    # 初始化
    print("\n[1/3] 初始化系统...")
    from dotenv import load_dotenv
    load_dotenv()
    
    from infrastructure.event_bus import bus
    from core.services.intent_parser import IntentParser
    from core.services.planner import Planner
    from adapters.llm.ollama_adapter import OllamaAdapter
    import threading
    
    adapters = {}
    adapters_lock = threading.Lock()
    
    # 加载Ollama模型
    try:
        adapters["qwen2.5-coder:7b"] = OllamaAdapter(model_name="qwen2.5-coder:7b")
        print("  ✅ 已加载 qwen2.5-coder:7b")
    except Exception as e:
        print(f"  ❌ 加载失败: {e}")
        return
    
    intent_parser = IntentParser()
    planner = Planner(adapters, adapters_lock=adapters_lock)
    
    # 测试聊天
    print("\n[2/3] 测试聊天...")
    user_input = "你好"
    
    intent = intent_parser.parse(user_input)
    print(f"  意图: {intent.type}, 置信度: {intent.confidence:.2f}")
    
    response_queue = asyncio.Queue()
    
    def on_response(data):
        response_queue.put_nowait(data)
    
    bus.subscribe("plan_executed", on_response)
    
    # 执行规划
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, planner.plan, intent)
    
    # 等待响应
    try:
        response = await asyncio.wait_for(response_queue.get(), timeout=30.0)
        print(f"  ✅ 收到响应: {str(response)[:100]}...")
    except asyncio.TimeoutError:
        print("  ❌ 响应超时")
    
    # 测试知识检索
    print("\n[3/3] 测试知识检索...")
    from core.learning import enhanced_learner
    result = enhanced_learner.retrieve_knowledge(user_input)
    if result:
        print(f"  ✅ 知识命中: {result.get('source', 'unknown')}")
        print(f"     置信度: {result.get('confidence', 0):.2f}")
    else:
        print("  ⚠️  无知识匹配")

asyncio.run(test_chat())

print("\n" + "=" * 60)
print("  测试完成")
print("=" * 60)