"""简化FAISS测试"""
print("\nFAISS配置测试\n")

# 1. 检查FAISS
try:
    import faiss
    print(f"✓ FAISS {faiss.__version__}")
except:
    print("✗ FAISS未安装: pip install faiss-cpu")

# 2. 检查sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    print("✓ sentence-transformers")
except:
    print("✗ 未安装: pip install sentence-transformers")

# 3. 测试向量检索器
try:
    from core.vector_retriever import VectorRetriever
    retriever = VectorRetriever()
    
    if retriever.model:
        print("✓ 向量检索器正常")
    else:
        print("⚠ 使用关键词检索（模型未加载）")
except Exception as e:
    print(f"⚠ 向量检索器: {e}")

print("\n配置建议:")
print("1. 首次使用需要下载模型（约400MB）")
print("2. 设置环境变量允许下载:")
print("   $env:STRICT_OFFLINE='false'")
print("3. 或手动下载模型:")
print("   python -c \"from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')\"")