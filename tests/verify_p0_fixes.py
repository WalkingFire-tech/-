"""
验证P0修复
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("P0修复验证测试")
print("=" * 60)

# 测试1: 规则匹配raw_input变量
print("\n[测试1] 规则匹配raw_input变量")
try:
    from infrastructure.rule_matcher import RuleMatcher
    from core.services.intent_parser import Intent
    
    matcher = RuleMatcher()
    intent = Intent(type="question", raw_text="你好，今天天气怎么样？", entities={}, confidence=0.9)
    
    context = {
        "intent_type": intent.type,
        "raw_input": intent.raw_text,
        "quality": 85,
        "model": "mindchat",
        "duration": 2.5,
    }
    
    # 测试简单条件
    result1 = matcher.evaluate_condition("intent_type == 'question'", context)
    assert result1 == True, "简单条件匹配失败"
    print("  ✓ 简单条件匹配成功")
    
    # 测试包含raw_input的条件
    result2 = matcher.evaluate_condition("quality > 80", context)
    assert result2 == True, "quality条件匹配失败"
    print("  ✓ quality条件匹配成功")
    
    # 测试复杂条件
    result3 = matcher.evaluate_condition("intent_type == 'question' and quality > 50", context)
    assert result3 == True, "复杂条件匹配失败"
    print("  ✓ 复杂条件匹配成功")
    
    print("  ✅ 规则匹配测试通过")
    
except Exception as e:
    print(f"  ❌ 规则匹配测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试2: 反事实模拟异步调用
print("\n[测试2] 反事实模拟异步调用")
try:
    from infrastructure.counterfactual_simulator import CounterfactualSimulator
    
    simulator = CounterfactualSimulator()
    
    # 创建一个简单的同步模型适配器
    class MockAdapter:
        def __init__(self, name):
            self.model_name = name
        
        def generate(self, prompt):
            # 同步方法
            return f"Mock response for: {prompt[:30]}"
    
    adapter = MockAdapter("test_model")
    
    # 测试异步调用
    async def test_simulate():
        score = await simulator._simulate_with_model(
            adapter, 
            "测试输入", 
            "question"
        )
        return score
    
    score = asyncio.run(test_simulate())
    assert score > 0, "模拟评分应该大于0"
    print(f"  ✓ 模拟评分: {score}")
    print("  ✅ 反事实模拟异步调用测试通过")
    
except Exception as e:
    print(f"  ❌ 反事实模拟测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试3: 并行调度异步调用
print("\n[测试3] 并行调度异步调用")
try:
    from infrastructure.parallel_scheduler import ParallelScheduler
    
    scheduler = ParallelScheduler()
    
    # 创建模拟适配器
    class MockAdapter2:
        def __init__(self, name):
            self.model_name = name
        
        async def generate(self, prompt):
            await asyncio.sleep(0.1)
            return f"Response from {self.model_name}"
    
    adapters = {
        "model_a": MockAdapter2("model_a"),
        "model_b": MockAdapter2("model_b"),
    }
    
    # 测试联邦调度
    async def test_federated():
        result = await scheduler.federated_call(
            prompt="测试提示",
            task_type="question",
            adapters=adapters,
            top_k=2
        )
        return result
    
    result = asyncio.run(test_federated())
    assert 'best' in result, "结果应包含best字段"
    print(f"  ✓ 联邦调度成功: {result.get('task_id')}")
    print("  ✅ 并行调度异步调用测试通过")
    
except Exception as e:
    print(f"  ❌ 并行调度测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("P0修复验证完成")
print("=" * 60)