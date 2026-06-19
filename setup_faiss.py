"""
FAISS向量检索配置和测试
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

print("\n" + "="*60)
print("FAISS向量检索配置")
print("="*60)

# 1. 检查依赖
print("\n【1. 检查依赖】")
try:
    import faiss
    print(f"  ✓ FAISS: {faiss.__version__}")
except ImportError:
    print("  ✗ FAISS未安装")
    print("    安装: pip install faiss-cpu")
    sys.exit(1)

try:
    from sentence_transformers import SentenceTransformer
    print("  ✓ sentence-transformers")
except ImportError:
    print("  ✗ sentence-transformers未安装")
    print("    安装: pip install sentence-transformers")
    sys.exit(1)

# 2. 下载/加载模型
print("\n【2. 加载向量模型】")
print("  首次使用需要下载约400MB模型，请耐心等待...")

try:
    import os
    # 允许在线下载
    os.environ.pop('HF_HUB_OFFLINE', None)
    os.environ.pop('TRANSFORMERS_OFFLINE', None)
    
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    print("  ✓ 模型加载成功")
    
    # 测试编码
    test_text = "这是一个测试句子"
    embedding = model.encode(test_text)
    print(f"  ✓ 向量维度: {len(embedding)}")
    
except Exception as e:
    print(f"  ✗ 模型加载失败: {e}")
    sys.exit(1)

# 3. 测试FAISS索引
print("\n【3. 测试FAISS索引】")
try:
    import numpy as np
    
    # 创建测试向量
    dimension = 384
    n_vectors = 100
    
    # 生成随机向量
    vectors = np.random.random((n_vectors, dimension)).astype('float32')
    
    # 创建FAISS索引
    index = faiss.IndexFlatL2(dimension)
    index.add(vectors)
    
    print(f"  ✓ 索引创建成功: {n_vectors}个向量")
    
    # 测试搜索
    query = np.random.random((1, dimension)).astype('float32')
    k = 5
    distances, indices = index.search(query, k)
    
    print(f"  ✓ 搜索成功: 返回{k}个结果")
    
except Exception as e:
    print(f"  ✗ FAISS测试失败: {e}")
    sys.exit(1)

# 4. 初始化向量检索器
print("\n【4. 初始化向量检索器】")
try:
    from core.vector_retriever import VectorRetriever
    
    retriever = VectorRetriever()
    
    if retriever.model is not None:
        print("  ✓ 向量检索器初始化成功")
    else:
        print("  ⚠ 向量检索器使用关键词检索（模型未加载）")
    
except Exception as e:
    print(f"  ✗ 向量检索器初始化失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 5. 测试知识检索
print("\n【5. 测试知识检索】")
try:
    # 添加测试知识
    test_knowledge = [
        "Python是一种编程语言",
        "机器学习是人工智能的分支",
        "深度学习使用神经网络",
        "向量检索基于语义相似度",
        "FAISS是Facebook的向量检索库"
    ]
    
    for i, text in enumerate(test_knowledge):
        retriever.add(text, {"id": i, "source": "test"})
    
    print(f"  ✓ 添加{len(test_knowledge)}条测试知识")
    
    # 搜索测试
    results = retriever.search("什么是机器学习", top_k=3)
    
    print(f"  ✓ 搜索成功: 返回{len(results)}条结果")
    for i, result in enumerate(results):
        print(f"    {i+1}. {result['content'][:50]}... (得分: {result.get('score', 0):.2f})")
    
except Exception as e:
    print(f"  ⚠ 知识检索测试失败: {e}")

print("\n" + "="*60)
print("✅ FAISS向量检索配置完成")
print("="*60)

print("\n使用说明:")
print("  • 向量检索已启用，将使用语义相似度搜索")
print("  • 首次加载模型需要下载约400MB")
print("  • 如需离线使用，设置环境变量: STRICT_OFFLINE=true")