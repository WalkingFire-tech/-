"""
工具库核心接口 - 统一工具抽象
支持动态注册、自动生成、自我完善的工具生态
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime


class ToolCategory(Enum):
    """工具类别"""
    CODE = "code"              # 代码执行
    CALCULATION = "calculation" # 数学计算
    FILE = "file"              # 文件操作
    SEARCH = "search"          # 搜索查询
    EXTRACTION = "extraction"  # 信息提取
    TRANSFORMATION = "transform" # 数据转换
    ANALYSIS = "analysis"      # 数据分析
    CUSTOM = "custom"          # 自定义工具
    MACRO = "macro"            # 宏工具(组合)


@dataclass
class Parameter:
    """工具参数定义"""
    name: str
    type: str  # str, int, float, bool, list, dict
    description: str
    required: bool = True
    default: Any = None
    choices: List[Any] = field(default_factory=list)


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    output: Any
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
            "execution_time": self.execution_time
        }


@dataclass
class ToolMetadata:
    """工具元数据"""
    name: str
    description: str
    category: ToolCategory
    parameters: List[Parameter]
    version: str = "1.0.0"
    author: str = "system"
    tags: List[str] = field(default_factory=list)
    examples: List[Dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class Tool(ABC):
    """统一工具接口"""
    
    def __init__(self):
        self._metadata: Optional[ToolMetadata] = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass
    
    @property
    @abstractmethod
    def category(self) -> ToolCategory:
        """工具类别"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[Parameter]:
        """参数定义"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        pass
    
    def get_metadata(self) -> ToolMetadata:
        """获取元数据"""
        if self._metadata is None:
            self._metadata = ToolMetadata(
                name=self.name,
                description=self.description,
                category=self.category,
                parameters=self.parameters
            )
        return self._metadata
    
    def validate_parameters(self, **kwargs) -> Optional[str]:
        """验证参数"""
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                return f"缺少必需参数: {param.name}"
            
            if param.name in kwargs:
                value = kwargs[param.name]
                
                # 类型检查
                if param.type == "str" and not isinstance(value, str):
                    return f"参数{param.name}应为字符串"
                elif param.type == "int" and not isinstance(value, int):
                    return f"参数{param.name}应为整数"
                elif param.type == "float" and not isinstance(value, (int, float)):
                    return f"参数{param.name}应为数字"
                elif param.type == "bool" and not isinstance(value, bool):
                    return f"参数{param.name}应为布尔值"
                elif param.type == "list" and not isinstance(value, list):
                    return f"参数{param.name}应为列表"
                elif param.type == "dict" and not isinstance(value, dict):
                    return f"参数{param.name}应为字典"
                
                # 选项检查
                if param.choices and value not in param.choices:
                    return f"参数{param.name}的值必须是: {param.choices}"
        
        return None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        metadata = self.get_metadata()
        return {
            "name": metadata.name,
            "description": metadata.description,
            "category": metadata.category.value,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                    "choices": p.choices
                }
                for p in metadata.parameters
            ],
            "version": metadata.version,
            "author": metadata.author,
            "tags": metadata.tags,
            "examples": metadata.examples
        }
    
    def safe_execute(self, **kwargs) -> ToolResult:
        """安全执行(带参数验证)"""
        import time
        
        # 验证参数
        error = self.validate_parameters(**kwargs)
        if error:
            return ToolResult(
                success=False,
                output=None,
                error=error
            )
        
        # 执行
        start_time = time.time()
        try:
            result = self.execute(**kwargs)
            result.execution_time = time.time() - start_time
            return result
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
                execution_time=time.time() - start_time
            )