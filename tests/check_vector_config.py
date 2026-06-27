"""
检查向量检索器配置
"""
import os
import sys

print("=" * 60)
print("向量检索器配置检查")
print("=" * 60)

# 检查环境变量
print("\n[环境变量]")
print(f"HF_ENDPOINT: {os.environ.get('HF_ENDPOINT', '未设置')}")

# 检查代码配置
print("\n[代码配置]")
with open('core/vector_retriever.py', 'r', encoding='utf-8') as f:
    content = f.read()
    
if 'HF_ENDPOINT' in content and 'hf-mirror.com' in content:
    print("✓ 已配置镜像站点: hf-mirror.com")
else:
    print("✗ 未配置镜像站点")

if 'HUGGINGFACE_HUB_CACHE' in content:
    print("✓ 已配置缓存目录")
else:
    print("✗ 未配置缓存目录")

if 'cache_folder' in content:
    print("✓ 已配置cache_folder参数")
else:
    print("✗ 未配置cache_folder参数")

# 检查启动脚本
print("\n[启动脚本]")
if os.path.exists('start_backend.bat'):
    with open('start_backend.bat', 'r', encoding='utf-8') as f:
        bat_content = f.read()
    if 'HF_ENDPOINT' in bat_content and 'hf-mirror.com' in bat_content:
        print("✓ start_backend.bat 已配置环境变量")
    else:
        print("✗ start_backend.bat 未配置环境变量")
else:
    print("✗ start_backend.bat 不存在")

print("\n" + "=" * 60)
print("检查完成")
print("=" * 60)
print("\n修复内容:")
print("1. 在导入sentence_transformers前设置HF_ENDPOINT")
print("2. 设置HUGGINGFACE_HUB_CACHE缓存目录")
print("3. 使用cache_folder参数强制使用本地缓存")
print("4. 创建start_backend.bat启动脚本")
print("\n使用方法:")
print("1. 关闭当前后端服务")
print("2. 运行 start_backend.bat 启动")
print("3. 或手动设置环境变量后启动: set HF_ENDPOINT=https://hf-mirror.com && python backend/main.py")