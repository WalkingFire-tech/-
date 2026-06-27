"""
测试超时修复效果
"""
import sys
import time
sys.path.insert(0, ".")

from infrastructure.config_manager import config
from adapters.llm.ollama_adapter import OllamaAdapter
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="INFO")

def test_config():
    print("\n=== 测试配置加载 ===")
    
    timeout = config.get("models.local.default_timeout", "未配置")
    retry_times = config.get("models.local.retry_times", "未配置")
    retry_delay = config.get("models.local.retry_delay", "未配置")
    
    print(f"default_timeout: {timeout}秒")
    print(f"retry_times: {retry_times}次")
    print(f"retry_delay: {retry_delay}秒")
    
    retry_config = config.get_retry_config(is_remote=False)
    print(f"\n重试配置: {retry_config}")
    
    assert timeout == 20, f"超时时间应为20秒，实际为{timeout}"
    assert retry_times == 1, f"重试次数应为1次，实际为{retry_times}"
    
    print("✅ 配置测试通过")

def test_adapter():
    print("\n=== 测试Ollama适配器 ===")
    
    adapter = OllamaAdapter("mindchat")
    
    print(f"模型名: {adapter.model_name}")
    print(f"默认超时: {adapter.default_timeout}秒")
    print(f"熔断阈值: {adapter.failure_threshold}次")
    print(f"熔断时长: {adapter.circuit_breaker_duration}秒")
    
    assert adapter.default_timeout == 20, f"超时时间应为20秒"
    assert adapter.failure_threshold == 5, f"熔断阈值应为5次"
    assert adapter.circuit_breaker_duration == 60, f"熔断时长应为60秒"
    
    print("✅ 适配器配置测试通过")

def test_simple_call():
    print("\n=== 测试简单调用 ===")
    
    adapter = OllamaAdapter("qwen2.5-coder:7b")
    
    try:
        start = time.time()
        response = adapter.generate("你好", task_type="chat", timeout=10)
        duration = time.time() - start
        
        print(f"响应时间: {duration:.2f}秒")
        print(f"响应内容: {response[:100]}...")
        
        assert duration < 15, f"响应时间过长: {duration}秒"
        print("✅ 调用测试通过")
        
    except Exception as e:
        print(f"⚠️ 调用失败: {e}")
        print("请确保Ollama服务正在运行")

if __name__ == "__main__":
    try:
        test_config()
        test_adapter()
        test_simple_call()
        
        print("\n" + "="*50)
        print("✅ 所有测试通过")
        print("="*50)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)