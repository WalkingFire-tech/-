"""
技能树与能力评估系统
实现动态能力认知与工具调度
"""
import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """技能定义"""
    id: str
    name: str
    description: str
    skill_type: str  # "local", "external", "lora", "script"
    keywords: List[str]
    confidence: float = 0.8
    usage_count: int = 0
    success_count: int = 0
    last_used: Optional[str] = None
    config: Dict = field(default_factory=dict)
    
    def match(self, task_description: str) -> bool:
        """检查任务是否匹配此技能"""
        task_lower = task_description.lower()
        return any(kw in task_lower for kw in self.keywords)
    
    def get_success_rate(self) -> float:
        """获取成功率"""
        if self.usage_count == 0:
            return 0.5
        return self.success_count / self.usage_count


class SkillTree:
    """
    技能树 - 管理系统的所有能力
    支持：本地技能、外部API、LoRA适配器、脚本
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.skills: Dict[str, Skill] = {}
        self.skill_categories = {
            "local": [],      # 本地脚本
            "external": [],   # 外部API
            "lora": [],       # LoRA适配器
            "script": []      # 动态生成的脚本
        }
        
        self._register_default_skills()
        self._load_skills()
        
        logger.info(f"🌳 技能树初始化完成，共 {len(self.skills)} 个技能")
    
    def _register_default_skills(self):
        """注册默认技能"""
        default_skills = [
            # 本地技能
            Skill(
                id="file_operations",
                name="文件操作",
                description="读取、写入、重命名、复制文件",
                skill_type="local",
                keywords=["文件", "读取", "写入", "重命名", "复制", "file", "read", "write"],
                config={"module": "os", "functions": ["read", "write", "rename", "copy"]}
            ),
            Skill(
                id="excel_operations",
                name="Excel处理",
                description="读取、处理、合并Excel文件",
                skill_type="local",
                keywords=["excel", "表格", "xlsx", "合并", "数据处理", "pandas"],
                config={"module": "pandas", "functions": ["read_excel", "to_excel", "merge"]}
            ),
            Skill(
                id="code_generation",
                name="代码生成",
                description="生成Python、Shell等代码",
                skill_type="lora",
                keywords=["写代码", "生成脚本", "编程", "python", "代码", "script"],
                config={"model": "qwen2.5-coder:7b", "max_tokens": 500}
            ),
            Skill(
                id="data_analysis",
                name="数据分析",
                description="分析数据、生成统计报告",
                skill_type="local",
                keywords=["分析", "统计", "数据", "报告", "可视化", "analysis"],
                config={"module": "pandas", "functions": ["describe", "groupby", "plot"]}
            ),
            Skill(
                id="web_search",
                name="网络搜索",
                description="搜索网络获取实时信息",
                skill_type="external",
                keywords=["搜索", "查找", "网络", "最新", "search", "web"],
                config={"api": "duckduckgo", "max_results": 5}
            ),
            Skill(
                id="question_answer",
                name="问答推理",
                description="回答一般性问题",
                skill_type="lora",
                keywords=["是什么", "为什么", "如何", "解释", "说明", "什么", "怎么"],
                config={"model": "qwen2.5-coder:7b", "max_tokens": 300}
            ),
            Skill(
                id="task_decomposition",
                name="任务拆解",
                description="将复杂任务拆解为子任务",
                skill_type="lora",
                keywords=["拆解", "分解", "步骤", "计划", "如何做", "流程"],
                config={"model": "qwen2.5-coder:7b", "max_tokens": 400}
            ),
            Skill(
                id="sql_generation",
                name="SQL生成",
                description="根据自然语言生成SQL查询",
                skill_type="lora",
                keywords=["sql", "查询", "数据库", "select", "数据提取"],
                config={"model": "qwen2.5-coder:7b", "max_tokens": 200}
            ),
        ]
        
        for skill in default_skills:
            self.skills[skill.id] = skill
            self.skill_categories[skill.skill_type].append(skill.id)
    
    def _load_skills(self):
        """从文件加载技能"""
        skills_file = self.data_dir / "skill_tree.json"
        if skills_file.exists():
            try:
                with open(skills_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for skill_data in data.get("skills", []):
                        skill = Skill(**skill_data)
                        self.skills[skill.id] = skill
                        if skill.skill_type in self.skill_categories:
                            self.skill_categories[skill.skill_type].append(skill.id)
            except Exception as e:
                logger.warning(f"加载技能文件失败: {e}")
    
    def _save_skills(self):
        """保存技能到文件"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        skills_file = self.data_dir / "skill_tree.json"
        
        data = {
            "skills": [asdict(s) for s in self.skills.values()],
            "categories": self.skill_categories,
            "updated_at": datetime.now().isoformat()
        }
        
        with open(skills_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def register_skill(self, skill: Skill):
        """注册新技能"""
        self.skills[skill.id] = skill
        if skill.skill_type in self.skill_categories:
            self.skill_categories[skill.skill_type].append(skill.id)
        self._save_skills()
        logger.info(f"✅ 注册新技能: {skill.name} ({skill.skill_type})")
    
    def evaluate_task(self, task_description: str) -> Dict:
        """
        评估任务，返回最佳执行策略
        
        Returns:
            {
                "action": "local" | "external" | "lora" | "train_new" | "ask_other",
                "skill": Skill对象,
                "confidence": 置信度,
                "reason": 原因说明
            }
        """
        # 1. 检查本地技能
        for skill_id in self.skill_categories["local"]:
            skill = self.skills[skill_id]
            if skill.match(task_description):
                return {
                    "action": "local",
                    "skill": skill,
                    "confidence": skill.get_success_rate(),
                    "reason": f"匹配本地技能: {skill.name}"
                }
        
        # 2. 检查LoRA适配器
        for skill_id in self.skill_categories["lora"]:
            skill = self.skills[skill_id]
            if skill.match(task_description):
                return {
                    "action": "lora",
                    "skill": skill,
                    "confidence": skill.get_success_rate(),
                    "reason": f"匹配LoRA模型: {skill.name}"
                }
        
        # 3. 检查外部API
        for skill_id in self.skill_categories["external"]:
            skill = self.skills[skill_id]
            if skill.match(task_description):
                return {
                    "action": "external",
                    "skill": skill,
                    "confidence": 0.8,
                    "reason": f"调用外部服务: {skill.name}"
                }
        
        # 4. 检查动态脚本
        for skill_id in self.skill_categories["script"]:
            skill = self.skills[skill_id]
            if skill.match(task_description):
                return {
                    "action": "script",
                    "skill": skill,
                    "confidence": skill.get_success_rate(),
                    "reason": f"执行动态脚本: {skill.name}"
                }
        
        # 5. 没有匹配技能，需要生成
        return {
            "action": "generate",
            "skill": None,
            "confidence": 0.3,
            "reason": "无匹配技能，需要生成新工具"
        }
    
    def update_skill_usage(self, skill_id: str, success: bool):
        """更新技能使用统计"""
        if skill_id in self.skills:
            skill = self.skills[skill_id]
            skill.usage_count += 1
            if success:
                skill.success_count += 1
            skill.last_used = datetime.now().isoformat()
            self._save_skills()
    
    def get_skill_stats(self) -> Dict:
        """获取技能统计"""
        return {
            "total": len(self.skills),
            "by_type": {k: len(v) for k, v in self.skill_categories.items()},
            "most_used": sorted(
                self.skills.values(), 
                key=lambda s: s.usage_count, 
                reverse=True
            )[:5]
        }


class TaskScheduler:
    """
    任务调度器 - 管理并行执行和依赖关系
    """
    
    def __init__(self, skill_tree: SkillTree):
        self.skill_tree = skill_tree
        self.execution_queue: List[Dict] = []
        self.results: Dict[str, Any] = {}
        self.dependencies: Dict[str, List[str]] = {}
    
    def schedule(self, task_tree: Dict) -> List[Dict]:
        """
        生成执行计划
        
        Args:
            task_tree: 拆解后的任务树
        
        Returns:
            执行计划列表
        """
        execution_plan = []
        
        for task_id, task in task_tree.items():
            # 评估任务
            strategy = self.skill_tree.evaluate_task(task.get("content", ""))
            
            # 构建执行项
            execution_item = {
                "task_id": task_id,
                "task": task,
                "strategy": strategy,
                "status": "pending",
                "dependencies": task.get("dependencies", []),
                "priority": self._calculate_priority(strategy, task)
            }
            
            execution_plan.append(execution_item)
        
        # 按优先级排序
        execution_plan.sort(key=lambda x: x["priority"], reverse=True)
        
        return execution_plan
    
    def _calculate_priority(self, strategy: Dict, task: Dict) -> float:
        """计算任务优先级"""
        base_priority = 1.0
        
        # 本地任务优先级高
        if strategy["action"] == "local":
            base_priority += 0.3
        
        # 高置信度优先
        base_priority += strategy["confidence"] * 0.2
        
        # 无依赖的任务优先
        if not task.get("dependencies"):
            base_priority += 0.2
        
        return base_priority
    
    def execute_plan(self, execution_plan: List[Dict], executor_callback) -> Dict:
        """
        执行计划
        
        Args:
            execution_plan: 执行计划
            executor_callback: 执行回调函数
        
        Returns:
            执行结果
        """
        results = {}
        
        for item in execution_plan:
            task_id = item["task_id"]
            strategy = item["strategy"]
            
            # 检查依赖是否满足
            deps_satisfied = all(
                dep_id in results and results[dep_id].get("success")
                for dep_id in item["dependencies"]
            )
            
            if not deps_satisfied and item["dependencies"]:
                results[task_id] = {
                    "success": False,
                    "error": "依赖未满足",
                    "result": None
                }
                continue
            
            # 执行任务
            try:
                result = executor_callback(
                    task=item["task"],
                    strategy=strategy
                )
                results[task_id] = {
                    "success": True,
                    "result": result
                }
                
                # 更新技能统计
                if strategy["skill"]:
                    self.skill_tree.update_skill_usage(
                        strategy["skill"].id, 
                        success=True
                    )
            except Exception as e:
                results[task_id] = {
                    "success": False,
                    "error": str(e),
                    "result": None
                }
                
                if strategy["skill"]:
                    self.skill_tree.update_skill_usage(
                        strategy["skill"].id, 
                        success=False
                    )
        
        return results


class ToolGenerator:
    """
    工具生成器 - 动态创建新技能
    """
    
    def __init__(self, skill_tree: SkillTree):
        self.skill_tree = skill_tree
        self.generated_tools: List[Dict] = []
    
    def should_generate_tool(self, task_description: str, failed_attempts: int = 0) -> bool:
        """判断是否需要生成新工具"""
        # 检查是否有匹配技能
        evaluation = self.skill_tree.evaluate_task(task_description)
        
        # 如果没有匹配且失败次数>=2，则生成
        if evaluation["action"] == "generate" and failed_attempts >= 2:
            return True
        
        # 如果匹配但成功率低，也考虑生成
        if evaluation["skill"] and evaluation["skill"].get_success_rate() < 0.3:
            return True
        
        return False
    
    def generate_tool(
        self, 
        task_description: str,
        llm_callback,
        examples: List[Dict] = None
    ) -> Optional[Skill]:
        """
        生成新工具
        
        Args:
            task_description: 任务描述
            llm_callback: LLM回调函数
            examples: 示例数据
        
        Returns:
            生成的技能
        """
        # 构建提示词
        prompt = f"""请为以下任务生成一个Python脚本工具：

任务描述：{task_description}

要求：
1. 脚本应该是一个完整的、可执行的Python函数
2. 包含必要的错误处理
3. 有清晰的输入输出
4. 添加必要的注释

请生成脚本代码：
"""
        
        if examples:
            prompt += f"\n\n参考示例：\n{json.dumps(examples, ensure_ascii=False, indent=2)}"
        
        # 调用LLM生成
        try:
            response = llm_callback(prompt)
            
            # 提取代码
            code = self._extract_code(response)
            
            if code:
                # 创建新技能
                skill = Skill(
                    id=f"generated_{len(self.generated_tools)}",
                    name=f"动态工具_{task_description[:20]}",
                    description=task_description,
                    skill_type="script",
                    keywords=self._extract_keywords(task_description),
                    config={"code": code, "auto_generated": True}
                )
                
                # 注册技能
                self.skill_tree.register_skill(skill)
                
                self.generated_tools.append({
                    "skill_id": skill.id,
                    "task": task_description,
                    "code": code,
                    "created_at": datetime.now().isoformat()
                })
                
                logger.info(f"🔧 生成新工具: {skill.name}")
                return skill
        
        except Exception as e:
            logger.error(f"工具生成失败: {e}")
        
        return None
    
    def _extract_code(self, response: str) -> Optional[str]:
        """从响应中提取代码"""
        # 提取```python```之间的代码
        pattern = r'```python\s*(.*?)\s*```'
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1)
        
        # 如果没有代码块，尝试提取函数定义
        if 'def ' in response:
            lines = response.split('\n')
            code_lines = []
            in_function = False
            for line in lines:
                if line.strip().startswith('def '):
                    in_function = True
                if in_function:
                    code_lines.append(line)
                    if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                        break
            return '\n'.join(code_lines)
        
        return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词"""
        # 简单的关键词提取
        keywords = []
        
        # 常见操作关键词
        operation_keywords = [
            "读取", "写入", "处理", "分析", "生成", "合并",
            "转换", "计算", "查询", "搜索", "下载", "上传"
        ]
        
        text_lower = text.lower()
        for kw in operation_keywords:
            if kw in text_lower:
                keywords.append(kw)
        
        # 添加文本中的关键名词
        words = re.findall(r'[\u4e00-\u9fa5]{2,}', text)
        keywords.extend(words[:3])
        
        return list(set(keywords))


# ============================================================
# 便捷函数
# ============================================================

def create_skill_system(data_dir: str = "data") -> tuple:
    """创建技能系统"""
    skill_tree = SkillTree(data_dir)
    scheduler = TaskScheduler(skill_tree)
    generator = ToolGenerator(skill_tree)
    
    return skill_tree, scheduler, generator


if __name__ == "__main__":
    # 测试
    skill_tree, scheduler, generator = create_skill_system()
    
    # 测试任务评估
    test_tasks = [
        "帮我读取data.xlsx文件",
        "什么是深度学习？",
        "写一个Python脚本批量重命名文件",
        "搜索最新的AI新闻",
    ]
    
    print("=" * 60)
    print("技能系统测试")
    print("=" * 60)
    
    for task in test_tasks:
        print(f"\n任务: {task}")
        evaluation = skill_tree.evaluate_task(task)
        print(f"策略: {evaluation['action']}")
        print(f"技能: {evaluation['skill'].name if evaluation['skill'] else 'N/A'}")
        print(f"置信度: {evaluation['confidence']:.2f}")
        print(f"原因: {evaluation['reason']}")
    
    print("\n" + "=" * 60)
    print("技能统计")
    print("=" * 60)
    stats = skill_tree.get_skill_stats()
    print(f"总技能数: {stats['total']}")
    print(f"按类型: {stats['by_type']}")