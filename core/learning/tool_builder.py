"""
工具自我构建 - 从需求中生成长久工具

核心理态：工具不是预设的，而是从需求中自然生长

安全约束：
- exec()执行LLM生成的代码时，使用受限全局命名空间
- 禁止导入os/sys/subprocess/shutil等危险模块
- 禁止文件写操作(open with 'w'/'a')、网络操作(socket)
- 执行超时保护（独立线程+超时）
"""
import re as _re
import signal
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
from loguru import logger


_SANDBOX_BLOCKED_MODULES = frozenset({
    "os", "sys", "subprocess", "shutil", "pathlib",
    "socket", "http", "urllib", "requests",
    "ctypes", "multiprocessing", "pickle", "shelve",
    "importlib", "runpy", "code", "codeop",
    "builtins",
})

_SANDBOX_BLOCKED_BUILTINS = frozenset({
    "exec", "eval", "compile", "__import__", "open",
    "globals", "locals", "vars", "dir",
    "breakpoint", "exit", "quit",
})

_SANDBOX_SAFE_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
    "chr": chr, "dict": dict, "divmod": divmod, "enumerate": enumerate,
    "filter": filter, "float": float, "format": format, "frozenset": frozenset,
    "hash": hash, "hex": hex, "int": int, "isinstance": isinstance,
    "issubclass": issubclass, "iter": iter, "len": len, "list": list,
    "map": map, "max": max, "min": min, "next": next, "oct": oct,
    "ord": ord, "pow": pow, "print": print, "range": range,
    "repr": repr, "reversed": reversed, "round": round, "set": set,
    "slice": slice, "sorted": sorted, "str": str, "sum": sum,
    "tuple": tuple, "type": type, "zip": zip,
    "True": True, "False": False, "None": None,
    "ValueError": ValueError, "TypeError": TypeError, "KeyError": KeyError,
    "IndexError": IndexError, "AttributeError": AttributeError,
    "RuntimeError": RuntimeError, "Exception": Exception,
    "StopIteration": StopIteration, "NotImplementedError": NotImplementedError,
}


def _validate_tool_code(code: str) -> List[str]:
    """静态检查工具代码是否包含危险操作"""
    violations = []
    for mod in _SANDBOX_BLOCKED_MODULES:
        if _re.search(rf'\bimport\s+{mod}\b', code) or _re.search(rf'\bfrom\s+{mod}\b', code):
            violations.append(f"禁止导入模块: {mod}")
    if _re.search(r'\bopen\s*\(', code):
        if _re.search(r"open\s*\([^)]*['\"][wa]", code):
            violations.append("禁止文件写操作")
    if _re.search(r'\bsocket\b', code):
        violations.append("禁止网络操作")
    if _re.search(r'\b__import__\s*\(', code):
        violations.append("禁止动态导入")
    if _re.search(r'\bos\.system\b', code) or _re.search(r'\bos\.popen\b', code):
        violations.append("禁止系统命令执行")
    return violations


def _sandbox_exec(code: str, timeout: float = 5.0) -> tuple:
    """
    在沙箱中执行代码，返回 (local_namespace, errors)
    - 受限全局命名空间（无os/sys/subprocess等）
    - 超时保护（独立线程）
    """
    violations = _validate_tool_code(code)
    if violations:
        return {}, [f"安全检查未通过: {'; '.join(violations)}"]

    sandbox_globals = {"__builtins__": dict(_SANDBOX_SAFE_BUILTINS)}
    sandbox_globals["re"] = _re
    try:
        import math
        sandbox_globals["math"] = math
    except ImportError:
        pass
    try:
        import json
        sandbox_globals["json"] = json
    except ImportError:
        pass
    try:
        import datetime as _dt
        sandbox_globals["datetime"] = _dt
    except ImportError:
        pass

    local_namespace = {}
    errors = []

    result_holder = {"done": False, "error": None}

    def _run():
        try:
            exec(code, sandbox_globals, local_namespace)
            result_holder["done"] = True
        except Exception as e:
            result_holder["error"] = str(e)
            result_holder["done"] = True

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=timeout)

    if not result_holder["done"]:
        errors.append(f"代码执行超时({timeout}s)")
        return {}, errors
    if result_holder["error"]:
        errors.append(f"代码执行错误: {result_holder['error']}")
        return {}, errors

    return local_namespace, errors


class ToolStatus(Enum):
    DRAFT = "draft"
    TESTING = "testing"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class NeedPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ToolNeed:
    need_id: str
    description: str
    priority: NeedPriority
    context: Dict[str, Any] = field(default_factory=dict)
    frequency: int = 1
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)


@dataclass
class Tool:
    tool_id: str
    name: str
    description: str
    implementation: Optional[Callable] = None
    code: str = ""
    status: ToolStatus = ToolStatus.DRAFT
    satisfies_needs: List[str] = field(default_factory=list)
    usage_count: int = 0
    success_rate: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class BuildResult:
    success: bool
    tool: Optional[Tool]
    errors: List[str]
    test_results: Dict[str, Any]


class ToolSelfBuilder:
    """
    工具自我构建器
    
    从需求模式中自动生成工具
    """
    
    def __init__(self, need_threshold: int = 3):
        self.need_threshold = need_threshold
        self.needs: Dict[str, ToolNeed] = {}
        self.tools: Dict[str, Tool] = {}
        self.tool_templates: Dict[str, str] = {}
        self.test_cases: Dict[str, Callable] = {}
        self._setup_default_templates()
    
    def record_success(self, source: str, query: str, response_snippet: str = ""):
        need_id = self._hash_description(f"{source}:{query[:50]}")
        if need_id in self.needs:
            self.needs[need_id].frequency += 1
        else:
            self.needs[need_id] = ToolNeed(
                need_id=need_id,
                description=f"成功路径:{source} → {query[:60]}",
                priority=NeedPriority.MEDIUM,
                frequency=1,
                context={"source": source, "query": query[:100], "response_hint": response_snippet[:100]}
            )
    
    def _setup_default_templates(self):
        self.tool_templates = {
            "data_transform": '''
def {name}(data):
    """Auto-generated: {description}"""
    if not data:
        return data
    result = []
    for item in data:
        transformed = {{}}
        for key, value in item.items():
            transformed[key] = {transform_logic}
        result.append(transformed)
    return result
''',
            "validator": '''
def {name}(value):
    """Auto-generated: {description}"""
    if value is None:
        return False
    {validation_logic}
    return True
''',
            "filter": '''
def {name}(items):
    """Auto-generated: {description}"""
    return [item for item in items if {filter_condition}]
''',
            "aggregator": '''
def {name}(items):
    """Auto-generated: {description}"""
    if not items:
        return {default_value}
    return {aggregation_logic}
''',
        }
    
    def observe_need(
        self,
        description: str,
        priority: NeedPriority = NeedPriority.MEDIUM,
        context: Dict[str, Any] = None,
    ) -> str:
        need_key = self._generate_need_key(description)
        
        if need_key in self.needs:
            need = self.needs[need_key]
            need.frequency += 1
            need.last_seen = datetime.now()
            if priority.value > need.priority.value:
                need.priority = priority
        else:
            need_id = f"need_{len(self.needs)}"
            self.needs[need_key] = ToolNeed(
                need_id=need_id,
                description=description,
                priority=priority,
                context=context or {},
            )
        
        return need_key
    
    def _generate_need_key(self, description: str) -> str:
        import hashlib
        return hashlib.md5(description.encode()).hexdigest()[:8]
    
    def identify_tool_opportunities(self) -> List[ToolNeed]:
        candidates = []
        
        for need in self.needs.values():
            if need.frequency >= self.need_threshold:
                candidates.append(need)
        
        candidates.sort(key=lambda n: (n.priority.value, n.frequency), reverse=True)
        
        return candidates
    
    def build_tool(
        self,
        need: ToolNeed,
        template_type: str = None,
        custom_code: str = None,
    ) -> BuildResult:
        tool_id = f"tool_{len(self.tools)}"
        
        errors = []
        test_results = {}
        
        if custom_code:
            code = custom_code
        elif template_type and template_type in self.tool_templates:
            code = self._instantiate_template(
                template_type,
                need.description,
            )
        else:
            code = self._generate_basic_tool(need.description)
        
        try:
            local_namespace, exec_errors = _sandbox_exec(code, timeout=5.0)
            errors.extend(exec_errors)
            
            func_name = self._extract_function_name(code)
            if func_name and func_name in local_namespace:
                implementation = local_namespace[func_name]
            else:
                implementation = None
                errors.append("无法提取工具函数")
        except Exception as e:
            implementation = None
            errors.append(f"代码生成错误: {str(e)}")
        
        tool = Tool(
            tool_id=tool_id,
            name=self._generate_tool_name(need.description),
            description=need.description,
            implementation=implementation,
            code=code,
            status=ToolStatus.DRAFT if errors else ToolStatus.TESTING,
            satisfies_needs=[need.need_id],
        )
        
        if not errors:
            test_results = self._test_tool(tool)
            if test_results.get("passed", False):
                tool.status = ToolStatus.ACTIVE
            else:
                tool.status = ToolStatus.TESTING
                errors.append("工具测试未通过")
        
        self.tools[tool_id] = tool

        if tool.status == ToolStatus.ACTIVE:
            try:
                from core.tool_registry import tool_registry
                tool_registry.register(self._wrap_tool_for_registry(tool))
                logger.info(f"ToolBuilder: 工具 {tool.name} 已自动注册到tool_registry")
            except Exception as e:
                logger.error(f"ToolBuilder自动注册失败: {e}")
        
        return BuildResult(
            success=len(errors) == 0 and tool.status == ToolStatus.ACTIVE,
            tool=tool,
            errors=errors,
            test_results=test_results,
        )
    
    def _instantiate_template(self, template_type: str, description: str) -> str:
        template = self.tool_templates[template_type]
        name = self._generate_tool_name(description)
        
        return template.format(
            name=name,
            description=description,
            transform_logic="value",
            validation_logic="pass",
            filter_condition="True",
            aggregation_logic="sum(items)",
            default_value="0",
        )
    
    def _generate_basic_tool(self, description: str) -> str:
        name = self._generate_tool_name(description)
        llm_code = self._synthesize_tool_code(name, description)
        if llm_code:
            return llm_code
        return f'''
def {name}(input_data):
    """Auto-generated tool: {description}"""
    # TODO: Implement based on actual requirements
    return input_data
'''
    
    def _synthesize_tool_code(self, func_name: str, description: str) -> Optional[str]:
        try:
            from adapters.llm.ollama_adapter import ollama_chat_request
            from infrastructure.config_manager import config_manager
            base_url = config_manager.get("ollama.base_url", "http://localhost:11434")
            model = config_manager.get("ollama.model", "qwen2.5-coder:7b")
            prompt = f"""你需要生成一个Python函数来解决以下问题。只输出函数代码，不要解释。

要求：
- 函数名: {func_name}
- 功能: {description}
- 必须是纯Python，可用标准库
- 函数接收一个dict参数，包含用户输入的query等信息
- 函数返回一个dict，包含success(bool)、data(str)、source(str)字段
- 如果需要访问硬件/系统，使用subprocess或标准库
- 代码必须安全，不执行危险操作（不删文件、不格式化等）

示例格式：
def {func_name}(params: dict) -> dict:
    query = params.get("query", "")
    # ... 实现逻辑 ...
    return {{"success": True, "data": result_text, "source": "{func_name}"}}

问题: {description}
"""
            result = ollama_chat_request(base_url, model, prompt, timeout=60)
            if result and result.get("content"):
                code = result["content"]
                code = re.sub(r'^```python\s*', '', code)
                code = re.sub(r'^```\s*', '', code)
                code = re.sub(r'\s*```$', '', code)
                if f"def {func_name}" in code or "def " in code:
                    logger.info(f"ToolBuilder: LLM合成了工具代码 ({len(code)}字符)")
                    return code
        except Exception as e:
            logger.error(f"LLM工具合成失败，降级为模板: {e}")
        return None
    
    def _generate_tool_name(self, description: str) -> str:
        words = description.lower().split()[:3]
        name = "_".join(words)
        import re
        name = re.sub(r'[^a-z0-9_]', '', name)
        return f"auto_{name}"
    
    def _extract_function_name(self, code: str) -> Optional[str]:
        import re
        match = re.search(r'def\s+(\w+)\s*\(', code)
        if match:
            return match.group(1)
        return None
    
    def _test_tool(self, tool: Tool) -> Dict[str, Any]:
        if tool.implementation is None:
            return {"passed": False, "error": "无实现"}
        
        try:
            result_holder = {"result": None, "error": None}
            def _run_test():
                try:
                    result_holder["result"] = tool.implementation({"query": "test"})
                except Exception as e:
                    result_holder["error"] = str(e)
            
            t = threading.Thread(target=_run_test, daemon=True)
            t.start()
            t.join(timeout=3.0)
            
            if t.is_alive():
                return {"passed": False, "error": "工具测试执行超时(3s)"}
            
            if result_holder["error"]:
                return {"passed": False, "error": result_holder["error"]}
            
            return {"passed": True, "result": result_holder["result"]}
        except Exception as e:
            return {"passed": False, "error": str(e)}
    
    def use_tool(self, tool_id: str, *args, **kwargs) -> Any:
        if tool_id not in self.tools:
            raise ValueError(f"工具不存在: {tool_id}")
        
        tool = self.tools[tool_id]
        
        if tool.status != ToolStatus.ACTIVE:
            raise ValueError(f"工具未激活: {tool_id}")
        
        if tool.implementation is None:
            raise ValueError(f"工具无实现: {tool_id}")
        
        tool.usage_count += 1
        
        try:
            result = tool.implementation(*args, **kwargs)
            self._update_success_rate(tool, success=True)
            return result
        except Exception as e:
            self._update_success_rate(tool, success=False)
            raise
    
    def _update_success_rate(self, tool: Tool, success: bool) -> None:
        if tool.usage_count == 0:
            return
        
        old_count = tool.usage_count - 1
        old_rate = tool.success_rate
        
        if success:
            tool.success_rate = (old_rate * old_count + 1) / tool.usage_count
        else:
            tool.success_rate = (old_rate * old_count) / tool.usage_count
    
    def deprecate_tool(self, tool_id: str, reason: str = "") -> bool:
        if tool_id not in self.tools:
            return False
        
        self.tools[tool_id].status = ToolStatus.DEPRECATED
        return True
    
    def get_active_tools(self) -> List[Tool]:
        return [
            tool for tool in self.tools.values()
            if tool.status == ToolStatus.ACTIVE
        ]
    
    def get_tool_for_need(self, need_description: str) -> Optional[Tool]:
        need_key = self._generate_need_key(need_description)
        
        if need_key not in self.needs:
            return None
        
        need_id = self.needs[need_key].need_id
        
        for tool in self.tools.values():
            if need_id in tool.satisfies_needs and tool.status == ToolStatus.ACTIVE:
                return tool
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_needs": len(self.needs),
            "total_tools": len(self.tools),
            "active_tools": sum(1 for t in self.tools.values() if t.status == ToolStatus.ACTIVE),
            "needs_above_threshold": len(self.identify_tool_opportunities()),
            "average_success_rate": (
                sum(t.success_rate for t in self.tools.values()) / len(self.tools)
                if self.tools else 0.0
            ),
        }
    
    def add_template(self, name: str, template: str) -> None:
        self.tool_templates[name] = template

    def _wrap_tool_for_registry(self, tool: 'Tool') -> 'ToolInterface':
        from core.tool_registry import ToolInterface, ToolResult as RegistryToolResult
        _tool = tool

        class AutoToolWrapper(ToolInterface):
            @property
            def name(self) -> str:
                return f"auto_{_tool.tool_id}"

            @property
            def description(self) -> str:
                return _tool.description

            @property
            def parameters(self) -> Dict:
                return {"input": {"type": "string", "description": "输入数据"}}

            @property
            def category(self) -> str:
                return "auto_generated"

            @property
            def priority(self) -> int:
                return 25

            async def execute(self, **kwargs) -> RegistryToolResult:
                if _tool.implementation is None:
                    return RegistryToolResult(success=False, error="工具无实现", source=self.name)
                try:
                    inp = kwargs.get("input", kwargs.get("query", ""))
                    result = _tool.implementation(inp)
                    return RegistryToolResult(
                        success=True, data=str(result) if result is not None else "",
                        source=self.name, quality=35,
                    )
                except Exception as e:
                    return RegistryToolResult(success=False, error=str(e), source=self.name)

        return AutoToolWrapper()
    
    def export_tools(self) -> Dict[str, str]:
        return {
            tool.tool_id: tool.code
            for tool in self.tools.values()
            if tool.status == ToolStatus.ACTIVE
        }