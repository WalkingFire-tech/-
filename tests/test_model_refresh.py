"""
测试本地模型动态刷新功能
"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("测试本地模型动态刷新功能")
print("=" * 60)

# 测试1: 检查API端点
print("\n[测试1] 检查API端点定义")
from backend.main import app
routes = [route.path for route in app.routes]
model_routes = [r for r in routes if '/models' in r]
print(f"✓ 模型相关API端点: {len(model_routes)}个")
for route in sorted(model_routes):
    print(f"  - {route}")

# 测试2: 检查刷新功能
print("\n[测试2] 检查刷新功能")
import inspect
from backend.main import reload_models
sig = inspect.signature(reload_models)
print(f"✓ reload_models函数签名: {sig}")
print(f"✓ 函数文档: {reload_models.__doc__}")

# 测试3: 模拟刷新（不启动服务）
print("\n[测试3] 模拟刷新流程")
try:
    import requests
    response = requests.get("http://localhost:11434/api/tags", timeout=2)
    if response.status_code == 200:
        models_data = response.json()
        models = models_data.get('models', [])
        print(f"✓ Ollama服务可用")
        print(f"✓ 检测到 {len(models)} 个模型:")
        for m in models:
            print(f"  - {m['name']} (大小: {m.get('size', 0) / 1024**3:.2f} GB)")
    else:
        print(f"⚠ Ollama响应异常: {response.status_code}")
except Exception as e:
    print(f"⚠ Ollama服务未启动: {e}")
    print("  提示: 启动Ollama服务后，前端可以自动检测模型")

# 测试4: 检查前端刷新按钮
print("\n[测试4] 检查前端刷新按钮")
with open('frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()
    if 'refreshModels()' in html:
        print("✓ 前端已添加刷新按钮")
    else:
        print("✗ 前端未找到刷新按钮")

# 测试5: 检查自动刷新功能
print("\n[测试5] 检查自动刷新功能")
with open('frontend/app.js', 'r', encoding='utf-8') as f:
    js = f.read()
    if 'startAutoRefresh' in js:
        print("✓ 前端已添加自动刷新功能")
        # 提取刷新间隔
        import re
        match = re.search(r'startAutoRefresh\((\d+)\)', js)
        if match:
            interval = match.group(1)
            print(f"  刷新间隔: {interval}秒")
    else:
        print("✗ 前端未找到自动刷新功能")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
print("\n功能说明:")
print("1. 手动刷新: 点击'🔄 刷新'按钮立即检测新模型")
print("2. 自动刷新: 每30秒自动检测Ollama中的新模型")
print("3. 无需重启服务器即可使用新拉取的模型")
print("\n使用方法:")
print("1. 启动Ollama服务: ollama serve")
print("2. 拉取新模型: ollama pull <model-name>")
print("3. 前端自动检测到新模型，或点击刷新按钮")