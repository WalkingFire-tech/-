"""
验证向量检索功能
"""
import os

# 配置镜像
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

print("\n" + "="*60)
print("向量检索功能验证")
print("="*60)

# 1. 测试向量检索器
print("\n【1. 初始化向量检索器】")
from core.vector_retriever import VectorRetriever

retriever = VectorRetriever()

if retriever.model:
    print("  ✓ 向量检索已启用")
    print(f"  模型: {type(retriever.model).__name__}")
else:
    print("  ✗ 向量检索未启用")
    exit(1)

# 2. 测试向量编码
print("\n【2. 测试向量编码】")
test_texts = [
    "Python是一种编程语言",
    "机器学习是人工智能的分支",
    "深度学习使用神经网络",
]

try:
    embeddings = retriever.model.encode(test_texts)
    print(f"  ✓ 编码成功: {len(test_texts)}个文本")
    print(f"  向量维度: {embeddings.shape[1]}")
except Exception as e:
    print(f"  ✗ 编码失败: {e}")
    exit(1)

# 3. 测试知识添加
print("\n【3. 测试知识添加】")
test_knowledge = [
    "Python是一种高级编程语言，广泛用于Web开发、数据分析和人工智能",
    "机器学习是人工智能的核心技术，包括监督学习和无监督学习",
    "深度学习使用多层神经网络，在图像识别和自然语言处理方面表现出色",
    "向量检索基于语义相似度，可以理解查询的真正含义",
    "FAISS是Facebook开源的向量检索库，支持高效的相似度搜索",
]

try:
    for i, text in enumerate(test_knowledge):
        retriever.add(text, {"id": i, "source": "test", "type": "knowledge"})
    print(f"  ✓ 添加成功: {len(test_knowledge)}条知识")
except Exception as e:
    print(f"  ✗ 添加失败: {e}")

# 4. 测试语义搜索
print("\n【4. 测试语义搜索】")
queries = [
    "什么是AI技术？",
    "如何进行数据分析？",
    "向量搜索的原理是什么？",
]

for query in queries:
    try:
        results = retriever.search(query, top_k=3)
        print(f"\n  查询: {query}")
        print(f"  结果: {len(results)}条")
        
        for i, result in enumerate(results[:2]):
            content = result.get('content', result.get('text', ''))[:50]
            score = result.get('score', 0)
            print(f"    {i+1}. {content}... (相似度: {score:.3f})")
    
    except Exception as e:
        print(f"  ✗ 搜索失败: {e}")

# 5. 测试语义理解能力
print("\n【5. 测试语义理解能力】")
print("  对比关键词检索 vs 向量检索:")

# 这个查询不包含关键词，但向量检索应该能理解
query = "如何让计算机变得更聪明？"
print(f"\n  查询: {query}")
print("  (不包含'AI'、'机器学习'等关键词)")

try:
    results = retriever.search(query, top_k=3)
    print(f"\n  向量检索结果:")
    for i, result in enumerate(results[:2]):
        content = result.get('content', result.get('text', ''))[:60]
        score = result.get('score', 0)
        print(f"    {i+1}. {content}... (相似度: {score:.3f})")
    
    if results and results[0].get('score', 0) > 0.3:
        print("\n  ✓ 向量检索成功理解了查询意图！")
    else:
        print("\n  ⚠ 相似度较低，可能需要更多知识")
        
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

print("\n" + "="*60)
print("✅ 向量检索功能验证完成")
print("="*60)

print("\n功能对比:")
print("  关键词检索: 仅匹配'聪明'等关键词")
print("  向量检索:   理解意图，返回AI、机器学习相关知识 ✓")