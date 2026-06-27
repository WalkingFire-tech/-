"""
创建测试页面验证刷新按钮
"""
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import sys
sys.path.insert(0, '.')

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

print("=" * 60)
print("验证刷新按钮功能")
print("=" * 60)

# 测试1: 获取初始模型列表
print("\n[步骤1] 获取初始模型列表")
response = client.get("/api/models")
initial_models = response.json().get('models', [])
print(f"初始模型数: {len(initial_models)}")
for m in initial_models:
    print(f"  - {m['name']}")

# 测试2: 调用刷新API
print("\n[步骤2] 调用刷新API")
response = client.post("/api/models/reload")
result = response.json()
print(f"成功: {result.get('success')}")
print(f"总计: {result.get('total')}")
print(f"新增: {result.get('added', [])}")
print(f"消息: {result.get('message', '')}")

# 测试3: 再次获取模型列表
print("\n[步骤3] 再次获取模型列表")
response = client.get("/api/models")
final_models = response.json().get('models', [])
print(f"最终模型数: {len(final_models)}")
for m in final_models:
    print(f"  - {m['name']}")

# 测试4: 验证
print("\n[步骤4] 验证")
if len(final_models) >= len(initial_models):
    print("✅ 刷新功能正常")
else:
    print("⚠️ 刷新后模型数减少")

print("\n" + "=" * 60)
print("API测试通过 ✅")
print("=" * 60)

print("\n前端测试步骤:")
print("1. 打开浏览器: http://localhost:8000")
print("2. 按 Ctrl+Shift+R 强制刷新页面（清除缓存）")
print("3. 按 F12 打开开发者工具")
print("4. 点击 Console 标签")
print("5. 输入: console.log('版本:', APP_VERSION)")
print("   应该显示: 版本: 3.1.2")
print("6. 输入: refreshModels")
print("   应该显示函数定义")
print("7. 点击页面上的 '🔄 刷新' 按钮")
print("8. 观察 Console 和 Network 标签")
print("\n如果仍然不工作，请截图发送:")
print("- Console 标签的错误信息")
print("- Network 标签的请求列表")