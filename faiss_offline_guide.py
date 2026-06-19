"""
离线向量检索方案 - 使用更小的模型或手动下载
"""

print("""
FAISS向量检索配置方案
====================

问题：无法连接到HuggingFace下载模型

解决方案：

【方案1】使用中国镜像站点（推荐）
--------------------------------
$env:HF_ENDPOINT = "https://hf-mirror.com"
python setup_faiss_mirror.py


【方案2】使用更小的模型
--------------------------------
修改 core/vector_retriever.py:

将:
  model_name = 'paraphrase-multilingual-MiniLM-L12-v2'  # 400MB

改为:
  model_name = 'paraphrase-MiniLM-L3-v2'  # 60MB

或:
  model_name = 'all-MiniLM-L6-v2'  # 80MB


【方案3】手动下载模型
--------------------------------
1. 访问镜像站点:
   https://hf-mirror.com/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

2. 下载以下文件:
   - config.json
   - pytorch_model.bin
   - tokenizer.json
   - tokenizer_config.json
   - vocab.txt
   - modules.json
   - sentence_bert_config.json

3. 放到本地目录:
   C:\\Users\\Administrator\\.cache\\huggingface\\hub\\
   models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2\\
   snapshots\\<commit-hash>\\


【方案4】使用关键词检索（降级方案）
--------------------------------
系统会自动降级到关键词检索，无需向量模型。

优点：
- 无需下载
- 启动快速
- 无网络依赖

缺点：
- 仅匹配关键词
- 无法理解语义


【推荐配置】
--------------------------------
1. 首先尝试镜像站点（方案1）
2. 如果仍然失败，使用更小的模型（方案2）
3. 如果网络完全不通，使用关键词检索（方案4）


当前系统状态：
- FAISS: ✓ 已安装
- sentence-transformers: ✓ 已安装
- 模型: ✗ 未下载
- 降级方案: ✓ 关键词检索可用
""")