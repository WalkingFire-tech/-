"""
工具自我构建 - 从需求中生成长久工具

核心理念：工具不是预设的，而是从需求中自然生长
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum


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
            local_namespace = {}
            exec(code, {}, local_namespace)
            
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
        return f'''
def {name}(input_data):
    """Auto-generated tool: {description}"""
    # TODO: Implement based on actual requirements
    return input_data
'''
    
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
            result = tool.implementation(None)
            return {"passed": True, "result": result}
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
    
    def export_tools(self) -> Dict[str, str]:
        return {
            tool.tool_id: tool.code
            for tool in self.tools.values()
            if tool.status == ToolStatus.ACTIVE
        }