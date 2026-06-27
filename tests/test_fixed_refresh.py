"""
测试修复后的刷新功能（Ollama未启动场景）
"""
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import sys
sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

print("=" * 60)
print("测试修复后的刷新功能")
print("=" * 60)

# 测试刷新API（Ollama可能未启动）
print("\n[测试1] 调用刷新API")
response = client.post("/api/models/reload")
print(f"状态: {response.status_code}")
data = response.json()
print(f"成功: {data.get('success')}")
print(f"总计: {data.get('total')}")
print(f"新增: {data.get('added', [])}")
print(f"消息: {data.get('message', '')}")
print(f"Ollama状态: {data.get('ollama_status', 'unknown')}")

if data.get('hint'):
    print(f"提示: {data.get('hint')}")

# 验证：即使Ollama未启动，也应该返回success=True
if data.get('success'):
    print("\n✅ 刷新API正常工作（优雅降级）")
    print("   即使Ollama未启动，也不会报错")
else:
    print("\n❌ 刷新API失败")

# 获取模型列表
print("\n[测试2] 获取模型列表")
response = client.get("/api/models")
data = response.json()
print(f"模型数: {len(data.get('models', []))}")
for m in data.get('models', []):
    print(f"  - {m['name']}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)

print("\n修复内容:")
print("1. 后端优雅降级：Ollama未启动时返回当前模型")
print("2. 返回ollama_status字段：online/offline/error")
print("3. 前端根据状态显示不同提示")
print("4. 不再显示错误弹窗，改为友好提示")
print("\n使用方法:")
print("1. 正常情况：Ollama运行，刷新检测新模型")
print("2. Ollama未启动：显示当前已加载模型，提示启动Ollama")
print("3. 点击刷新按钮不会报错")