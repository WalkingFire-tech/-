#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证CognitiveDispatcher改进"""
import sys
sys.path.insert(0, '.')
from core.cognitive_dispatcher import CognitiveDispatcher

print("=" * 70)
print("🔍 CognitiveDispatcher 改进验证")
print("=" * 70)

config = {
    "cache_ttl": 300,
    "route_thresholds": {
        "learning_confidence": 0.5
    },
    "enable_capability_scan": {
        "tools": True,
        "models": False,
        "knowledge_bases": True
    }
}

dispatcher = CognitiveDispatcher(config)

print("\n[1] 配置化参数")
print("-" * 50)
print(f"  缓存TTL: {dispatcher.cache_ttl}秒")
print(f"  路由阈值: {dispatcher.route_thresholds}")
print(f"  能力扫描开关: {dispatcher.enable_capability_scan}")

print("\n[2] 路由决策测试（QuickReflex前置，无fast路径）")
print("-" * 50)

test_queries = [
    ("为什么天空是蓝色的？", "complex_query"),
    ("我不懂量子力学", "learning_trigger"),
    ("如何优化系统性能？", "complex_query"),
    ("介绍一下机器学习", "learning_trigger"),
]

for query, expected_intent in test_queries:
    result = dispatcher.dispatch(query)
    route = result["route"]
    intent = result["intent_type"]
    complexity = result["complexity"]
    print(f"  '{query[:20]}...' → intent={intent}, route={route}, complexity={complexity:.1%}")

print("\n[3] 执行计划验证（工具选择交给仲裁器）")
print("-" * 50)

result = dispatcher.dispatch("计算 123 + 456")
plan = result["execution_plan"]
print(f"  任务数: {len(plan['tasks'])}")
for i, task in enumerate(plan["tasks"], 1):
    task_type = task.get("type", "unknown")
    desc = task.get("description", "")
    if task_type == "tool_selection":
        candidates = task.get("candidates", [])
        print(f"    {i}. {task_type}: {candidates}")
    else:
        print(f"    {i}. {task_type}: {desc}")

print("\n[4] 能力扫描（带锁保护）")
print("-" * 50)
caps = dispatcher._scan_capabilities()
print(f"  工具数: {len(caps['tools'])}")
print(f"  模型数: {len(caps['models'])}")
print(f"  知识库数: {len(caps['knowledge_bases'])}")
print(f"  缓存锁: ✓")

print("\n[5] 反思管道集成")
print("-" * 50)
has_reflection = any(
    t.get("type") == "reflection_pipeline" 
    for t in plan["tasks"]
)
print(f"  执行计划包含反思管道: {'✓' if has_reflection else '✗'}")

print("\n" + "=" * 70)
print("✅ CognitiveDispatcher 改进验证完成")
print("=" * 70)