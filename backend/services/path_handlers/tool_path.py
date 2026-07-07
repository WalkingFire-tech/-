import re
import asyncio
from typing import Optional
from loguru import logger
from backend.services.path_handlers._shared import _fast_executor


async def fetch_tool_results(query: str, intent_type: str = "", tool_intent: bool = False) -> Optional[list]:
    """路径I：工具调用框架（P0-4）— 使用独立线程池，不阻塞共享_executor"""
    try:
        from core.tool_registry import tool_executor, tool_registry
        tool_names = tool_registry.plan_tools(query, intent_type)
        if not tool_names:
            return None
        tool_names = tool_names[:5]
        if tool_intent:
            code_tools = [n for n in tool_names if n in ("file_reader", "project_scanner", "code_indexer", "dependency_analyzer")]
            other_tools = [n for n in tool_names if n not in ("file_reader", "project_scanner", "code_indexer", "dependency_analyzer")]
            tool_names = code_tools + other_tools[:3]
        params = extract_tool_params(query, intent_type)
        results = await tool_executor.execute_parallel(tool_names, params, total_timeout=20.0)
        candidates = []
        for r in results:
            c = r.to_candidate()
            if c:
                candidates.append(c)
            try:
                from core.memory.layered_memory import layered_memory
                layered_memory.record_tool_usage(
                    r.source, query, r.success, r.quality, r.duration_ms
                )
            except Exception:
                pass
        return candidates if candidates else None
    except Exception as e:
        logger.debug(f"工具调用异常: {e}")
        return None


def query_needs_tools(query: str) -> bool:
    """判断用户查询是否需要工具调用（代码/文件/项目分析相关）"""
    ql = query.lower()
    tool_triggers = [
        "读取", "打开", "查看文件", "文件内容", "看看文件", "读一下",
        "项目结构", "目录树", "技术栈", "项目概览", "有哪些文件",
        "在哪定义", "函数在哪", "类在哪", "代码索引", "代码结构",
        "依赖", "调用链", "影响范围", "模块关系",
        "readme", "read file", "open file", "show file",
        "project structure", "scan project", "dependency",
        "where defined", "code index",
    ]
    if any(t in ql for t in tool_triggers):
        return True
    if re.search(r'[\w/\\]+\.\w{1,6}', query):
        return True
    return False


def extract_tool_params(query: str, intent_type: str = "") -> dict:
    """从用户消息中智能提取工具参数"""
    params = {"query": query}

    path_pattern = r'(?:读取|打开|查看|看看|读一下|read|open|show|cat)\s*[`"\']?([\w/\\.-]+\.\w{1,6})[`"\']?'
    path_match = re.search(path_pattern, query, re.IGNORECASE)
    if path_match:
        params["query"] = path_match.group(1).strip()
    else:
        file_pattern = r'([\w/\\]+\.\w{1,6})'
        file_match = re.search(file_pattern, query)
        if file_match:
            params["query"] = file_match.group(1).strip()

    if "项目结构" in query or "目录树" in query or "project structure" in query.lower():
        params.setdefault("_tool_hint", "project_scanner")
    if "依赖" in query or "dependency" in query.lower():
        params.setdefault("_tool_hint", "dependency_analyzer")

    return params