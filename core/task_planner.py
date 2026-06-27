"""
任务规划执行器 - 有条不紊地处理复杂任务
"""
import asyncio
from typing import List, Dict, Callable, Any
from dataclasses import dataclass
from enum import Enum
from loguru import logger

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class Task:
    """任务单元"""
    name: str
    func: Callable
    priority: int = 5  # 1-10, 1最高
    timeout: float = 10.0
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = None
    progress: str = ""

class TaskPlanner:
    """任务规划执行器"""
    
    def __init__(self):
        self.tasks: List[Task] = []
        self.results: Dict[str, Any] = {}
        self.progress_callback = None
        
    def add_task(self, name: str, func: Callable, 
                 priority: int = 5, timeout: float = 10.0):
        """添加任务"""
        task = Task(name=name, func=func, priority=priority, timeout=timeout)
        self.tasks.append(task)
        return self
    
    def set_progress_callback(self, callback: Callable):
        """设置进度回调"""
        self.progress_callback = callback
    
    async def emit_progress(self, task_name: str, status: str, message: str):
        """发送进度更新"""
        if self.progress_callback:
            await self.progress_callback({
                "task": task_name,
                "status": status,
                "message": message,
                "timestamp": asyncio.get_event_loop().time()
            })
        
        # 同时记录日志
        logger.info(f"[{task_name}] {status}: {message}")
    
    async def execute_task(self, task: Task) -> Any:
        """执行单个任务"""
        task.status = TaskStatus.RUNNING
        
        try:
            await self.emit_progress(task.name, "开始", f"正在执行...")
            
            # 执行任务（支持同步和异步函数）
            if asyncio.iscoroutinefunction(task.func):
                result = await asyncio.wait_for(
                    task.func(),
                    timeout=task.timeout
                )
            else:
                # 同步函数在executor中运行
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, task.func),
                    timeout=task.timeout
                )
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            await self.emit_progress(task.name, "完成", f"执行成功")
            return result
            
        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.error = "超时"
            await self.emit_progress(task.name, "超时", f"执行超时({task.timeout}秒)")
            return None
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            await self.emit_progress(task.name, "失败", f"错误: {e}")
            return None
    
    async def execute_parallel(self, task_names: List[str] = None):
        """并行执行指定任务（或所有任务）"""
        if task_names:
            tasks = [t for t in self.tasks if t.name in task_names]
        else:
            tasks = self.tasks
        
        # 按优先级排序
        tasks.sort(key=lambda t: t.priority)
        
        # 并行执行
        results = await asyncio.gather(
            *[self.execute_task(task) for task in tasks],
            return_exceptions=True
        )
        
        # 收集结果
        for task, result in zip(tasks, results):
            if isinstance(result, Exception):
                task.status = TaskStatus.FAILED
                task.error = str(result)
            else:
                self.results[task.name] = result
        
        return self.results
    
    async def execute_sequential(self, task_names: List[str] = None):
        """顺序执行任务"""
        if task_names:
            tasks = [t for t in self.tasks if t.name in task_names]
        else:
            tasks = self.tasks
        
        # 按优先级排序
        tasks.sort(key=lambda t: t.priority)
        
        # 顺序执行
        for task in tasks:
            result = await self.execute_task(task)
            self.results[task.name] = result
        
        return self.results
    
    async def execute_smart(self):
        """智能执行：高优先级顺序，低优先级并行"""
        # 分组：高优先级(1-3)顺序执行，其他并行
        high_priority = [t for t in self.tasks if t.priority <= 3]
        low_priority = [t for t in self.tasks if t.priority > 3]
        
        # 先顺序执行高优先级任务
        for task in sorted(high_priority, key=lambda t: t.priority):
            result = await self.execute_task(task)
            self.results[task.name] = result
        
        # 再并行执行低优先级任务
        if low_priority:
            await self.execute_parallel([t.name for t in low_priority])
        
        return self.results
    
    def get_summary(self) -> Dict:
        """获取执行摘要"""
        return {
            "total": len(self.tasks),
            "completed": len([t for t in self.tasks if t.status == TaskStatus.COMPLETED]),
            "failed": len([t for t in self.tasks if t.status == TaskStatus.FAILED]),
            "skipped": len([t for t in self.tasks if t.status == TaskStatus.SKIPPED]),
            "results": self.results,
            "details": [
                {
                    "name": t.name,
                    "status": t.status.value,
                    "error": t.error
                }
                for t in self.tasks
            ]
        }