"""
学术知识源适配器 - 支持arXiv、PubMed、Semantic Scholar等学术库

三层知识源体系 - 第二层：权威学术/技术库
"""

import json
import re
import os
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger


class AcademicSourceAdapter:
    """
    学术库适配器
    
    支持：
    - arXiv（物理/数学/计算机/生物）
    - PubMed（生物医学）
    - Semantic Scholar（通用学术）
    - CORE（开放获取）
    - IEEE Xplore（电子工程/计算机）
    - CNKI（中国知网）
    - 万方数据
    """
    
    def __init__(self):
        self._cache = {}
        self._request_history = []
    
    def query(self, source_name: str, query: str, config: Dict) -> Dict:
        """查询指定学术库"""
        source_type = source_name.lower().replace(" ", "_").replace("（", "").replace("）", "")
        
        handlers = {
            "arxiv": self._query_arxiv,
            "pubmed": self._query_pubmed,
            "semantic_scholar": self._query_semantic_scholar,
            "core": self._query_core,
            "ieee": self._query_ieee,
            "cnki": self._query_cnki,
            "万方数据": self._query_wanfang,
        }
        
        handler = handlers.get(source_type)
        if handler:
            return handler(query, config)
        
        return {"success": False, "error": f"不支持的学术库: {source_name}"}
    
    def _query_arxiv(self, query: str, config: Dict) -> Dict:
        """查询 arXiv"""
        try:
            import requests
            import xml.etree.ElementTree as ET
            
            max_results = config.get("max_results", 3)
            categories = config.get("categories", ["cs.AI", "cs.LG"])
            
            search_query = f'(ti:"{query}" OR abs:"{query}")'
            
            url = config.get("api_url", "http://export.arxiv.org/api/query")
            params = {
                "search_query": search_query,
                "max_results": max_results,
                "sortBy": "relevance"
            }
            
            logger.info(f"查询arXiv: {query}")
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code != 200:
                return {"success": False, "error": f"arXiv API错误: {response.status_code}"}
            
            root = ET.fromstring(response.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            
            entries = root.findall("atom:entry", ns)
            results = []
            
            for entry in entries[:max_results]:
                title_elem = entry.find("atom:title", ns)
                title = title_elem.text.strip() if title_elem is not None else ""
                
                authors = []
                for author in entry.findall("atom:author", ns):
                    name = author.find("atom:name", ns)
                    if name is not None:
                        authors.append(name.text.strip())
                
                summary = entry.find("atom:summary", ns)
                abstract = summary.text.strip() if summary is not None else ""
                
                link = entry.find("atom:link[@type='text/html']", ns)
                url = link.get("href") if link is not None else ""
                
                published = entry.find("atom:published", ns)
                date = published.text[:10] if published is not None else ""
                
                results.append({
                    "title": title,
                    "authors": ", ".join(authors[:3]),
                    "abstract": abstract[:500] + "..." if len(abstract) > 500 else abstract,
                    "url": url,
                    "date": date,
                    "source": "arXiv"
                })
            
            logger.info(f"arXiv返回 {len(results)} 条结果")
            
            return {
                "success": True,
                "results": results,
                "total_results": len(results),
                "source": "arxiv"
            }
            
        except Exception as e:
            logger.error(f"arXiv查询失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _query_pubmed(self, query: str, config: Dict) -> Dict:
        """查询 PubMed"""
        try:
            import requests
            import xml.etree.ElementTree as ET
            
            max_results = config.get("max_results", 3)
            base_url = config.get("api_url", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils")
            
            logger.info(f"查询PubMed: {query}")
            
            search_url = f"{base_url}/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "xml"
            }
            
            response = requests.get(search_url, params=params, timeout=15)
            
            if response.status_code != 200:
                return {"success": False, "error": f"PubMed API错误: {response.status_code}"}
            
            root = ET.fromstring(response.text)
            id_list = root.findall(".//Id")
            
            if not id_list:
                return {"success": True, "results": [], "total_results": 0, "source": "pubmed"}
            
            paper_ids = [id_elem.text for id_elem in id_list]
            
            fetch_url = f"{base_url}/efetch.fcgi"
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(paper_ids),
                "retmode": "xml"
            }
            
            fetch_response = requests.get(fetch_url, params=fetch_params, timeout=15)
            
            if fetch_response.status_code != 200:
                return {"success": True, "results": [], "total_results": len(paper_ids), "source": "pubmed"}
            
            root = ET.fromstring(fetch_response.text)
            
            results = []
            for article in root.findall(".//PubmedArticle"):
                title_elem = article.find(".//ArticleTitle")
                title = title_elem.text if title_elem is not None else ""
                
                abstract_elem = article.find(".//AbstractText")
                abstract = abstract_elem.text if abstract_elem is not None else ""
                
                authors = []
                for author in article.findall(".//Author"):
                    last = author.find("LastName")
                    first = author.find("ForeName")
                    if last is not None and first is not None:
                        authors.append(f"{first.text} {last.text}")
                    elif last is not None:
                        authors.append(last.text)
                
                pmid_elem = article.find(".//PMID")
                pmid = pmid_elem.text if pmid_elem is not None else ""
                
                results.append({
                    "title": title,
                    "authors": ", ".join(authors[:3]),
                    "abstract": abstract[:500] + "..." if len(abstract) > 500 else abstract,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "source": "PubMed"
                })
            
            logger.info(f"PubMed返回 {len(results)} 条结果")
            
            return {
                "success": True,
                "results": results[:max_results],
                "total_results": len(paper_ids),
                "source": "pubmed"
            }
            
        except Exception as e:
            logger.error(f"PubMed查询失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _query_semantic_scholar(self, query: str, config: Dict) -> Dict:
        """查询 Semantic Scholar"""
        try:
            import requests
            
            api_key = os.getenv(config.get("api_key_env", "S2_API_KEY"), "")
            headers = {"x-api-key": api_key} if api_key else {}
            
            url = config.get("api_url", "https://api.semanticscholar.org/v1/paper/search")
            params = {
                "query": query,
                "limit": config.get("max_results", 3)
            }
            
            logger.info(f"查询Semantic Scholar: {query}")
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return {"success": False, "error": f"Semantic Scholar API错误: {response.status_code}"}
            
            data = response.json()
            results = []
            
            for item in data.get("data", []):
                results.append({
                    "title": item.get("title", ""),
                    "authors": ", ".join([a.get("name", "") for a in item.get("authors", [])[:3]]),
                    "abstract": (item.get("abstract", "") or "")[:500],
                    "url": item.get("url", ""),
                    "year": item.get("year", ""),
                    "source": "Semantic Scholar"
                })
            
            logger.info(f"Semantic Scholar返回 {len(results)} 条结果")
            
            return {
                "success": True,
                "results": results,
                "total_results": data.get("total", 0),
                "source": "semantic_scholar"
            }
            
        except Exception as e:
            logger.error(f"Semantic Scholar查询失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _query_core(self, query: str, config: Dict) -> Dict:
        """查询 CORE（开放获取论文）"""
        try:
            import requests
            
            api_key = os.getenv(config.get("api_key_env", "CORE_API_KEY"), "")
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            
            url = config.get("api_url", "https://api.core.ac.uk/v3/search/works")
            params = {
                "q": query,
                "limit": config.get("max_results", 3)
            }
            
            logger.info(f"查询CORE: {query}")
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return {"success": False, "error": f"CORE API错误: {response.status_code}"}
            
            data = response.json()
            results = []
            
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "authors": ", ".join(item.get("authors", [])[:3]),
                    "abstract": (item.get("abstract", "") or "")[:500],
                    "url": item.get("downloadUrl", item.get("url", "")),
                    "source": "CORE"
                })
            
            logger.info(f"CORE返回 {len(results)} 条结果")
            
            return {
                "success": True,
                "results": results,
                "total_results": data.get("totalHits", 0),
                "source": "core"
            }
            
        except Exception as e:
            logger.error(f"CORE查询失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _query_ieee(self, query: str, config: Dict) -> Dict:
        """查询 IEEE Xplore"""
        return {
            "success": False,
            "error": "IEEE Xplore API需要配置，请设置IEEE_API_KEY",
            "results": []
        }
    
    def _query_cnki(self, query: str, config: Dict) -> Dict:
        """查询中国知网（CNKI）"""
        return {
            "success": False,
            "error": "CNKI API需要商业授权，请配置API密钥",
            "results": []
        }
    
    def _query_wanfang(self, query: str, config: Dict) -> Dict:
        """查询万方数据"""
        return {
            "success": False,
            "error": "万方数据API需要商业授权，请配置API密钥",
            "results": []
        }


_academic_adapter: Optional[AcademicSourceAdapter] = None


def get_academic_adapter() -> AcademicSourceAdapter:
    global _academic_adapter
    if _academic_adapter is None:
        _academic_adapter = AcademicSourceAdapter()
    return _academic_adapter