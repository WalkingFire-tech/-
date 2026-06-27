"""
外部学习器实现
包含Wikipedia、DuckDuckGo等知识源
"""
from typing import List, Optional
import re
from core.external_learner_base import ExternalLearnerBase, KnowledgeItem

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


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
        
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            logger.warning("duckduckgo_search库未安装，DDGSearchLearner不可用")
            return results
        
        enhanced_query = query
        if context:
            keywords = self._extract_keywords(context)
            if keywords:
                enhanced_query = f"{query} {' '.join(keywords[:2])}"
        
        try:
            with DDGS() as ddgs:
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
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text("test", max_results=1))
            self._available = True
        except:
            self._available = False
        
        return self._available
    
    def get_cost_estimate(self, query: str) -> float:
        """预估成本（DuckDuckGo免费，成本为0）"""
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
composite_learner = CompositeLearner([wikipedia_learner, ddg_search_learner])