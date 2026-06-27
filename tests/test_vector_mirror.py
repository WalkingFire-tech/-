"""
测试向量检索器镜像配置
"""
import os
import sys

# 在导入任何模块之前设置环境变量
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['HUGGINGFACE_HUB_CACHE'] = os.path.expanduser('~/.cache/huggingface/hub')
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['TRANSFORMERS_VERBOSITY'] = 'error'

sys.path.insert(0, '.')

print("=" * 60)
print("测试向量检索器镜像配置")
print("=" * 60)

# 测试1: 检查环境变量
print("\n[测试1] 环境变量检查")
print(f"HF_ENDPOINT: {os.environ.get('HF_ENDPOINT', '未设置')}")
print(f"HUGGINGFACE_HUB_CACHE: {os.environ.get('HUGGINGFACE_HUB_CACHE', '未设置')}")
print(f"HF_HUB_DISABLE_TELEMETRY: {os.environ.get('HF_HUB_DISABLE_TELEMETRY', '未设置')}")

# 测试2: 导入向量检索器
print("\n[测试2] 导入向量检索器")
from core.vector_retriever import vector_retriever, EMBEDDING_AVAILABLE, hf_endpoint
print(f"EMBEDDING_AVAILABLE: {EMBEDDING_AVAILABLE}")
print(f"镜像站点: {hf_endpoint}")
print(f"模型已加载: {vector_retriever.model is not None}")

# 测试3: 测试向量编码
print("\n[测试3] 测试向量编码")
if vector_retriever.model:
    vec = vector_retriever.encode("测试文本")
    if vec:
        print(f"✓ 向量维度: {len(vec)}")
        print(f"✓ 前5个值: {vec[:5]}")
    else:
        print("✗ 编码失败")
else:
    print("✗ 模型未加载")

# 测试4: 测试混合检索
print("\n[测试4] 测试混合检索")
try:
    results = vector_retriever.hybrid_search("如何学习Python", top_k=3)
    print(f"✓ 检索结果: {len(results)}条")
    for i, r in enumerate(results[:3]):
        print(f"  [{i+1}] ID={r.get('id')} 得分={r.get('final_score', 0):.3f}")
except Exception as e:
    print(f"✗ 检索失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
print("\n配置说明:")
print("1. 镜像站点: https://hf-mirror.com")
print("2. 本地缓存: ~/.cache/huggingface/hub")
print("3. 已禁止连接官方站点 huggingface.co")
print("\n如果仍出现连接huggingface.co的错误，请:")
print("1. 重启后端服务")
print("2. 或使用 start_backend.bat 启动")