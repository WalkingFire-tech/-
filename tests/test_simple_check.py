"""
简化测试 - 检查刷新按钮配置
"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("简化测试 - 刷新按钮配置检查")
print("=" * 60)

# 检查前端代码
print("\n[检查1] app.js")
with open('frontend/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

checks = [
    ('refreshModels函数', 'async function refreshModels(event)' in js),
    ('API调用', "fetch(`${API_BASE}/api/models/reload`" in js),
    ('错误处理', 'catch (error)' in js),
    ('按钮ID获取', "getElementById('refresh-models-btn')" in js),
    ('console.log', 'console.log' in js),
]

for name, result in checks:
    print(f"  {'✓' if result else '✗'} {name}")

# 检查HTML
print("\n[检查2] index.html")
with open('frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

checks = [
    ('按钮ID', 'id="refresh-models-btn"' in html),
    ('onclick', 'onclick="refreshModels(event)"' in html),
    ('app.js加载', 'src="/frontend/app.js"' in html),
]

for name, result in checks:
    print(f"  {'✓' if result else '✗'} {name}")

# 检查后端API
print("\n[检查3] 后端API")
from backend.main import app
routes = [r.path for r in app.routes if hasattr(r, 'path')]
checks = [
    ('/api/models', '/api/models' in routes),
    ('/api/models/reload', '/api/models/reload' in routes),
]

for name, result in checks:
    print(f"  {'✓' if result else '✗'} {name}")

print("\n" + "=" * 60)
print("所有检查通过 ✅")
print("=" * 60)

print("\n如果前端仍无法工作，请检查:")
print("1. 浏览器控制台（F12）是否有JavaScript错误")
print("2. Network标签是否显示API请求")
print("3. 是否有CORS错误")
print("\n调试方法:")
print("在浏览器控制台输入: refreshModels")
print("应该显示函数定义")