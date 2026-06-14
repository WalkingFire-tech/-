"""
向量检索系统 - 相似问题检索与经验重用
使用FAISS进行高效向量检索
"""
import os
import json
import hashlib
import threading
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from loguru import logger
from infrastructure.config_manager import config

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS未安装,向量检索功能受限")


class VectorRetriever:
    """向量检索器"""
    
    MAX_INDEX_SIZE = 100 * 1024 * 1024  # 100MB
    BASE_DATA_DIR = Path("data")
    
    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self.index = None
        self.id_map: Dict[int, Dict] = {}
        self.current_id = 0
        self._lock = threading.Lock()
        
        index_path = config.get("vector.index_path", "data/faiss_index.bin")
        self.index_path = self._sanitize_path(index_path)
        
        if FAISS_AVAILABLE:
            self.index = faiss.IndexFlatL2(embedding_dim)
            logger.info(f"FAISS索引初始化完成(维度={embedding_dim})")
        else:
            logger.warning("使用内存检索(性能较低)")
    
    def _sanitize_path(self, path: str) -> Path:
        """路径沙盒验证"""
        resolved = Path(path).resolve()
        base = self.BASE_DATA_DIR.resolve()
        
        if not resolved.is_relative_to(base):
            logger.warning(f"路径越权，强制使用data目录: {path}")
            return base / Path(path).name
        
        return resolved
    
    def add_experience(self, text: str, metadata: Dict, embedding: np.ndarray = None):
        """添加经验到向量库"""
        if embedding is None:
            embedding = self._get_embedding(text)
        
        if embedding is None:
            logger.warning(f"无法获取embedding: {text[:50]}")
            return
        
        embedding = embedding.reshape(1, -1).astype('float32')
        
        with self._lock:
            if FAISS_AVAILABLE and self.index is not None:
                self.index.add(embedding)
            
            self.id_map[self.current_id] = {
                "text": text,
                "metadata": metadata,
                "embedding": embedding.flatten().tolist(),
                "timestamp": datetime.now().isoformat()
            }
            
            self.current_id += 1
            logger.debug(f"添加经验: ID={self.current_id-1}, 文本={text[:50]}")
    
    def search_similar(self, query: str, k: int = 5, 
                      threshold: float = 0.8) -> List[Tuple[Dict, float]]:
        """检索相似经验"""
        query_embedding = self._get_embedding(query)
        
        if query_embedding is None:
            return []
        
        query_embedding = query_embedding.reshape(1, -1).astype('float32')
        
        if FAISS_AVAILABLE and self.index is not None:
            D, I = self.index.search(query_embedding, k)
            
            results = []
            for idx, distance in zip(I[0], D[0]):
                if idx < 0 or idx not in self.id_map:
                    continue
                
                similarity = 1 / (1 + distance)
                
                if similarity >= threshold:
                    results.append((self.id_map[idx], similarity))
            
            return results
        
        else:
            results = []
            for idx, item in self.id_map.items():
                item_embedding = np.array(item["embedding"]).reshape(1, -1).astype('float32')
                distance = np.linalg.norm(query_embedding - item_embedding)
                similarity = 1 / (1 + distance)
                
                if similarity >= threshold:
                    results.append((item, similarity))
            
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:k]
    
    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """获取文本embedding"""
        try:
            from sentence_transformers import SentenceTransformer
            
            model_name = config.get("embedding.model", "paraphrase-multilingual-MiniLM-L12-v2")
            
            if not hasattr(self, '_embedding_model'):
                try:
                    cache_folder = config.get("embedding.cache_folder", None)
                    self._embedding_model = SentenceTransformer(
                        model_name,
                        cache_folder=cache_folder
                    )
                except Exception as e:
                    logger.warning(f"无法加载embedding模型: {e}")
                    logger.info("使用简单hash embedding作为降级方案")
                    self._embedding_model = None
            
            if self._embedding_model is None:
                return self._simple_embedding(text)
            
            embedding = self._embedding_model.encode(text)
            return embedding
        
        except ImportError:
            logger.warning("sentence-transformers未安装,使用简单hash")
            return self._simple_embedding(text)
        
        except Exception as e:
            logger.error(f"获取embedding失败: {e}")
            return self._simple_embedding(text)
    
    def _simple_embedding(self, text: str) -> np.ndarray:
        """简单embedding(降级方案)"""
        embedding = np.zeros(self.embedding_dim)
        
        for i, char in enumerate(text[:self.embedding_dim]):
            embedding[i] = ord(char) / 255.0
        
        if len(text) < self.embedding_dim:
            text_hash = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            embedding[-1] = (text_hash % 1000) / 1000.0
        
        return embedding
    
    def get_successful_plans(self, intent_type: str = None, 
                            min_quality: int = 70) -> List[Dict]:
        """获取成功计划(用于类比检索)"""
        import sqlite3
        
        db_path = config.get("memory.long_term.db_path", "experience_pool.db")
        
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                if intent_type:
                    cur = conn.execute('''
                        SELECT intent_type, raw_input, plan, model_name, 
                               quality_score, duration, response
                        FROM experiences
                        WHERE intent_type = ? AND quality_score >= ? AND success = 1
                        ORDER BY quality_score DESC
                        LIMIT 100
                    ''', (intent_type, min_quality))
                else:
                    cur = conn.execute('''
                        SELECT intent_type, raw_input, plan, model_name,
                               quality_score, duration, response
                        FROM experiences
                        WHERE quality_score >= ? AND success = 1
                        ORDER BY quality_score DESC
                        LIMIT 100
                    ''', (min_quality,))
                
                return [dict(row) for row in cur.fetchall()]
        
        except Exception as e:
            logger.error(f"获取成功计划失败: {e}")
            return []
    
    def find_similar_plan(self, current_input: str, intent_type: str = None,
                         similarity_threshold: float = 0.85) -> Optional[Dict]:
        """查找相似的成功计划"""
        successful_plans = self.get_successful_plans(intent_type)
        
        if not successful_plans:
            return None
        
        for plan in successful_plans:
            historical_input = plan["raw_input"]
            
            results = self.search_similar(
                current_input, 
                k=1, 
                threshold=similarity_threshold
            )
            
            if results:
                similar_item, similarity = results[0]
                
                if similarity >= similarity_threshold:
                    logger.info(
                        f"找到相似计划: 相似度{similarity:.2f}, "
                        f"历史质量{plan['quality_score']}"
                    )
                    
                    return {
                        "plan": plan,
                        "similarity": similarity,
                        "source": "analogical_retrieval"
                    }
        
        return None
    
    def save_index(self, path: str = None):
        """保存索引到磁盘"""
        if not FAISS_AVAILABLE or self.index is None:
            return
        
        save_path = self._sanitize_path(path) if path else self.index_path
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self._lock:
            faiss.write_index(self.index, str(save_path))
            
            id_map_path = save_path.with_suffix('.json')
            with open(id_map_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "id_map": self.id_map,
                    "current_id": self.current_id
                }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"向量索引已保存: {save_path}")
    
    def load_index(self, path: str = None):
        """从磁盘加载索引"""
        load_path = self._sanitize_path(path) if path else self.index_path
        
        if not FAISS_AVAILABLE or not load_path.exists():
            return
        
        if load_path.stat().st_size > self.MAX_INDEX_SIZE:
            logger.error(f"索引文件过大: {load_path} ({load_path.stat().st_size} bytes)")
            return
        
        with self._lock:
            self.index = faiss.read_index(str(load_path))
            
            id_map_path = load_path.with_suffix('.json')
            if id_map_path.exists():
                with open(id_map_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.id_map = {int(k): v for k, v in data["id_map"].items()}
                    self.current_id = data["current_id"]
        
        logger.info(f"向量索引已加载: {load_path} ({self.index.ntotal}个向量)")


vector_retriever = VectorRetriever()