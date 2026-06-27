"""
测试联网搜索学习功能
"""
import sys
sys.path.insert(0, ".")

print("\n" + "="*60)
print("测试联网搜索学习功能")
print("="*60)

# 1. 测试ddgs搜索
print("\n【1】测试ddgs搜索...")
try:
    from ddgs import DDGS
    import threading
    
    search_results = None
    
    def search_task():
        global search_results
        try:
            with DDGS() as ddgs:
                search_results = list(ddgs.text('二十四节气有哪些', max_results=3))
        except Exception as e:
            print(f"搜索线程错误: {e}")
    
    thread = threading.Thread(target=search_task, daemon=True)
    thread.start()
    thread.join(timeout=15)
    
    if thread.is_alive():
        print("❌ 搜索超时")
    elif search_results:
        print(f"✅ 搜索成功: {len(search_results)}条结果")
        for i, sr in enumerate(search_results, 1):
            print(f"  {i}. {sr.get('title', '无标题')[:50]}")
            print(f"     {sr.get('body', '')[:100]}...")
    else:
        print("❌ 无搜索结果")
        
except Exception as e:
    print(f"❌ 搜索失败: {e}")

# 2. 测试learning_loop搜索
print("\n【2】测试learning_loop搜索...")
try:
    from core.learning_loop import learning_loop
    
    results = learning_loop._search_and_learn("Python编程")
    
    if results:
        print(f"✅ learning_loop搜索成功: {len(results)}条")
        print(f"  第一条: {results[0].get('title', '无标题')[:50]}")
    else:
        print("❌ learning_loop无结果")
        
except Exception as e:
    print(f"❌ learning_loop失败: {e}")

# 3. 测试external_learner搜索
print("\n【3】测试external_learner搜索...")
try:
    from core.external_learner import external_learner
    
    results = external_learner.search_web("机器学习", num_results=3)
    
    if results:
        print(f"✅ external_learner搜索成功: {len(results)}条")
        if isinstance(results[0], dict):
            print(f"  第一条: {results[0].get('title', results[0])[:50]}")
        else:
            print(f"  第一条: {results[0][:50]}")
    else:
        print("❌ external_learner无结果")
        
except Exception as e:
    print(f"❌ external_learner失败: {e}")

# 4. 测试搜索增强回答
print("\n【4】测试搜索增强回答...")
try:
    from core.services.planner import planner
    from core.services.intent_parser import intent_parser
    
    # 测试问题
    test_questions = [
        "一年有多少个节气？",
        "Python是什么？",
        "什么是机器学习？"
    ]
    
    for q in test_questions:
        print(f"\n  问题: {q}")
        
        intent = intent_parser.parse(q)
        print(f"  意图: {intent.type} (置信度: {intent.confidence:.2f})")
        
        # 尝试搜索增强
        response = planner._try_search_enhanced_answer(intent)
        
        if response:
            print(f"  ✅ 搜索增强回答成功")
            print(f"  回答长度: {len(response)} 字符")
            print(f"  回答预览: {response[:150]}...")
        else:
            print(f"  ⚠️ 搜索增强返回None")
        
except Exception as e:
    print(f"❌ 搜索增强测试失败: {e}")
    import traceback
    traceback.print_exc()

# 5. 测试完整对话流程（模拟）
print("\n【5】测试完整对话流程...")
try:
    import requests
    
    # 检查后端是否运行
    try:
        health = requests.get("http://localhost:8000/api/health", timeout=3)
        if health.status_code == 200:
            print("  ✅ 后端服务运行中")
            
            # 发送测试问题
            response = requests.post(
                "http://localhost:8000/api/chat",
                json={"message": "二十四节气都有哪些？"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ 对话成功")
                print(f"  模型: {data.get('model_used', 'unknown')}")
                print(f"  回答长度: {len(data.get('response', ''))} 字符")
            else:
                print(f"  ❌ 对话失败: {response.status_code}")
        else:
            print("  ⚠️ 后端服务异常")
    except:
        print("  ⚠️ 后端服务未运行，跳过对话测试")
        
except Exception as e:
    print(f"❌ 对话流程测试失败: {e}")

print("\n" + "="*60)
print("测试完成")
print("="*60)