"""
FAISS向量检索配置 - 支持镜像站点
解决HuggingFace连接超时问题
"""
import os
import sys
from pathlib import Path

print("\n" + "="*60)
print("FAISS向量检索配置（支持镜像）")
print("="*60)

# 配置HuggingFace镜像
print("\n【配置镜像站点】")
print("可用的镜像站点：")
print("  1. HF-Mirror (中国镜像): https://hf-mirror.com")
print("  2. 官方站点: https://huggingface.co")

# 设置镜像
mirror_url = os.getenv("HF_ENDPOINT", "https://hf-mirror.com")
print(f"\n当前镜像: {mirror_url}")

# 设置环境变量
os.environ['HF_ENDPOINT'] = mirror_url
print(f"✓ 已设置 HF_ENDPOINT={mirror_url}")

# 检查依赖
print("\n【检查依赖】")
try:
    import faiss
    print(f"✓ FAISS: {faiss.__version__}")
except ImportError:
    print("✗ FAISS未安装: pip install faiss-cpu")
    sys.exit(1)

try:
    from sentence_transformers import SentenceTransformer
    print("✓ sentence-transformers")
except ImportError:
    print("✗ 未安装: pip install sentence-transformers")
    sys.exit(1)

# 加载模型
print("\n【加载向量模型】")
print(f"使用镜像: {mirror_url}")
print("模型: paraphrase-multilingual-MiniLM-L12-v2 (约400MB)")
print("\n开始下载（首次使用）...")

try:
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    print("\n✓ 模型加载成功！")
    
    # 测试编码
    test_text = "这是一个测试句子"
    embedding = model.encode(test_text)
    print(f"✓ 向量维度: {len(embedding)}")
    
    # 保存模型信息
    print(f"\n模型已缓存到: {Path.home() / '.cache' / 'huggingface' / 'hub'}")
    
except Exception as e:
    print(f"\n✗ 模型加载失败: {e}")
    print("\n解决方案：")
    print("1. 使用镜像站点（推荐）：")
    print("   $env:HF_ENDPOINT='https://hf-mirror.com'")
    print("   python setup_faiss_mirror.py")
    print("\n2. 手动下载模型：")
    print("   访问: https://hf-mirror.com/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    print("   下载所有文件到: ~/.cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2")
    print("\n3. 使用更小的模型：")
    print("   修改代码使用 'paraphrase-MiniLM-L3-v2' (约60MB)")
    print("\n4. 使用关键词检索（降级方案）：")
    print("   系统会自动降级到关键词检索，无需向量模型")
    sys.exit(1)

# 测试FAISS
print("\n【测试FAISS索引】")
try:
    import numpy as np
    
    dimension = 384
    vectors = np.random.random((10, dimension)).astype('float32')
    
    index = faiss.IndexFlatL2(dimension)
    index.add(vectors)
    
    query = np.random.random((1, dimension)).astype('float32')
    distances, indices = index.search(query, 5)
    
    print("✓ FAISS索引测试通过")
    
except Exception as e:
    print(f"✗ FAISS测试失败: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✅ FAISS向量检索配置完成！")
print("="*60)

print("\n使用说明：")
print("• 向量检索已启用")
print("• 模型已缓存，下次启动无需重新下载")
print("• 如需更换镜像，设置环境变量：")
print("  $env:HF_ENDPOINT='https://hf-mirror.com'")