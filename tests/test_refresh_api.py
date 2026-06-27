"""
测试模型刷新API
"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("测试模型刷新API")
print("=" * 60)

# 测试1: 检查API端点
print("\n[测试1] 检查API端点")
from backend.main import app
routes = {}
for route in app.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        for method in route.methods:
            key = f"{method} {route.path}"
            routes[key] = route.name

if 'POST /api/models/reload' in routes:
    print(f"✓ POST /api/models/reload -> {routes['POST /api/models/reload']}")
else:
    print("✗ POST /api/models/reload 不存在")

if 'GET /api/models' in routes:
    print(f"✓ GET /api/models -> {routes['GET /api/models']}")
else:
    print("✗ GET /api/models 不存在")

# 测试2: 测试Ollama连接
print("\n[测试2] 测试Ollama连接")
try:
    import requests
    response = requests.get("http://localhost:11434/api/tags", timeout=3)
    if response.status_code == 200:
        models_data = response.json()
        models = models_data.get('models', [])
        print(f"✓ Ollama服务可用，检测到 {len(models)} 个模型:")
        for m in models:
            print(f"  - {m['name']}")
    else:
        print(f"✗ Ollama响应异常: {response.status_code}")
except Exception as e:
    print(f"✗ Ollama服务不可用: {e}")

# 测试3: 模拟刷新流程
print("\n[测试3] 模拟刷新流程")
try:
    from adapters.llm.ollama_adapter import OllamaAdapter
    import requests
    
    # 获取Ollama模型列表
    response = requests.get("http://localhost:11434/api/tags", timeout=3)
    if response.status_code == 200:
        models_data = response.json()
        ollama_models = [m['name'] for m in models_data.get('models', [])]
        
        # 模拟动态加载
        test_adapters = {}
        added = []
        for model_name in ollama_models[:2]:  # 只测试前2个
            try:
                test_adapters[model_name] = OllamaAdapter(model_name=model_name)
                added.append(model_name)
                print(f"  ✓ 成功加载: {model_name}")
            except Exception as e:
                print(f"  ✗ 加载失败: {model_name} - {e}")
        
        print(f"\n✓ 模拟刷新成功，加载了 {len(added)} 个模型")
    else:
        print("✗ Ollama服务不可用")
        
except Exception as e:
    print(f"✗ 模拟刷新失败: {e}")

# 测试4: 检查前端代码
print("\n[测试4] 检查前端代码")
with open('frontend/app.js', 'r', encoding='utf-8') as f:
    js = f.read()
    
if 'async function refreshModels(event)' in js:
    print("✓ refreshModels函数已定义（带event参数）")
elif 'async function refreshModels()' in js:
    print("⚠ refreshModels函数已定义（无event参数）")
else:
    print("✗ refreshModels函数未定义")

if 'document.getElementById(\'refresh-models-btn\')' in js:
    print("✓ 已添加按钮ID获取逻辑")
else:
    print("⚠ 未找到按钮ID获取逻辑")

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()
    
if 'id="refresh-models-btn"' in html:
    print("✓ 刷新按钮已添加ID")
else:
    print("✗ 刷新按钮未添加ID")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
print("\n修复内容:")
print("1. 给刷新按钮添加ID: refresh-models-btn")
print("2. refreshModels函数添加event参数")
print("3. 添加错误处理和用户提示")
print("4. 添加详细日志输出")
print("\n使用方法:")
print("1. 打开前端页面")
print("2. 点击'🔄 刷新'按钮")
print("3. 查看控制台日志和提示信息")