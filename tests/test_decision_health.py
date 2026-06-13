"""测试决策日志和模型健康检查"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*60)
print("决策日志 + 模型健康检查 测试")
print("="*60)

# 1. 决策日志测试
print("\n1️⃣ 决策日志测试")
from infrastructure.decision_logger import decision_logger

# 记录几个决策
decision_logger.start_request("test_001")
decision_logger.log_decision(
    decision_type="model_selection",
    choice="deepseek-chat",
    reason="统计库推荐，任务类型: code",
    alternatives=["mindchat", "qwen2.5-coder:1.5b"],
    score=0.85
)

decision_logger.log_decision(
    decision_type="tool_selection",
    choice="math_calculator",
    reason="意图匹配calculation类别",
    score=0.92
)

# 解释最近决策
explanation = decision_logger.explain_last_decision()
print(explanation)

# 获取摘要
summary = decision_logger.get_decision_summary()
print(summary)

# 2. 模型健康检查测试
print("\n2️⃣ 模型健康检查测试")
from infrastructure.model_health_checker import model_health_checker

# 测试模型可用性
print(f"  mindchat 可用: {model_health_checker.is_available('mindchat')}")

# 记录失败
print("\n  记录失败...")
model_health_checker.record_failure("test_model", "timeout", "响应超时")
model_health_checker.record_failure("test_model", "timeout", "响应超时")
model_health_checker.record_failure("test_model", "timeout", "响应超时")

# 检查是否在黑名单
print(f"  test_model 可用: {model_health_checker.is_available('test_model')}")

# 获取黑名单报告
report = model_health_checker.get_blacklist_report()
print(report)

# 获取统计
stats = model_health_checker.get_statistics()
print(f"\n  统计: {stats['total_models']}个模型, {stats['blacklisted']}个在黑名单")

# 3. 集成测试
print("\n3️⃣ 集成测试")
all_models = ["mindchat", "deepseek-chat", "test_model", "qwen2.5-coder:1.5b"]
available = model_health_checker.get_available_models(all_models)
print(f"  所有模型: {all_models}")
print(f"  可用模型: {available}")

print("\n" + "="*60)
print("测试完成！")
print("="*60)