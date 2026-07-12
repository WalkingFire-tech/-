"""
闭环进化模块 (Closed-Loop Evolution Module)
完整的自我进化AI系统核心代码

功能：
1. 元认知启动 - 自我提问
2. 问题拆解 - 任务调度
3. 工具调用 - 执行引擎
4. 评估反思 - 概率优化
5. 知识固化 - 自我微调
6. 工具生成 - 技能积累
"""

import json
import re
import time
import hashlib
import subprocess
import tempfile
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import traceback

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class QuestionNode:
    """问题节点 - 表示一个待处理的问题或子问题"""
    id: str
    content: str
    parent_id: Optional[str] = None
    depth: int = 0
    status: str = "pending"  # pending, processing, answered, failed, skipped
    answer: Optional[str] = None
    sub_questions: List[str] = field(default_factory=list)
    execution_plan: Optional[Dict] = None
    execution_result: Optional[Dict] = None
    confidence: float = 0.0
    iteration_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved_at: Optional[str] = None


@dataclass
class ReflectionRecord:
    """反思记录"""
    question_id: str
    round: int
    reflection_type: str  # "self", "tool", "knowledge", "strategy"
    content: str
    insights: List[str] = field(default_factory=list)
    adjustments: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class KnowledgeItem:
    """知识条目"""
    id: str
    title: str
    content: str
    category: str  # "concept", "method", "fact", "strategy"
    tags: List[str] = field(default_factory=list)
    source: str  # "self_reflection", "execution", "user_input", "external"
    confidence: float = 0.7
    usage_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used_at: Optional[str] = None


@dataclass
class ToolSkill:
    """工具技能"""
    id: str
    name: str
    description: str
    script_code: str
    language: str  # "python", "powershell", "cmd", "bash"
    dependencies: List[str] = field(default_factory=list)
    usage_example: str
    success_rate: float = 0.0
    usage_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================
# 核心闭环引擎
# ============================================================

class ClosedLoopEngine:
    """
    闭环进化引擎
    核心流程：问题输入 → 自我问答 → 分解执行 → 反思收敛 → 知识固化 → 工具生成
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.max_depth = self.config.get('max_depth', 5)
        self.max_iterations = self.config.get('max_iterations', 10)
        self.convergence_threshold = self.config.get('convergence_threshold', 0.85)
        
        # 核心数据结构
        self.question_tree: Dict[str, QuestionNode] = {}
        self.root_question: Optional[QuestionNode] = None
        self.reflection_history: List[ReflectionRecord] = []
        self.knowledge_base: Dict[str, KnowledgeItem] = {}
        self.tool_skills: Dict[str, ToolSkill] = {}
        self.execution_stack: List[Dict] = []
        
        # 回调函数（外部注入）
        self.llm_callback: Optional[Callable] = None
        self.search_callback: Optional[Callable] = None
        self.execute_script_callback: Optional[Callable] = None
        self.ask_other_model_callback: Optional[Callable] = None
        
        # 状态
        self.is_running = False
        self.current_iteration = 0
        
        # 加载已有数据
        self._load_persistent_data()
        
        logger.info("🧬 闭环进化引擎已初始化")
    
    # ============================================================
    # 主流程：处理问题
    # ============================================================
    
    def process(self, question: str, context: Dict = None) -> Dict:
        """
        处理一个问题的完整闭环流程
        """
        logger.info(f"📥 收到问题: {question[:100]}...")
        
        # 重置状态
        self.is_running = True
        self.current_iteration = 0
        self.execution_stack = []
        
        # 步骤1：创建根问题节点
        root_id = self._generate_id("q")
        self.root_question = QuestionNode(
            id=root_id,
            content=question,
            depth=0
        )
        self.question_tree[root_id] = self.root_question
        
        # 步骤2：初始自我问答（元认知启动）
        meta_questions = self._generate_meta_questions(question)
        logger.info(f"🧠 生成元认知问题: {len(meta_questions)} 个")
        
        for mq in meta_questions:
            child = self._add_sub_question(root_id, mq)
            self._process_question_node(child)
        
        # 步骤3：问题拆解与处理
        self._process_question_node(self.root_question)
        
        # 步骤4：执行与反思循环
        while not self._check_convergence():
            self.current_iteration += 1
            logger.info(f"🔄 迭代 {self.current_iteration}/{self.max_iterations}")
            
            pending_nodes = self._get_pending_nodes()
            for node in pending_nodes:
                self._execute_question_node(node)
            
            self._reflect_on_progress()
            
            if self.current_iteration >= self.max_iterations:
                break
        
        # 步骤5：知识提取与固化
        new_knowledge = self._extract_knowledge()
        for k in new_knowledge:
            self.knowledge_base[k.id] = k
        
        # 步骤6：工具生成
        new_tools = self._generate_tools_from_solutions()
        for t in new_tools:
            self.tool_skills[t.id] = t
        
        # 步骤7：保存数据
        self._save_persistent_data()
        
        self.is_running = False
        
        result = {
            "answer": self.root_question.answer or "未能生成完整答案",
            "knowledge": [{"id": k.id, "title": k.title, "content": k.content} for k in new_knowledge],
            "tools": [{"id": t.id, "name": t.name, "description": t.description} for t in new_tools],
            "reflection_summary": self._generate_reflection_summary(),
            "execution_trace": self.execution_stack[-20:],
            "iterations": self.current_iteration,
            "nodes_processed": len([n for n in self.question_tree.values() if n.status == "answered"])
        }
        
        logger.info(f"✅ 问题处理完成: {len(result['knowledge'])} 条知识, {len(result['tools'])} 个工具")
        return result
    
    # ============================================================
    # 核心方法实现
    # ============================================================
    
    def _generate_meta_questions(self, question: str) -> List[str]:
        """生成元认知问题"""
        return [
            f"这个问题的核心是什么？",
            f"这个问题属于哪个领域？",
            f"我当前掌握哪些相关信息？",
            f"我还缺少哪些信息？",
            f"有哪些可能的解决路径？",
        ]
    
    def _add_sub_question(self, parent_id: str, content: str) -> QuestionNode:
        """添加子问题"""
        node_id = self._generate_id("q")
        parent = self.question_tree[parent_id]
        node = QuestionNode(
            id=node_id,
            content=content,
            parent_id=parent_id,
            depth=parent.depth + 1
        )
        self.question_tree[node_id] = node
        parent.sub_questions.append(node_id)
        return node
    
    def _process_question_node(self, node: QuestionNode):
        """处理问题节点"""
        if node.status in ["answered", "failed", "skipped"]:
            return
        
        if node.depth > self.max_depth:
            node.status = "skipped"
            return
        
        node.status = "processing"
        
        # 尝试直接回答
        direct_answer = self._try_direct_answer(node)
        if direct_answer and direct_answer.get('confidence', 0) > 0.6:
            node.answer = direct_answer['content']
            node.confidence = direct_answer['confidence']
            node.status = "answered"
            node.resolved_at = datetime.now().isoformat()
            return
        
        # 拆解问题
        sub_questions = self._decompose_question(node.content)
        if sub_questions:
            for sq in sub_questions:
                child = self._add_sub_question(node.id, sq)
                self._process_question_node(child)
            
            # 合并答案
            if all(self.question_tree[sid].status == "answered" for sid in node.sub_questions):
                merged = self._merge_answers(node)
                if merged:
                    node.answer = merged['content']
                    node.confidence = merged['confidence']
                    node.status = "answered"
                    node.resolved_at = datetime.now().isoformat()
                else:
                    node.status = "failed"
        else:
            node.status = "failed"
    
    def _try_direct_answer(self, node: QuestionNode) -> Optional[Dict]:
        """尝试直接回答"""
        strategies = [
            ('internal', self._answer_from_internal),
            ('search', self._answer_from_search),
            ('other_model', self._answer_from_other_model),
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                result = strategy_func(node.content)
                if result and result.get('confidence', 0) > 0.5:
                    return result
            except Exception as e:
                logger.error(f"策略 {strategy_name} 失败: {e}")
                continue
        
        return None
    
    def _answer_from_internal(self, question: str) -> Optional[Dict]:
        """从内部知识库回答"""
        relevant = []
        for k in self.knowledge_base.values():
            if question in k.content or k.title in question:
                relevant.append(k)
        
        if relevant:
            best = max(relevant, key=lambda x: x.confidence)
            return {
                'content': f"根据已有知识：{best.content}",
                'confidence': best.confidence * 0.8
            }
        return None
    
    def _answer_from_search(self, question: str) -> Optional[Dict]:
        """从搜索获取答案"""
        if self.search_callback:
            try:
                results = self.search_callback(question)
                if results:
                    return {
                        'content': results[:500],
                        'confidence': 0.6,
                        'source': 'search'
                    }
            except Exception as e:
                logger.error(f"搜索失败: {e}")
        return None
    
    def _answer_from_other_model(self, question: str) -> Optional[Dict]:
        """从其他模型获取答案"""
        if self.ask_other_model_callback:
            try:
                response = self.ask_other_model_callback(question)
                if response:
                    return {
                        'content': response,
                        'confidence': 0.7,
                        'source': 'other_model'
                    }
            except Exception as e:
                logger.error(f"其他模型调用失败: {e}")
        return None
    
    def _decompose_question(self, question: str) -> List[str]:
        """拆解问题"""
        if self.llm_callback:
            prompt = f"""
请将以下问题拆解为3-5个子问题，每行一个，格式为"1. 子问题内容"。

问题：{question}
"""
            try:
                response = self.llm_callback(prompt)
                lines = [l.strip() for l in response.split('\n') if l.strip() and l.strip()[0].isdigit()]
                if lines:
                    sub_questions = []
                    for line in lines:
                        parts = line.split('.', 1)
                        if len(parts) > 1:
                            sub_questions.append(parts[1].strip())
                        else:
                            sub_questions.append(line)
                    return sub_questions
            except Exception as e:
                logger.error(f"LLM拆解失败: {e}")
        
        return self._decompose_by_rules(question)
    
    def _decompose_by_rules(self, question: str) -> List[str]:
        """基于规则的问题拆解"""
        if "如何" in question or "怎样" in question:
            return [
                f"{question} 的第一步是什么？",
                f"{question} 的关键难点是什么？",
                f"{question} 的最终目标是什么？",
            ]
        elif "为什么" in question:
            return [
                f"{question} 的根本原因是什么？",
                f"{question} 的机制或原理是什么？",
            ]
        else:
            return [
                f"这个问题的核心概念是什么？",
                f"解决这个问题需要哪些信息？",
            ]
    
    def _execute_question_node(self, node: QuestionNode):
        """执行问题节点"""
        if node.status != "pending":
            return
        
        if self._needs_execution(node):
            plan = self._create_execution_plan(node)
            if plan:
                result = self._execute_plan(plan)
                node.execution_result = result
                if result.get('success'):
                    node.answer = result.get('output', '执行完成')
                    node.status = "answered"
                    node.resolved_at = datetime.now().isoformat()
                else:
                    node.status = "failed"
    
    def _needs_execution(self, node: QuestionNode) -> bool:
        """判断是否需要执行"""
        keywords = ['生成', '创建', '写', '运行', '执行', '调用', '自动化', '脚本', '代码']
        return any(kw in node.content for kw in keywords)
    
    def _create_execution_plan(self, node: QuestionNode) -> Optional[Dict]:
        """创建执行计划"""
        if self.llm_callback:
            prompt = f"""
请为以下任务创建执行计划，输出JSON格式：
{{
    "tool_type": "python|powershell|cmd",
    "description": "简短描述",
    "code": "可执行代码"
}}

任务：{node.content}
"""
            try:
                response = self.llm_callback(prompt)
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except Exception as e:
                logger.error(f"生成执行计划失败: {e}")
        return None
    
    def _execute_plan(self, plan: Dict) -> Dict:
        """执行计划"""
        tool_type = plan.get('tool_type', '')
        code = plan.get('code', '')
        
        if self.execute_script_callback:
            try:
                result = self.execute_script_callback(code, tool_type)
                return {'success': True, 'output': result}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        
        return {'success': False, 'error': '执行回调未配置'}
    
    def _merge_answers(self, node: QuestionNode) -> Optional[Dict]:
        """合并子问题答案"""
        answers = [self.question_tree[sid].answer for sid in node.sub_questions if self.question_tree[sid].answer]
        if not answers:
            return None
        
        if self.llm_callback:
            prompt = f"请整合以下回答：\n\n{' '.join(answers)}"
            try:
                response = self.llm_callback(prompt)
                return {
                    'content': response,
                    'confidence': sum(self.question_tree[sid].confidence for sid in node.sub_questions) / len(node.sub_questions)
                }
            except Exception:
                logger.warning("操作降级跳过")
        
        return {
            'content': '\n\n'.join(answers),
            'confidence': 0.5
        }
    
    # ============================================================
    # 反思与收敛
    # ============================================================
    
    def _reflect_on_progress(self):
        """反思进度"""
        reflection = {
            'round': self.current_iteration,
            'nodes_answered': len([n for n in self.question_tree.values() if n.status == "answered"]),
            'nodes_failed': len([n for n in self.question_tree.values() if n.status == "failed"]),
            'pending': len(self._get_pending_nodes()),
        }
        
        total = reflection['nodes_answered'] + reflection['nodes_failed']
        if total > 0 and reflection['nodes_failed'] / total > 0.4:
            self._adjust_strategy()
        
        self.reflection_history.append(ReflectionRecord(
            question_id=self.root_question.id,
            round=self.current_iteration,
            reflection_type="progress",
            content=json.dumps(reflection)
        ))
        
        logger.info(f"📊 反思: 已回答 {reflection['nodes_answered']} 个节点")
    
    def _adjust_strategy(self):
        """调整策略"""
        logger.warning("⚠️ 失败率过高，调整策略")
        for node in self.question_tree.values():
            if node.status == "failed" and node.depth < self.max_depth:
                sub_questions = self._decompose_question(node.content)
                if sub_questions:
                    for sq in sub_questions:
                        self._add_sub_question(node.id, sq)
                    node.status = "pending"
    
    def _check_convergence(self) -> bool:
        """检查收敛"""
        all_processed = all(
            n.status in ["answered", "failed", "skipped"]
            for n in self.question_tree.values()
        )
        if all_processed:
            return True
        
        answered = [n for n in self.question_tree.values() if n.status == "answered"]
        if answered and all(n.confidence > self.convergence_threshold for n in answered):
            return True
        
        return False
    
    def _get_pending_nodes(self) -> List[QuestionNode]:
        """获取待处理节点"""
        return [n for n in self.question_tree.values() if n.status == "pending"]
    
    # ============================================================
    # 知识提取与工具生成
    # ============================================================
    
    def _extract_knowledge(self) -> List[KnowledgeItem]:
        """提取知识"""
        knowledge_items = []
        
        for node in self.question_tree.values():
            if node.status == "answered" and node.answer and node.confidence > 0.6:
                item = KnowledgeItem(
                    id=self._generate_id("k"),
                    title=node.content[:50],
                    content=node.answer[:500],
                    category="method",
                    source="self_reflection",
                    confidence=node.confidence
                )
                knowledge_items.append(item)
        
        return knowledge_items
    
    def _generate_tools_from_solutions(self) -> List[ToolSkill]:
        """生成工具"""
        tools = []
        
        for node in self.question_tree.values():
            if node.execution_result and node.execution_result.get('success'):
                if node.execution_plan:
                    plan = node.execution_plan
                    if plan.get('code'):
                        tool = ToolSkill(
                            id=self._generate_id("t"),
                            name=node.content[:30].replace(" ", "_"),
                            description=node.content[:100],
                            script_code=plan.get('code', ''),
                            language=plan.get('tool_type', 'python'),
                            usage_example=node.content
                        )
                        tools.append(tool)
        
        return tools
    
    # ============================================================
    # 数据持久化
    # ============================================================
    
    def _load_persistent_data(self):
        """加载数据"""
        data_dir = Path(self.config.get('data_dir', './data/closed_loop'))
        data_dir.mkdir(parents=True, exist_ok=True)
        
        knowledge_file = data_dir / 'knowledge.json'
        if knowledge_file.exists():
            try:
                with open(knowledge_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        self.knowledge_base[item['id']] = KnowledgeItem(**item)
                logger.info(f"📚 加载知识库: {len(self.knowledge_base)} 条")
            except Exception as e:
                logger.warning(f"加载知识库失败: {e}")
        
        tools_file = data_dir / 'tools.json'
        if tools_file.exists():
            try:
                with open(tools_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        self.tool_skills[item['id']] = ToolSkill(**item)
                logger.info(f"🔧 加载工具库: {len(self.tool_skills)} 个")
            except Exception as e:
                logger.warning(f"加载工具库失败: {e}")
    
    def _save_persistent_data(self):
        """保存数据"""
        data_dir = Path(self.config.get('data_dir', './data/closed_loop'))
        data_dir.mkdir(parents=True, exist_ok=True)
        
        knowledge_file = data_dir / 'knowledge.json'
        try:
            with open(knowledge_file, 'w', encoding='utf-8') as f:
                data = [asdict(k) for k in self.knowledge_base.values()]
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.warning(f"保存知识库失败: {e}")
        
        tools_file = data_dir / 'tools.json'
        try:
            with open(tools_file, 'w', encoding='utf-8') as f:
                data = [asdict(t) for t in self.tool_skills.values()]
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.warning(f"保存工具库失败: {e}")
    
    # ============================================================
    # 辅助方法
    # ============================================================
    
    def _generate_id(self, prefix: str) -> str:
        """生成ID"""
        return f"{prefix}_{int(time.time()*1000)}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"
    
    def _generate_reflection_summary(self) -> str:
        """生成反思总结"""
        summary = f"反思总结 (共 {self.current_iteration} 轮迭代)\n"
        summary += "=" * 40 + "\n"
        
        answered = [n for n in self.question_tree.values() if n.status == "answered"]
        summary += f"已回答节点: {len(answered)}\n"
        
        failed = [n for n in self.question_tree.values() if n.status == "failed"]
        summary += f"失败节点: {len(failed)}\n"
        
        return summary


# ============================================================
# 集成器
# ============================================================

class ClosedLoopIntegrator:
    """闭环进化模块集成器"""
    
    def __init__(self, pioneer_system=None):
        self.pioneer = pioneer_system
        self.engine = ClosedLoopEngine({
            'data_dir': './data/closed_loop',
            'max_depth': 5,
            'max_iterations': 10,
            'convergence_threshold': 0.85
        })
        
        # 注入回调
        self.engine.llm_callback = self._call_llm
        self.engine.search_callback = self._call_search
        self.engine.execute_script_callback = self._call_execute_script
        self.engine.ask_other_model_callback = self._call_other_model
        
        logger.info("🔗 闭环进化模块已集成")
    
    def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        if self.pioneer and hasattr(self.pioneer, 'generate'):
            return self.pioneer.generate(prompt)
        return ""
    
    def _call_search(self, query: str) -> str:
        """调用搜索"""
        if self.pioneer and hasattr(self.pioneer, 'search'):
            return self.pioneer.search(query)
        return ""
    
    def _call_execute_script(self, code: str, language: str) -> str:
        """执行脚本"""
        if language == 'python':
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                script_path = f.name
            
            try:
                result = subprocess.run(
                    ['python', script_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                return result.stdout + result.stderr
            except Exception as e:
                return f"执行错误: {e}"
            finally:
                Path(script_path).unlink(missing_ok=True)
        
        return f"不支持的语言: {language}"
    
    def _call_other_model(self, question: str) -> str:
        """调用其他模型"""
        return f"其他模型回答: (模型未配置) {question}"
    
    def process_with_loop(self, question: str) -> Dict:
        """使用闭环处理问题"""
        return self.engine.process(question)
    
    def get_knowledge_base(self) -> Dict:
        """获取知识库"""
        return self.engine.knowledge_base
    
    def get_tool_skills(self) -> Dict:
        """获取工具库"""
        return self.engine.tool_skills


# ============================================================
# 使用示例
# ============================================================

if __name__ == "__main__":
    # 模拟主系统
    class MockPioneer:
        def generate(self, prompt):
            if "拆解" in prompt:
                return "1. 子问题A\n2. 子问题B\n3. 子问题C"
            if "整合" in prompt:
                return "这是整合后的完整回答"
            return f"模拟回答: {prompt[:50]}"
        
        def search(self, query):
            return f"搜索到关于 {query} 的信息..."
    
    # 创建集成器
    pioneer = MockPioneer()
    integrator = ClosedLoopIntegrator(pioneer)
    
    # 处理问题
    result = integrator.process_with_loop(
        "如何用Python批量重命名文件夹中的所有文件？"
    )
    
    print("\n" + "="*60)
    print("📊 处理结果")
    print("="*60)
    print(f"回答: {result['answer'][:200]}...")
    print(f"知识: {len(result['knowledge'])} 条")
    print(f"工具: {len(result['tools'])} 个")
    print(f"迭代: {result['iterations']} 轮")
    print(f"节点: {result['nodes_processed']} 个")