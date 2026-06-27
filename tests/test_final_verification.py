"""
最终验证测试 - 确保没有huggingface.co连接
"""
import os
import sys
import io
from contextlib import redirect_stderr, redirect_stdout

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['OFFLINE_MODE'] = 'false'  # 测试在线模式

sys.path.insert(0, '.')

print("=" * 70)
print("最终验证测试 - 检查是否有huggingface.co连接")
print("=" * 70)

# 测试1: 导入镜像补丁
print("\n[测试1] 导入镜像补丁")
from core.hf_mirror_patch import *
print("✓ 镜像补丁已加载")

# 测试2: 导入向量检索器并捕获输出
print("\n[测试2] 导入向量检索器")
output = io.StringIO()
try:
    with redirect_stdout(output), redirect_stderr(output):
        from core.vector_retriever import vector_retriever, EMBEDDING_AVAILABLE
    
    log_output = output.getvalue()
    
    # 检查是否有huggingface.co连接
    if 'huggingface.co' in log_output and 'Connection to huggingface.co' in log_output:
        print("✗ 检测到 huggingface.co 连接尝试！")
        print("\n日志输出:")
        print(log_output)
    else:
        print("✓ 未检测到 huggingface.co 连接")
        
    # 检查是否使用镜像
    if 'hf-mirror.com' in log_output or '使用镜像站点' in log_output:
        print("✓ 使用镜像站点")
    else:
        print("⚠ 未检测到镜像站点日志")
        
    print(f"\n模型状态: EMBEDDING_AVAILABLE={EMBEDDING_AVAILABLE}")
    print(f"模型加载: {vector_retriever.model is not None}")
    
except Exception as e:
    print(f"✗ 导入失败: {e}")
    print(output.getvalue())

# 测试3: 测试向量编码（如果模型已加载）
print("\n[测试3] 测试向量编码")
if vector_retriever.model:
    try:
        vec = vector_retriever.encode("测试文本编码")
        if vec:
            print(f"✓ 向量编码成功，维度: {len(vec)}")
        else:
            print("✗ 向量编码失败")
    except Exception as e:
        print(f"✗ 编码失败: {e}")
else:
    print("⚠ 模型未加载，跳过编码测试")

# 测试4: 检查huggingface_hub配置
print("\n[测试4] 检查huggingface_hub配置")
import huggingface_hub.constants as c
print(f"HUGGINGFACE_CO_URL_HOME: {c.HUGGINGFACE_CO_URL_HOME}")
print(f"HUGGINGFACE_CO_URL_TEMPLATE: {c.HUGGINGFACE_CO_URL_TEMPLATE[:50]}...")

if 'hf-mirror.com' in c.HUGGINGFACE_CO_URL_HOME:
    print("✓ huggingface_hub使用镜像")
else:
    print("✗ huggingface_hub未使用镜像")

print("\n" + "=" * 70)
print("验证完成")
print("=" * 70)

print("\n结论:")
print("1. 如果未检测到 huggingface.co 连接 → 镜像配置成功 ✅")
print("2. 如果检测到 huggingface.co 连接 → 需要重启后端服务")
print("\n最终测试:")
print("运行 start_backend.bat 启动后端")
print("检查日志中是否出现 'Connection to huggingface.co' 错误")
print("如果没有错误，说明修复成功！")