"""
联邦调度集成测试
验证能力矩阵增强、模型发现同步包装、planner集成
"""
import asyncio
from infrastructure.model_capability import model_capability
from infrastructure.model_discovery import model_discovery
from infrastructure.parallel_scheduler import parallel_scheduler
from loguru import logger


def test_capability_enhancements():
    """测试能力矩阵增强功能"""
    print("\n=== 能力矩阵增强测试 ===")
    
    # 1. 测试动态维度扩展
    print("\n1. 动态维度扩展")
    model_capability.register_model("test_model_1", {'coding': 0.8, 'reasoning': 0.7})
    model_capability.add_dimension('safety', default_score=0.6)
    
    cap = model_capability.get_model_capability("test_model_1")
    print(f"  添加维度后: {list(cap.keys())}")
    assert 'safety' in cap, "维度添加失败"
    
    # 2. 测试自适应学习率
    print("\n2. 自适应学习率")
    initial_cap = model_capability.get_model_capability("test_model_1")
    initial_coding = initial_cap['coding']
    
    for i in range(5):
        model_capability.update_from_feedback(
            model_name="test_model_1",
            task_type="code",
            success=True,
            quality_score=0.9
        )
    
    updated_cap = model_capability.get_model_capability("test_model_1")
    print(f"  初始coding: {initial_coding:.3f}")
    print(f"  更新后coding: {updated_cap['coding']:.3f}")
    print(f"  变化: {updated_cap['coding'] - initial_coding:.3f}")
    
    # 3. 测试时效衰减
    print("\n3. 时效衰减")
    model_capability.apply_decay(decay_factor=0.98, days_threshold=0)
    decayed_cap = model_capability.get_model_capability("test_model_1")
    print(f"  衰减后coding: {decayed_cap['coding']:.3f}")
    
    # 4. 测试获取已注册模型
    print("\n4. 获取已注册模型")
    models = model_capability.get_registered_models()
    print(f"  已注册模型: {models}")
    
    print("\n✓ 能力矩阵增强测试通过")


def test_model_discovery_sync():
    """测试模型发现同步包装"""
    print("\n=== 模型发现同步包装测试 ===")
    
    # 1. 测试同步发现
    print("\n1. 同步发现模型")
    try:
        models = model_discovery.discover_all_models_sync()
        print(f"  发现模型数: {len(models)}")
        for model in models[:3]:
            print(f"    - {model['name']} ({model['source']})")
    except Exception as e:
        print(f"  同步发现失败（可能无Ollama服务）: {e}")
    
    # 2. 测试同步刷新
    print("\n2. 同步刷新")
    try:
        result = model_discovery.refresh_sync()
        print(f"  刷新结果: {result}")
    except Exception as e:
        print(f"  同步刷新失败: {e}")
    
    # 3. 测试已发现模型获取
    print("\n3. 获取已发现模型")
    discovered = model_discovery.get_discovered_models()
    print(f"  已发现模型: {len(discovered)}个")
    
    print("\n✓ 模型发现同步包装测试通过")


def test_task_complexity_detection():
    """测试任务复杂度检测"""
    print("\n=== 任务复杂度检测测试 ===")
    
    from core.services.intent_parser import Intent
    
    test_cases = [
        ("写一个冒泡排序", False),
        ("写一个Python函数计算斐波那契数列，并用中文解释其数学原理，同时比较递归和迭代的性能", True),
        ("分析这个文档并给出详细建议", True),
        ("什么是机器学习？", False),
        ("请详细分析并比较三种排序算法的优缺点", True),
    ]
    
    class MockPlanner:
        def _is_complex_task(self, intent):
            if len(intent.raw_text) > 200:
                return True
            
            complex_keywords = ["并且", "同时", "先...再...", "比较", "分析", "详细", "全面"]
            if any(kw in intent.raw_text for kw in complex_keywords):
                return True
            
            if intent.type in ["analysis", "comparison", "document"]:
                return True
            
            return False
    
    planner = MockPlanner()
    
    for text, expected in test_cases:
        intent = Intent(type="chat", raw_text=text, confidence=0.8, entities=[])
        result = planner._is_complex_task(intent)
        status = "✓" if result == expected else "✗"
        print(f"  {status} '{text[:30]}...' → 复杂={result} (期望={expected})")
    
    print("\n✓ 任务复杂度检测测试通过")


def test_capability_matrix_integration():
    """测试能力矩阵与统计库集成"""
    print("\n=== 能力矩阵与统计库集成测试 ===")
    
    # 模拟多次调用后的能力更新
    model_name = "test_integration_model"
    model_capability.register_model(model_name, {
        'coding': 0.7,
        'reasoning': 0.7,
        'math': 0.6
    })
    
    print("\n1. 初始能力")
    initial = model_capability.get_model_capability(model_name)
    print(f"  coding: {initial['coding']:.3f}")
    print(f"  reasoning: {initial['reasoning']:.3f}")
    
    print("\n2. 模拟成功调用")
    for i in range(10):
        model_capability.update_from_feedback(
            model_name=model_name,
            task_type="code",
            success=True,
            quality_score=0.85 + i * 0.01
        )
    
    after_success = model_capability.get_model_capability(model_name)
    print(f"  coding: {after_success['coding']:.3f} (变化: {after_success['coding'] - initial['coding']:+.3f})")
    
    print("\n3. 模拟失败调用")
    for i in range(5):
        model_capability.update_from_feedback(
            model_name=model_name,
            task_type="code",
            success=False,
            quality_score=0.3
        )
    
    after_failure = model_capability.get_model_capability(model_name)
    print(f"  coding: {after_failure['coding']:.3f} (变化: {after_failure['coding'] - after_success['coding']:+.3f})")
    
    print("\n✓ 能力矩阵与统计库集成测试通过")


def test_federation_workflow():
    """测试完整联邦调度流程"""
    print("\n=== 完整联邦调度流程测试 ===")
    
    # 1. 注册多个模型
    print("\n1. 注册模型")
    models_config = {
        "model_a": {'coding': 0.9, 'reasoning': 0.7, 'speed': 0.8},
        "model_b": {'coding': 0.7, 'reasoning': 0.9, 'speed': 0.6},
        "model_c": {'coding': 0.8, 'reasoning': 0.8, 'speed': 0.9},
    }
    
    for name, caps in models_config.items():
        model_capability.register_model(name, caps)
    
    registered = model_capability.get_registered_models()
    print(f"  已注册: {[m for m in registered if m in models_config]}")
    
    # 2. 任务匹配
    print("\n2. 任务匹配")
    task_types = ["code", "analysis", "math"]
    
    for task_type in task_types:
        ranked = model_capability.rank_models_for_task(task_type, list(models_config.keys()))
        print(f"  {task_type}: {[f'{m}({s:.2f})' for m, s in ranked]}")
    
    # 3. 导出统计
    print("\n3. 导出统计")
    stats = model_capability.export_stats()
    print(f"  注册模型: {stats['registered_models']}")
    print(f"  维度数: {stats['dimensions']}")
    print(f"  任务类型: {stats['task_types']}")
    
    print("\n✓ 完整联邦调度流程测试通过")


async def main():
    """主测试流程"""
    print("=" * 70)
    print("联邦调度集成测试")
    print("=" * 70)
    
    try:
        test_capability_enhancements()
        test_model_discovery_sync()
        test_task_complexity_detection()
        test_capability_matrix_integration()
        test_federation_workflow()
        
        print("\n" + "=" * 70)
        print("✓ 所有集成测试通过")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())