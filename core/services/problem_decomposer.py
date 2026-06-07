"""
问题拆解器 - 当主模型无法处理时的智能降级策略
使用轻量本地模型拆解复杂问题,制定应对策略
"""
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
from infrastructure.event_bus import bus


@dataclass
class SubTask:
    """子任务"""
    task_id: str
    description: str
    handler: str  # code_model, local_kb, template, user_clarify
    priority: int
    dependencies: List[str]


class ProblemDecomposer:
    """问题拆解器"""
    
    def __init__(self, light_llm_adapter=None):
        self.llm = light_llm_adapter
        self.decompose_strategies = {
            "code": self._decompose_code_task,
            "question": self._decompose_question_task,
            "calculation": self._decompose_calculation_task,
            "document": self._decompose_document_task
        }
        
        logger.info("问题拆解器初始化完成")
    
    def should_decompose(self, intent_type: str, quality_score: int, 
                        error_count: int) -> bool:
        """判断是否需要拆解问题"""
        if quality_score < 30:
            return True
        
        if error_count >= 2:
            return True
        
        if intent_type == "code" and quality_score < 50:
            return True
        
        return False
    
    def decompose(self, user_request: str, intent_type: str, 
                 context: Dict = None) -> List[SubTask]:
        """拆解问题为子任务"""
        
        strategy = self.decompose_strategies.get(intent_type, self._decompose_generic)
        
        subtasks = strategy(user_request, context)
        
        logger.info(f"问题拆解: {intent_type} -> {len(subtasks)}个子任务")
        
        bus.publish("problem_decomposed", {
            "intent_type": intent_type,
            "subtask_count": len(subtasks),
            "user_request": user_request[:100]
        })
        
        return subtasks
    
    def _decompose_code_task(self, request: str, context: Dict) -> List[SubTask]:
        """拆解代码任务"""
        subtasks = [
            SubTask(
                task_id="code_1",
                description="理解代码需求和约束条件",
                handler="local_kb",
                priority=1,
                dependencies=[]
            ),
            SubTask(
                task_id="code_2",
                description="生成代码框架和核心逻辑",
                handler="code_model",
                priority=2,
                dependencies=["code_1"]
            ),
            SubTask(
                task_id="code_3",
                description="语法检查和优化",
                handler="static_analyzer",
                priority=3,
                dependencies=["code_2"]
            )
        ]
        
        if self.llm:
            try:
                prompt = f"""分析以下代码需求,拆解为子任务:
需求: {request}

输出JSON格式:
[
  {{"task": "子任务描述", "handler": "处理方式"}},
  ...
]

仅输出JSON,不要其他内容。"""
                
                response = self.llm.generate(prompt, task_type="decompose")
                
                if response:
                    parsed = self._parse_decomposition(response)
                    if parsed:
                        subtasks = parsed
                        
            except Exception as e:
                logger.warning(f"LLM拆解失败,使用默认策略: {e}")
        
        return subtasks
    
    def _decompose_question_task(self, request: str, context: Dict) -> List[SubTask]:
        """拆解问答任务"""
        return [
            SubTask(
                task_id="q_1",
                description="检索相关知识",
                handler="local_kb",
                priority=1,
                dependencies=[]
            ),
            SubTask(
                task_id="q_2",
                description="生成详细回答",
                handler="chat_model",
                priority=2,
                dependencies=["q_1"]
            )
        ]
    
    def _decompose_calculation_task(self, request: str, context: Dict) -> List[SubTask]:
        """拆解计算任务"""
        return [
            SubTask(
                task_id="calc_1",
                description="解析计算表达式",
                handler="parser",
                priority=1,
                dependencies=[]
            ),
            SubTask(
                task_id="calc_2",
                description="执行计算",
                handler="calculator",
                priority=2,
                dependencies=["calc_1"]
            ),
            SubTask(
                task_id="calc_3",
                description="格式化结果",
                handler="formatter",
                priority=3,
                dependencies=["calc_2"]
            )
        ]
    
    def _decompose_document_task(self, request: str, context: Dict) -> List[SubTask]:
        """拆解文档任务"""
        return [
            SubTask(
                task_id="doc_1",
                description="提取文档关键信息",
                handler="extractor",
                priority=1,
                dependencies=[]
            ),
            SubTask(
                task_id="doc_2",
                description="生成摘要或分析",
                handler="chat_model",
                priority=2,
                dependencies=["doc_1"]
            )
        ]
    
    def _decompose_generic(self, request: str, context: Dict) -> List[SubTask]:
        """通用拆解策略"""
        return [
            SubTask(
                task_id="gen_1",
                description="理解用户需求",
                handler="chat_model",
                priority=1,
                dependencies=[]
            ),
            SubTask(
                task_id="gen_2",
                description="生成响应",
                handler="chat_model",
                priority=2,
                dependencies=["gen_1"]
            )
        ]
    
    def _parse_decomposition(self, response: str) -> Optional[List[SubTask]]:
        """解析LLM返回的拆解结果"""
        try:
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            data = json.loads(json_str.strip())
            
            subtasks = []
            for i, item in enumerate(data):
                subtasks.append(SubTask(
                    task_id=f"task_{i+1}",
                    description=item.get("task", ""),
                    handler=item.get("handler", "chat_model"),
                    priority=i+1,
                    dependencies=[f"task_{i}"] if i > 0 else []
                ))
            
            return subtasks
        
        except Exception as e:
            logger.error(f"解析拆解结果失败: {e}")
            return None
    
    def generate_fallback_message(self, intent_type: str, 
                                 available_handlers: List[str]) -> str:
        """生成友好的降级提示"""
        
        messages = {
            "code": "抱歉,当前未检测到可用的编程模型。\n\n"
                   "建议:\n"
                   "1. 安装代码模型: ollama pull qwen2.5-coder:1.5b\n"
                   "2. 或配置远程API: deepseek-coder\n"
                   "3. 或简化问题,我将尽力用通用模型协助您",
            
            "calculation": "抱歉,计算功能需要专门的数学模块。\n\n"
                          "建议:\n"
                          "1. 安装计算工具库\n"
                          "2. 或使用在线计算服务",
            
            "document": "抱歉,文档处理功能暂不可用。\n\n"
                       "建议:\n"
                       "1. 上传更小的文档片段\n"
                       "2. 或使用专门的文档分析工具"
        }
        
        return messages.get(intent_type, 
                          "抱歉,当前无法处理该类型任务。\n"
                          "请尝试其他方式或稍后重试。")


problem_decomposer = ProblemDecomposer()