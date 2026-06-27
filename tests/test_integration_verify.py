import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 70)
print("第二阶段集成测试验证")
print("=" * 70)

tests_passed = 0
tests_total = 6

# 测试1: 关系模型适配
try:
    from core.relationship.model import get_relationship_model
    model = get_relationship_model()
    changes = model.update_from_conversation({"user_satisfaction": 0.8, "emotional_intensity": 0.5, "duration_minutes": 10, "system_helpfulness": 0.7})
    metrics = model.get_metrics()
    phase = model.get_relationship_phase()
    print("✅ 关系模型适配: 通过")
    tests_passed += 1
except Exception as e:
    print(f"❌ 关系模型适配: 失败 - {e}")

# 测试2: 立体记忆适配
try:
    from core.memory.stereo_memory import get_stereo_memory
    store = get_stereo_memory()
    recent = store.get_recent(limit=5)
    topic_memories = store.get_by_topic("项目", limit=5)
    stats = store.get_stats()
    print("✅ 立体记忆适配: 通过")
    tests_passed += 1
except Exception as e:
    print(f"❌ 立体记忆适配: 失败 - {e}")

# 测试3: 情绪检测器
try:
    from core.layers.l1_perception_enhanced import get_emotion_detector
    detector = get_emotion_detector()
    result = detector.detect("我很高兴")
    print("✅ 情绪检测器: 通过")
    tests_passed += 1
except Exception as e:
    print(f"❌ 情绪检测器: 失败 - {e}")

# 测试4: 完整集成
try:
    from core.layers.l1_perception_enhanced import get_emotion_detector
    from core.relationship.model import get_relationship_model
    from core.presence.self_review import get_self_review_engine
    from core.presence.active_perception import get_active_perception_engine
    
    emotion_detector = get_emotion_detector()
    relationship_model = get_relationship_model()
    review_engine = get_self_review_engine()
    active_perception = get_active_perception_engine()
    
    user_input = "我真的很感谢你的帮助"
    emotion = emotion_detector.detect(user_input)
    relationship_model.update_from_conversation({"user_satisfaction": 0.9, "emotional_intensity": emotion.intensity, "duration_minutes": 5, "system_helpfulness": 0.8})
    metrics = relationship_model.get_metrics()
    print("✅ 完整集成: 通过")
    tests_passed += 1
except Exception as e:
    print(f"❌ 完整集成: 失败 - {e}")

# 测试5: 认知周期
try:
    from core.layers.l1_perception_enhanced import get_emotion_detector
    from core.relationship.model import get_relationship_model
    
    emotion_detector = get_emotion_detector()
    relationship_model = get_relationship_model()
    
    for user_input in ["你好", "谢谢", "再见"]:
        emotion = emotion_detector.detect(user_input)
        relationship_model.update_from_conversation({"user_satisfaction": 0.8, "emotional_intensity": emotion.intensity, "duration_minutes": 3, "system_helpfulness": 0.7})
    
    print("✅ 认知周期: 通过")
    tests_passed += 1
except Exception as e:
    print(f"❌ 认知周期: 失败 - {e}")

# 测试6: 统计功能
try:
    from core.relationship.model import get_relationship_model
    from core.memory.stereo_memory import get_stereo_memory
    from core.presence.self_review import get_self_review_engine
    
    relationship_model = get_relationship_model()
    metrics = relationship_model.get_metrics()
    
    stereo_store = get_stereo_memory()
    stats = stereo_store.get_stats()
    
    review_engine = get_self_review_engine()
    review_stats = review_engine.get_stats()
    
    print("✅ 统计功能: 通过")
    tests_passed += 1
except Exception as e:
    print(f"❌ 统计功能: 失败 - {e}")

print("\n" + "=" * 70)
print(f"测试结果: {tests_passed}/{tests_total} 通过")
print("=" * 70)

if tests_passed == tests_total:
    print("\n🎉 第二阶段前半部分集成测试全部通过！")
    print("\n下一步: 集成到Planner")
else:
    print(f"\n⚠️ 有 {tests_total - tests_passed} 个测试失败")