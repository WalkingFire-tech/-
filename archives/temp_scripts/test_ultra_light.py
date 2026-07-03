"""
超轻量测试：只测试不涉及外部调用的部分
"""
import sys
import time
sys.path.insert(0, ".")

print("测试1：精神内核加载")
from core.spirit_core import spirit_core
print(f"  ✅ 精神内核加载成功")

print("\n测试2：永不放弃引擎")
from core.never_give_up import NeverGiveUpEngine
engine = NeverGiveUpEngine()
response = engine._generate_meaningful_response("测试", [("方法1", False, "错误1")])
print(f"  ✅ 有意义回复: {len(response)}字")

print("\n测试3：问题类型分析")
qtype = engine._analyze_question_type("认知的概念是什么")
print(f"  ✅ 问题类型: {qtype}")

print("\n测试4：智能规划生成")
from core.metacognitive_executor import MetacognitiveExecutor
executor = MetacognitiveExecutor()
plan = executor._smart_generate_plan("认知的概念是什么", {"capability_prompt": ""})
print(f"  ✅ 规划生成: {len(plan['tasks'])}个任务")
for task in plan['tasks']:
    print(f"     - {task['type']}: {task['description']}")

print("\n测试5：默认计划")
plan = executor._create_default_plan("测试问题")
print(f"  ✅ 默认计划: {len(plan['tasks'])}个任务")

print("\n✅ 所有超轻量测试通过！")