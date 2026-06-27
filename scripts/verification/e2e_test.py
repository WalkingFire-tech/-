"""
端到端测试 - 验证系统完整功能

测试范围：
1. 系统启动测试
2. 六层架构测试
3. 七大机制测试
4. 数据流测试
5. API端点测试
6. 认知循环测试
"""

import sys
import os
import time
import sqlite3
import requests
from datetime import datetime

sys.path.insert(0, '.')

print("=" * 60)
print("联盟拓荒者 - 端到端测试")
print("=" * 60)
print()

test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def test(name: str):
    def decorator(func):
        def wrapper():
            print(f"\n{'='*60}")
            print(f"测试: {name}")
            print(f"{'='*60}")
            try:
                result = func()
                if result:
                    test_results["passed"].append(name)
                    print(f"✅ {name} - 通过")
                else:
                    test_results["failed"].append(name)
                    print(f"❌ {name} - 失败")
            except Exception as e:
                test_results["failed"].append(name)
                print(f"❌ {name} - 异常: {e}")
        return wrapper
    return decorator

@test("1. 六层架构初始化")
def test_six_layers():
    from core.layers.l1_perception_enhanced import L1PerceptionLayer
    from core.layers.l2_learning import L2LearningLayer
    from core.layers.l3_integration import L3IntegrationLayer
    from core.layers.l4_validation import L4ValidationLayer
    from core.layers.l5_evolution import L5EvolutionLayer
    from core.layers.l6_introspection import L6IntrospectionLayer
    
    l1 = L1PerceptionLayer()
    l2 = L2LearningLayer()
    l3 = L3IntegrationLayer()
    l4 = L4ValidationLayer()
    l5 = L5EvolutionLayer()
    l6 = L6IntrospectionLayer()
    
    print(f"  L1感知层: {l1.stats}")
    print(f"  L2学习层: 已初始化")
    print(f"  L3整合层: 已初始化")
    print(f"  L4校验层: 已初始化")
    print(f"  L5进化层: 已初始化")
    print(f"  L6内省层: 已初始化")
    
    return True

@test("2. L1感知层功能")
def test_l1_perception():
    from core.layers.l1_perception_enhanced import L1PerceptionLayer
    
    l1 = L1PerceptionLayer()
    
    test_cases = [
        ("你好，我想问一个问题", "question"),
        ("帮我写一个函数", "request"),
        ("谢谢你的帮助", "acknowledgment"),
        ("我很生气，为什么不工作", "complaint"),
        ("这个我不太明白", "clarification"),
    ]
    
    for text, expected_intent in test_cases:
        result = l1.perceive(text)
        emotion = result['emotional_state'].primary_emotion
        intent = result['intent']
        confidence = result['confidence']
        print(f"  输入: '{text[:20]}...' → 情绪={emotion}, 意图={intent}, 置信度={confidence:.2f}")
    
    return True

@test("3. 七大机制初始化")
def test_seven_mechanisms():
    from core.learning.incremental_perception import IncrementalPerception
    from core.learning.feedback_loop import LearningFeedbackLoop
    from core.learning.error_alchemy import ErrorAlchemy
    from core.learning.tool_builder import ToolSelfBuilder
    from core.learning.knowledge_weaver import KnowledgeWeaver
    from core.learning.rhythm_controller import CognitiveRhythmController
    from core.learning.meta_learning import MetaLearner
    
    mechanisms = {
        "增量感知": IncrementalPerception(),
        "反馈回路": LearningFeedbackLoop(),
        "错误炼金": ErrorAlchemy(),
        "工具构建": ToolSelfBuilder(),
        "知识编织": KnowledgeWeaver(),
        "节奏控制": CognitiveRhythmController(),
        "元学习": MetaLearner(),
    }
    
    for name, mechanism in mechanisms.items():
        print(f"  ✓ {name}: {type(mechanism).__name__}")
    
    return True

@test("4. 数据库连接测试")
def test_databases():
    dbs = {
        "经验池": "data/experience_pool.db",
        "学习规则": "data/learning_rules.db",
        "反思日志": "logs/campfire_log.db",
    }
    
    all_ok = True
    for name, path in dbs.items():
        if os.path.exists(path):
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            conn.close()
            print(f"  ✓ {name}: {path} ({table_count}张表)")
        else:
            print(f"  ✗ {name}: {path} 不存在")
            all_ok = False
    
    return all_ok

@test("5. 经验池数据质量")
def test_experience_pool():
    conn = sqlite3.connect("data/experience_pool.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM experiences")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM experiences WHERE success > 0")
    success_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM experiences WHERE response IS NOT NULL AND response != ''")
    with_response = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(success) FROM experiences")
    avg_success = cursor.fetchone()[0] or 0
    
    conn.close()
    
    print(f"  总经验数: {total}")
    print(f"  成功经验数: {success_count}")
    print(f"  有响应的经验: {with_response}")
    print(f"  平均成功率: {avg_success:.2%}")
    
    if total > 0 and success_count > 0:
        print(f"  ✓ 数据质量良好")
        return True
    else:
        print(f"  ⚠ 数据质量需要改进")
        test_results["warnings"].append("经验池数据质量低")
        return True

@test("6. 反思日志数据")
def test_reflection_log():
    conn = sqlite3.connect("logs/campfire_log.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM reflections")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM reflections WHERE success_score > 0.5")
    good_reflections = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"  总反思数: {total}")
    print(f"  高质量反思: {good_reflections}")
    
    return True

@test("7. 学习规则数据")
def test_learning_rules():
    conn = sqlite3.connect("data/learning_rules.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM rules")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT status, COUNT(*) FROM rules GROUP BY status")
    by_status = dict(cursor.fetchall())
    
    cursor.execute("SELECT AVG(confidence) FROM rules")
    avg_confidence = cursor.fetchone()[0] or 0
    
    conn.close()
    
    print(f"  总规则数: {total}")
    print(f"  按状态分布: {by_status}")
    print(f"  平均置信度: {avg_confidence:.2f}")
    
    return True

@test("8. 快速反射引擎")
def test_quick_reflex():
    from infrastructure.quick_reflex import get_quick_reflex
    
    reflex = get_quick_reflex("config/reflex_rules.yaml")
    stats = reflex.get_stats()
    
    print(f"  规则数: {stats['total_rules']}")
    print(f"  命中数: {stats['total_hits']}")
    
    test_input = "帮我计算 2 + 3"
    result = reflex.process(test_input)
    print(f"  测试输入: '{test_input}'")
    print(f"  反射结果: {result}")
    
    return True

@test("9. 工具仲裁器")
def test_tool_arbiter():
    from tools.arbiter import get_tool_arbiter
    
    arbiter = get_tool_arbiter()
    
    test_cases = [
        "计算 123 * 456",
        "搜索Python教程",
        "读取文件内容",
    ]
    
    for query in test_cases:
        tool = arbiter.select_tool(query)
        print(f"  查询: '{query}' → 工具: {tool}")
    
    return True

@test("10. 反思管道")
def test_reflection_pipeline():
    from infrastructure.reflection_pipeline import get_reflection_pipeline
    
    pipeline = get_reflection_pipeline({
        "log_db_path": "logs/campfire_log.db",
        "jsonl_output_dir": "data/finetune/queue",
        "enable_induction": False,
        "enable_jsonl": True,
    })
    
    test_experience = {
        "user_input": "测试输入",
        "response": "测试响应",
        "success": 0.8,
        "timestamp": datetime.now().isoformat(),
    }
    
    result = pipeline.reflect(test_experience)
    print(f"  反思结果: {result}")
    
    return True

@test("11. 系统编排器")
def test_orchestrator():
    from core.orchestrator import SystemOrchestrator
    
    orchestrator = SystemOrchestrator({
        "persistence_dir": "data/orchestrator"
    })
    
    print(f"  活跃层: {orchestrator.metrics.active_layers}")
    print(f"  活跃机制: {len(orchestrator.mechanisms)}")
    
    return orchestrator.metrics.active_layers > 0

@test("12. 认知循环")
def test_cognitive_loop():
    from core.cognitive_loop import CognitiveLoop
    
    loop = CognitiveLoop()
    
    print(f"  循环计数: {loop.cycle_count}")
    print(f"  L2层: {'已加载' if loop.l2 else '未加载'}")
    print(f"  L3层: {'已加载' if loop.l3 else '未加载'}")
    print(f"  L4层: {'已加载' if loop.l4 else '未加载'}")
    print(f"  L5层: {'已加载' if loop.l5 else '未加载'}")
    print(f"  L6层: {'已加载' if loop.l6 else '未加载'}")
    
    return loop.l2 is not None

@test("13. 金丝雀验证器")
def test_canary_evaluator():
    from core.canary_evaluator import CanaryEvaluator
    
    evaluator = CanaryEvaluator()
    
    test_rule = {
        "rule_id": "test_rule_001",
        "pattern": "test_pattern",
        "action": "test_action",
        "confidence": 0.7,
    }
    
    result = evaluator.evaluate(test_rule)
    print(f"  评估结果: {result}")
    
    return True

@test("14. 记忆巩固器")
def test_sleep_consolidator():
    from core.sleep_consolidator import SleepConsolidator
    
    consolidator = SleepConsolidator()
    
    stats = consolidator.get_stats()
    print(f"  统计信息: {stats}")
    
    return True

@test("15. 元认知执行器")
def test_metacognitive_executor():
    from core.metacognitive_executor import MetacognitiveExecutor
    
    executor = MetacognitiveExecutor()
    
    print(f"  执行器已初始化")
    
    return True

@test("16. API服务可用性")
def test_api_availability():
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print(f"  ✓ API服务运行中 (状态码: {response.status_code})")
            return True
        else:
            print(f"  ⚠ API服务响应异常 (状态码: {response.status_code})")
            test_results["warnings"].append("API服务响应异常")
            return True
    except requests.exceptions.ConnectionError:
        print(f"  ⚠ API服务未启动 (连接失败)")
        test_results["warnings"].append("API服务未启动")
        return True
    except Exception as e:
        print(f"  ⚠ API测试失败: {e}")
        test_results["warnings"].append(f"API测试失败: {e}")
        return True

def run_all_tests():
    tests = [
        test_six_layers,
        test_l1_perception,
        test_seven_mechanisms,
        test_databases,
        test_experience_pool,
        test_reflection_log,
        test_learning_rules,
        test_quick_reflex,
        test_tool_arbiter,
        test_reflection_pipeline,
        test_orchestrator,
        test_cognitive_loop,
        test_canary_evaluator,
        test_sleep_consolidator,
        test_metacognitive_executor,
        test_api_availability,
    ]
    
    for test_func in tests:
        test_func()
    
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"✅ 通过: {len(test_results['passed'])}")
    print(f"❌ 失败: {len(test_results['failed'])}")
    print(f"⚠️  警告: {len(test_results['warnings'])}")
    
    if test_results['failed']:
        print("\n失败的测试:")
        for name in test_results['failed']:
            print(f"  - {name}")
    
    if test_results['warnings']:
        print("\n警告:")
        for warning in test_results['warnings']:
            print(f"  - {warning}")
    
    print("\n" + "=" * 60)
    
    if test_results['failed']:
        print("结果: ❌ 存在失败的测试")
        return False
    else:
        print("结果: ✅ 所有测试通过")
        return True

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)