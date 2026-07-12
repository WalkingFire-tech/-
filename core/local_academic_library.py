"""
本地学术库 - 用户自建的学术论文/技术文档索引

三层知识源体系 - 第一层：本地知识库
"""

import hashlib
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
from infrastructure.database_manager import DatabaseManager


class LocalAcademicLibrary:
    """
    本地学术库
    
    功能：
    1. 索引本地学术论文（PDF）
    2. 支持关键词搜索
    3. 支持语义搜索（嵌入）
    4. 与知识源路由器集成
    """
    
    def __init__(self, db_path: str = "data/academic_library.db"):
        self.db_path = db_path
        self._init_database()
        self._embedding_model = None
        self._embedding_available = False
        
        self._init_embedding()
        
        logger.info(f"📚 本地学术库已初始化: {db_path}")
    
    def _init_database(self):
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT,
                authors TEXT,
                abstract TEXT,
                filename TEXT,
                file_path TEXT,
                tags TEXT,
                source TEXT,
                language TEXT,
                content TEXT,
                embedding TEXT,
                indexed_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS library_stats (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_title ON documents(title);
            CREATE INDEX IF NOT EXISTS idx_tags ON documents(tags);
            CREATE INDEX IF NOT EXISTS idx_source ON documents(source);
        ''')
    
    def _init_embedding(self):
        """初始化嵌入模型（用于语义搜索）"""
        try:
            import os
            os.environ['HF_HUB_OFFLINE'] = '1'
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self._embedding_available = True
            logger.info("✅ 学术库嵌入模型已加载")
        except Exception as e:
            logger.warning(f"嵌入模型不可用: {e}")
    
    def index_pdf(self, file_path: str, metadata: Dict = None) -> Dict:
        """索引PDF文件"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"success": False, "error": "文件不存在"}
        
        if file_path.suffix.lower() != '.pdf':
            return {"success": False, "error": "仅支持PDF文件"}
        
        try:
            import fitz
            
            doc = fitz.open(str(file_path))
            text_parts = []
            
            for page in doc:
                text_parts.append(page.get_text())
            
            doc.close()
            content = "\n\n".join(text_parts)
            
            metadata = metadata or {}
            title = metadata.get("title", file_path.stem)
            authors = metadata.get("authors", "")
            tags = metadata.get("tags", [])
            source = metadata.get("source", "local")
            language = metadata.get("language", "zh")
            
            abstract = content[:500] + "..." if len(content) > 500 else content
            
            doc_id = hashlib.md5(f"{file_path}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
            
            embedding = None
            if self._embedding_available and content:
                try:
                    embedding_vec = self._embedding_model.encode(content[:1000])
                    embedding = json.dumps(embedding_vec.tolist())
                except Exception:
                    pass
            
            db = DatabaseManager.get(self.db_path)
            db.execute('''
                INSERT OR REPLACE INTO documents
                (id, title, authors, abstract, filename, file_path, tags, source, language, content, embedding, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                doc_id,
                title,
                authors,
                abstract,
                file_path.name,
                str(file_path),
                json.dumps(tags, ensure_ascii=False),
                source,
                language,
                content[:10000],
                embedding,
                datetime.now().isoformat()
            ), commit=True)
            
            logger.info(f"📄 已索引PDF: {file_path.name}")
            
            return {
                "success": True,
                "id": doc_id,
                "title": title,
                "file": str(file_path)
            }
            
        except ImportError:
            logger.error("PyMuPDF未安装，无法索引PDF")
            return {"success": False, "error": "PyMuPDF未安装，请安装: pip install pymupdf"}
        except Exception as e:
            logger.error(f"索引PDF失败: {e}")
            return {"success": False, "error": str(e)}
    
    def index_directory(self, directory: str, recursive: bool = True) -> Dict:
        """索引整个目录的PDF文件"""
        directory = Path(directory)
        
        if not directory.exists():
            return {"success": False, "error": "目录不存在"}
        
        results = {"total": 0, "successful": 0, "failed": 0, "files": []}
        
        pattern = "**/*.pdf" if recursive else "*.pdf"
        
        for pdf_file in directory.glob(pattern):
            if pdf_file.is_file():
                result = self.index_pdf(str(pdf_file))
                results["total"] += 1
                if result.get("success"):
                    results["successful"] += 1
                    results["files"].append(str(pdf_file.name))
                else:
                    results["failed"] += 1
        
        logger.info(f"📚 索引完成: {results['successful']}/{results['total']} 个文件")
        
        return results
    
    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """搜索本地学术库"""
        results = []
        
        if self._embedding_available:
            try:
                query_vec = self._embedding_model.encode(query)
                
                db = DatabaseManager.get(self.db_path)
                rows = db.query('''
                    SELECT id, title, authors, abstract, file_path, tags, source
                    FROM documents
                    WHERE embedding IS NOT NULL
                ''')
                
                import numpy as np
                
                similarities = []
                for row in rows:
                    embedding = row['embedding']
                    if embedding:
                        doc_vec = np.array(json.loads(embedding))
                        sim = np.dot(query_vec, doc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec))
                        similarities.append((row, float(sim)))
                
                similarities.sort(key=lambda x: x[1], reverse=True)
                
                for row, sim in similarities[:limit]:
                    results.append({
                        "id": row['id'],
                        "title": row['title'],
                        "authors": row['authors'],
                        "abstract": row['abstract'][:300],
                        "file_path": row['file_path'],
                        "tags": json.loads(row['tags']) if row['tags'] else [],
                        "source": row['source'],
                        "similarity": sim
                    })
                
                if results:
                    logger.info(f"语义搜索返回 {len(results)} 条结果")
                    return results
            except Exception as e:
                logger.debug(f"语义搜索失败: {e}")
        
        try:
            db = DatabaseManager.get(self.db_path)
            rows = db.query('''
                SELECT id, title, authors, abstract, file_path, tags, source
                FROM documents
                WHERE title LIKE ? OR abstract LIKE ? OR content LIKE ?
                LIMIT ?
            ''', (f'%{query}%', f'%{query}%', f'%{query}%', limit))
            
            for row in rows:
                results.append({
                    "id": row['id'],
                    "title": row['title'],
                    "authors": row['authors'],
                    "abstract": row['abstract'][:300],
                    "file_path": row['file_path'],
                    "tags": json.loads(row['tags']) if row['tags'] else [],
                    "source": row['source']
                })
            
            logger.info(f"关键词搜索返回 {len(results)} 条结果")
        except Exception as e:
            logger.error(f"关键词搜索失败: {e}")
        
        return results
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """获取单个文档"""
        try:
            db = DatabaseManager.get(self.db_path)
            row = db.query_one(
                'SELECT * FROM documents WHERE id = ?',
                (doc_id,)
            )
            
            if row:
                return {
                    "id": row['id'],
                    "title": row['title'],
                    "authors": row['authors'],
                    "abstract": row['abstract'],
                    "content": row['content'],
                    "file_path": row['file_path'],
                    "tags": json.loads(row['tags']) if row['tags'] else [],
                    "source": row['source'],
                    "indexed_at": row['indexed_at']
                }
        except Exception as e:
            logger.error(f"获取文档失败: {e}")
        
        return None
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        try:
            db = DatabaseManager.get(self.db_path)
            total_row = db.query_one("SELECT COUNT(*) FROM documents")
            total = total_row[0] if total_row else 0
            
            source_rows = db.query(
                "SELECT source, COUNT(*) FROM documents GROUP BY source"
            )
            by_source = {row[0]: row[1] for row in source_rows}
            
            language_rows = db.query(
                "SELECT language, COUNT(*) FROM documents GROUP BY language"
            )
            by_language = {row[0]: row[1] for row in language_rows}
            
            return {
                "total_documents": total,
                "by_source": by_source,
                "by_language": by_language,
                "embedding_available": self._embedding_available
            }
        except Exception as e:
            return {"total_documents": 0, "error": str(e)}
    
    def clear(self):
        """清空库"""
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute("DELETE FROM documents", commit=True)
            logger.info("本地学术库已清空")
        except Exception as e:
            logger.error(f"清空失败: {e}")


_local_academic_library: Optional[LocalAcademicLibrary] = None


def get_local_academic_library() -> LocalAcademicLibrary:
    global _local_academic_library
    if _local_academic_library is None:
        _local_academic_library = LocalAcademicLibrary()
    return _local_academic_library