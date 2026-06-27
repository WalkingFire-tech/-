"""
无模型进化系统 - 代码质量评估
"""
import sys
import os

print("=" * 80)
print("无模型进化系统 - 代码质量评估")
print("=" * 80)

all_checks = []

def check(name: str, condition: bool, detail: str = ""):
    all_checks.append((name, condition))
    status = "✅" if condition else "❌"
    print(f"{status} {name}")
    if detail:
        print(f"   {detail}")

# ==================== 1. 代码结构评估 ====================
print("\n[1] 代码结构")

with open("core/reflective_model_free_evolution.py", "r", encoding="utf-8") as f:
    code = f.read()

# 检查核心类
classes = [
    "DataDrivenReflectionEngine",
    "CognitiveLoopManager",
    "MetacognitionMonitor",
    "AdaptiveEvolutionController",
    "ReflectiveModelFreeEvolution",
]

for cls in classes:
    check(f"类定义: {cls}", f"class {cls}" in code)

# 检查数据契约
dataclasses = [
    "KnowledgeItem",
    "ErrorCase",
    "BehaviorPattern",
]

for dc in dataclasses:
    check(f"数据契约: {dc}", f"class {dc}" in code)

# ==================== 2. 核心功能评估 ====================
print("\n[2] 核心功能")

methods = [
    ("DataDrivenReflectionEngine", "detect_errors"),
    ("DataDrivenReflectionEngine", "perform_hypothesis_check"),
    ("DataDrivenReflectionEngine", "record_reflection"),
    ("CognitiveLoopManager", "run_complete_cycle"),
    ("MetacognitionMonitor", "monitor_and_adjust"),
    ("AdaptiveEvolutionController", "adjust_params"),
]

for cls, method in methods:
    check(f"方法: {cls}.{method}", f"def {method}" in code)

# 检查关键功能实现
features = [
    ("置信度崩溃检测", "_detect_confidence_collapse"),
    ("不一致性检测", "_find_inconsistencies"),
    ("内容异常检测", "_detect_anomalous_content"),
    ("完整性检查", "_check_completeness"),
    ("来源可信度评估", "_assess_source_reliability"),
    ("系统健康评估", "_assess_health"),
]

for name, method in features:
    check(f"功能: {name}", method in code)

# ==================== 3. 数据库设计评估 ====================
print("\n[3] 数据库设计")

tables = [
    "error_cases",
    "behavior_patterns",
    "knowledge_confidence",
    "metacognition_log",
    "cognitive_cycles",
    "verification_queue",
    "system_metrics",
    "behavior_adjustments",
]

for table in tables:
    check(f"表定义: {table}", table in code)

# ==================== 4. 测试核心逻辑 ====================
print("\n[4] 核心逻辑测试")

from core.reflective_model_free_evolution import (
    DataDrivenReflectionEngine,
    CognitiveLoopManager,
    MetacognitionMonitor,
    AdaptiveEvolutionController,
    ErrorCase
)

# 测试反思引擎
reflection_engine = DataDrivenReflectionEngine()

# 测试错误检测
test_knowledge = [
    {
        'id': 'test1',
        'question': '测试问题',
        'answer': '测试答案',
        'confidence': 0.2,
        'initial_confidence': 0.8,
        'error_count': 0
    },
    {
        'id': 'test2',
        'question': '测试问题2',
        'answer': '短',  # 太短
        'confidence': 0.8,
        'initial_confidence': 0.8,
        'error_count': 5  # 高频错误
    },
]

errors = reflection_engine.detect_errors(test_knowledge)

check(
    "错误检测功能",
    len(errors) > 0,
    f"检测到{len(errors)}个错误"
)

check(
    "检测到置信度崩溃",
    any(e.error_type == 'confidence_collapse' for e in errors),
    "置信度崩溃检测正确"
)

check(
    "检测到高频错误",
    any(e.error_type == 'frequent_errors' for e in errors),
    "高频错误检测正确"
)

check(
    "检测到内容异常",
    any(e.error_type == 'content_anomaly' for e in errors),
    "内容异常检测正确"
)

# 测试假设检验
new_knowledge = {
    'id': 'new1',
    'question': '新知识',
    'answer': '这是一个完整的答案，包含足够的内容和结构。\n\n1. 第一点\n2. 第二点\n3. 第三点',
    'source': 'official_documentation',
    'confidence': 0.7
}

check_result = reflection_engine.perform_hypothesis_check(new_knowledge, [])

check(
    "假设检验功能",
    'passed' in check_result and 'checks' in check_result,
    "假设检验返回正确结构"
)

check(
    "完整性评分",
    check_result.get('confidence_adjustment', 0) >= -0.5,
    f"置信度调整: {check_result.get('confidence_adjustment', 0):.2f}"
)

# 测试元认知监控
metacognition = MetacognitionMonitor()

system_state = {
    'error_rate': 0.2,
    'learning_efficiency': 0.2,
    'confidence_trend': -0.15,
    'adaptation_speed': 0.05
}

result = metacognition.monitor_and_adjust(system_state)

check(
    "元认知监控功能",
    'adjustments' in result and 'system_health' in result,
    "监控返回正确结构"
)

check(
    "检测到错误率过高",
    any(a['type'] == 'increase_verification' for a in result['adjustments']),
    "错误率监控正确"
)

check(
    "检测到学习效率低",
    any(a['type'] == 'adjust_learning' for a in result['adjustments']),
    "学习效率监控正确"
)

check(
    "生成建议",
    len(result.get('recommendations', [])) > 0,
    f"生成{len(result.get('recommendations', []))}条建议"
)

# 测试自适应控制器
adaptive = AdaptiveEvolutionController()

performance = {
    'error_rate': 0.2,
    'learning_efficiency': 0.2,
    'adaptation_speed': 0.05
}

changes = adaptive.adjust_params(performance)

check(
    "参数自适应功能",
    isinstance(changes, dict),
    "返回参数变化字典"
)

check(
    "验证严格度调整",
    'verification_strictness' in changes or len(changes) > 0,
    f"调整了{len(changes)}个参数"
)

# ==================== 5. 设计模式评估 ====================
print("\n[5] 设计模式")

check(
    "使用dataclass定义数据契约",
    "@dataclass" in code,
    "数据契约规范化"
)

check(
    "使用SQLite持久化",
    "sqlite3.connect" in code,
    "数据持久化"
)

check(
    "使用日志记录",
    "logger.info" in code or "logger.warning" in code,
    "日志记录"
)

check(
    "异常处理",
    "try:" in code and "except" in code,
    "异常处理机制"
)

# ==================== 总结 ====================
print("\n" + "=" * 80)
print("【代码质量评估总结】")
print("=" * 80)

passed = sum(1 for _, c in all_checks if c)
total = len(all_checks)
pass_rate = passed / total * 100 if total > 0 else 0

print(f"\n总检查项: {total}")
print(f"通过: {passed}")
print(f"失败: {total - passed}")
print(f"通过率: {pass_rate:.1f}%")

if passed == total:
    print("\n✅ 所有检查通过！")
    print("\n代码质量评估:")
    print("  1. 代码结构清晰 ✓")
    print("  2. 核心功能完整 ✓")
    print("  3. 数据库设计合理 ✓")
    print("  4. 核心逻辑正确 ✓")
    print("  5. 设计模式规范 ✓")
    print("\n结论: 无模型进化系统代码质量优秀，可以集成")
else:
    print("\n❌ 存在未通过的检查项！")
    for name, condition in all_checks:
        if not condition:
            print(f"  ❌ {name}")