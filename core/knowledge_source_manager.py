"""
外部知识源管理器 - 统一管理多种知识来源

支持：
1. LLM API（DeepSeek、OpenAI等）
2. 搜索引擎（DuckDuckGo、百度、Bing）
3. 知识库（维基百科、百度百科）
4. 开发者资源（GitHub、Stack Overflow）
5. 学术资源（arXiv、知乎）
6. 官方文档（Python、PyTorch等）

特性：
- 智能路由：根据问题类型选择最佳知识源
- 降级策略：主源失败自动切换备用源
- 结果缓存：避免重复查询
- 速率限制：防止API滥用
"""

import json
import sqlite3
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from loguru import logger


class KnowledgeSourceManager:
    """外部知识源管理器"""
    
    def __init__(self, config_path: str = "config/knowledge_sources.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        self._cache_db = Path(self.config.get("cache_config", {}).get("db_path", "data/knowledge_cache.db"))
        self._init_cache_db()
        
        self._rate_limits = {}
        self._request_history = []
        
        logger.info(f"📚 知识源管理器已初始化，加载 {self._count_sources()} 个知识源")
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        if not self.config_path.exists():
            logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
            return self._get_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "knowledge_sources": {
                "llm_apis": {
                    "deepseek": {
                        "enabled": True,
                        "priority": 1,
                        "type": "llm",
                        "api_key_env": "DEEPSEEK_API_KEY",
                        "base_url": "https://api.deepseek.com/v1",
                        "model": "deepseek-chat"
                    }
                },
                "search_engines": {
                    "duckduckgo": {
                        "enabled": True,
                        "priority": 1,
                        "type": "search"
                    }
                }
            },
            "cache_config": {
                "enabled": True,
                "ttl_hours": 24,
                "max_entries": 1000,
                "db_path": "data/knowledge_cache.db"
            }
        }
    
    def _count_sources(self) -> int:
        """统计启用的知识源数量"""
        count = 0
        sources = self.config.get("knowledge_sources", {})
        for category, items in sources.items():
            for name, config in items.items():
                if config.get("enabled", False):
                    count += 1
        return count
    
    def _init_cache_db(self):
        """初始化缓存数据库"""
        try:
            self._cache_db.parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(str(self._cache_db)) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS knowledge_cache (
                        query_hash TEXT PRIMARY KEY,
                        query TEXT,
                        source TEXT,
                        result TEXT,
                        created_at TEXT,
                        expires_at TEXT
                    )
                ''')
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_expires ON knowledge_cache(expires_at)
                ''')
                conn.commit()
        except Exception as e:
            logger.warning(f"缓存数据库初始化失败: {e}")
    
    def query(self, question: str, source_type: str = "auto") -> Dict[str, Any]:
        """
        查询知识源
        
        Args:
            question: 问题
            source_type: 知识源类型 (auto, llm, search, wiki, etc.)
        
        Returns:
            查询结果
        """
        query_hash = hashlib.md5(question.encode()).hexdigest()
        
        cached = self._get_cached(query_hash)
        if cached:
            logger.debug(f"命中缓存: {question[:30]}...")
            return cached
        
        if source_type == "auto":
            sources = self._route_query(question)
        else:
            sources = self._get_sources_by_type(source_type)
        
        for source_name, source_config in sources:
            if not source_config.get("enabled", False):
                continue
            
            if not self._check_rate_limit(source_name):
                continue
            
            try:
                result = self._query_source(source_name, source_config, question)
                
                if result and result.get("success"):
                    self._cache_result(query_hash, question, source_name, result)
                    
                    return {
                        "success": True,
                        "source": source_name,
                        "data": result.get("data"),
                        "confidence": result.get("confidence", 0.8),
                        "metadata": {
                            "source_type": source_config.get("type"),
                            "reliability": source_config.get("reliability", "medium"),
                            "timestamp": datetime.now().isoformat()
                        }
                    }
            except Exception as e:
                logger.debug(f"查询 {source_name} 失败: {e}")
                continue
        
        return {
            "success": False,
            "error": "所有知识源查询失败",
            "fallback": self._generate_fallback_response(question)
        }
    
    def _route_query(self, question: str) -> List[tuple]:
        """根据问题类型路由到最佳知识源"""
        routing_rules = self.config.get("query_routing", {}).get("rules", [])
        sources = self.config.get("knowledge_sources", {})
        
        matched_sources = []
        
        for rule in routing_rules:
            keywords = rule.get("keywords", [])
            if any(kw in question for kw in keywords):
                for source_name in rule.get("sources", []):
                    for category, items in sources.items():
                        if source_name in items:
                            matched_sources.append((source_name, items[source_name]))
        
        if not matched_sources:
            llm_sources = sources.get("llm_apis", {})
            for name, config in sorted(llm_sources.items(), key=lambda x: x[1].get("priority", 999)):
                matched_sources.append((name, config))
            
            search_sources = sources.get("search_engines", {})
            for name, config in sorted(search_sources.items(), key=lambda x: x[1].get("priority", 999)):
                matched_sources.append((name, config))
        
        return matched_sources
    
    def _get_sources_by_type(self, source_type: str) -> List[tuple]:
        """获取指定类型的知识源"""
        sources = self.config.get("knowledge_sources", {})
        result = []
        
        for category, items in sources.items():
            for name, config in items.items():
                if config.get("type") == source_type or category == source_type:
                    result.append((name, config))
        
        return sorted(result, key=lambda x: x[1].get("priority", 999))
    
    def _query_source(self, source_name: str, source_config: Dict, question: str) -> Dict:
        """查询单个知识源"""
        source_type = source_config.get("type")
        
        if source_type == "llm":
            return self._query_llm(source_name, source_config, question)
        elif source_type == "search":
            return self._query_search(source_name, source_config, question)
        elif source_type == "wiki":
            return self._query_wiki(source_name, source_config, question)
        elif source_type == "api":
            return self._query_api(source_name, source_config, question)
        elif source_type == "docs":
            return self._query_docs(source_name, source_config, question)
        elif source_type == "academic":
            return self._query_academic(source_name, source_config, question)
        elif source_type == "local_academic":
            return self._query_local_academic(source_name, source_config, question)
        elif source_type == "local":
            return self._query_local_kb(source_name, source_config, question)
        else:
            return {"success": False, "error": f"未知知识源类型: {source_type}"}
    
    def _query_llm(self, source_name: str, config: Dict, question: str) -> Dict:
        """查询LLM API"""
        import os
        
        api_key = os.getenv(config.get("api_key_env", ""), "")
        if not api_key:
            logger.debug(f"{source_name} API密钥未配置")
            return {"success": False, "error": "API密钥未配置"}
        
        try:
            import requests
            
            base_url = config.get("base_url", "")
            model = config.get("model", "deepseek-chat")
            
            response = requests.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "你是一个知识渊博的助手，请准确回答问题。"},
                        {"role": "user", "content": question}
                    ],
                    "temperature": 0.7
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                return {
                    "success": True,
                    "data": answer,
                    "confidence": 0.85
                }
            else:
                return {"success": False, "error": f"API返回 {response.status_code}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _query_search(self, source_name: str, config: Dict, question: str) -> Dict:
        """查询搜索引擎"""
        if source_name == "duckduckgo":
            try:
                from ddgs import DDGS
                with DDGS() as ddgs:
                    results = list(ddgs.text(question, max_results=config.get("max_results", 3)))
                
                if results:
                    formatted = []
                    for r in results:
                        formatted.append({
                            "title": r.get("title", ""),
                            "snippet": r.get("body", ""),
                            "url": r.get("href", "")
                        })
                    
                    return {
                        "success": True,
                        "data": formatted,
                        "confidence": 0.7
                    }
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": f"搜索引擎 {source_name} 未实现"}
    
    def _query_wiki(self, source_name: str, config: Dict, question: str) -> Dict:
        """查询维基百科"""
        try:
            import requests
            
            base_url = config.get("base_url", "")
            
            search_term = question.split()[0] if question else ""
            
            response = requests.get(
                f"{base_url}{search_term}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                extract = data.get("extract", "")
                
                if extract:
                    return {
                        "success": True,
                        "data": {
                            "title": data.get("title", ""),
                            "summary": extract,
                            "url": data.get("content_urls", {}).get("desktop", {}).get("page", "")
                        },
                        "confidence": 0.9
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "未找到相关条目"}
    
    def _query_api(self, source_name: str, config: Dict, question: str) -> Dict:
        """查询API类知识源（GitHub、Stack Overflow等）"""
        if source_name == "github":
            return self._query_github(config, question)
        elif source_name == "arxiv":
            return self._query_arxiv(config, question)
        
        return {"success": False, "error": f"API {source_name} 未实现"}
    
    def _query_github(self, config: Dict, question: str) -> Dict:
        """查询GitHub"""
        try:
            import requests
            import os
            
            token = os.getenv(config.get("api_key_env", ""), "")
            headers = {"Accept": "application/vnd.github.v3+json"}
            if token:
                headers["Authorization"] = f"token {token}"
            
            response = requests.get(
                config.get("base_url", ""),
                params={"q": question, "sort": "stars", "order": "desc", "per_page": 3},
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                if items:
                    results = []
                    for item in items:
                        results.append({
                            "name": item.get("full_name", ""),
                            "description": item.get("description", ""),
                            "stars": item.get("stargazers_count", 0),
                            "url": item.get("html_url", "")
                        })
                    
                    return {
                        "success": True,
                        "data": results,
                        "confidence": 0.75
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "GitHub查询失败"}
    
    def _query_arxiv(self, config: Dict, question: str) -> Dict:
        """查询arXiv"""
        try:
            import requests
            import feedparser
            
            response = requests.get(
                config.get("base_url", ""),
                params={
                    "search_query": f"all:{question}",
                    "start": 0,
                    "max_results": 3
                },
                timeout=15
            )
            
            if response.status_code == 200:
                feed = feedparser.parse(response.text)
                
                if feed.entries:
                    results = []
                    for entry in feed.entries:
                        results.append({
                            "title": entry.get("title", ""),
                            "summary": entry.get("summary", ""),
                            "authors": [a.get("name", "") for a in entry.get("authors", [])],
                            "link": entry.get("link", "")
                        })
                    
                    return {
                        "success": True,
                        "data": results,
                        "confidence": 0.95
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "arXiv查询失败"}
    
    def _query_docs(self, source_name: str, config: Dict, question: str) -> Dict:
        """查询官方文档"""
        return {"success": False, "error": "官方文档查询待实现"}
    
    def _query_academic(self, source_name: str, config: Dict, question: str) -> Dict:
        """查询学术库（arXiv、PubMed等）"""
        try:
            from core.academic_source_adapter import get_academic_adapter
            adapter = get_academic_adapter()
            
            result = adapter.query(source_name, question, config)
            
            if result.get("success") and result.get("results"):
                papers = result["results"]
                
                formatted = []
                for paper in papers[:3]:
                    formatted.append({
                        "title": paper.get("title", ""),
                        "authors": paper.get("authors", ""),
                        "abstract": paper.get("abstract", ""),
                        "url": paper.get("url", ""),
                        "source": paper.get("source", source_name)
                    })
                
                return {
                    "success": True,
                    "data": formatted,
                    "confidence": 0.9
                }
            
            return result
        except Exception as e:
            logger.debug(f"学术库查询失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _query_local_academic(self, source_name: str, config: Dict, question: str) -> Dict:
        """查询本地学术库"""
        try:
            from core.local_academic_library import get_local_academic_library
            library = get_local_academic_library()
            
            results = library.search(question, limit=3)
            
            if results:
                formatted = []
                for doc in results:
                    formatted.append({
                        "title": doc.get("title", ""),
                        "authors": doc.get("authors", ""),
                        "abstract": doc.get("abstract", ""),
                        "file_path": doc.get("file_path", ""),
                        "similarity": doc.get("similarity", 0.0),
                        "source": "local_academic"
                    })
                
                return {
                    "success": True,
                    "data": formatted,
                    "confidence": 0.95
                }
            
            return {"success": False, "error": "本地学术库未找到相关文档"}
        except Exception as e:
            logger.debug(f"本地学术库查询失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _query_local_kb(self, source_name: str, config: Dict, question: str) -> Dict:
        """查询本地知识库"""
        try:
            import sqlite3
            
            db_path = config.get("db_path", "data/knowledge_store.db")
            
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute('''
                    SELECT question, answer, source, quality_score
                    FROM knowledge_items
                    WHERE question LIKE ?
                    ORDER BY quality_score DESC
                    LIMIT 1
                ''', (f'%{question[:30]}%',))
                
                row = cursor.fetchone()
                if row:
                    return {
                        "success": True,
                        "data": [{
                            "question": row['question'],
                            "answer": row['answer'],
                            "source": row['source'],
                            "quality_score": row['quality_score']
                        }],
                        "confidence": min(0.9, row['quality_score'] / 100.0) if row['quality_score'] else 0.7
                    }
            
            return {"success": False, "error": "本地知识库未找到相关条目"}
        except Exception as e:
            logger.debug(f"本地知识库查询失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_rate_limit(self, source_name: str) -> bool:
        """检查速率限制"""
        rate_config = self.config.get("rate_limiting", {})
        max_per_minute = rate_config.get("requests_per_minute", 60)
        
        now = time.time()
        minute_ago = now - 60
        
        recent_requests = [
            r for r in self._request_history
            if r["source"] == source_name and r["time"] > minute_ago
        ]
        
        if len(recent_requests) >= max_per_minute:
            logger.debug(f"{source_name} 达到速率限制")
            return False
        
        self._request_history.append({"source": source_name, "time": now})
        
        self._request_history = [r for r in self._request_history if r["time"] > minute_ago]
        
        return True
    
    def _get_cached(self, query_hash: str) -> Optional[Dict]:
        """获取缓存结果"""
        if not self.config.get("cache_config", {}).get("enabled", True):
            return None
        
        try:
            with sqlite3.connect(str(self._cache_db)) as conn:
                cursor = conn.execute('''
                    SELECT result, source FROM knowledge_cache
                    WHERE query_hash = ? AND expires_at > ?
                ''', (query_hash, datetime.now().isoformat()))
                
                row = cursor.fetchone()
                if row:
                    return {
                        "success": True,
                        "source": row[1],
                        "data": json.loads(row[0]),
                        "from_cache": True
                    }
        except Exception as e:
            logger.debug(f"读取缓存失败: {e}")
        
        return None
    
    def _cache_result(self, query_hash: str, query: str, source: str, result: Dict):
        """缓存结果"""
        try:
            ttl_hours = self.config.get("cache_config", {}).get("ttl_hours", 24)
            expires_at = datetime.now() + timedelta(hours=ttl_hours)
            
            with sqlite3.connect(str(self._cache_db)) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO knowledge_cache
                    (query_hash, query, source, result, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    query_hash,
                    query,
                    source,
                    json.dumps(result.get("data")),
                    datetime.now().isoformat(),
                    expires_at.isoformat()
                ))
                conn.commit()
        except Exception as e:
            logger.debug(f"缓存结果失败: {e}")
    
    def _generate_fallback_response(self, question: str) -> str:
        """生成降级响应"""
        return f"抱歉，我暂时无法从知识源获取关于'{question}'的信息。建议您：\n1. 稍后再试\n2. 尝试简化问题\n3. 查看配置的知识源是否可用"
    
    def get_available_sources(self) -> Dict[str, List[str]]:
        """获取可用的知识源列表"""
        sources = self.config.get("knowledge_sources", {})
        result = {}
        
        for category, items in sources.items():
            available = []
            for name, config in items.items():
                if config.get("enabled", False):
                    available.append(name)
            if available:
                result[category] = available
        
        return result
    
    def enable_source(self, source_name: str):
        """启用知识源"""
        sources = self.config.get("knowledge_sources", {})
        for category, items in sources.items():
            if source_name in items:
                items[source_name]["enabled"] = True
                self._save_config()
                logger.info(f"✅ 已启用知识源: {source_name}")
                return
        logger.warning(f"未找到知识源: {source_name}")
    
    def disable_source(self, source_name: str):
        """禁用知识源"""
        sources = self.config.get("knowledge_sources", {})
        for category, items in sources.items():
            if source_name in items:
                items[source_name]["enabled"] = False
                self._save_config()
                logger.info(f"❌ 已禁用知识源: {source_name}")
                return
        logger.warning(f"未找到知识源: {source_name}")
    
    def _save_config(self):
        """保存配置"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存配置失败: {e}")


_knowledge_source_manager: Optional[KnowledgeSourceManager] = None


def get_knowledge_source_manager() -> KnowledgeSourceManager:
    """获取知识源管理器单例"""
    global _knowledge_source_manager
    if _knowledge_source_manager is None:
        _knowledge_source_manager = KnowledgeSourceManager()
    return _knowledge_source_manager