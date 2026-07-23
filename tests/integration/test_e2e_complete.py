"""
完整端到端测试 - 模拟浏览器点击刷新按钮
"""
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import sys
sys.path.insert(0, '.')

print("=" * 60)
print("完整端到端测试 - 刷新按钮功能")
print("=" * 60)

# 测试1: 检查后端路由
print("\n[测试1] 检查后端路由")
from backend.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

# 测试健康检查
print("测试 GET /api/health")
response = client.get("/api/health")
print(f"状态: {response.status_code}")
print(f"响应: {response.json()}")

# 测试模型列表
print("\n测试 GET /api/models")
response = client.get("/api/models")
print(f"状态: {response.status_code}")
data = response.json()
print(f"模型数: {len(data.get('models', []))}")
for m in data.get('models', []):
    print(f"  - {m['name']} ({m['type']})")

# 测试模型刷新
print("\n测试 POST /api/models/reload")
response = client.post("/api/models/reload")
print(f"状态: {response.status_code}")
data = response.json()
print(f"成功: {data.get('success')}")
print(f"总计: {data.get('total')}")
print(f"新增: {data.get('added', [])}")
print(f"消息: {data.get('message', '')}")

# 再次获取模型列表
print("\n再次测试 GET /api/models")
response = client.get("/api/models")
data = response.json()
print(f"模型数: {len(data.get('models', []))}")
for m in data.get('models', []):
    print(f"  - {m['name']} ({m['type']})")

# 测试2: 检查前端代码
print("\n[测试2] 检查前端代码")
with open('frontend/app.js', 'r', encoding='utf-8') as f:
    js_content = f.read()

# 检查refreshModels函数
if 'async function refreshModels(event)' in js_content:
    print("✓ refreshModels函数定义正确（带event参数）")
else:
    print("✗ refreshModels函数定义错误")

# 检查API调用
if "fetch(`${API_BASE}/api/models/reload`" in js_content:
    print("✓ API调用代码存在")
else:
    print("✗ API调用代码不存在")

# 检查错误处理
if 'catch (error)' in js_content and 'console.error' in js_content:
    print("✓ 错误处理代码存在")
else:
    print("✗ 错误处理代码不存在")

# 测试3: 检查HTML
print("\n[测试3] 检查HTML")
with open('frontend/index.html', 'r', encoding='utf-8') as f:
    html_content = f.read()

# 检查按钮
if 'id="refresh-models-btn"' in html_content:
    print("✓ 刷新按钮ID存在")
else:
    print("✗ 刷新按钮ID不存在")

if 'onclick="refreshModels(event)"' in html_content:
    print("✓ 刷新按钮onclick正确（传递event）")
else:
    print("✗ 刷新按钮onclick错误")

# 检查app.js加载
if 'src="/frontend/app.js"' in html_content:
    print("✓ app.js加载路径正确")
else:
    print("✗ app.js加载路径错误")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)

print("\n诊断建议:")
print("1. 打开浏览器开发者工具（F12）")
print("2. 查看Console标签是否有错误")
print("3. 点击刷新按钮，查看Network标签的请求")
print("4. 检查是否有CORS错误或404错误")
print("\n如果按钮点击无反应，可能原因:")
print("- JavaScript加载失败")
print("- 函数未定义")
print("- event对象未正确传递")
print("- API请求被阻止（CORS）")