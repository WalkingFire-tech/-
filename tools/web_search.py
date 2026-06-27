"""
安全网络搜索工具 - 支持白名单过滤和内容验证
遵循安全第一原则，所有网络访问需经过验证
"""
from typing import List, Dict, Any
from tools.base import Tool, ToolCategory, Parameter, ToolResult
from loguru import logger
import re


class WebSearchTool(Tool):
    """安全网络搜索工具"""
    
    SEARCH_WHITELIST = [
        "wikipedia.org",
        "stackoverflow.com",
        "github.com",
        "docs.python.org",
        "developer.mozilla.org",
        "arxiv.org",
        "medium.com",
        "towardsdatascience.com",
        "pytorch.org",
        "tensorflow.org",
        "huggingface.co",
        "openai.com",
        "anthropic.com"
    ]
    
    CONTENT_FILTERS = [
        r"password\s*=",
        r"api[_-]?key\s*=",
        r"secret\s*=",
        r"token\s*=",
        r"credential",
        r"private[_-]?key"
    ]
    
    def __init__(self):
        super().__init__()
        self._search_engine = None
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "安全网络搜索工具，支持白名单过滤和内容验证"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SEARCH
    
    @property
    def parameters(self) -> List[Parameter]:
        return [
            Parameter(
                name="query",
                type="str",
                description="搜索查询文本",
                required=True
            ),
            Parameter(
                name="max_results",
                type="int",
                description="最大返回结果数",
                required=False,
                default=5
            ),
            Parameter(
                name="use_whitelist",
                type="bool",
                description="是否启用白名单过滤",
                required=False,
                default=True
            )
        ]
    
    def _init_search_engine(self):
        if self._search_engine is None:
            try:
                from ddgs import DDGS
                self._search_engine = DDGS()
                return True
            except ImportError:
                pass
            
            try:
                from ddgs import DDGS
                self._search_engine = DDGS()
                return True
            except ImportError:
                pass
            
            logger.warning("搜索库未安装，请运行: pip install ddgs 或 pip install duckduckgo-search")
            return False
        return True
    
    def _is_safe_content(self, text: str) -> bool:
        if not text:
            return True
        
        for pattern in self.CONTENT_FILTERS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"检测到敏感内容，已过滤: {pattern}")
                return False
        return True
    
    def _filter_by_whitelist(self, url: str) -> bool:
        for domain in self.SEARCH_WHITELIST:
            if domain in url:
                return True
        return False
    
    def _sanitize_result(self, result: Dict) -> Dict:
        sanitized = {
            "title": result.get("title", ""),
            "href": result.get("href", ""),
            "body": result.get("body", "")[:500]
        }
        
        if not self._is_safe_content(sanitized["body"]):
            sanitized["body"] = "[内容已过滤：包含敏感信息]"
            sanitized["filtered"] = True
        
        return sanitized
    
    def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 5)
        use_whitelist = kwargs.get("use_whitelist", True)
        
        if not self._init_search_engine():
            return ToolResult(
                success=False,
                output=None,
                error="搜索引擎初始化失败"
            )
        
        try:
            logger.info(f"执行网络搜索: {query}")
            
            results = []
            search_results = self._search_engine.text(query, max_results=max_results * 2)
            
            for result in search_results:
                url = result.get("href", "")
                
                if use_whitelist and not self._filter_by_whitelist(url):
                    continue
                
                sanitized = self._sanitize_result(result)
                results.append(sanitized)
                
                if len(results) >= max_results:
                    break
            
            logger.info(f"搜索完成，返回{len(results)}条结果")
            
            return ToolResult(
                success=True,
                output={
                    "query": query,
                    "results": results,
                    "total": len(results),
                    "whitelist_enabled": use_whitelist
                },
                metadata={
                    "search_engine": "duckduckgo",
                    "filtered_count": len(search_results) - len(results)
                }
            )
            
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )


class QuickSearchTool(Tool):
    """快速搜索工具（仅返回摘要）"""
    
    def __init__(self):
        super().__init__()
        self._web_search = WebSearchTool()
    
    @property
    def name(self) -> str:
        return "quick_search"
    
    @property
    def description(self) -> str:
        return "快速搜索并返回简洁摘要"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.SEARCH
    
    @property
    def parameters(self) -> List[Parameter]:
        return [
            Parameter(
                name="query",
                type="str",
                description="搜索查询",
                required=True
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        
        result = self._web_search.execute(query=query, max_results=3)
        
        if not result.success:
            return result
        
        output = result.output
        summaries = []
        
        for item in output.get("results", []):
            summary = f"【{item['title']}】{item['body'][:150]}..."
            summaries.append(summary)
        
        return ToolResult(
            success=True,
            output={
                "query": query,
                "summary": "\n\n".join(summaries),
                "sources": [item["href"] for item in output.get("results", [])]
            }
        )