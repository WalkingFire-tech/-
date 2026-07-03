"""
外部学习器实现
包含Wikipedia、DuckDuckGo、arXiv、多源深度搜索等知识源
"""
from typing import List, Optional, Dict
import re
from core.external_learner_base import ExternalLearnerBase, KnowledgeItem

try:
    from ddgs import DDGS as _DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS as _DDGS
    except ImportError:
        _DDGS = None

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

SOURCE_QUALITY = {
    "arxiv.org": 0.95,
    "zenodo.org": 0.93,
    "semanticscholar.org": 0.92,
    "nature.com": 0.95,
    "science.org": 0.95,
    "sciencedirect.com": 0.93,
    "sagepub.com": 0.90,
    "wikipedia.org": 0.85,
    "apple.com": 0.88,
    "microsoft.com": 0.88,
    "openai.com": 0.87,
    "deepmind.com": 0.87,
    "anthropic.com": 0.87,
    "aws.amazon.com": 0.86,
    "cloud.google.com": 0.86,
    "huawei.com": 0.85,
    "xiaomi.com": 0.82,
    "zhihu.com": 0.80,
    "hub.baai.com": 0.80,
    "geekpark.net": 0.78,
    "developer.aliyun.com": 0.78,
    "36kr.com": 0.78,
    "huxiu.com": 0.77,
    "ifanr.com": 0.77,
    "ithome.com": 0.75,
    "developer.baidu.com": 0.75,
    "npmjs.com": 0.75,
    "pypi.org": 0.75,
    "github.com": 0.80,
    "csdn.net": 0.70,
    "donews.com": 0.72,
    "msup.com.cn": 0.70,
    "jd.com": 0.72,
    "tmall.com": 0.72,
    "dangdang.com": 0.73,
    "xiaohongshu.com": 0.73,
    "douban.com": 0.74,
    "weread.qq.com": 0.76,
    "cnki.net": 0.88,
    "wanfangdata.com.cn": 0.85,
}

SITE_SEARCH_MAP = {
    "academic": ["arxiv.org", "zenodo.org", "semanticscholar.org", "cnki.net"],
    "tech_cn": ["geekpark.net", "hub.baai.com", "developer.aliyun.com", "csdn.net", "developer.baidu.com", "36kr.com", "huxiu.com"],
    "community": ["zhihu.com", "donews.com", "npmjs.com", "msup.com.cn", "ifanr.com", "ithome.com"],
    "product": ["jd.com", "tmall.com", "xiaohongshu.com", "douban.com", "weread.qq.com", "dangdang.com"],
    "official": ["apple.com", "microsoft.com", "openai.com", "huawei.com", "aws.amazon.com", "cloud.google.com", "github.com"],
}

QUERY_TYPE_SITES = {
    "科学": "academic",
    "物理": "academic",
    "化学": "academic",
    "生物": "academic",
    "数学": "academic",
    "天文": "academic",
    "论文": "academic",
    "研究": "academic",
    "技术": "tech_cn",
    "编程": "tech_cn",
    "代码": "tech_cn",
    "开发": "tech_cn",
    "架构": "tech_cn",
    "框架": "tech_cn",
    "算法": "academic",
    "AI": "tech_cn",
    "人工智能": "tech_cn",
    "深度学习": "academic",
    "机器学习": "academic",
    "思想": "community",
    "观点": "community",
    "评价": "community",
    "经验": "community",
    "推荐": "product",
    "评测": "product",
    "对比": "product",
    "选购": "product",
    "哪个好": "product",
    "值得买": "product",
    "使用体验": "product",
    "怎么样": "product",
    "好不好": "product",
    "书": "product",
    "课程": "product",
    "培训": "product",
    "产品": "product",
    "手机": "product",
    "电脑": "product",
    "相机": "product",
    "官方": "official",
    "文档": "official",
    "API": "official",
    "SDK": "official",
    "白皮书": "official",
    "发布": "official",
    "更新": "official",
    "版本": "official",
}


class WikipediaLearner(ExternalLearnerBase):
    """
    维基百科学习器
    通过Wikipedia API获取知识
    """
    
    def __init__(self, language: str = "zh"):
        self.language = language
        self._available = None
        self.base_url = f"https://{language}.wikipedia.org/api/rest_v1/page/summary/"
    
    def learn(
        self,
        query: str,
        context: Optional[str] = None,
        max_results: int = 5
    ) -> List[KnowledgeItem]:
        """
        从维基百科获取知识
        
        Args:
            query: 搜索关键词
            context: 上下文（未使用）
            max_results: 最多返回条目数
        
        Returns:
            知识条目列表
        """
        results = []
        
        try:
            import requests
        except ImportError:
            logger.warning("requests库未安装，WikipediaLearner不可用")
            return results
        
        search_terms = self._extract_search_terms(query)
        
        for term in search_terms[:max_results]:
            try:
                url = f"{self.base_url}{term}"
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('type') != 'disambiguation':
                        content = data.get('extract', '')
                        title = data.get('title', term)
                        
                        if content and len(content) > 50:
                            results.append(KnowledgeItem(
                                content=f"{title}: {content}",
                                source=f"wikipedia:{self.language}",
                                confidence=0.85,
                                metadata={
                                    'title': title,
                                    'url': data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                                    'language': self.language
                                }
                            ))
                            logger.info(f"📖 Wikipedia: 获取到 '{title}' 的知识")
                
            except Exception as e:
                logger.debug(f"Wikipedia查询失败 '{term}': {e}")
        
        return results
    
    def _extract_search_terms(self, query: str) -> List[str]:
        """从查询中提取搜索词"""
        query = re.sub(r'[?？。.!！，,]', ' ', query)
        words = query.split()
        
        terms = []
        for word in words:
            if len(word) >= 2:
                terms.append(word)
        
        if len(terms) == 0 and len(query) >= 2:
            terms = [query]
        
        return terms
    
    def is_available(self) -> bool:
        """检查Wikipedia API是否可用"""
        if self._available is not None:
            return self._available
        
        try:
            import requests
            response = requests.get(
                f"https://{self.language}.wikipedia.org/api/rest_v1/",
                timeout=3
            )
            self._available = response.status_code < 500
        except:
            self._available = False
        
        return self._available
    
    def get_cost_estimate(self, query: str) -> float:
        """预估成本（Wikipedia免费，成本为0）"""
        return 0.0


class DDGSearchLearner(ExternalLearnerBase):
    """
    DuckDuckGo搜索学习器
    通过DuckDuckGo搜索获取知识
    """
    
    def __init__(self, region: str = "cn-zh"):
        self.region = region
        self._available = None
    
    def learn(
        self,
        query: str,
        context: Optional[str] = None,
        max_results: int = 5
    ) -> List[KnowledgeItem]:
        """
        从DuckDuckGo搜索获取知识
        
        Args:
            query: 搜索查询
            context: 上下文（用于增强查询）
            max_results: 最多返回条目数
        
        Returns:
            知识条目列表
        """
        results = []
        
        if _DDGS is None:
            return results
        
        enhanced_query = query
        if context:
            keywords = self._extract_keywords(context)
            if keywords:
                enhanced_query = f"{query} {' '.join(keywords[:2])}"
        
        try:
            with _DDGS() as ddgs:
                search_results = list(ddgs.text(
                    enhanced_query,
                    region=self.region,
                    max_results=max_results
                ))
            
            for item in search_results:
                title = item.get('title', '')
                body = item.get('body', '')
                href = item.get('href', '')
                
                if body and len(body) > 30:
                    content = f"{title}: {body}" if title else body
                    
                    results.append(KnowledgeItem(
                        content=content[:500],
                        source="duckduckgo",
                        confidence=0.75,
                        metadata={
                            'title': title,
                            'url': href,
                            'query': enhanced_query
                        }
                    ))
            
            logger.info(f"🔍 DuckDuckGo: 获取到 {len(results)} 条搜索结果")
            
        except Exception as e:
            logger.warning(f"DuckDuckGo搜索失败: {e}")
        
        return results
    
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        text = re.sub(r'[?？。.!！，,]', ' ', text)
        words = text.split()
        
        keywords = []
        for word in words:
            if len(word) >= 2 and not word.isdigit():
                keywords.append(word)
        
        return keywords[:5]
    
    def is_available(self) -> bool:
        """检查DuckDuckGo是否可用"""
        if self._available is not None:
            return self._available
        
        try:
            if _DDGS is None:
                return False
            with _DDGS() as ddgs:
                results = list(ddgs.text("test", max_results=1))
            self._available = True
        except:
            self._available = False
        
        return self._available
    
    def get_cost_estimate(self, query: str) -> float:
        """预估成本（DuckDuckGo免费，成本为0）"""
        return 0.0


class ArxivLearner(ExternalLearnerBase):
    """arXiv论文学习器 — 通过arXiv API获取论文摘要"""
    
    def __init__(self):
        self._available = None
    
    def learn(self, query: str, context: Optional[str] = None, max_results: int = 3) -> List[KnowledgeItem]:
        results = []
        try:
            import requests
        except ImportError:
            return results
        
        search_terms = self._extract_search_terms(query)
        search_query = " AND ".join(f'all:"{t}"' for t in search_terms[:3])
        if not search_query:
            search_query = f'all:"{query}"'
        
        try:
            url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": search_query,
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending"
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                
                for entry in root.findall("atom:entry", ns):
                    title_el = entry.find("atom:title", ns)
                    summary_el = entry.find("atom:summary", ns)
                    id_el = entry.find("atom:id", ns)
                    
                    if summary_el is not None and summary_el.text:
                        title = title_el.text.strip().replace("\n", " ") if title_el is not None else ""
                        summary = summary_el.text.strip().replace("\n", " ")[:400]
                        arxiv_id = id_el.text.strip() if id_el is not None else ""
                        
                        if summary and len(summary) > 50:
                            results.append(KnowledgeItem(
                                content=f"[arXiv] {title}: {summary}",
                                source="arxiv",
                                confidence=0.95,
                                metadata={
                                    "title": title,
                                    "url": arxiv_id,
                                    "type": "paper_abstract"
                                }
                            ))
                
                logger.info(f"📄 arXiv: 获取到 {len(results)} 篇论文摘要")
        except Exception as e:
            logger.debug(f"arXiv查询失败: {e}")
        
        return results
    
    def _extract_search_terms(self, query: str) -> List[str]:
        query = re.sub(r'[?？。.!！，,的了吗呢]', ' ', query)
        words = query.split()
        return [w for w in words if len(w) >= 2][:5]
    
    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import requests
            r = requests.get("http://export.arxiv.org/api/query?search_query=all:test&max_results=1", timeout=5)
            self._available = r.status_code == 200
        except:
            self._available = False
        return self._available
    
    def get_cost_estimate(self, query: str) -> float:
        return 0.0


class MultiSourceSearchLearner(ExternalLearnerBase):
    """多源深度搜索学习器 — DuckDuckGo站点限定搜索 + URL深度抓取"""
    
    def __init__(self, region: str = "cn-zh"):
        self.region = region
        self._available = None
        self._ddg_available = None
    
    def learn(self, query: str, context: Optional[str] = None, max_results: int = 5) -> List[KnowledgeItem]:
        results = []
        
        try:
            from infrastructure.stealth_search import search_web_stealthy
            stealth_results = search_web_stealthy(query, max_results=max_results)
            if stealth_results:
                for r in stealth_results:
                    results.append(KnowledgeItem(
                        content=f"{r['title']}: {r['snippet']}" if r.get('title') else r.get('snippet', ''),
                        source=r.get('source', 'stealth'),
                        confidence=0.75,
                        metadata={"title": r.get('title', ''), "url": r.get('link', ''), "query": query}
                    ))
                if len(results) >= max_results:
                    logger.info(f"🌐 隐身搜索: 获取到 {len(results)} 条结果")
                    return results[:max_results * 2]
        except Exception as e:
            logger.debug(f"隐身搜索失败: {e}")
        
        try:
            if _DDGS is None:
                return results
        except:
            return results
        
        site_groups = self._select_site_groups(query)
        
        search_queries = self._build_site_queries(query, site_groups)
        search_queries.insert(0, query)
        
        seen_urls = set()
        
        for sq in search_queries[:4]:
            try:
                with _DDGS() as ddgs:
                    search_results = list(ddgs.text(sq, region=self.region, max_results=3))
                
                for item in search_results:
                    href = item.get("href", "")
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)
                    
                    title = item.get("title", "")
                    body = item.get("body", "")
                    source_confidence = self._get_source_confidence(href)
                    
                    if body and len(body) > 30:
                        content = f"{title}: {body}" if title else body
                        results.append(KnowledgeItem(
                            content=content[:500],
                            source=self._extract_source_name(href),
                            confidence=source_confidence,
                            metadata={"title": title, "url": href, "query": sq}
                        ))
                    
                    if source_confidence >= 0.85 and len(results) < max_results + 3:
                        deep_content = self._deep_fetch(href)
                        if deep_content:
                            results.append(KnowledgeItem(
                                content=deep_content[:800],
                                source=f"deep:{self._extract_source_name(href)}",
                                confidence=source_confidence + 0.05,
                                metadata={"title": title, "url": href, "type": "deep_fetch"}
                            ))
                
            except Exception as e:
                logger.debug(f"多源搜索失败 '{sq[:30]}': {e}")
            
            if len(results) >= max_results * 2:
                break
        
        results.sort(key=lambda x: x.confidence, reverse=True)
        logger.info(f"🌐 多源搜索: 获取到 {len(results)} 条结果 (搜索了{len(search_queries[:4])}个查询)")
        return results[:max_results * 2]
    
    def _select_site_groups(self, query: str) -> List[str]:
        groups = set()
        for kw, group in QUERY_TYPE_SITES.items():
            if kw in query:
                groups.add(group)
        if not groups:
            groups = {"academic", "tech_cn"}
        return list(groups)
    
    def _build_site_queries(self, query: str, site_groups: List[str]) -> List[str]:
        queries = []
        for group in site_groups:
            sites = SITE_SEARCH_MAP.get(group, [])
            if sites:
                site_str = " OR ".join(f"site:{s}" for s in sites[:3])
                queries.append(f"{query} {site_str}")
        return queries
    
    def _get_source_confidence(self, url: str) -> float:
        for domain, conf in SOURCE_QUALITY.items():
            if domain in url:
                return conf
        return 0.65
    
    def _extract_source_name(self, url: str) -> str:
        for domain in SOURCE_QUALITY:
            if domain in url:
                return domain.split(".")[0]
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc.split(".")[-2] if url else "web"
        except:
            return "web"
    
    def _deep_fetch(self, url: str) -> Optional[str]:
        try:
            import requests
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            }
            response = requests.get(url, headers=headers, timeout=8)
            if response.status_code != 200:
                return None
            
            text = response.text
            
            if "arxiv.org" in url:
                content = self._parse_arxiv_html(text)
                if content:
                    return content
            
            content = self._strip_html(text)
            return content[:1000] if content and len(content) > 100 else None
        except Exception as e:
            logger.debug(f"深度抓取失败 {url[:50]}: {e}")
            return None
    
    def _parse_arxiv_html(self, html: str) -> Optional[str]:
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(html)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            summary = root.find(".//atom:summary", ns)
            title = root.find(".//atom:title", ns)
            if summary is not None and summary.text:
                t = title.text.strip() if title is not None else ""
                return f"[arXiv深度] {t}: {summary.text.strip()[:500]}"
        except:
            pass
        return None
    
    def _strip_html(self, html: str) -> Optional[str]:
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        text = re.sub(r'&[a-zA-Z]+;', ' ', text)
        return text if len(text) > 100 else None
    
    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        self._available = _DDGS is not None
        return self._available
    
    def get_cost_estimate(self, query: str) -> float:
        return 0.0


class CompositeLearner(ExternalLearnerBase):
    """
    组合学习器
    同时使用多个学习源，按优先级返回结果
    """
    
    def __init__(self, learners: List[ExternalLearnerBase]):
        self.learners = learners
    
    def learn(
        self,
        query: str,
        context: Optional[str] = None,
        max_results: int = 5
    ) -> List[KnowledgeItem]:
        """
        从多个学习源获取知识
        
        Args:
            query: 查询
            context: 上下文
            max_results: 每个学习源最多返回条目数
        
        Returns:
            合并后的知识条目列表，按置信度降序
        """
        all_results = []
        
        for learner in self.learners:
            if learner.is_available():
                try:
                    results = learner.learn(query, context, max_results)
                    all_results.extend(results)
                except Exception as e:
                    logger.warning(f"学习器 {learner.get_name()} 失败: {e}")
        
        all_results.sort(key=lambda x: x.confidence, reverse=True)
        
        return all_results[:max_results * 2]
    
    def is_available(self) -> bool:
        """至少有一个学习器可用"""
        return any(learner.is_available() for learner in self.learners)
    
    def get_cost_estimate(self, query: str) -> float:
        """总成本为各学习器成本之和"""
        return sum(
            learner.get_cost_estimate(query)
            for learner in self.learners
            if learner.is_available()
        )


wikipedia_learner = WikipediaLearner()
ddg_search_learner = DDGSearchLearner()
arxiv_learner = ArxivLearner()
multi_source_learner = MultiSourceSearchLearner()
composite_learner = CompositeLearner([wikipedia_learner, arxiv_learner, multi_source_learner, ddg_search_learner])