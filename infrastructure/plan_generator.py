"""
规划生成器 - 认知层核心组件
生成子任务列表，包含依赖关系、资源需求、预期输出

核心能力：
- 生成执行计划
- 标注资源依赖
- 识别执行顺序
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger
from infrastructure.config_manager import config


@dataclass
class Subtask:
    """子任务"""
    id: int
    description: str
    dependencies: List[int]
    required_resource: str  # "local_model", "remote_api", "human", "none"
    expected_output_type: str  # "code", "text", "data", "decision"
    priority: int  # 1-5, 5最高
    estimated_duration: float  # 秒
    uncertainty: float  # 0-1
    alternatives: List[str]


class PlanGenerator:
    """规划生成器 - 认知层第三步"""
    
    def __init__(self):
        self.templates = self._load_templates()
        logger.info("规划生成器初始化完成")
    
    def generate(
        self,
        analysis: Dict,
        causal_chain: List[Dict]
    ) -> List[Subtask]:
        """
        生成执行计划
        
        Args:
            analysis: 问题分析结果
            causal_chain: 因果链
        
        Returns:
            子任务列表
        """
        logger.info("开始生成执行计划...")
        
        subtasks = []
        problem_type = analysis.get("problem_type", "general")
        core_need = analysis.get("core_need", "")
        
        # 1. 基于问题类型的模板计划
        template_tasks = self._generate_from_template(problem_type, analysis)
        subtasks.extend(template_tasks)
        
        # 2. 基于信息缺口的澄清任务
        gap_tasks = self._generate_gap_tasks(analysis)
        subtasks.extend(gap_tasks)
        
        # 3. 基于因果链的推理任务
        causal_tasks = self._generate_causal_tasks(causal_chain)
        subtasks.extend(causal_tasks)
        
        # 4. 基于约束的检查任务
        constraint_tasks = self._generate_constraint_tasks(analysis)
        subtasks.extend(constraint_tasks)
        
        # 5. 分配ID和优先级
        subtasks = self._assign_ids_and_priorities(subtasks)
        
        # 6. 排序
        subtasks = self._sort_by_dependencies(subtasks)
        
        logger.info(f"执行计划生成完成: {len(subtasks)}个子任务")
        
        return subtasks
    
    def _load_templates(self) -> Dict:
        """加载计划模板"""
        return {
            "code": [
                {
                    "description": "澄清输入输出规格",
                    "required_resource": "human",
                    "expected_output_type": "decision",
                    "priority": 5,
                    "estimated_duration": 30
                },
                {
                    "description": "生成代码实现",
                    "required_resource": "local_model",
                    "expected_output_type": "code",
                    "priority": 4,
                    "estimated_duration": 10,
                    "dependencies": [1]  # 依赖任务1
                },
                {
                    "description": "代码解释与复杂度分析",
                    "required_resource": "local_model",
                    "expected_output_type": "text",
                    "priority": 3,
                    "estimated_duration": 5,
                    "dependencies": [2]
                },
                {
                    "description": "代码质量检查",
                    "required_resource": "local_model",
                    "expected_output_type": "text",
                    "priority": 2,
                    "estimated_duration": 3,
                    "dependencies": [2]
                }
            ],
            "question": [
                {
                    "description": "检索相关知识",
                    "required_resource": "local_model",
                    "expected_output_type": "text",
                    "priority": 4,
                    "estimated_duration": 5
                },
                {
                    "description": "组织答案结构",
                    "required_resource": "none",
                    "expected_output_type": "text",
                    "priority": 3,
                    "estimated_duration": 2,
                    "dependencies": [1]
                },
                {
                    "description": "生成详细解释",
                    "required_resource": "local_model",
                    "expected_output_type": "text",
                    "priority": 4,
                    "estimated_duration": 8,
                    "dependencies": [2]
                }
            ],
            "analysis": [
                {
                    "description": "明确分析维度",
                    "required_resource": "human",
                    "expected_output_type": "decision",
                    "priority": 5,
                    "estimated_duration": 30
                },
                {
                    "description": "收集分析数据",
                    "required_resource": "local_model",
                    "expected_output_type": "data",
                    "priority": 4,
                    "estimated_duration": 10,
                    "dependencies": [1]
                },
                {
                    "description": "执行对比分析",
                    "required_resource": "local_model",
                    "expected_output_type": "text",
                    "priority": 4,
                    "estimated_duration": 8,
                    "dependencies": [2]
                },
                {
                    "description": "生成分析报告",
                    "required_resource": "local_model",
                    "expected_output_type": "text",
                    "priority": 3,
                    "estimated_duration": 5,
                    "dependencies": [3]
                }
            ]
        }
    
    def _generate_from_template(self, problem_type: str, analysis: Dict) -> List[Subtask]:
        """基于模板生成任务"""
        tasks = []
        
        if problem_type in self.templates:
            for template in self.templates[problem_type]:
                # 检查是否需要跳过（如信息已明确）
                if self._should_skip(template, analysis):
                    continue
                
                task = Subtask(
                    id=0,  # 稍后分配
                    description=template["description"],
                    dependencies=template.get("dependencies", []),
                    required_resource=template["required_resource"],
                    expected_output_type=template["expected_output_type"],
                    priority=template["priority"],
                    estimated_duration=template["estimated_duration"],
                    uncertainty=0.3,
                    alternatives=[]
                )
                tasks.append(task)
        
        return tasks
    
    def _should_skip(self, template: Dict, analysis: Dict) -> bool:
        """检查是否应该跳过任务"""
        desc = template["description"]
        
        # 如果输入输出已明确，跳过澄清任务
        if "澄清输入输出" in desc:
            gaps = analysis.get("info_gaps", [])
            io_gap = any("输入输出" in g.get("description", "") for g in gaps)
            if not io_gap:
                return True
        
        return False
    
    def _generate_gap_tasks(self, analysis: Dict) -> List[Subtask]:
        """基于信息缺口生成澄清任务"""
        tasks = []
        gaps = analysis.get("info_gaps", [])
        
        for gap in gaps:
            if gap.get("importance") == "high":
                task = Subtask(
                    id=0,
                    description=f"澄清：{gap['description']}",
                    dependencies=[],
                    required_resource="human",
                    expected_output_type="decision",
                    priority=5,
                    estimated_duration=30,
                    uncertainty=0.5,
                    alternatives=["假设默认值", "跳过此步骤"]
                )
                tasks.append(task)
        
        return tasks
    
    def _generate_causal_tasks(self, causal_chain: List[Dict]) -> List[Subtask]:
        """基于因果链生成任务"""
        tasks = []
        
        for causal in causal_chain:
            if causal.get("type") == "gap":
                # 信息缺口已在gap_tasks中处理
                continue
            
            cause = causal.get("cause", "")
            effect = causal.get("effect", "")
            
            # 如果是约束相关的，生成检查任务
            if causal.get("type") == "constraint":
                task = Subtask(
                    id=0,
                    description=f"确保：{effect}",
                    dependencies=[],
                    required_resource="none",
                    expected_output_type="decision",
                    priority=3,
                    estimated_duration=2,
                    uncertainty=0.2,
                    alternatives=[]
                )
                tasks.append(task)
        
        return tasks
    
    def _generate_constraint_tasks(self, analysis: Dict) -> List[Subtask]:
        """基于约束生成检查任务"""
        tasks = []
        constraints = analysis.get("constraints", [])
        
        for constraint in constraints:
            ctype = constraint.get("type")
            value = constraint.get("value")
            
            if ctype == "performance":
                task = Subtask(
                    id=0,
                    description=f"性能验证：确保满足{value}要求",
                    dependencies=[],
                    required_resource="local_model",
                    expected_output_type="text",
                    priority=2,
                    estimated_duration=5,
                    uncertainty=0.4,
                    alternatives=["跳过性能验证"]
                )
                tasks.append(task)
        
        return tasks
    
    def _assign_ids_and_priorities(self, tasks: List[Subtask]) -> List[Subtask]:
        """分配ID和调整优先级"""
        for i, task in enumerate(tasks, 1):
            task.id = i
        
        return tasks
    
    def _sort_by_dependencies(self, tasks: List[Subtask]) -> List[Subtask]:
        """按依赖关系排序（拓扑排序）"""
        # 简单实现：按优先级排序
        # 完整实现需要拓扑排序算法
        return sorted(tasks, key=lambda t: -t.priority)


# 全局实例
plan_generator = PlanGenerator()