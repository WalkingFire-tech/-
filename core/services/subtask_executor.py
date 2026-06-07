"""
子任务执行器 - 执行问题拆解器生成的子任务
支持依赖管理、结果传递、错误隔离
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger
from infrastructure.event_bus import bus
from core.services.problem_decomposer import SubTask


class SubTaskExecutor:
    """子任务执行器"""
    
    def __init__(self, adapters: dict, tools: dict = None):
        self.adapters = adapters
        self.tools = tools or {}
        self.results: Dict[str, Any] = {}
        self.execution_trace: List[Dict] = []
    
    def execute(self, subtasks: List[SubTask], context: Dict = None) -> Dict[str, Any]:
        """顺序执行子任务(按优先级和依赖)"""
        self.results = {}
        self.execution_trace = []
        
        sorted_tasks = self._topological_sort(subtasks)
        
        logger.info(f"开始执行{len(sorted_tasks)}个子任务")
        
        for task in sorted_tasks:
            if not self._dependencies_met(task):
                logger.warning(f"任务 {task.task_id} 依赖未满足,跳过")
                self._record_trace(task, "skipped", "依赖未满足")
                continue
            
            try:
                result = self._execute_one(task, context)
                self.results[task.task_id] = result
                self._record_trace(task, "success", result)
                
            except Exception as e:
                logger.error(f"任务 {task.task_id} 执行失败: {e}")
                self.results[task.task_id] = None
                self._record_trace(task, "failed", str(e))
        
        bus.publish("subtasks_executed", {
            "total": len(subtasks),
            "success": sum(1 for t in self.execution_trace if t["status"] == "success"),
            "failed": sum(1 for t in self.execution_trace if t["status"] == "failed"),
            "timestamp": datetime.now().isoformat()
        })
        
        return self.results
    
    def _execute_one(self, task: SubTask, context: Dict = None) -> Any:
        """执行单个子任务"""
        handler = task.handler
        
        logger.info(f"执行子任务 {task.task_id}: {task.description} (handler={handler})")
        
        if handler == "code_model":
            return self._handle_code_model(task, context)
        
        elif handler == "chat_model":
            return self._handle_chat_model(task, context)
        
        elif handler == "local_kb":
            return self._handle_local_kb(task, context)
        
        elif handler == "calculator":
            return self._handle_calculator(task, context)
        
        elif handler == "static_analyzer":
            return self._handle_static_analyzer(task, context)
        
        elif handler == "parser":
            return self._handle_parser(task, context)
        
        elif handler == "extractor":
            return self._handle_extractor(task, context)
        
        elif handler == "formatter":
            return self._handle_formatter(task, context)
        
        elif handler in self.tools:
            return self.tools[handler](task.description, context)
        
        else:
            return self._handle_generic(task, context)
    
    def _handle_code_model(self, task: SubTask, context: Dict) -> str:
        """处理代码模型任务"""
        model_names = ["qwen2.5-coder:1.5b", "deepseek-coder", "code_light"]
        
        for model_name in model_names:
            if model_name in self.adapters:
                model = self.adapters[model_name]
                prompt = f"Generate code for: {task.description}"
                response = model.generate(prompt, task_type="code")
                
                if isinstance(response, tuple):
                    return response[0]
                return response
        
        raise RuntimeError("无可用的代码模型")
    
    def _handle_chat_model(self, task: SubTask, context: Dict) -> str:
        """处理对话模型任务"""
        model_names = ["mindchat", "deepseek-chat", "gpt-4o-mini"]
        
        for model_name in model_names:
            if model_name in self.adapters:
                model = self.adapters[model_name]
                response = model.generate(task.description, task_type="chat")
                
                if isinstance(response, tuple):
                    return response[0]
                return response
        
        raise RuntimeError("无可用的对话模型")
    
    def _handle_local_kb(self, task: SubTask, context: Dict) -> str:
        """处理本地知识库检索"""
        return f"[本地知识库] 检索: {task.description}"
    
    def _handle_calculator(self, task: SubTask, context: Dict) -> str:
        """处理计算任务"""
        try:
            from math import sqrt, sin, cos, tan, log, log10, exp, pi, e
            
            safe_dict = {
                'abs': abs, 'round': round, 'min': min, 'max': max,
                'sum': sum, 'pow': pow, 'sqrt': sqrt,
                'sin': sin, 'cos': cos, 'tan': tan,
                'log': log, 'log10': log10, 'exp': exp,
                'pi': pi, 'e': e
            }
            
            expression = task.description
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            return str(result)
        
        except Exception as e:
            return f"计算错误: {str(e)}"
    
    def _handle_static_analyzer(self, task: SubTask, context: Dict) -> str:
        """处理静态分析任务"""
        code = self._get_dependency_result(task, "code")
        
        if not code:
            return "[静态分析] 无代码输入"
        
        issues = []
        
        if "eval(" in code:
            issues.append("警告: 使用了eval()")
        if "exec(" in code:
            issues.append("警告: 使用了exec()")
        if "import os" in code:
            issues.append("警告: 导入了os模块")
        
        if not issues:
            return "[静态分析] 代码安全检查通过"
        
        return "[静态分析] " + "; ".join(issues)
    
    def _handle_parser(self, task: SubTask, context: Dict) -> str:
        """处理解析任务"""
        return f"[解析器] {task.description}"
    
    def _handle_extractor(self, task: SubTask, context: Dict) -> str:
        """处理提取任务"""
        return f"[提取器] {task.description}"
    
    def _handle_formatter(self, task: SubTask, context: Dict) -> str:
        """处理格式化任务"""
        result = self._get_dependency_result(task)
        
        if result:
            return f"[格式化] {str(result)}"
        
        return f"[格式化] {task.description}"
    
    def _handle_generic(self, task: SubTask, context: Dict) -> str:
        """处理通用任务"""
        if self.adapters:
            model = next(iter(self.adapters.values()))
            response = model.generate(task.description, task_type="generic")
            
            if isinstance(response, tuple):
                return response[0]
            return response
        
        return f"[通用处理] {task.description}"
    
    def _get_dependency_result(self, task: SubTask, key: str = None) -> Any:
        """获取依赖任务的结果"""
        if task.dependencies:
            for dep_id in task.dependencies:
                if dep_id in self.results:
                    result = self.results[dep_id]
                    if key and isinstance(result, dict):
                        return result.get(key)
                    return result
        return None
    
    def _dependencies_met(self, task: SubTask) -> bool:
        """检查依赖是否满足"""
        for dep_id in task.dependencies:
            if dep_id not in self.results:
                return False
            if self.results[dep_id] is None:
                return False
        return True
    
    def _topological_sort(self, tasks: List[SubTask]) -> List[SubTask]:
        """拓扑排序(简化版:按优先级)"""
        return sorted(tasks, key=lambda t: t.priority)
    
    def _record_trace(self, task: SubTask, status: str, result: Any):
        """记录执行轨迹"""
        self.execution_trace.append({
            "task_id": task.task_id,
            "description": task.description,
            "handler": task.handler,
            "status": status,
            "result": str(result)[:200] if result else None,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_execution_summary(self) -> Dict:
        """获取执行摘要"""
        return {
            "total_tasks": len(self.execution_trace),
            "success_count": sum(1 for t in self.execution_trace if t["status"] == "success"),
            "failed_count": sum(1 for t in self.execution_trace if t["status"] == "failed"),
            "skipped_count": sum(1 for t in self.execution_trace if t["status"] == "skipped"),
            "results": self.results
        }