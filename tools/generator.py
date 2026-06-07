"""
工具生成器 - 自动生成和改进工具
基于失败分析和需求识别,使用LLM生成新工具
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
from tools.base import Tool, ToolCategory, Parameter, ToolResult
from tools.registry import registry


class ToolGenerator:
    """工具生成器"""
    
    def __init__(self, llm_adapter=None):
        self.llm_adapter = llm_adapter
        self.generated_tools_dir = Path("tools/generated")
        self.generated_tools_dir.mkdir(exist_ok=True)
    
    def analyze_need_for_new_tool(self, failure_context: Dict) -> Optional[Dict]:
        """分析是否需要新工具"""
        if not self.llm_adapter:
            return None
        
        prompt = f"""分析以下失败案例,判断是否需要创建新工具。

## 失败上下文
- 任务类型: {failure_context.get('task_type')}
- 用户需求: {failure_context.get('user_input')}
- 失败原因: {failure_context.get('failure_reason')}
- 现有工具: {list(registry._tools.keys())}

## 请回答
1. 是否需要新工具? (是/否)
2. 如果需要,工具应该做什么?
3. 工具名称和描述?
4. 需要什么参数?

以JSON格式返回:
{{
  "need_new_tool": true/false,
  "tool_name": "名称",
  "description": "描述",
  "category": "calculation/extraction/transform/custom",
  "parameters": [
    {{"name": "参数名", "type": "str/int", "description": "描述", "required": true}}
  ],
  "reasoning": "判断理由"
}}
"""
        
        try:
            response = self.llm_adapter.generate(prompt, task_type="tool_analysis")
            
            # 解析JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                
                if result.get("need_new_tool"):
                    return result
        
        except Exception as e:
            logger.error(f"分析失败: {e}")
        
        return None
    
    def generate_tool_code(self, tool_spec: Dict) -> Optional[str]:
        """生成工具代码"""
        if not self.llm_adapter:
            return None
        
        prompt = f"""根据以下规范生成Python工具代码。

## 工具规范
- 名称: {tool_spec['tool_name']}
- 描述: {tool_spec['description']}
- 类别: {tool_spec['category']}
- 参数: {json.dumps(tool_spec['parameters'], ensure_ascii=False)}

## 要求
1. 继承Tool基类
2. 实现所有必需方法
3. 包含错误处理
4. 代码简洁高效
5. 包含docstring

## 代码模板
```python
from tools.base import Tool, ToolCategory, Parameter, ToolResult
from typing import List

class GeneratedTool(Tool):
    @property
    def name(self) -> str:
        return "{tool_spec['tool_name']}"
    
    @property
    def description(self) -> str:
        return "{tool_spec['description']}"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.{tool_spec['category'].upper()}
    
    @property
    def parameters(self) -> List[Parameter]:
        return [
            # 根据规范定义参数
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        # 实现核心逻辑
        pass
```

请生成完整的工具代码。
"""
        
        try:
            response = self.llm_adapter.generate(prompt, task_type="code_generation")
            
            # 提取代码
            code_match = re.search(r'```python\n(.*?)```', response, re.DOTALL)
            if code_match:
                return code_match.group(1)
        
        except Exception as e:
            logger.error(f"生成代码失败: {e}")
        
        return None
    
    def validate_generated_code(self, code: str) -> bool:
        """验证生成的代码"""
        # 安全检查
        dangerous_patterns = [
            r'os\.system',
            r'subprocess\.call',
            r'eval\s*\(',
            r'exec\s*\(',
            r'__import__',
            r'open\s*\([^)]*,\s*["\']w["\']',  # 写文件
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                logger.warning(f"代码包含危险模式: {pattern}")
                return False
        
        # 语法检查
        try:
            compile(code, '<string>', 'exec')
        except SyntaxError as e:
            logger.warning(f"代码语法错误: {e}")
            return False
        
        return True
    
    def create_tool_from_code(self, code: str, tool_name: str) -> Optional[Tool]:
        """从代码创建工具实例"""
        try:
            # 创建命名空间
            namespace = {
                'Tool': Tool,
                'ToolCategory': ToolCategory,
                'Parameter': Parameter,
                'ToolResult': ToolResult,
                'List': List
            }
            
            # 执行代码
            exec(code, namespace)
            
            # 查找工具类
            for name, obj in namespace.items():
                if isinstance(obj, type) and issubclass(obj, Tool) and obj != Tool:
                    # 创建实例
                    tool_instance = obj()
                    logger.info(f"成功创建工具: {tool_instance.name}")
                    return tool_instance
        
        except Exception as e:
            logger.error(f"创建工具失败: {e}")
        
        return None
    
    def generate_and_register_tool(self, failure_context: Dict, 
                                   auto_register: bool = False) -> Optional[Tool]:
        """生成并注册新工具"""
        # 1. 分析需求
        tool_spec = self.analyze_need_for_new_tool(failure_context)
        
        if not tool_spec:
            logger.info("不需要新工具")
            return None
        
        # 2. 生成代码
        code = self.generate_tool_code(tool_spec)
        
        if not code:
            logger.error("生成代码失败")
            return None
        
        # 3. 验证代码
        if not self.validate_generated_code(code):
            logger.error("代码验证失败")
            return None
        
        # 4. 创建工具
        tool = self.create_tool_from_code(code, tool_spec['tool_name'])
        
        if not tool:
            logger.error("创建工具失败")
            return None
        
        # 5. 保存代码
        tool_file = self.generated_tools_dir / f"{tool.name}.py"
        with open(tool_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        logger.info(f"保存工具代码: {tool_file}")
        
        # 6. 注册工具
        if auto_register:
            registry.register(tool)
            logger.info(f"自动注册工具: {tool.name}")
        
        return tool
    
    def improve_tool(self, tool_name: str, failure_analysis: Dict) -> Optional[Tool]:
        """改进现有工具"""
        tool = registry.get(tool_name)
        
        if not tool:
            logger.warning(f"工具不存在: {tool_name}")
            return None
        
        if not self.llm_adapter:
            return None
        
        # 生成改进代码
        prompt = f"""分析工具失败并生成改进版本。

## 原工具
- 名称: {tool.name}
- 描述: {tool.description}
- 代码: {tool.__class__.__module__}

## 失败分析
{json.dumps(failure_analysis, ensure_ascii=False, indent=2)}

## 请生成改进后的工具代码
保持接口不变,修复问题并提升健壮性。
"""
        
        try:
            response = self.llm_adapter.generate(prompt, task_type="tool_improvement")
            
            code_match = re.search(r'```python\n(.*?)```', response, re.DOTALL)
            if code_match:
                improved_code = code_match.group(1)
                
                if self.validate_generated_code(improved_code):
                    improved_tool = self.create_tool_from_code(improved_code, tool_name)
                    
                    if improved_tool:
                        # 保存新版本
                        version = datetime.now().strftime("%Y%m%d_%H%M%S")
                        tool_file = self.generated_tools_dir / f"{tool_name}_v{version}.py"
                        
                        with open(tool_file, 'w', encoding='utf-8') as f:
                            f.write(improved_code)
                        
                        logger.info(f"生成改进版本: {tool_file}")
                        
                        return improved_tool
        
        except Exception as e:
            logger.error(f"改进工具失败: {e}")
        
        return None