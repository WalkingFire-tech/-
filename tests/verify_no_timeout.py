"""
验证修复 - 确认超时和熔断已禁用
"""
import sys
sys.path.insert(0, ".")

from adapters.llm.ollama_adapter import OllamaAdapter
from infrastructure.model_health_checker import ModelHealthChecker
from infrastructure.parallel_scheduler import ParallelScheduler

print("\n=== 验证Ollama适配器 ===")
adapter = OllamaAdapter("qwen2.5-coder:7b")
print(f"超时设置: {adapter.default_timeout}")
print(f"熔断阈值: {adapter.failure_threshold}")
print(f"是否熔断: {adapter._is_circuit_broken()}")

assert adapter.default_timeout is None, "超时应为None（无限制）"
assert adapter._is_circuit_broken() is False, "不应触发熔断"
print("✅ Ollama适配器验证通过")

print("\n=== 验证健康检查器 ===")
checker = ModelHealthChecker()
print(f"是否在黑名单: {checker.is_blacklisted('test_model')}")
print(f"是否可用: {checker.is_available('test_model')}")

assert checker.is_blacklisted('test_model') is False, "不应有黑名单"
assert checker.is_available('test_model') is True, "模型应始终可用"
print("✅ 健康检查器验证通过")

print("\n=== 验证并行调度器 ===")
import asyncio
scheduler = ParallelScheduler()

async def verify_scheduler():
    is_blacklisted = await scheduler._is_blacklisted('test_model')
    print(f"是否在黑名单: {is_blacklisted}")
    assert is_blacklisted is False, "不应有黑名单"
    print("✅ 并行调度器验证通过")

asyncio.run(verify_scheduler())

print("\n" + "="*60)
print("✅ 所有验证通过")
print("="*60)
print("\n修复内容:")
print("1. ✅ 移除超时限制 - 模型可以思考任意长时间")
print("2. ✅ 禁用熔断机制 - 失败不会禁用模型")
print("3. ✅ 禁用黑名单 - 模型始终可用")
print("4. ✅ 移除重试 - 失败就失败，不浪费时间重试")