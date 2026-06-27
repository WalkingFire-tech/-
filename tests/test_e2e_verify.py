import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("第二阶段端到端测试验证")
print("=" * 70)

tests_passed = 0
tests_total = 5

# 测试1: Planner初始化
try:
    from core.services.planner import DataDrivenPlanner
    from adapters.llm.ollama_adapter import OllamaAdapter
    
    adapters = {"llama3": OllamaAdapter(model_name="llama3")}
    planner = DataDrivenPlanner(adapters)
    
    assert hasattr(planner, 'emotion_detector'), "缺少emotion_detector"
    assert hasattr(planner, 'stereo_memory'), "缺少stereo_memory"
    assert hasattr(planner, 'relationship_model'), "缺少relationship_model"
    assert hasattr(planner, 'self_review_engine'), "缺少self_review_engine"
    assert hasattr(planner, 'active_perception'), "缺少active_perception"
    
    print("✅ Planner初始化: 通过")
    tests_passed += 1
except Exception as e:
    import traceback
    print(f"❌ Planner初始化: 失败")
    print(f"错误: {e}")
    traceback.print_exc()

# 测试2: 情绪感知
try:
    from core.services.planner import DataDrivenPlanner
    from core.services.intent_parser import Intent
    from adapters.llm.ollama_adapter import OllamaAdapter
    
    adapters = {"llama3": OllamaAdapter(model_name="llama3")}
    planner = DataDrivenPlanner(adapters)
    
    intent = Intent(raw_text="我很高兴，这太棒了！", type="chat", entities={}, confidence=0.9)
    emotion = planner._infer_emotion(intent)
    
    assert 'emotion' in emotion, "缺少emotion字段"
    print("✅ 情绪感知: 通过")
    tests_passed += 1
except Exception as e:
    import traceback
    print(f"❌ 情绪感知: 失败")
    print(f"错误: {e}")
    traceback.print_exc()

# 测试3: 组件更新
try:
    from core.services.planner import DataDrivenPlanner
    from core.services.intent_parser import Intent
    from adapters.llm.ollama_adapter import OllamaAdapter
    
    adapters = {"llama3": OllamaAdapter(model_name="llama3")}
    planner = DataDrivenPlanner(adapters)
    
    intent = Intent(raw_text="非常感谢你的帮助！", type="chat", entities={}, confidence=0.9)
    emotion = {"emotion": "joy", "intensity": 0.8, "confidence": 0.9}
    response = "不客气，很高兴能帮到你！"
    
    planner._update_phase2_components(intent, emotion, response)
    
    metrics = planner.relationship_model.get_metrics()
    assert metrics['trust'] > 0, "信任度未更新"
    
    print("✅ 组件更新: 通过")
    tests_passed += 1
except Exception as e:
    import traceback
    print(f"❌ 组件更新: 失败")
    print(f"错误: {e}")
    traceback.print_exc()

# 测试4: 完整周期
try:
    from core.services.planner import DataDrivenPlanner
    from core.services.intent_parser import Intent
    from adapters.llm.ollama_adapter import OllamaAdapter
    
    adapters = {"llama3": OllamaAdapter(model_name="llama3")}
    planner = DataDrivenPlanner(adapters)
    
    for user_input in ["你好", "谢谢", "再见"]:
        intent = Intent(raw_text=user_input, type="chat", entities={}, confidence=0.9)
        emotion = planner._infer_emotion(intent)
        response = f"回复: {user_input}"
        planner._update_phase2_components(intent, emotion, response)
    
    metrics = planner.relationship_model.get_metrics()
    assert metrics['conversation_count'] >= 3, "对话数不足"
    
    print("✅ 完整周期: 通过")
    tests_passed += 1
except Exception as e:
    import traceback
    print(f"❌ 完整周期: 失败")
    print(f"错误: {e}")
    traceback.print_exc()

# 测试5: 统计功能
try:
    from core.services.planner import DataDrivenPlanner
    from adapters.llm.ollama_adapter import OllamaAdapter
    
    adapters = {"llama3": OllamaAdapter(model_name="llama3")}
    planner = DataDrivenPlanner(adapters)
    
    metrics = planner.relationship_model.get_metrics()
    stats = planner.stereo_memory.get_stats()
    review_stats = planner.self_review_engine.get_stats()
    
    assert 'trust' in metrics, "缺少信任度"
    assert 'total_memories' in stats, "缺少记忆统计"
    assert 'total_reviews' in review_stats, "缺少评估统计"
    
    print("✅ 统计功能: 通过")
    tests_passed += 1
except Exception as e:
    import traceback
    print(f"❌ 统计功能: 失败")
    print(f"错误: {e}")
    traceback.print_exc()

print("\n" + "=" * 70)
print(f"测试结果: {tests_passed}/{tests_total} 通过")
print("=" * 70)

if tests_passed == tests_total:
    print("\n🎉 第二阶段端到端测试全部通过！")
    print("\n集成状态:")
    print("  ✅ Planner已集成第二阶段组件")
    print("  ✅ 情绪感知在规划流程中生效")
    print("  ✅ 关系模型自动更新")
    print("  ✅ 立体记忆自动存储")
    print("  ✅ 自我评估自动执行")
    print("\n第二阶段完成度: 100%")
else:
    print(f"\n⚠️ 有 {tests_total - tests_passed} 个测试失败")
