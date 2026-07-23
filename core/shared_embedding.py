"""
共享嵌入模型管理器 - 避免重复加载
"""
import os

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

from loguru import logger

_model = None
_model_name = None

def get_embedding_model():
    """获取共享的嵌入模型实例（带超时保护，失败立即降级）"""
    global _model, _model_name
    
    if _model is not None:
        return _model
    
    try:
        from sentence_transformers import SentenceTransformer
        
        model_name = os.getenv(
            "EMBEDDING_MODEL", 
            "paraphrase-multilingual-MiniLM-L12-v2"
        )
        
        if _model_name == model_name:
            return _model
        
        logger.info(f"加载共享嵌入模型: {model_name}")
        
        cache_folder = os.path.expanduser('~/.cache/huggingface/hub')
        
        import threading
        load_result = {"model": None, "error": None}
        
        def _load():
            try:
                load_result["model"] = SentenceTransformer(model_name, cache_folder=cache_folder)
            except Exception as e:
                load_result["error"] = str(e)
        
        load_thread = threading.Thread(target=_load, daemon=True)
        load_thread.start()
        load_thread.join(timeout=15)
        
        if load_thread.is_alive():
            logger.warning(f"嵌入模型加载超时(15s)，降级跳过")
            _model = None
            _model_name = None
            return None
        
        if load_result["error"]:
            logger.warning(f"嵌入模型加载失败: {load_result['error'][:100]}")
            _model = None
            return None
        
        _model = load_result["model"]
        _model_name = model_name
        
        logger.info("✓ 共享嵌入模型已加载")
        return _model
        
    except Exception as e:
        logger.warning(f"嵌入模型加载失败(离线模式): {e}")
        _model = None
        return None

def get_embeddings(texts):
    """获取文本嵌入向量"""
    model = get_embedding_model()
    if model is None:
        return None
    
    try:
        return model.encode(texts, convert_to_numpy=True)
    except Exception as e:
        logger.error(f"嵌入计算失败: {e}")
        return None

def similarity(text1, text2):
    """计算两段文本的相似度"""
    import numpy as np
    
    embeddings = get_embeddings([text1, text2])
    if embeddings is None:
        return 0.0
    
    try:
        emb1, emb2 = embeddings[0], embeddings[1]
        cos_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(cos_sim)
    except Exception:
        return 0.0