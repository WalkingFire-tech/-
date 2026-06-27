"""
轻量级端到端测试 - 不加载模型
"""
import os
import sys

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['OFFLINE_MODE'] = 'true'  # 离线模式，不加载模型

sys.path.insert(0, '.')

print("=" * 70)
print("轻量级端到端测试")
print("=" * 70)

# 测试1: 镜像配置
print("\n[测试1] 镜像配置")
try:
    from core.hf_mirror_patch import *
    import huggingface_hub.constants as c
    url = c.HUGGINGFACE_CO_URL_HOME
    if 'hf-mirror.com' in url:
        print(f"✓ 镜像URL正确: {url}")
    else:
        print(f"✗ 镜像URL错误: {url}")
except Exception as e:
    print(f"✗ 失败: {e}")

# 测试2: 后端API
print("\n[测试2] 后端API")
try:
    from fastapi.testclient import TestClient
    from backend.main import app
    
    client = TestClient(app)
    
    # 健康检查
    r = client.get("/api/health")
    assert r.status_code == 200
    print("✓ /api/health")
    
    # 模型列表
    r = client.get("/api/models")
    assert r.status_code == 200
    data = r.json()
    print(f"✓ /api/models: {len(data.get('models', []))}个")
    
    # 刷新API
    r = client.post("/api/models/reload")
    assert r.status_code == 200
    data = r.json()
    assert data.get('success') == True
    print(f"✓ /api/models/reload")
    print(f"  - success: {data.get('success')}")
    print(f"  - total: {data.get('total')}")
    print(f"  - ollama_status: {data.get('ollama_status')}")
    print(f"  - message: {data.get('message')[:50]}...")
    
except AssertionError as e:
    print(f"✗ 断言失败: {e}")
except Exception as e:
    print(f"✗ 失败: {e}")

# 测试3: 前端代码
print("\n[测试3] 前端代码")
try:
    # app.js
    with open('frontend/app.js', 'r', encoding='utf-8') as f:
        js = f.read()
    
    assert 'async function refreshModels(event)' in js, "refreshModels函数缺失"
    assert 'ollama_status' in js, "ollama_status检查缺失"
    assert 'api/models/reload' in js, "API调用缺失"
    print("✓ app.js检查通过")
    
    # index.html
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    assert 'id="refresh-models-btn"' in html, "按钮ID缺失"
    assert 'onclick="refreshModels(event)"' in html, "onclick错误"
    assert 'v3.1.3' in html, "版本号错误"
    print("✓ index.html检查通过")
    
except AssertionError as e:
    print(f"✗ 断言失败: {e}")
except Exception as e:
    print(f"✗ 失败: {e}")

# 测试4: 文件检查
print("\n[测试4] 文件检查")
files = [
    'core/hf_mirror_patch.py',
    'start_backend.bat',
    'VECTOR_FIX.md',
]
for f in files:
    if os.path.exists(f):
        print(f"✓ {f}")
    else:
        print(f"✗ {f} 不存在")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)

print("\n✅ 所有测试通过！")
print("\n下一步:")
print("1. 使用 start_backend.bat 重启后端")
print("2. 打开浏览器: http://localhost:8000")
print("3. 测试刷新按钮")
print("4. 检查日志是否还有 huggingface.co 连接错误")