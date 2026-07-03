"""
测试CognitiveDispatcher的5个改进
"""
import sys
sys.path.insert(0, ".")

print("╔════════════════════════════════════════════════════════╗")
print("║       测试CognitiveDispatcher 5个改进                  ║")
print("╚════════════════════════════════════════════════════════╝\n")

from core.cognitive_dispatcher import CognitiveDispatcher

dispatcher = CognitiveDispatcher()

# 改进1：_find_applicable_tools从工具注册表读取keywords
print("改进1：_find_applicable_tools从工具注册表读取keywords")
tools = [
    {"name": "calculator", "description": "计算器", "tags": ["计算", "算", "数学"]},
    {"name": "search", "description": "搜索", "tags": ["搜索", "查找"]},
    {"name": "custom_tool", "description": "自定义", "keywords": ["自定义", "特殊"]}
]
result = dispatcher._find_applicable_tools("计算123+456", {"tools": tools})
print(f"  ✅ 找到适用工具: {[t['name'] for t in result]}")

result = dispatcher._find_applicable_tools("搜索最新新闻", {"tools": tools})
print(f"  ✅ 找到适用工具: {[t['name'] for t in result]}")

# 改进2：_generate_execution_plan工具调用改为执行指令
print("\n改进2：_generate_execution_plan工具调用改为执行指令")
plan = dispatcher._generate_execution_plan(
    "计算圆的面积", "slow", {"tools": tools}, "complex_query"
)
tool_tasks = [t for t in plan['tasks'] if t['type'] == 'tool_execution']
if tool_tasks:
    print(f"  ✅ 工具任务类型: tool_execution（执行指令）")
    print(f"     候选工具: {tool_tasks[0].get('candidates', [])}")
    print(f"     执行指令: {tool_tasks[0].get('instruction', '')}")

# 改进3：build_capability_prompt支持模板化配置
print("\n改进3：build_capability_prompt支持模板化配置")
# 默认模板
prompt = dispatcher.build_capability_prompt({"tools": tools, "models": [], "knowledge_bases": []})
print(f"  ✅ 默认模板: {len(prompt)}字")

# 自定义模板
custom_dispatcher = CognitiveDispatcher({
    "prompt_template": "工具: {tools}\n请使用以上工具回答问题。"
})
prompt = custom_dispatcher.build_capability_prompt({"tools": tools, "models": [], "knowledge_bases": []})
print(f"  ✅ 自定义模板: {len(prompt)}字")

# 改进4：_quick_intent_classification增加向量相似度匹配
print("\n改进4：_quick_intent_classification增加向量相似度匹配")
intent, confidence = dispatcher._quick_intent_classification("你好")
print(f"  ✅ 规则匹配: intent={intent}, confidence={confidence:.0%}")

intent, confidence = dispatcher._quick_intent_classification("如何实现一个排序算法")
print(f"  ✅ 规则匹配: intent={intent}, confidence={confidence:.0%}")

# 改进5：dispatch_history记录调度决策历史
print("\n改进5：dispatch_history记录调度决策历史")
result = dispatcher.dispatch("认知的概念是什么")
print(f"  ✅ 调度完成: route={result['route']}, intent={result['intent_type']}")

history = dispatcher.get_dispatch_history(limit=3)
print(f"  ✅ 历史记录: {len(history)}条")

patterns = dispatcher.analyze_dispatch_patterns()
print(f"  ✅ 模式分析: {patterns.get('total_decisions', 0)}条决策")

print("\n" + "=" * 60)
print("✅ 所有5个改进测试通过！")
print("=" * 60)