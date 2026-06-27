"""
认知调度器（Cognitive Dispatcher）- 系统的神经中枢

职责：
1. 意图分类 - 判断问题复杂度
2. 能力盘点 - 扫描可用工具/模型
3. 路由决策 - 选择执行路径
4. 计划生成 - 拆解任务步骤

跨学科理论：
- 认知科学：双重加工理论（System 1快思考 vs System 2慢思考）
- 控制论：前馈控制（Feedforward Control）
- 系统论：分层递阶控制（Hierarchical Control）

与QuickReflexEngine的关系：
- QuickReflex作为T0层前置拦截简单问题
- CognitiveDispatcher仅处理QuickReflex未匹配的请求
- 因此移除fast路径，专注于slow/learning路径
"""
import json
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from loguru import logger
from pathlib import Path
import sqlite3
import threading


class CognitiveDispatcher:
    """
    认知调度器 - 决定问题走哪条路径
    
    路径分类：
    - 快路径（System 1）：问候、确认、简单查询 → 直接回答
    - 慢路径（System 2）：复杂问题 → 完整认知流程
    - 学习路径：知识缺失 → 触发外部学习
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        self.intent_patterns = self._load_intent_patterns(config)
        self.capability_cache = None
        self.cache_timestamp = 0
        self.cache_ttl = config.get("cache_ttl", 300)
        self._cache_lock = threading.Lock()
        
        self.complexity_weights = config.get("complexity_weights", {
            "base": 1.0,
            "length": 0.1,
            "keyword": 0.1,
            "multi_question": 0.2
        })
        
        self.route_thresholds = config.get("route_thresholds", {
            "fast_complexity": 0.3,
            "fast_confidence": 0.7,
            "learning_confidence": 0.5
        })
        
        self.enable_capability_scan = config.get("enable_capability_scan", {
            "tools": True,
            "models": True,
            "knowledge_bases": True
        })
        
        logger.info("🧠 认知调度器已初始化")
        logger.info(f"  - 缓存TTL: {self.cache_ttl}秒")
        logger.info(f"  - 能力扫描: {self.enable_capability_scan}")
    
    def _load_intent_patterns(self, config: Dict = None) -> Dict[str, List[str]]:
        """加载意图模式（支持外部配置）"""
        config = config or {}
        
        if "intent_patterns_file" in config:
            try:
                with open(config["intent_patterns_file"], "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载外部意图模式失败: {e}，使用默认模式")
        
        return {
            "greeting": [
                "你好", "您好", "hi", "hello", "在吗", "在不在"
            ],
            "confirmation": [
                "好的", "收到", "明白", "知道了", "谢谢", "感谢"
            ],
            "simple_query": [
                "是什么", "什么是", "怎么读", "多少", "什么时候"
            ],
            "complex_query": [
                "为什么", "如何实现", "怎么优化", "分析", "比较",
                "设计", "构建", "创建", "实现", "改进"
            ],
            "learning_trigger": [
                "我不懂", "不明白", "什么是", "介绍一下", "解释一下"
            ]
        }
    
    def dispatch(self, user_query: str, context: Dict = None) -> Dict[str, Any]:
        """
        调度决策 - 返回执行计划
        
        返回：
        {
            "route": "fast" | "slow" | "learning",
            "complexity": 0.0-1.0,
            "intent_type": str,
            "capabilities": dict,
            "execution_plan": dict,
            "reasoning": str
        }
        """
        start_time = time.time()
        
        # ========== 第一步：快速意图分类（System 1） ==========
        intent_type, confidence = self._quick_intent_classification(user_query)
        
        logger.info(f"🎯 意图分类: {intent_type} (置信度: {confidence:.0%})")
        
        # ========== 第二步：复杂度评估 ==========
        complexity = self._evaluate_complexity(user_query, intent_type)
        
        logger.info(f"📊 复杂度: {complexity:.0%}")
        
        # ========== 第三步：路由决策 ==========
        route = self._decide_route(intent_type, complexity, confidence)
        
        logger.info(f"🔀 路由决策: {route}")
        
        # ========== 第四步：能力盘点（缓存） ==========
        capabilities = self._scan_capabilities()
        
        logger.info(f"🔧 能力清单: {len(capabilities['tools'])}个工具, {len(capabilities['models'])}个模型")
        
        # ========== 第五步：生成执行计划 ==========
        execution_plan = self._generate_execution_plan(
            user_query, route, capabilities, intent_type
        )
        
        logger.info(f"📋 执行计划: {len(execution_plan['tasks'])}个任务")
        
        # 构建调度结果
        result = {
            "route": route,
            "complexity": complexity,
            "intent_type": intent_type,
            "confidence": confidence,
            "capabilities": capabilities,
            "execution_plan": execution_plan,
            "reasoning": self._explain_routing(route, intent_type, complexity),
            "elapsed_ms": int((time.time() - start_time) * 1000)
        }
        
        return result
    
    def _quick_intent_classification(self, query: str) -> Tuple[str, float]:
        """快速意图分类（规则匹配）"""
        query_lower = query.lower().strip()
        
        # 检查各模式
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in query_lower:
                    # 计算匹配置信度
                    confidence = min(1.0, len(pattern) / max(len(query_lower), 1) + 0.5)
                    return intent_type, confidence
        
        # 默认：复杂查询
        return "complex_query", 0.5
    
    def _evaluate_complexity(self, query: str, intent_type: str) -> float:
        """评估问题复杂度"""
        complexity = 0.0
        
        # 基础复杂度（根据意图类型）
        base_complexity = {
            "greeting": 0.1,
            "confirmation": 0.1,
            "simple_query": 0.3,
            "complex_query": 0.7,
            "learning_trigger": 0.5
        }
        complexity = base_complexity.get(intent_type, 0.5)
        
        # 长度加成
        if len(query) > 50:
            complexity += 0.1
        if len(query) > 100:
            complexity += 0.1
        
        # 关键词加成
        complex_keywords = ["为什么", "如何", "分析", "比较", "设计", "优化", "实现"]
        for kw in complex_keywords:
            if kw in query:
                complexity += 0.1
        
        # 多问号（多个问题）
        if query.count("？") > 1 or query.count("?") > 1:
            complexity += 0.2
        
        return min(1.0, complexity)
    
    def _decide_route(self, intent_type: str, complexity: float, confidence: float) -> str:
        """
        路由决策
        
        注意：QuickReflexEngine作为T0层已前置拦截简单问题
        此处专注于slow/learning路径决策
        """
        # 简单意图走fast路径
        if intent_type in ["greeting", "confirmation", "simple_query"]:
            return "fast"
        
        learning_threshold = self.route_thresholds.get("learning_confidence", 0.5)
        
        if intent_type == "learning_trigger" or confidence < learning_threshold:
            return "learning"
        
        return "slow"
    
    def _scan_capabilities(self) -> Dict[str, Any]:
        """扫描系统能力（带缓存和锁保护）"""
        now = time.time()
        
        with self._cache_lock:
            if self.capability_cache and (now - self.cache_timestamp) < self.cache_ttl:
                return self.capability_cache
        
        tools = []
        if self.enable_capability_scan.get("tools", True):
            try:
                from tools.registry import ToolRegistry
                registry = ToolRegistry()
                for tool in registry.list_tools():
                    tools.append({
                        "name": tool.name,
                        "type": tool.category.value if hasattr(tool.category, 'value') else str(tool.category),
                        "description": tool.description
                    })
            except Exception as e:
                logger.warning(f"工具扫描失败: {e}")
        
        models = []
        if self.enable_capability_scan.get("models", True):
            try:
                import requests
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    for model in response.json().get("models", []):
                        models.append({
                            "name": model["name"],
                            "available": True
                        })
            except Exception as e:
                logger.debug(f"模型扫描失败: {e}")
        
        knowledge_bases = []
        if self.enable_capability_scan.get("knowledge_bases", True):
            if Path("data/knowledge_store.db").exists():
                knowledge_bases.append({"name": "主知识库", "available": True})
            if Path("data/experience_pool.db").exists():
                knowledge_bases.append({"name": "经验池", "available": True})
        
        capabilities = {
            "tools": tools,
            "models": models,
            "knowledge_bases": knowledge_bases,
            "timestamp": datetime.now().isoformat()
        }
        
        with self._cache_lock:
            self.capability_cache = capabilities
            self.cache_timestamp = now
        
        return capabilities
    
    def _generate_execution_plan(
        self, 
        query: str, 
        route: str, 
        capabilities: Dict,
        intent_type: str
    ) -> Dict[str, Any]:
        """
        生成执行计划
        
        注意：
        - fast路径已由QuickReflexEngine处理，此处不生成
        - 工具调用改为"工具选择"意图，由ToolArbiter运行时决策
        """
        
        if route == "learning":
            return {
                "tasks": [
                    {"type": "knowledge_retrieval", "description": f"检索关于'{query}'的知识"},
                    {"type": "external_learning", "description": "触发外部搜索学习"},
                    {"type": "llm_reasoning", "description": "综合推理生成答案"},
                    {"type": "reflection_pipeline", "description": "写入反思管道"}
                ],
                "expected_confidence": 0.6,
                "reasoning": "知识缺失，需要外部学习"
            }
        
        else:  # slow
            tasks = []
            
            tasks.append({
                "type": "knowledge_retrieval",
                "description": f"检索关于'{query}'的知识"
            })
            
            applicable_tools = self._find_applicable_tools(query, capabilities)
            if applicable_tools:
                tasks.append({
                    "type": "tool_selection",
                    "description": "需要工具辅助",
                    "intent": "select_best_tool",
                    "candidates": [t["name"] for t in applicable_tools[:3]]
                })
            
            tasks.append({
                "type": "llm_reasoning",
                "description": "综合推理生成答案"
            })
            
            tasks.append({
                "type": "validation",
                "description": "验证答案质量"
            })
            
            tasks.append({
                "type": "reflection_pipeline",
                "description": "写入反思管道"
            })
            
            return {
                "tasks": tasks,
                "expected_confidence": 0.8,
                "reasoning": "复杂问题，需要完整认知流程",
                "applicable_tools": applicable_tools
            }
    
    def _find_applicable_tools(self, query: str, capabilities: Dict) -> List[Dict]:
        """找到适用的工具"""
        applicable = []
        
        # 关键词匹配
        tool_keywords = {
            "calculator": ["计算", "算", "多少", "+", "-", "*", "/"],
            "search": ["搜索", "查找", "找", "查询"],
            "file_reader": ["读取", "打开", "查看文件"],
            "web_search": ["网上", "网络", "互联网"]
        }
        
        for tool in capabilities.get("tools", []):
            tool_name = tool["name"]
            keywords = tool_keywords.get(tool_name, [])
            
            for kw in keywords:
                if kw in query:
                    applicable.append(tool)
                    break
        
        return applicable
    
    def _explain_routing(self, route: str, intent_type: str, complexity: float) -> str:
        """解释路由决策"""
        explanations = {

            "slow": f"复杂问题（{intent_type}），复杂度{complexity:.0%}，走慢路径（完整认知流程）",
            "learning": f"知识缺失（{intent_type}），触发外部学习"
        }
        return explanations.get(route, "未知路由")
    
    def build_capability_prompt(self, capabilities: Dict) -> str:
        """构建能力注入提示（注入到LLM上下文）"""
        
        prompt = "\n【当前能力清单 - 实时扫描结果】\n\n"
        
        # 工具列表
        if capabilities["tools"]:
            prompt += "可调用的工具：\n"
            for tool in capabilities["tools"][:10]:
                prompt += f"- {tool['name']}: {tool.get('description', '无描述')}\n"
            prompt += "\n"
        
        # 模型列表
        if capabilities["models"]:
            prompt += "可调用的模型：\n"
            for model in capabilities["models"]:
                prompt += f"- {model['name']}\n"
            prompt += "\n"
        
        # 知识库
        if capabilities["knowledge_bases"]:
            prompt += "可检索的知识库：\n"
            for kb in capabilities["knowledge_bases"]:
                prompt += f"- {kb['name']}\n"
            prompt += "\n"
        
        # 执行原则
        prompt += """【执行原则】
1. 优先使用工具而非纯推理
2. 如果需要计算，必须调用calculator工具
3. 如果需要搜索信息，必须调用search工具
4. 每个步骤都要输出置信度评估
5. 置信度低于70%必须承认无知并触发外部学习
"""
        
        return prompt


# 全局实例
_dispatcher = None

def get_cognitive_dispatcher() -> CognitiveDispatcher:
    """获取认知调度器实例"""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = CognitiveDispatcher()
    return _dispatcher