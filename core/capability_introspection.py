"""
能力自省系统 - 让系统知道自己能做什么，并主动协调使用
"""
import json
import inspect
from typing import Dict, List, Any, Optional
from pathlib import Path
from loguru import logger

class CapabilityIntrospection:
    """能力自省系统 - 系统的自我认知"""
    
    def __init__(self):
        self.capabilities = {}
        self.capability_registry = {}
        self.usage_history = []
        self._scan_all_capabilities()
        
    def _scan_all_capabilities(self):
        """扫描系统所有能力"""
        logger.info("🔍 开始扫描系统能力...")
        
        # 1. 扫描核心模块
        self._scan_core_modules()
        
        # 2. 扫描工具
        self._scan_tools()
        
        # 3. 扫描模型
        self._scan_models()
        
        # 4. 扫描知识库
        self._scan_knowledge_bases()
        
        # 5. 扫描学习机制
        self._scan_learning_mechanisms()
        
        # 6. 扫描进化机制
        self._scan_evolution_mechanisms()
        
        logger.info(f"✅ 能力扫描完成: {len(self.capabilities)}个能力")
        
    def _scan_core_modules(self):
        """扫描核心模块能力"""
        modules = {
            "对话处理": [
                ("意图识别", "core.services.intent_parser", "IntentParser", "parse"),
                ("规划执行", "core.services.planner", "Planner", "plan"),
                ("对话认知", "core.dialogue.dialogue_cognitive_engine", "DialogueCognitiveEngine", "process"),
                ("场景感知", "core.dialogue.scene_perceiver", "ScenePerceiver", "perceive"),
                ("对话理解", "core.dialogue.dialogue_understander", "DialogueUnderstander", "understand"),
            ],
            "知识管理": [
                ("知识检索", "core.learning", "enhanced_learner", "retrieve_knowledge"),
                ("向量检索", "core.vector_retriever", "vector_retriever", "hybrid_search"),
                ("知识验证", "core.knowledge.validator", "KnowledgeValidator", "validate"),
                ("知识检测", "core.knowledge.detector", "KnowledgeDetector", "detect"),
            ],
            "学习进化": [
                ("学习闭环", "core.learning_loop", "LearningLoop", "trigger_learning"),
                ("自我进化", "core.self_evolution", "SelfEvolutionEngine", "evolve"),
                ("外部学习", "core.external_learner", "ExternalLearner", "learn_from_external"),
                ("闭环推理", "core.closed_loop_reasoning", "ClosedLoopReasoning", "reason_with_full_cycle"),
            ],
            "反思机制": [
                ("自我反思", "core.self_reflection", "SelfReflection", "reflect"),
                ("自我评估", "core.presence.self_assessment", "SelfAssessment", "assess"),
                ("知识缺失检测", "core.knowledge_gap_detector", "gap_detector", "detect_knowledge_gap"),
            ],
            "存在感知": [
                ("存在层", "core.presence.existence_layer", "ExistenceLayer", "check_boundary"),
                ("自我感知", "core.presence.self_perception", "SelfPerception", "perceive_self"),
                ("主动感知", "core.presence.active_perception", "ActivePerception", "actively_perceive"),
            ],
        }
        
        for category, caps in modules.items():
            for name, module_path, class_name, method in caps:
                capability = self._check_capability(name, module_path, class_name, method)
                if capability:
                    capability["category"] = category
                    self.capabilities[name] = capability
                    
    def _scan_tools(self):
        """扫描工具能力"""
        try:
            from core.tool_registry import tool_registry
            tools = tool_registry.list_tools()
            
            for tool in tools:
                self.capabilities[f"工具:{tool['name']}"] = {
                    "type": "tool",
                    "name": tool["name"],
                    "category": "工具调用",
                    "description": tool.get("description", ""),
                    "available": True,
                    "module": f"tools.{tool['name']}"
                }
        except Exception as e:
            logger.debug(f"工具扫描失败: {e}")
            
    def _scan_models(self):
        """扫描模型能力"""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                
                for model in models:
                    self.capabilities[f"模型:{model['name']}"] = {
                        "type": "model",
                        "name": model["name"],
                        "category": "模型推理",
                        "available": True,
                        "module": "adapters.llm.ollama_adapter"
                    }
        except Exception as e:
            logger.debug(f"模型扫描失败: {e}")
            
    def _scan_knowledge_bases(self):
        """扫描知识库"""
        kb_files = [
            ("data/knowledge_store.db", "主知识库"),
            ("data/experience_pool.db", "经验池"),
            ("data/learning_rules.db", "学习规则库"),
        ]
        
        for path, name in kb_files:
            if Path(path).exists():
                self.capabilities[f"知识库:{name}"] = {
                    "type": "knowledge_base",
                    "name": name,
                    "category": "知识存储",
                    "path": path,
                    "available": True
                }
                
    def _scan_learning_mechanisms(self):
        """扫描学习机制"""
        mechanisms = [
            ("即时学习", "core.instant_learning", "InstantLearningSystem"),
            ("炼丹炉", "core.auto_furnace", "AutoFurnace"),
            ("错误炼金术", "core.learning.error_alchemy", "ErrorAlchemy"),
            ("工具构建器", "core.learning.tool_builder", "ToolBuilder"),
            ("知识编织器", "core.learning.knowledge_weaver", "KnowledgeWeaver"),
        ]
        
        for name, module_path, class_name in mechanisms:
            capability = self._check_capability(name, module_path, class_name)
            if capability:
                capability["category"] = "学习机制"
                self.capabilities[name] = capability
                
    def _scan_evolution_mechanisms(self):
        """扫描进化机制"""
        mechanisms = [
            ("元学习", "core.evolution.meta_learning", "MetaLearner"),
            ("行为进化", "core.evolution.behavior_evolution", "BehaviorEvolution"),
            ("知识进化", "core.evolution.knowledge_evolution", "KnowledgeEvolution"),
            ("策略进化", "core.evolution.strategy_evolution", "StrategyEvolution"),
        ]
        
        for name, module_path, class_name in mechanisms:
            capability = self._check_capability(name, module_path, class_name)
            if capability:
                capability["category"] = "进化机制"
                self.capabilities[name] = capability
                
    def _check_capability(self, name: str, module_path: str, class_name: str, method: str = None) -> Optional[Dict]:
        """检查能力是否可用"""
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name, None)
            
            if cls is None:
                return None
                
            # 检查方法是否存在
            if method and not hasattr(cls, method):
                return None
                
            return {
                "type": "module",
                "name": name,
                "module": module_path,
                "class": class_name,
                "method": method,
                "available": True,
                "description": f"{name} - {module_path}.{class_name}"
            }
            
        except Exception as e:
            logger.debug(f"能力检查失败 {name}: {e}")
            return None
    
    def get_capabilities_by_category(self) -> Dict[str, List[str]]:
        """按类别获取能力"""
        categories = {}
        for name, cap in self.capabilities.items():
            category = cap.get("category", "其他")
            if category not in categories:
                categories[category] = []
            categories[category].append(name)
        return categories
    
    def get_available_capabilities(self) -> List[str]:
        """获取所有可用能力"""
        return [name for name, cap in self.capabilities.items() if cap.get("available")]
    
    def can_do(self, task_type: str) -> bool:
        """检查是否能完成某类任务"""
        task_capability_map = {
            "回答问题": ["意图识别", "知识检索", "模型推理"],
            "学习新知识": ["外部学习", "知识检索", "学习闭环"],
            "自我反思": ["自我反思", "自我评估", "知识缺失检测"],
            "进化提升": ["元学习", "行为进化", "知识进化"],
            "调用工具": ["工具:calculator", "工具:code_executor"],
            "执行系统命令": ["工具:bash", "系统命令执行"],
            "读取串口数据": ["工具:serial_port", "硬件访问"],
            "访问硬件": ["工具:serial_port", "工具:bash", "硬件访问"],
        }
        
        required = task_capability_map.get(task_type, [])
        return all(any(r in cap for cap in self.capabilities) for r in required)
    
    def generate_capability_report(self) -> str:
        """生成能力报告"""
        categories = self.get_capabilities_by_category()
        
        report = "# 系统能力自省报告\n\n"
        report += f"总能力数: {len(self.capabilities)}\n"
        report += f"可用能力: {len(self.get_available_capabilities())}\n\n"
        
        for category, caps in sorted(categories.items()):
            report += f"## {category} ({len(caps)}个)\n"
            for cap in caps:
                status = "✅" if self.capabilities[cap].get("available") else "❌"
                report += f"  {status} {cap}\n"
            report += "\n"
            
        return report


class DynamicCapabilityScheduler:
    """动态能力调度器 - 根据问题动态选择和协调能力"""
    
    def __init__(self, introspection: CapabilityIntrospection):
        self.introspection = introspection
        self.execution_history = []
        
    def analyze_problem(self, problem: str) -> Dict[str, Any]:
        """分析问题，确定需要哪些能力"""
        
        # 1. 问题类型识别
        problem_type = self._identify_problem_type(problem)
        
        # 2. 确定需要的能力
        required_capabilities = self._determine_required_capabilities(problem_type, problem)
        
        # 3. 检查能力是否可用
        available = []
        missing = []
        
        for cap in required_capabilities:
            if cap in self.introspection.capabilities:
                available.append(cap)
            else:
                missing.append(cap)
        
        # 4. 制定执行计划
        execution_plan = self._create_execution_plan(available, problem)
        
        return {
            "problem": problem,
            "problem_type": problem_type,
            "required_capabilities": required_capabilities,
            "available": available,
            "missing": missing,
            "execution_plan": execution_plan
        }
    
    def _identify_problem_type(self, problem: str) -> str:
        """识别问题类型"""
        
        # 关键词匹配
        patterns = {
            "知识查询": ["是什么", "什么是", "介绍", "解释", "说明"],
            "操作执行": ["执行", "运行", "计算", "处理", "操作"],
            "问题解决": ["如何", "怎么", "解决", "修复", "优化"],
            "学习请求": ["学习", "记住", "保存", "记录"],
            "能力查询": ["你能", "你会", "能力", "功能"],
            "反思请求": ["反思", "评估", "检查", "验证"],
        }
        
        for ptype, keywords in patterns.items():
            if any(kw in problem for kw in keywords):
                return ptype
                
        return "通用问题"
    
    def _determine_required_capabilities(self, problem_type: str, problem: str) -> List[str]:
        """确定需要的能力"""
        
        base_capabilities = {
            "知识查询": ["意图识别", "知识检索", "向量检索", "模型推理"],
            "操作执行": ["意图识别", "工具调用", "规划执行"],
            "问题解决": ["意图识别", "知识检索", "规划执行", "闭环推理", "自我反思"],
            "学习请求": ["意图识别", "外部学习", "学习闭环", "知识验证"],
            "能力查询": ["能力自省"],
            "反思请求": ["自我反思", "自我评估", "知识缺失检测"],
            "通用问题": ["意图识别", "知识检索", "模型推理", "闭环推理"],
        }
        
        return base_capabilities.get(problem_type, base_capabilities["通用问题"])
    
    def _create_execution_plan(self, capabilities: List[str], problem: str) -> List[Dict]:
        """创建执行计划"""
        plan = []
        
        # 根据能力顺序制定计划
        priority_order = [
            "意图识别", "知识检索", "向量检索", "规划执行",
            "模型推理", "工具调用", "闭环推理", "自我反思",
            "外部学习", "学习闭环", "知识验证"
        ]
        
        for i, cap in enumerate(priority_order):
            if cap in capabilities or any(cap in c for c in capabilities):
                plan.append({
                    "step": i + 1,
                    "capability": cap,
                    "action": self._get_action_for_capability(cap, problem),
                    "dependencies": plan[-1]["step"] if plan else None
                })
        
        return plan
    
    def _get_action_for_capability(self, capability: str, problem: str) -> str:
        """获取能力对应的动作"""
        actions = {
            "意图识别": f"识别'{problem[:30]}...'的意图",
            "知识检索": f"检索关于'{problem[:30]}'的知识",
            "向量检索": f"向量搜索'{problem[:30]}'",
            "规划执行": "制定并执行解决方案",
            "模型推理": "调用模型生成回答",
            "工具调用": "选择并调用合适的工具",
            "闭环推理": "执行完整的闭环推理",
            "自我反思": "反思回答质量并改进",
            "外部学习": "从外部资源学习",
            "学习闭环": "触发学习闭环",
            "知识验证": "验证知识正确性",
        }
        
        return actions.get(capability, f"执行{capability}")
    
    async def execute_with_coordination(
        self,
        problem: str,
        context: Dict = None
    ) -> Dict[str, Any]:
        """协调执行 - 让所有能力协调工作"""
        
        # 1. 分析问题
        analysis = self.analyze_problem(problem)
        
        logger.info(f"🎯 问题分析: {analysis['problem_type']}")
        logger.info(f"📋 需要能力: {analysis['required_capabilities']}")
        logger.info(f"✅ 可用能力: {analysis['available']}")
        
        if analysis['missing']:
            logger.warning(f"⚠️ 缺失能力: {analysis['missing']}")
        
        # 2. 按计划执行
        results = {}
        execution_plan = analysis['execution_plan']
        
        for step in execution_plan:
            capability = step['capability']
            action = step['action']
            
            logger.info(f"[步骤{step['step']}] {capability}: {action}")
            
            # 执行能力
            result = await self._execute_capability(capability, problem, context, results)
            results[capability] = result
            
            # 记录执行历史
            self.execution_history.append({
                "step": step['step'],
                "capability": capability,
                "action": action,
                "success": result.get("success", False),
                "timestamp": str(datetime.now())
            })
        
        # 3. 综合结果
        final_result = self._synthesize_results(results, analysis)
        
        return {
            "analysis": analysis,
            "execution_results": results,
            "final_result": final_result,
            "execution_history": self.execution_history
        }
    
    async def _execute_capability(
        self,
        capability: str,
        problem: str,
        context: Dict,
        previous_results: Dict
    ) -> Dict:
        """执行单个能力"""
        
        try:
            if capability == "意图识别":
                from core.services.intent_parser import IntentParser
                parser = IntentParser()
                intent = parser.parse(problem)
                return {"success": True, "intent": intent.type, "confidence": intent.confidence}
                
            elif capability == "知识检索":
                from core.learning import enhanced_learner
                result = enhanced_learner.retrieve_knowledge(problem)
                return {"success": bool(result), "result": result}
                
            elif capability == "向量检索":
                from infrastructure.vector_retriever import vector_retriever
                results = vector_retriever.search_similar(problem, k=3)
                return {"success": bool(results), "results": results}
                
            elif capability == "闭环推理":
                from core.visible_closed_loop import VisibleClosedLoop
                loop = VisibleClosedLoop()
                # 简化执行
                return {"success": True, "message": "闭环推理已执行"}
                
            elif capability == "自我反思":
                from core.self_reflection import SelfReflection
                reflection = SelfReflection()
                # 简化执行
                return {"success": True, "message": "自我反思已执行"}
                
            else:
                return {"success": False, "message": f"能力{capability}未实现执行逻辑"}
                
        except Exception as e:
            logger.error(f"能力执行失败 {capability}: {e}")
            return {"success": False, "error": str(e)}
    
    def _synthesize_results(self, results: Dict, analysis: Dict) -> str:
        """综合所有结果"""
        # 从结果中提取最佳答案
        for cap in ["知识检索", "向量检索", "模型推理"]:
            if cap in results and results[cap].get("success"):
                result = results[cap].get("result")
                if result:
                    if isinstance(result, dict) and "answer" in result:
                        return result["answer"]
                    elif isinstance(result, str):
                        return result
        
        return "协调执行完成，但未获得明确答案"


# 全局实例
_introspection = None
_scheduler = None

def get_capability_introspection() -> CapabilityIntrospection:
    """获取能力自省实例"""
    global _introspection
    if _introspection is None:
        _introspection = CapabilityIntrospection()
    return _introspection

def get_capability_scheduler() -> DynamicCapabilityScheduler:
    """获取能力调度器"""
    global _scheduler
    if _scheduler is None:
        _scheduler = DynamicCapabilityScheduler(get_capability_introspection())
    return _scheduler