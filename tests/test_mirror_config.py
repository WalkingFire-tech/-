"""
测试镜像配置是否生效
"""
import os
import sys

# 在导入前设置环境变量
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

sys.path.insert(0, '.')

print("=" * 60)
print("测试镜像配置")
print("=" * 60)

# 测试1: 检查环境变量
print("\n[测试1] 环境变量")
print(f"HF_ENDPOINT: {os.environ.get('HF_ENDPOINT', '未设置')}")

# 测试2: 导入镜像补丁
print("\n[测试2] 导入镜像补丁")
try:
    from core.hf_mirror_patch import *
    print("✓ 镜像补丁导入成功")
except Exception as e:
    print(f"✗ 镜像补丁导入失败: {e}")

# 测试3: 检查huggingface_hub配置
print("\n[测试3] huggingface_hub配置")
try:
    import huggingface_hub.constants as constants
    print(f"HUGGINGFACE_CO_URL_HOME: {constants.HUGGINGFACE_CO_URL_HOME}")
    print(f"HUGGINGFACE_CO_URL_TEMPLATE: {constants.HUGGINGFACE_CO_URL_TEMPLATE}")
    
    if 'hf-mirror.com' in constants.HUGGINGFACE_CO_URL_HOME:
        print("✓ 镜像配置成功")
    else:
        print("✗ 镜像配置失败")
except Exception as e:
    print(f"✗ 检查失败: {e}")

# 测试4: 导入向量检索器
print("\n[测试4] 导入向量检索器")
try:
    from core.vector_retriever import vector_retriever, EMBEDDING_AVAILABLE
    print(f"EMBEDDING_AVAILABLE: {EMBEDDING_AVAILABLE}")
    print(f"模型已加载: {vector_retriever.model is not None}")
    
    if vector_retriever.model:
        print("✓ 向量检索器加载成功")
    else:
        print("⚠ 向量检索器未加载模型")
except Exception as e:
    print(f"✗ 导入失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)

print("\n如果仍出现huggingface.co连接错误，请:")
print("1. 重启后端服务")
print("2. 检查是否有其他模块在导入前连接官方站点")
print("3. 使用 start_backend.bat 启动")