"""快速测试向量检索"""
import os

# 配置镜像
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
os.environ['EMBEDDING_MODEL'] = 'paraphrase-MiniLM-L3-v2'  # 小模型(60MB)

print("\n向量检索测试")
print("="*40)
print(f"镜像: {os.environ['HF_ENDPOINT']}")
print(f"模型: {os.environ['EMBEDDING_MODEL']}")
print("="*40)

try:
    from core.vector_retriever import VectorRetriever
    retriever = VectorRetriever()
    
    if retriever.model:
        print("\n✓ 向量检索已启用")
        print("  使用语义相似度搜索")
    else:
        print("\n⚠ 使用关键词检索")
        print("  向量模型未加载")
    
    # 测试搜索
    print("\n测试搜索...")
    results = retriever.search("Python编程", top_k=3)
    print(f"✓ 搜索成功: {len(results)}条结果")
    
except Exception as e:
    print(f"\n✗ 错误: {e}")
    print("\n降级方案: 系统将使用关键词检索")