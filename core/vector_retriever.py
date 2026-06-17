"""
向量检索器 - 基于语义相似度的知识检索
"""
import sqlite3
import hashlib
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from loguru import logger

EMBEDDING_AVAILABLE = False
CHROMA_AVAILABLE = False
SentenceTransformer = None
chromadb = None

# 检查是否启用离线模式
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "false").lower() == "true"

if not OFFLINE_MODE:
    try:
        from sentence_transformers import SentenceTransformer
        EMBEDDING_AVAILABLE = True
    except Exception as e:
        logger.warning(f"sentence-transformers不可用: {e}")
    
    try:
        import chromadb
        from chromadb.config import Settings
        CHROMA_AVAILABLE = True
    except Exception as e:
        logger.warning(f"chromadb不可用: {e}")
else:
    logger.info("离线模式启用，跳过向量依赖检查")


class VectorRetriever:
    """向量检索器 - 支持语义相似度搜索"""
    
    def __init__(self, db_path: str = "data/knowledge_store.db",
                 collection_name: str = "knowledge"):
        self.db_path = db_path
        self.collection_name = collection_name
        self.model = None
        self.client = None
        self.collection = None
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 加载句子编码模型（严格离线模式）
        if EMBEDDING_AVAILABLE:
            try:
                logger.info("检查向量检索模型...")
                
                # 严格离线模式：在导入前设置环境变量
                os.environ['HF_HUB_OFFLINE'] = '1'
                os.environ['TRANSFORMERS_OFFLINE'] = '1'
                os.environ['HF_DATASETS_OFFLINE'] = '1'
                
                # 检查本地缓存是否存在
                from pathlib import Path
                cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
                model_cache = cache_dir / "models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2"
                
                if not model_cache.exists():
                    logger.warning("本地模型缓存不存在，跳过向量检索")
                    self.model = None
                else:
                    logger.info("加载本地缓存的句子编码模型...")
                    model_name = 'paraphrase-multilingual-MiniLM-L12-v2'
                    self.model = SentenceTransformer(model_name)
                    logger.info("句子编码模型已加载（离线模式）")
            except Exception as e:
                logger.warning(f"加载编码模型失败，将使用关键词检索: {e}")
                self.model = None
        else:
            logger.info("向量检索不可用，使用关键词检索")
            self.model = None
        
        if CHROMA_AVAILABLE and self.model:
            try:
                self.client = chromadb.Client(Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory="data/chroma"
                ))
                self.collection = self.client.get_or_create_collection(collection_name)
                logger.info(f"ChromaDB集合已创建: {collection_name}")
            except Exception as e:
                logger.error(f"ChromaDB初始化失败: {e}")
                self.client = None
                self.collection = None
        
        if not self.collection:
            self._init_vector_db()
        
        logger.info("向量检索器已初始化")
    
    def _init_vector_db(self):
        """初始化SQLite向量存储"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_vectors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    knowledge_id INTEGER,
                    question_hash TEXT,
                    vector_blob BLOB,
                    created_at TEXT,
                    FOREIGN KEY (knowledge_id) REFERENCES knowledge_items(id)
                )
            ''')
            conn.commit()
    
    def encode(self, text: str) -> Optional[List[float]]:
        """编码文本为向量"""
        if not self.model:
            return None
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"编码失败: {e}")
            return None
    
    def add(self, knowledge_id: int, question: str, answer: str) -> bool:
        """添加知识到向量索引"""
        
        text = f"{question}\n{answer}"
        
        if self.collection:
            try:
                embedding = self.encode(text)
                if embedding:
                    self.collection.upsert(
                        ids=[str(knowledge_id)],
                        embeddings=[embedding],
                        metadatas=[{
                            "question": question[:200],
                            "answer": answer[:500]
                        }],
                        documents=[text]
                    )
                    return True
            except Exception as e:
                logger.error(f"ChromaDB添加失败: {e}")
        
        return False
    
    def search(self, query: str, top_k: int = 5, 
               min_similarity: float = 0.3) -> List[Dict]:
        """向量搜索"""
        
        if self.collection:
            try:
                query_embedding = self.encode(query)
                if not query_embedding:
                    return []
                
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k
                )
                
                items = []
                if results['ids'] and results['ids'][0]:
                    for i, id_ in enumerate(results['ids'][0]):
                        distance = results['distances'][0][i] if results['distances'] else 0
                        similarity = 1 - distance
                        
                        if similarity >= min_similarity:
                            items.append({
                                "id": int(id_),
                                "similarity": similarity,
                                "question": results['metadatas'][0][i]['question'] if results['metadatas'] else "",
                                "answer": results['metadatas'][0][i]['answer'] if results['metadatas'] else ""
                            })
                
                return items
            except Exception as e:
                logger.error(f"向量搜索失败: {e}")
                return []
        
        return []
    
    def hybrid_search(self, query: str, top_k: int = 5,
                     keyword_weight: float = 0.3,
                     vector_weight: float = 0.7) -> List[Dict]:
        """混合检索：向量 + 关键词"""
        
        vector_results = self.search(query, top_k=top_k)
        
        keyword_results = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            keywords = query.lower().split()
            for keyword in keywords[:3]:
                if len(keyword) > 2:
                    cursor = conn.execute('''
                        SELECT id, question, answer, quality_score
                        FROM knowledge_items
                        WHERE question LIKE ? OR answer LIKE ?
                        ORDER BY quality_score DESC
                        LIMIT ?
                    ''', (f'%{keyword}%', f'%{keyword}%', top_k))
                    
                    for row in cursor.fetchall():
                        keyword_results.append({
                            "id": row['id'],
                            "question": row['question'],
                            "answer": row['answer'],
                            "quality_score": row['quality_score']
                        })
        
        merged = {}
        
        for item in vector_results:
            kid = item['id']
            merged[kid] = {
                **item,
                "vector_score": item['similarity'],
                "keyword_score": 0,
                "final_score": vector_weight * item['similarity']
            }
        
        for item in keyword_results:
            kid = item['id']
            keyword_score = item['quality_score'] / 100.0
            
            if kid in merged:
                merged[kid]['keyword_score'] = keyword_score
                merged[kid]['final_score'] = (
                    vector_weight * merged[kid]['vector_score'] +
                    keyword_weight * keyword_score
                )
            else:
                merged[kid] = {
                    **item,
                    "vector_score": 0,
                    "keyword_score": keyword_score,
                    "final_score": keyword_weight * keyword_score
                }
        
        sorted_results = sorted(
            merged.values(),
            key=lambda x: x['final_score'],
            reverse=True
        )
        
        return sorted_results[:top_k]
    
    def sync_from_knowledge_base(self):
        """从知识库同步所有知识到向量索引"""
        
        logger.info("开始同步知识库到向量索引...")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT id, question, answer
                FROM knowledge_items
                WHERE answer IS NOT NULL AND answer != ''
            ''')
            
            count = 0
            for row in cursor.fetchall():
                if self.add(row['id'], row['question'], row['answer']):
                    count += 1
            
            logger.info(f"同步完成: {count} 条知识")


vector_retriever = VectorRetriever()