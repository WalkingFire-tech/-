"""简单测试向量检索"""
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

print("\n测试向量检索\n")

try:
    from core.vector_retriever import VectorRetriever
    retriever = VectorRetriever()
    
    if retriever.model:
        print("✓ 向量检索已启用")
        
        # 测试搜索
        results = retriever.search("Python编程", top_k=3)
        print(f"✓ 搜索成功: {len(results)}条结果")
        
    else:
        print("⚠ 使用关键词检索")
        
except Exception as e:
    print(f"错误: {e}")