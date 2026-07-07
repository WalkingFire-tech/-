"""
系统级工具调用框架 (P0-4)

架构：
- ToolInterface: 工具接口基类（name/description/parameters/execute）
- ToolRegistry: 工具注册器（注册/查询/规划）
- ToolExecutor: 工具执行器（异步执行/超时/缓存/事件发布）

与 core/tool_manager.py 的关系：
- tool_manager.py 管理用户自定义代码工具（动态Python代码，沙箱执行）
- 本模块管理系统级工具（预定义接口，标准化调用）
- 两者通过 ToolRegistry 统一入口
"""

import asyncio
import concurrent.futures
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger

_tool_executor_pool = concurrent.futures.ThreadPoolExecutor(
    max_workers=8, thread_name_prefix="tool_exec"
)


def run_tool_sync(func, *args, timeout=10, **kwargs):
    """在独立线程池中运行同步函数，使用concurrent.futures.wait实现真正超时。
    超时后线程仍在运行但结果被丢弃，不会阻塞共享线程池。
    注意：此函数是同步阻塞的，在async上下文中请使用run_tool_async。"""
    future = _tool_executor_pool.submit(func, *args, **kwargs)
    done, _ = concurrent.futures.wait(
        [future], timeout=timeout,
        return_when=concurrent.futures.FIRST_COMPLETED
    )
    if not done:
        logger.warning(f"工具同步调用超时({timeout}s): {func.__name__ if hasattr(func, '__name__') else func}")
        return None
    return future.result()


async def run_tool_async(func, *args, timeout=10, **kwargs):
    """异步包装：在独立线程池中运行同步函数，不阻塞共享_executor。
    使用独立_tool_executor_pool，即使工具卡死也不影响主线程池。"""
    loop = asyncio.get_running_loop()
    try:
        if kwargs:
            result = await asyncio.wait_for(
                loop.run_in_executor(_tool_executor_pool, lambda: func(*args, **kwargs)),
                timeout=timeout
            )
        else:
            result = await asyncio.wait_for(
                loop.run_in_executor(_tool_executor_pool, func, *args),
                timeout=timeout
            )
        return result
    except asyncio.TimeoutError:
        logger.warning(f"工具异步调用超时({timeout}s): {func.__name__ if hasattr(func, '__name__') else func}")
        return None


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str = ""
    source: str = ""
    quality: int = 0
    duration_ms: float = 0.0
    from_cache: bool = False
    metadata: Dict = field(default_factory=dict)

    def to_candidate(self) -> Optional[Dict]:
        if not self.success or not self.data:
            return None
        response = self.data if isinstance(self.data, str) else str(self.data)
        if len(response) < 5:
            return None
        return {
            "source": self.source,
            "response": response,
            "quality": self.quality,
            "metadata": self.metadata,
        }


class ToolInterface(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    @abstractmethod
    def parameters(self) -> Dict:
        ...

    @property
    def timeout(self) -> float:
        return 15.0

    @property
    def category(self) -> str:
        return "general"

    @property
    def priority(self) -> int:
        return 50

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        ...

    def can_handle(self, query: str, intent_type: str = "") -> bool:
        return True


class ToolRegistry:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._tools: Dict[str, ToolInterface] = {}
                cls._instance._categories: Dict[str, List[str]] = {}
                cls._instance._initialized = False
            return cls._instance

    def register(self, tool: ToolInterface) -> bool:
        name = tool.name
        if name in self._tools:
            logger.warning(f"工具已存在，覆盖: {name}")
        self._tools[name] = tool
        cat = tool.category
        if cat not in self._categories:
            self._categories[cat] = []
        if name not in self._categories[cat]:
            self._categories[cat].append(name)
        logger.debug(f"工具已注册: {name} (分类:{cat}, 超时:{tool.timeout}s)")
        return True

    def unregister(self, name: str) -> bool:
        if name not in self._tools:
            return False
        tool = self._tools.pop(name)
        cat = tool.category
        if cat in self._categories and name in self._categories[cat]:
            self._categories[cat].remove(name)
        logger.debug(f"工具已注销: {name}")
        return True

    def get(self, name: str) -> Optional[ToolInterface]:
        return self._tools.get(name)

    def list_tools(self, category: str = None) -> List[Dict]:
        tools = []
        for name, tool in self._tools.items():
            if category and tool.category != category:
                continue
            tools.append({
                "name": name,
                "description": tool.description,
                "category": tool.category,
                "timeout": tool.timeout,
                "priority": tool.priority,
                "parameters": tool.parameters,
            })
        return sorted(tools, key=lambda t: t["priority"], reverse=True)

    def plan_tools(self, query: str, intent_type: str = "",
                   source_priority: List[str] = None) -> List[str]:
        scored: List[Tuple[str, int]] = []
        for name, tool in self._tools.items():
            if not tool.can_handle(query, intent_type):
                continue
            score = tool.priority
            if source_priority:
                for i, src in enumerate(source_priority):
                    if src.lower() in name.lower() or name.lower() in src.lower():
                        score += max(0, 30 - i * 10)
                        break
            if intent_type and intent_type in tool.category:
                score += 20
            scored.append((name, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in scored]

    def get_categories(self) -> Dict[str, List[str]]:
        return dict(self._categories)

    @property
    def tool_count(self) -> int:
        return len(self._tools)


class ToolExecutor:
    def __init__(self, registry: ToolRegistry = None, enable_cache: bool = True):
        self.registry = registry or ToolRegistry()
        self.enable_cache = enable_cache
        self._cache = None
        self._stats: Dict[str, Dict] = {}
        if enable_cache:
            try:
                from infrastructure.tool_cache import ToolResultCache
                self._cache = ToolResultCache(db_path="data/tool_cache.db")
                logger.info("工具执行器缓存已启用")
            except Exception as e:
                logger.warning(f"工具缓存初始化失败，禁用缓存: {e}")
                self._cache = None

    async def execute(self, tool_name: str, params: Dict = None,
                       timeout_override: float = None) -> ToolResult:
        params = params or {}
        tool = self.registry.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"工具不存在: {tool_name}",
                              source=tool_name)

        if self._cache:
            try:
                cached = self._cache.get(tool_name, params)
                if cached is not None:
                    return ToolResult(
                        success=True, data=cached.get("output", ""),
                        source=f"{tool_name}(cached)", quality=cached.get("quality", 50),
                        from_cache=True, metadata=cached.get("metadata", {}),
                    )
            except Exception:
                pass

        start = time.time()
        timeout = timeout_override or tool.timeout
        try:
            result = await asyncio.wait_for(tool.execute(**params), timeout=timeout)
            result.duration_ms = (time.time() - start) * 1000
            self._record_stat(tool_name, True, result.duration_ms)

            if self._cache and result.success and result.data:
                try:
                    self._cache.set(tool_name, params, {
                        "output": result.data if isinstance(result.data, str) else str(result.data),
                        "quality": result.quality,
                        "metadata": result.metadata,
                    }, quality_score=result.quality / 100.0)
                except Exception:
                    pass

            self._publish_event(tool_name, params, result)
            return result

        except asyncio.TimeoutError:
            duration = (time.time() - start) * 1000
            self._record_stat(tool_name, False, duration)
            logger.warning(f"工具执行超时: {tool_name} ({timeout}s)")
            return ToolResult(success=False, error=f"执行超时({timeout}s)",
                              source=tool_name, duration_ms=duration)
        except Exception as e:
            duration = (time.time() - start) * 1000
            self._record_stat(tool_name, False, duration)
            logger.error(f"工具执行异常: {tool_name} - {e}")
            return ToolResult(success=False, error=str(e),
                              source=tool_name, duration_ms=duration)

    async def execute_parallel(self, tool_names: List[str],
                               params: Dict = None,
                               total_timeout: float = 20.0) -> List[ToolResult]:
        params = params or {}
        tasks = [self.execute(name, params) for name in tool_names]
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=total_timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"工具并行执行总超时({total_timeout}s), 工具: {tool_names}")
            return [ToolResult(success=False, error=f"并行执行超时({total_timeout}s)",
                               source=name) for name in tool_names]
        output = []
        for r in results:
            if isinstance(r, ToolResult):
                output.append(r)
            elif isinstance(r, Exception):
                output.append(ToolResult(success=False, error=str(r)))
            else:
                output.append(ToolResult(success=False, error="未知结果类型"))
        return output

    def _record_stat(self, tool_name: str, success: bool, duration_ms: float):
        if tool_name not in self._stats:
            self._stats[tool_name] = {"calls": 0, "successes": 0, "total_ms": 0.0}
        s = self._stats[tool_name]
        s["calls"] += 1
        if success:
            s["successes"] += 1
        s["total_ms"] += duration_ms

    def _publish_event(self, tool_name: str, params: Dict, result: ToolResult):
        try:
            from infrastructure.event_bus import bus
            bus.publish("ToolResult", {
                "tool": tool_name,
                "success": result.success,
                "quality": result.quality,
                "duration_ms": result.duration_ms,
            })
        except Exception:
            pass

    def get_stats(self) -> Dict:
        stats = {}
        for name, s in self._stats.items():
            stats[name] = {
                "calls": s["calls"],
                "success_rate": s["successes"] / max(1, s["calls"]),
                "avg_ms": s["total_ms"] / max(1, s["calls"]),
            }
        return stats


tool_registry = ToolRegistry()
tool_executor = ToolExecutor(registry=tool_registry)


def register_builtin_tools():
    from core.tools.web_search_tool import WebSearchTool
    from core.tools.calculator_tool import CalculatorTool
    from core.tools.code_executor_tool import CodeExecutorTool
    from core.tools.knowledge_lookup_tool import KnowledgeLookupTool
    from core.tools.fact_check_tool import FactCheckTool
    from core.tools.project_scanner_tool import ProjectScannerTool
    from core.tools.code_indexer_tool import CodeIndexerTool
    from core.tools.dependency_analyzer_tool import DependencyAnalyzerTool
    from core.tools.file_reader_tool import FileReaderTool

    for tool_cls in [WebSearchTool, CalculatorTool, CodeExecutorTool,
                     KnowledgeLookupTool, FactCheckTool,
                     ProjectScannerTool, CodeIndexerTool, DependencyAnalyzerTool,
                     FileReaderTool]:
        try:
            tool = tool_cls()
            tool_registry.register(tool)
            logger.info(f"内置工具已注册: {tool.name}")
        except Exception as e:
            logger.warning(f"内置工具注册失败 {tool_cls.__name__}: {e}")

    try:
        from core.tool_manager import tool_manager
        user_tools = tool_manager.list_tools(include_disabled=False)
        registered_count = 0
        MAX_USER_TOOLS = 20
        for ut in user_tools:
            if registered_count >= MAX_USER_TOOLS:
                logger.warning(f"用户工具注册已达上限({MAX_USER_TOOLS})，跳过剩余{len(user_tools)-registered_count}个")
                break
            usage = ut.get("usage_count", 0)
            if usage == 0 and ut.get("name", "").startswith("auto_tool_"):
                continue
            try:
                _register_user_tool(ut["name"])
                registered_count += 1
            except Exception as e:
                logger.debug(f"用户工具注册跳过 {ut['name']}: {e}")
    except Exception:
        pass

    logger.info(f"工具注册完成: {tool_registry.tool_count}个工具")


def _register_user_tool(tool_name: str):
    from core.tool_manager import tool_manager

    info = tool_manager.get_tool_info(tool_name)
    desc = info.get("description", f"用户工具: {tool_name}") if info else f"用户工具: {tool_name}"

    class UserToolWrapper(ToolInterface):
        __tool_name = tool_name
        __desc = desc

        @property
        def name(self) -> str:
            return f"user_{self.__tool_name}"

        @property
        def description(self) -> str:
            return self.__desc

        @property
        def parameters(self) -> Dict:
            return {"query": {"type": "string", "description": "输入参数"}}

        @property
        def category(self) -> str:
            return "user"

        @property
        def priority(self) -> int:
            return 30

        async def execute(self, **kwargs) -> ToolResult:
            query = kwargs.get("query", kwargs.get("input", ""))
            try:
                result = await run_tool_async(tool_manager.execute_tool, self.__tool_name, query, timeout=10)
                if result is None:
                    return ToolResult(success=False, error="用户工具执行超时", source=f"用户工具:{self.__tool_name}")
                return ToolResult(
                    success=True, data=str(result),
                    source=f"用户工具:{self.__tool_name}", quality=40,
                )
            except Exception as e:
                return ToolResult(success=False, error=str(e), source=f"用户工具:{self.__tool_name}")

    wrapper = UserToolWrapper()
    tool_registry.register(wrapper)