"""诊断联网学习流程"""
import sys
sys.path.insert(0, ".")

print("\n" + "="*60)
print("诊断联网学习流程")
print("="*60)

test_query = "老冰棍是怎么做的？"

# 1. 测试意图识别
print(f"\n【1】意图识别: {test_query}")
try:
    from core.services.intent_parser import IntentParser
    parser = IntentParser()
    intent = parser.parse(test_query)
    print(f"  意图类型: {intent.type}")
    print(f"  置信度: {intent.confidence}")
    print(f"  是否会触发搜索增强: {intent.type in ['question', 'verification']}")
except Exception as e:
    print(f"  ❌ 失败: {e}")

# 2. 测试搜索功能
print(f"\n【2】搜索功能测试")
try:
    import threading
    from ddgs import DDGS
    
    search_results = None
    
    def search_task():
        global search_results
        try:
            with DDGS() as ddgs:
                search_results = list(ddgs.text(test_query, max_results=3))
        except Exception as e:
            print(f"  搜索线程错误: {e}")
    
    thread = threading.Thread(target=search_task, daemon=True)
    thread.start()
    thread.join(timeout=20)
    
    if thread.is_alive():
        print("  ❌ 搜索超时（20秒）")
    elif search_results:
        print(f"  ✅ 搜索成功: {len(search_results)}条")
        for i, sr in enumerate(search_results, 1):
            print(f"    {i}. {sr.get('title', '无标题')[:50]}")
    else:
        print("  ❌ 无搜索结果")
        
except Exception as e:
    print(f"  ❌ 搜索失败: {e}")

# 3. 测试planner搜索增强
print(f"\n【3】Planner搜索增强测试")
try:
    from core.services.planner import planner
    from core.services.intent_parser import IntentParser
    
    parser = IntentParser()
    intent = parser.parse(test_query)
    
    print(f"  调用 _try_search_enhanced_answer...")
    response = planner._try_search_enhanced_answer(intent)
    
    if response:
        print(f"  ✅ 搜索增强成功")
        print(f"  响应长度: {len(response)} 字符")
        print(f"  响应预览: {response[:200]}...")
    else:
        print(f"  ❌ 搜索增强返回None")
        
except Exception as e:
    print(f"  ❌ 失败: {e}")
    import traceback
    traceback.print_exc()

# 4. 测试external_learner
print(f"\n【4】External Learner测试")
try:
    from core.external_learner import external_learner
    
    results = external_learner.search_web(test_query, num_results=3)
    
    if results:
        print(f"  ✅ 搜索成功: {len(results)}条")
        for i, r in enumerate(results, 1):
            if isinstance(r, dict):
                print(f"    {i}. {r.get('title', r)[:50]}")
            else:
                print(f"    {i}. {r[:50]}")
    else:
        print("  ❌ 无结果")
        
except Exception as e:
    print(f"  ❌ 失败: {e}")

# 5. 测试完整对话流程
print(f"\n【5】完整对话流程测试")
try:
    import requests
    
    try:
        response = requests.post(
            "http://localhost:8000/api/chat",
            json={"message": test_query},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ 对话成功")
            print(f"  响应: {data.get('response', '')[:200]}...")
        else:
            print(f"  ❌ HTTP {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("  ⚠️ 后端未运行")
        
except Exception as e:
    print(f"  ❌ 失败: {e}")

print("\n" + "="*60)
print("诊断完成")
print("="*60)