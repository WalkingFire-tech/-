"""
完整端到端测试 - 向量检索器和刷新功能
"""
import os
import sys

# 在导入前设置环境变量
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HUGGINGFACE_HUB_CACHE'] = os.path.expanduser('~/.cache/huggingface/hub')
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

sys.path.insert(0, '.')

print("=" * 70)
print("完整端到端测试 - 向量检索器和刷新功能")
print("=" * 70)

# 测试1: 镜像配置
print("\n[测试1] 镜像配置检查")
try:
    from core.hf_mirror_patch import *
    print("✓ 镜像补丁导入成功")
    
    import huggingface_hub.constants as constants
    if 'hf-mirror.com' in constants.HUGGINGFACE_CO_URL_HOME:
        print(f"✓ 镜像URL: {constants.HUGGINGFACE_CO_URL_HOME}")
    else:
        print(f"✗ 镜像URL错误: {constants.HUGGINGFACE_CO_URL_HOME}")
except Exception as e:
    print(f"✗ 镜像配置失败: {e}")

# 测试2: 向量检索器
print("\n[测试2] 向量检索器")
try:
    from core.vector_retriever import vector_retriever, EMBEDDING_AVAILABLE
    print(f"EMBEDDING_AVAILABLE: {EMBEDDING_AVAILABLE}")
    print(f"模型已加载: {vector_retriever.model is not None}")
    
    if vector_retriever.model:
        # 测试向量编码
        vec = vector_retriever.encode("测试文本")
        if vec:
            print(f"✓ 向量编码成功，维度: {len(vec)}")
        else:
            print("✗ 向量编码失败")
    else:
        print("⚠ 模型未加载，跳过编码测试")
except Exception as e:
    print(f"✗ 向量检索器测试失败: {e}")

# 测试3: 后端API
print("\n[测试3] 后端API")
try:
    from fastapi.testclient import TestClient
    from backend.main import app
    
    client = TestClient(app)
    
    # 测试健康检查
    response = client.get("/api/health")
    print(f"✓ /api/health: {response.status_code}")
    
    # 测试模型列表
    response = client.get("/api/models")
    data = response.json()
    print(f"✓ /api/models: {len(data.get('models', []))}个模型")
    
    # 测试刷新API
    response = client.post("/api/models/reload")
    data = response.json()
    print(f"✓ /api/models/reload: success={data.get('success')}")
    print(f"  消息: {data.get('message', '')}")
    print(f"  Ollama状态: {data.get('ollama_status', 'unknown')}")
    
except Exception as e:
    print(f"✗ 后端API测试失败: {e}")

# 测试4: 前端代码
print("\n[测试4] 前端代码检查")
try:
    with open('frontend/app.js', 'r', encoding='utf-8') as f:
        js = f.read()
    
    checks = [
        ('refreshModels函数', 'async function refreshModels(event)' in js),
        ('API调用', 'api/models/reload' in js),
        ('ollama_status检查', 'ollama_status' in js),
        ('版本标识', 'APP_VERSION' in js),
    ]
    
    for name, result in checks:
        print(f"  {'✓' if result else '✗'} {name}")
        
    with open('frontend/index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    if 'v3.1.3' in html:
        print("  ✓ 版本号: v3.1.3")
    else:
        print("  ✗ 版本号错误")
        
except Exception as e:
    print(f"✗ 前端代码检查失败: {e}")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)

print("\n总结:")
print("1. 镜像配置: 检查是否使用 hf-mirror.com")
print("2. 向量检索器: 检查模型是否加载")
print("3. 后端API: 检查刷新功能是否正常")
print("4. 前端代码: 检查刷新按钮是否配置正确")
print("\n下一步:")
print("1. 如果所有测试通过，重启后端服务")
print("2. 使用 start_backend.bat 启动")
print("3. 打开浏览器测试刷新按钮")