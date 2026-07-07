"""
向量存储 - 基于ChromaDB的语义向量检索
"""
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from loguru import logger

CHROMA_AVAILABLE = False
EMBEDDING_AVAILABLE = False
chromadb = None
SentenceTransformer = None

try:
    import chromadb
    CHROMA_AVAILABLE = True
except Exception:
    pass

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except Exception:
    pass

if not CHROMA_AVAILABLE or not EMBEDDING_AVAILABLE:
    logger.warning("向量存储依赖不完整，将使用SQLite关键词检索")


class VectorStore:
    """向量存储 - 统一的向量检索接口"""
    
    def __init__(self, persist_dir: str = "data/chroma"):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self.client = None
        self.collection = None
        self.model = None
        
        if CHROMA_AVAILABLE and EMBEDDING_AVAILABLE:
            try:
                self.client = chromadb.PersistentClient(path=str(self.persist_dir))
                self.collection = self.client.get_or_create_collection("knowledge")
                
                logger.info("加载句子编码模型...")
                os.environ['HF_HUB_OFFLINE'] = '1'
                os.environ['TRANSFORMERS_OFFLINE'] = '1'
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info(f"向量存储已初始化: {persist_dir}")
            except Exception as e:
                logger.error(f"向量存储初始化失败: {e}")
        else:
            logger.warning("向量存储不可用，将使用SQLite关键词检索")
    
    def _id_from_text(self, text: str) -> str:
        """从文本生成唯一ID"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def add(self, question: str, answer: str, metadata: dict) -> Optional[str]:
        """添加知识到向量索引"""
        
        if not self.collection or not self.model:
            return None
        
        try:
            doc = f"{question}\n{answer}"
            emb = self.model.encode(doc).tolist()
            doc_id = self._id_from_text(doc)
            
            self.collection.upsert(
                ids=[doc_id],
                embeddings=[emb],
                metadatas=[{
                    **metadata,
                    "question": question,
                    "answer": answer[:500]
                }]
            )
            
            return doc_id
        except Exception as e:
            logger.error(f"向量添加失败: {e}")
            return None
    
    def search(self, query: str, top_k: int = 3, 
               threshold: float = 0.5) -> List[Tuple[float, dict]]:
        """向量搜索"""
        
        if not self.collection or not self.model:
            return []
        
        try:
            q_emb = self.model.encode(query).tolist()
            results = self.collection.query(
                query_embeddings=[q_emb],
                n_results=top_k
            )
            
            if not results['ids'] or not results['ids'][0]:
                return []
            
            distances = results['distances'][0]
            metadatas = results['metadatas'][0]
            
            filtered = [
                (d, m) 
                for d, m in zip(distances, metadatas) 
                if d < threshold
            ]
            
            return filtered
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            return []
    
    def delete(self, doc_id: str) -> bool:
        """删除向量"""
        
        if not self.collection:
            return False
        
        try:
            self.collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            logger.error(f"向量删除失败: {e}")
            return False
    
    def count(self) -> int:
        """获取向量数量"""
        
        if not self.collection:
            return 0
        
        try:
            return self.collection.count()
        except:
            return 0
    
    def clear(self):
        """清空向量索引"""
        
        if not self.client:
            return
        
        try:
            self.client.delete_collection("knowledge")
            self.collection = self.client.get_or_create_collection("knowledge")
            logger.info("向量索引已清空")
        except Exception as e:
            logger.error(f"清空向量索引失败: {e}")


if __name__ == "__main__":
    print("测试向量存储...")
    
    vs = VectorStore()
    
    if vs.collection:
        print("✅ 向量存储初始化成功")
        
        doc_id = vs.add("什么是机器学习？", "机器学习是AI的一个分支。", {"source": "test"})
        print(f"✅ 添加向量: {doc_id}")
        
        results = vs.search("机器学习", top_k=1)
        print(f"✅ 搜索结果: {len(results)} 条")
        
        print(f"✅ 向量数量: {vs.count()}")
    else:
        print("⚠️  向量存储不可用")