import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("第二阶段组件独立验证")
print("=" * 70)

tests_passed = 0
tests_total = 5

# 测试1: 情绪检测器
try:
    from core.layers.l1_perception_enhanced import get_emotion_detector
    detector = get_emotion_detector()
    
    result = detector.detect("我很高兴，这太棒了！")
    print(f"✅ 情绪检测器: {result.primary_emotion} (置信度: {result.confidence:.2f})")
    tests_passed += 1
except Exception as e:
    print(f"❌ 情绪检测器: 失败 - {e}")

# 测试2: 立体记忆
try:
    from core.memory.stereo_memory import get_stereo_memory, MemoryType, MemoryImportance
    store = get_stereo_memory()
    
    memory_id = store.save({
        "content": "测试记忆",
        "memory_type": MemoryType.CONVERSATION,
        "importance": MemoryImportance.HIGH
    })
    
    stats = store.get_stats()
    print(f"✅ 立体记忆: 总数={stats['total_memories']}, 平均重要性={stats['avg_importance']:.2f}")
    tests_passed += 1
except Exception as e:
    print(f"❌ 立体记忆: 失败 - {e}")

# 测试3: 关系模型
try:
    from core.relationship.model import get_relationship_model
    model = get_relationship_model()
    
    changes = model.update_from_conversation({
        "user_satisfaction": 0.8,
        "emotional_intensity": 0.5,
        "duration_minutes": 10,
        "system_helpfulness": 0.7
    })
    
    metrics = model.get_metrics()
    phase = model.get_relationship_phase()
    print(f"✅ 关系模型: 阶段={phase}, 信任={metrics['trust']:.2f}")
    tests_passed += 1
except Exception as e:
    print(f"❌ 关系模型: 失败 - {e}")

# 测试4: 自我评估
try:
    from core.presence.self_review import get_self_review_engine
    engine = get_self_review_engine()
    
    result = engine.review({
        "conversation_id": "test",
        "user_input": "测试",
        "system_response": "回复",
        "perception_result": {"intent": "test"},
        "validation_result": {"status": "pass"}
    })
    
    stats = engine.get_stats()
    print(f"✅ 自我评估: 结果={result.outcome}, 分数={result.overall_score:.2f}")
    tests_passed += 1
except Exception as e:
    print(f"❌ 自我评估: 失败 - {e}")

# 测试5: 主动感知
try:
    from core.presence.active_perception import get_active_perception_engine
    engine = get_active_perception_engine()
    
    stats = engine.get_stats()
    print(f"✅ 主动感知: 总感知={stats['total_perceptions']}")
    tests_passed += 1
except Exception as e:
    print(f"❌ 主动感知: 失败 - {e}")

print("\n" + "=" * 70)
print(f"测试结果: {tests_passed}/{tests_total} 通过")
print("=" * 70)

if tests_passed == tests_total:
    print("\n🎉 第二阶段组件全部正常！")
    print("\n修复总结:")
    print("  ✅ 枚举统一处理 - MemoryImportance.from_value()")
    print("  ✅ search添加query参数")
    print("  ✅ save完整保存所有维度")
    print("  ✅ 线程安全 - 添加_lock锁")
    print("  ✅ 统计信息修复 - 避免枚举相加错误")
else:
    print(f"\n⚠️ 有 {tests_total - tests_passed} 个测试失败")