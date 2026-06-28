"""
简单测试：只测试工具扫描
"""
import sys
import time
sys.path.insert(0, ".")

print("测试工具扫描...")

try:
    from tools.registry import registry
    start = time.time()
    tools = list(registry.list_tools())
    elapsed = time.time() - start
    print(f"✅ 工具扫描完成: {elapsed:.2f}秒, {len(tools)}个工具")
except Exception as e:
    print(f"❌ 工具扫描失败: {e}")