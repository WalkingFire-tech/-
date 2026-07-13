"""
认知调度器（Cognitive Dispatcher）- 系统的神经中枢

职责：
1. 意图分类 - 判断问题复杂度
2. 能力盘点 - 扫描可用工具/模型
3. 路由决策 - 选择执行路径
4. 计划生成 - 拆解任务步骤
5. 决策记录 - 为自进化提供数据

跨学科理论：
- 认知科学：双重加工理论（System 1快思考 vs System 2慢思考）
- 控制论：前馈控制（Feedforward Control）
- 系统论：分层递阶控制（Hierarchical Control）

三层架构定位：
- main_simple.py（策略层）：永不放弃的顶层调度器
- CognitiveDispatcher（认知层）：意图理解→能力盘点→路由决策→计划生成
- MetacognitiveExecutor（执行层）：四阶段闭环深度执行

改进记录：
1. _find_applicable_tools：从硬编码改为读取工具注册表keywords/tags
2. _generate_execution_plan：工具调用改为执行指令，由执行层决策
3. build_capability_prompt：支持模板化配置
4. _quick_intent_classification：增加向量相似度匹配（降级为规则匹配）
5. dispatch_history：记录调度决策历史，为自进化提供数据
"""
import json
import re
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple, TypedDict


class FieldContextDict(TypedDict, total=False):
    topic_continuity: float
    field_stability: float
    previous_topic: str
    residual_strength: float
    active_residuals: int
    dominant_topic: str
    scent: Dict[str, str]
    _sensing_mode: str
    _available: bool
    _blind_reason: str
    is_new_topic: bool
    is_familiar: bool

class CognitiveDispatchResult(TypedDict, total=False):
    route: str
    complexity: float
    intent_type: str
    confidence: float
    urgency: float
    confusion: float
    capabilities: Dict[str, Any]
    execution_plan: Dict[str, Any]
    reasoning: str
    elapsed_ms: int
    field_context: FieldContextDict
from datetime import datetime
from loguru import logger
from pathlib import Path
import threading
from infrastructure.database_manager import DatabaseManager


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
        
        self.prompt_template = config.get("prompt_template", None)
        
        self._init_dispatch_history_db()
        
        logger.info("🧠 认知调度器已初始化")
        logger.info(f"  - 缓存TTL: {self.cache_ttl}秒")
        logger.info(f"  - 能力扫描: {self.enable_capability_scan}")
    
    def _init_dispatch_history_db(self):
        """初始化调度决策历史数据库"""
        try:
            db = DatabaseManager.get("data/dispatch_history.db")
            db.execute('''
                CREATE TABLE IF NOT EXISTS dispatch_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT,
                    intent_type TEXT,
                    confidence REAL,
                    complexity REAL,
                    route TEXT,
                    execution_plan TEXT,
                    reasoning TEXT,
                    elapsed_ms INTEGER,
                    timestamp TEXT
                )
            ''', commit=True)
            db.execute('''
                CREATE TABLE IF NOT EXISTS learned_keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE,
                    intent_type TEXT,
                    source TEXT,
                    learned_at TEXT
                )
            ''', commit=True)
        except Exception as e:
            logger.error(f"调度历史数据库初始化失败: {e}")
    
    def learn_keyword_from_experience(self, query: str, correct_intent: str, source: str = "persistent_solver"):
        """从经验中学习意图关键词——当系统纠正了误分类后，自动补充词表"""
        try:
            import jieba
            words = [w for w in jieba.cut(query) if len(w) >= 2]
        except ImportError:
            words = []
            for w in re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{2,}\d*|COM\d+', query):
                if len(w) >= 2:
                    words.append(w)
            for w in re.split(r'[\s,，。.?？!！;；:：、]+', query):
                if 2 <= len(w) <= 6 and w not in words:
                    words.append(w)
        
        existing = set(self.intent_patterns.get(correct_intent, []))
        added = 0
        for w in words:
            if len(w) < 2 or w in existing:
                continue
            if w.isdigit() or re.match(r'^[a-zA-Z]$', w):
                continue
            self.intent_patterns.setdefault(correct_intent, []).append(w)
            existing.add(w)
            added += 1
            try:
                db = DatabaseManager.get("data/dispatch_history.db")
                db.execute(
                    "INSERT OR IGNORE INTO learned_keywords (keyword, intent_type, source, learned_at) VALUES (?, ?, ?, ?)",
                    (w, correct_intent, source, datetime.now().isoformat()),
                    commit=True,
                )
            except Exception:
                pass
        
        if added > 0:
            logger.info(f"📚 意图词表自动学习: +{added}个关键词→{correct_intent} (来源:{source})")
    
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
            "challenge": [
                "你确定", "确定吗", "真的吗", "不是吧", "不对吧",
                "你确定？", "确定吗？", "真的吗？", "不对吧？",
                "你错了", "你说错了", "不对", "不是这样的",
                "我不信", "不可能", "别瞎说", "胡说"
            ],
            "history_query": [
                "历史", "记录", "历史记录", "查看历史", "显示历史", "聊天记录"
            ],
            "hardware": [
                "串口", "com口", "serial", "波特率", "baudrate",
                "gps数据", "nmea", "gnss", "gpgga", "gprmc",
                "gps", "GPS", "经纬度", "坐标", "定位", "导航",
                "硬件", "设备", "端口", "com8", "com3", "com5",
                "读取数据", "获取数据", "传感器", "usb设备",
                "ch340", "cp210", "ft232", "arduino", "stm32", "esp32", "单片机",
                "运行命令", "执行命令", "cmd", "powershell", "bash", "shell",
            ],
            "weather": [
                "天气", "气温", "下雨", "下雪", "阴天", "晴天",
                "湿度", "气压", "降水", "暴雨", "台风",
                "天气预报", "天气如何", "天气怎么样", "今天天气", "明天天气",
                "最近天气", "附近天气", "当前天气", "实时天气",
            ],
            "map": [
                "地图", "标记", "渲染", "folium", "地图标记",
                "在地图上", "画地图", "生成地图", "显示地图",
                "可视化", "绘制", "图表", "plot", "chart",
                "heatmap", "散点图", "折线图", "柱状图",
            ],
            "simple_query": [
                "是什么", "什么是", "怎么读", "多少", "什么时候",
                "能做", "做什么", "有哪些", "能什么", "干什么", "会什么", "有什么用", "能帮我",
                "等于", "加", "减", "乘", "除", "计算"
            ],
            "complex_query": [
                "为什么", "如何实现", "怎么优化", "分析", "比较",
                "设计", "构建", "创建", "实现", "改进",
                "应该", "什么样", "怎样", "如何", "怎么样",
                "架构", "思路", "原理", "机制", "体系"
            ],
            "learning_trigger": [
                "我不懂", "不明白", "介绍一下", "解释一下",
                "教我", "告诉我", "说明一下", "讲讲", "说说"
            ]
        }
    
    def _get_field_context(self, query: str) -> Dict[str, Any]:
        """场域层激活：获取跨对话残余信号、话题连续性"""
        field = {
            "topic_continuity": 0.0,
            "field_stability": 0.5,
            "previous_topic": None,
            "residual_strength": 0.0,
            "active_residuals": 0,
            "dominant_topic": None,
            "scent": {},
            "_sensing_mode": "full",
            "is_new_topic": False,
            "is_familiar": False,
        }

        try:
            from core.cbnr.cognitive_residual import CognitiveResidual
            if not hasattr(self, '_residual_instance'):
                self._residual_instance = CognitiveResidual()
            residual = self._residual_instance

            input_data = {"topic": query}
            previous = residual._retrieve_previous_state(input_data)
            if previous:
                field["previous_topic"] = previous.get("similar_input", "")[:80]
                sim = previous.get("semantic_similarity", 0.5)
                field["residual_strength"] = sim
                field["topic_continuity"] = sim
                field["field_stability"] = sim if sim > 0.5 else sim * 0.6
                field["dominant_topic"] = previous.get("similar_input", "")[:50] if sim > 0.6 else None
                field["active_residuals"] = 1 if sim > 0.3 else 0
                if previous.get("_sensing_mode") == "blind":
                    field["_sensing_mode"] = "blind"
                    field["residual_strength"] = -1.0
                    logger.warning(f"场域失明: 认知残差层embedding不可用, 场域感知降级")
                else:
                    sim = previous.get("semantic_similarity", 0)
                    field["is_new_topic"] = sim < 0.3 and field["previous_topic"] is not None
                    field["is_familiar"] = sim > 0.7
        except Exception as e:
            logger.warning(f"场域层激活降级: {e}")
            field["_sensing_mode"] = "blind"
            field["_available"] = False

        try:
            from core.cognition.experience_abstractor import ExperienceAbstractor
            field["scent"] = ExperienceAbstractor.extract_scent(query)
        except Exception:
            pass

        return field

    def _assess_urgency_confusion(self, query: str) -> Dict[str, float]:
        urgency_keywords = ['紧急', '急', '马上', '立刻', '赶紧', '快点', 'urgent', 'asap', 'immediately', 'now']
        confusion_keywords = ['不确定', '不太确定', '困惑', '迷茫', '不懂', '不明白', '什么意思', '为什么', '怎么回事', '怎么用', '怎么搞', '怎么办', 'confused', 'what', 'why', 'how']
        repeat_markers = ['还是', '又', '还是不行', '还是不对', '还是没解决', 'still', 'again']

        query_lower = query.lower()
        urgency = 0.0
        confusion = 0.0

        for kw in urgency_keywords:
            if kw in query_lower:
                urgency += 0.3
        urgency = min(urgency, 1.0)

        for kw in confusion_keywords:
            if kw in query_lower:
                confusion += 0.25
        for kw in repeat_markers:
            if kw in query_lower:
                confusion += 0.2
        confusion = min(confusion, 1.0)

        if query.endswith('???') or query.endswith('！！！'):
            urgency = min(urgency + 0.3, 1.0)
        if '?' in query or '？' in query:
            confusion = min(confusion + 0.1, 1.0)

        return {"urgency": urgency, "confusion": confusion}

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
        
        # ========== 场域层激活：跨对话残余信号 ==========
        field_context = self._get_field_context(user_query)
        
        # ========== 第一步：快速意图分类（System 1） ==========
        intent_type, confidence = self._quick_intent_classification(user_query)
        
        # ========== 第一步半：紧迫度/困惑度信号 ==========
        signals = self._assess_urgency_confusion(user_query)
        
        logger.info(f"🎯 意图分类: {intent_type} (置信度: {confidence:.0%}) | 紧迫度: {signals['urgency']:.1f} 困惑度: {signals['confusion']:.1f}")
        
        # ========== 第二步：复杂度评估 ==========
        complexity = self._evaluate_complexity(user_query, intent_type)
        
        # 高困惑度提升复杂度（用户困惑时需要更深入的回答）
        if signals['confusion'] > 0.5:
            complexity = min(complexity + 0.15, 1.0)
        
        logger.info(f"📊 复杂度: {complexity:.0%}")
        
        # ========== 第三步：路由决策 ==========
        route = self._decide_route(intent_type, complexity, confidence)
        
        # 高紧迫度时，慢路径降级为快路径（紧急问题优先快速响应）
        if signals['urgency'] > 0.7 and route == "slow":
            route = "fast"
            logger.info(f"⚡ 高紧迫度({signals['urgency']:.1f})，慢路径降级为快路径")
        
        logger.info(f"🔀 路由决策: {route}")
        
        # ========== 快速路径：立即返回 ==========
        if route == "fast":
            return {
                "route": "fast",
                "complexity": complexity,
                "intent_type": intent_type,
                "confidence": confidence,
                "urgency": signals['urgency'],
                "confusion": signals['confusion'],
                "capabilities": {"tools": [], "models": [], "knowledge_bases": []},
                "execution_plan": {"tasks": []},
                "reasoning": f"简单意图({intent_type})，快速响应",
                "elapsed_ms": int((time.time() - start_time) * 1000),
                "field_context": field_context,
            }
        
        # ========== 第四步：能力盘点（缓存） ==========
        # 注意：能力扫描可能导致卡住，使用缓存或跳过
        capabilities = self._scan_capabilities_fast()
        
        logger.info(f"🔧 能力清单: {len(capabilities['tools'])}个工具, {len(capabilities['models'])}个模型")
        
        # ========== 第五步：生成执行计划 ==========
        execution_plan = self._generate_execution_plan(
            user_query, route, capabilities, intent_type
        )
        
        # ========== P1-7：反思教训注入 + 行为映射 ==========
        lessons_context = self._get_reflection_lessons(user_query, intent_type)
        if lessons_context:
            execution_plan["reflection_lessons"] = lessons_context
            methodology_patch = self._map_lessons_to_behavior(lessons_context)
            if methodology_patch:
                execution_plan["methodology_patch"] = methodology_patch
            logger.info(f"📝 反思教训注入: {len(lessons_context)}条, 行为映射: {list(methodology_patch.keys()) if methodology_patch else '无'}")
        
        logger.info(f"📋 执行计划: {len(execution_plan['tasks'])}个任务")
        
        # 构建调度结果
        result = {
            "route": route,
            "complexity": complexity,
            "intent_type": intent_type,
            "confidence": confidence,
            "urgency": signals['urgency'],
            "confusion": signals['confusion'],
            "capabilities": capabilities,
            "execution_plan": execution_plan,
            "reasoning": self._explain_routing(route, intent_type, complexity),
            "elapsed_ms": int((time.time() - start_time) * 1000),
            "field_context": field_context,
        }
        
        # 记录调度决策历史（异步，不阻塞）
        try:
            loop = asyncio.get_running_loop()
            loop.run_in_executor(None, self._record_dispatch, result, user_query)
        except RuntimeError:
            self._record_dispatch(result, user_query)
        
        return result
    
    def _quick_intent_classification(self, query: str) -> Tuple[str, float]:
        """快速意图分类（规则匹配 + 向量相似度降级）"""
        query_lower = query.lower().strip()

        query_clean = re.sub(r'[？?！!。.，,、；;：:""''\"\'\s]+$', '', query_lower)
        query_clean_all = re.sub(r'[？?！!。.，,、；;：:""''\"\'\s]', '', query_lower)
        
        # 超短句(<6字符)且包含greeting/confirmation/challenge关键词，直接判定
        if len(query_clean_all) <= 8:
            for pattern in self.intent_patterns.get("greeting", []):
                if pattern in query_clean_all or query_clean_all in pattern:
                    return "greeting", 0.95
            for pattern in self.intent_patterns.get("confirmation", []):
                if pattern in query_clean_all or query_clean_all in pattern:
                    return "confirmation", 0.95
            for pattern in self.intent_patterns.get("challenge", []):
                if pattern in query_clean_all or query_clean_all in pattern:
                    return "challenge", 0.9
        
        # 正则模式优先匹配：COM端口模式（COM1/COM3等）→ hardware
        if re.search(r'COM\d+', query, re.IGNORECASE):
            return "hardware", 0.9

        # 匹配优先级：hardware > challenge > complex > simple > 其他
        # hardware优先于challenge：当用户说"时间不对"时更可能是要求重新执行硬件操作
        match_order = ["weather", "map", "hardware", "challenge", "complex_query", "learning_trigger", "simple_query", "history_query", "greeting", "confirmation"]
        short_match_intents = {"greeting", "confirmation", "challenge"}
        
        for intent_type in match_order:
            patterns = self.intent_patterns.get(intent_type, [])
            for pattern in patterns:
                if intent_type == "challenge":
                    if pattern in query_clean_all or query_clean_all in pattern:
                        confidence = min(1.0, len(pattern) / max(len(query_lower), 1) + 0.5)
                        return intent_type, confidence
                elif intent_type in short_match_intents:
                    if query_clean == pattern or query_clean.startswith(pattern + " ") or query_clean_all == pattern:
                        confidence = min(1.0, len(pattern) / max(len(query_lower), 1) + 0.5)
                        return intent_type, confidence
                else:
                    if pattern in query_lower:
                        confidence = min(1.0, len(pattern) / max(len(query_lower), 1) + 0.5)
                        return intent_type, confidence
        
        # 向量相似度匹配（如果可用）
        try:
            similarity_result = self._vector_intent_match(query)
            if similarity_result:
                return similarity_result
        except Exception as e:
            logger.error(f"向量意图匹配失败: {e}")
        
        # 语义级意图推断：分析query的语义结构而非关键词
        semantic_result = self._semantic_intent_inference(query)
        if semantic_result:
            return semantic_result
        
        # 默认：复杂查询
        return "complex_query", 0.5
    
    def _semantic_intent_inference(self, query: str) -> Optional[Tuple[str, float]]:
        """
        语义级意图推断——理解用户在问什么，而非匹配关键词
        
        分析维度：
        1. 语句结构：疑问/陈述/祈使
        2. 信息需求：事实/方法/观点/能力
        3. 复杂度信号：多从句/条件/对比
        """

        
        has_question_mark = '？' in query or '?' in query
        
        capability_patterns = [
            r'你(?:能|可以|会|可)(?:做|帮|给|提供|完成|处理|解决|回答|解释|分析)',
            r'(?:有|具备)什么(?:能力|功能|本领|特点)',
            r'(?:介绍|说说|讲讲)(?:一下|一下你自己)?(?:你|自己)',
        ]
        if any(re.search(p, query) for p in capability_patterns):
            return "simple_query", 0.8
        
        code_patterns = [
            r'(?:写|编写|实现|开发|创建)(?:一个|一段|个)?(?:函数|代码|程序|脚本|类|模块)',
            r'(?:帮我|请帮我|麻烦)(?:写|编|做|实现)',
            r'(?:debug|调试|修复|fix|bug)',
        ]
        if any(re.search(p, query) for p in code_patterns):
            return "complex_query", 0.8
        
        method_patterns = [
            r'怎么.{0,4}(?:做|办|解决|处理|实现|操作)',
            r'如何.{0,4}(?:做|办|解决|处理|实现|操作)',
            r'(?:步骤|方法|流程|过程|方式)',
        ]
        if any(re.search(p, query) for p in method_patterns):
            return "complex_query", 0.75
        
        factual_patterns = [
            r'(?:是什么|什么是|定义|含义|意思|指的)',
            r'(?:多少|几|何时|什么时候|哪里|哪儿)',
            r'(?:等于|是否|有没有|是不是)',
        ]
        if any(re.search(p, query) for p in factual_patterns):
            return "simple_query", 0.75
        
        causal_patterns = [
            r'为什么.{0,6}(?:会|能|是|要|有)',
            r'(?:原因|缘故|缘由|根源)',
            r'(?:导致|引起|造成|使得).{0,6}(?:什么|为何|为什么)',
        ]
        if any(re.search(p, query) for p in causal_patterns):
            return "complex_query", 0.8
        
        if has_question_mark and len(query) < 15:
            return "simple_query", 0.65
        
        if len(query) < 6 and not has_question_mark:
            return "greeting", 0.6
        
        return None
    
    def _vector_intent_match(self, query: str) -> Optional[Tuple[str, float]]:
        """向量相似度意图匹配（降级为规则匹配）"""
        # TODO: 当向量检索器可用时，实现基于嵌入的意图匹配
        # 目前降级为规则匹配
        return None
    
    def _evaluate_complexity(self, query: str, intent_type: str) -> float:
        """评估问题复杂度"""
        complexity = 0.0
        
        # 基础复杂度（根据意图类型）
        base_complexity = {
            "greeting": 0.1,
            "confirmation": 0.1,
            "challenge": 0.8,
            "simple_query": 0.3,
            "complex_query": 0.7,
            "learning_trigger": 0.5,
            "hardware": 0.6,
            "map": 0.65,
            "weather": 0.5,
        }
        complexity = base_complexity.get(intent_type, 0.5)
        
        if len(query) > 50:
            complexity += 0.1
        if len(query) > 100:
            complexity += 0.1
        
        tool_dependent_intents = {"hardware", "map", "weather", "complex_query"}
        if intent_type in tool_dependent_intents:
            complexity += 0.05
        
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
        if intent_type in ["greeting", "confirmation", "simple_query", "history_query"]:
            return "fast"
        
        if intent_type == "hardware":
            return "slow"
        
        # 质疑检测走slow路径，需要重新验证
        if intent_type == "challenge":
            return "slow"
        
        learning_threshold = self.route_thresholds.get("learning_confidence", 0.5)
        
        if intent_type == "learning_trigger" or confidence < learning_threshold:
            return "learning"
        
        return "slow"
    
    def _scan_capabilities_fast(self) -> Dict[str, Any]:
        """快速能力扫描（不调用外部服务，避免卡住）"""
        now = time.time()
        
        with self._cache_lock:
            if self.capability_cache and (now - self.cache_timestamp) < self.cache_ttl:
                return self.capability_cache
        
        tools = []
        if self.enable_capability_scan.get("tools", True):
            try:
                from core.tool_registry import tool_registry
                for t in tool_registry.list_tools():
                    tools.append({"name": t["name"], "description": t["description"], "category": t["category"]})
            except Exception as e:
                logger.error(f"工具扫描失败: {e}")
        models = []
        # 跳过Ollama扫描，避免卡住
        knowledge_bases = []
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

    
    def _get_reflection_lessons(self, query: str, intent_type: str) -> List[Dict]:
        """P1-7: 从spirit_lessons.db读取相关反思教训，回流到规划"""
        try:
            db = DatabaseManager.get("data/spirit_lessons.db")
            rows = db.query(
                "SELECT lesson_type, lesson_text, severity, context FROM spirit_lessons "
                "WHERE lesson_text LIKE ? OR context LIKE ? "
                "ORDER BY severity DESC, created_at DESC LIMIT 5",
                (f"%{query[:15]}%", f"%{intent_type}%")
            )
            if not rows:
                rows = db.query(
                    "SELECT lesson_type, lesson_text, severity, context FROM spirit_lessons "
                    "WHERE severity >= 3 ORDER BY created_at DESC LIMIT 3"
                )
            return [dict(r) for r in rows]
        except Exception:
            return []
    
    def _map_lessons_to_behavior(self, lessons: List[Dict]) -> Dict[str, Any]:
        """
        将spirit_lessons映射为具体行为调整（methodology_patch）。
        教训不再只是"被读到"，而是转化为可执行的行为指令。
        """
        patch = {}
        lesson_types = set()
        high_severity_count = 0
        
        for lesson in lessons:
            lt = lesson.get("lesson_type", "")
            severity = lesson.get("severity", 0)
            text = lesson.get("lesson_text", "")
            lesson_types.add(lt)
            
            try:
                sev_int = int(severity) if severity else 0
            except (ValueError, TypeError):
                sev_int = 0
            if sev_int >= 3:
                high_severity_count += 1
            
            lt_lower = lt.lower()
            text_lower = text.lower() if text else ""
            
            if "hallucination" in lt_lower or "伪造" in text_lower or "幻觉" in text_lower:
                patch["force_honest_response"] = True
                patch["disable_llm_generation"] = True
                patch["require_data_verification"] = True
            
            if "field_blind" in lt_lower or "场域失明" in text_lower:
                patch["skip_field_sensing"] = True
                patch["use_keyword_fallback"] = True
            
            if "intent" in lt_lower or "意图" in text_lower or "误判" in text_lower:
                patch["force_slow_path"] = True
                patch["require_intent_confirmation"] = True
            
            if "timeout" in lt_lower or "超时" in text_lower:
                patch["use_cache_fallback"] = True
                patch["skip_slow_path"] = True
            
            if "entity" in lt_lower or "别名" in text_lower or "实体" in text_lower:
                patch["require_entity_normalization"] = True
            
            if "tool_not_found" in lt_lower or "工具未找到" in text_lower:
                patch["trigger_capability_creation"] = True
            
            if "context_lost" in lt_lower or "上下文" in text_lower:
                patch["require_explicit_confirmation"] = True
                patch["ask_for_clarification"] = True
            
            if "knowledge_gap" in lt_lower or "知识缺口" in text_lower:
                patch["trigger_external_learning"] = True
            
            if "audit_" in lt_lower:
                patch["enhanced_self_verification"] = True
        
        if high_severity_count >= 2:
            patch["conservative_mode"] = True
            patch["reduced_confidence_factor"] = 0.7
        
        return patch
    
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
        - 工具调用改为"执行指令"，由执行层决定如何使用工具
        - 调度器只做决策，不执行
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
                    "type": "tool_execution",
                    "description": f"执行工具辅助解决问题",
                    "candidates": [t["name"] for t in applicable_tools[:3]],
                    "instruction": "由执行层选择并调用最合适的工具"
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
        """找到适用的工具（从工具注册表读取keywords/tags，不硬编码）"""
        applicable = []
        
        default_keywords = {
            "calculator": ["计算", "算", "多少", "+", "-", "*", "/", "数学"],
            "search": ["搜索", "查找", "找", "查询"],
            "file_reader": ["读取", "打开", "查看文件"],
            "web_search": ["网上", "网络", "互联网"],
            "code_execution": ["代码", "编程", "运行", "执行"],
            "text_extractor": ["提取", "抽取", "解析"],
            "datetime_tool": ["时间", "日期", "几点"]
        }
        
        for tool in capabilities.get("tools", []):
            tool_name = tool.get("name", "")
            
            # 优先从工具的tags字段读取关键词
            keywords = tool.get("tags", [])
            if not keywords:
                keywords = tool.get("keywords", [])
            if not keywords:
                keywords = default_keywords.get(tool_name, [])
            
            for kw in keywords:
                if kw in query:
                    applicable.append(tool)
                    break
        
        return applicable
    
    def _explain_routing(self, route: str, intent_type: str, complexity: float) -> str:
        """解释路由决策"""
        explanations = {
            "fast": f"简单意图({intent_type})，快速响应",
            "slow": f"复杂问题（{intent_type}），复杂度{complexity:.0%}，走慢路径（完整认知流程）",
            "learning": f"知识缺失（{intent_type}），触发外部学习"
        }
        return explanations.get(route, "未知路由")
    
    def _record_dispatch(self, result: Dict, query: str):
        """记录调度决策历史（同步写入，为自进化提供数据）"""
        try:
            db = DatabaseManager.get("data/dispatch_history.db")
            db.execute(
                """INSERT INTO dispatch_history 
                   (query, intent_type, confidence, complexity, route, execution_plan, reasoning, elapsed_ms, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    query,
                    result.get("intent_type", "unknown"),
                    result.get("confidence", 0.0),
                    result.get("complexity", 0.0),
                    result.get("route", "unknown"),
                    json.dumps(result.get("execution_plan", {}), ensure_ascii=False),
                    result.get("reasoning", ""),
                    result.get("elapsed_ms", 0),
                    datetime.now().isoformat()
                ),
                commit=True
            )
        except Exception as e:
            logger.error(f"调度历史记录失败: {e}")
    
    def get_dispatch_history(self, limit: int = 10) -> List[Dict]:
        """获取调度决策历史"""
        try:
            db = DatabaseManager.get("data/dispatch_history.db")
            rows = db.query(
                "SELECT * FROM dispatch_history ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"获取调度历史失败: {e}")
            return []
    
    def analyze_dispatch_patterns(self) -> Dict:
        """分析调度决策模式（为自进化提供洞察）"""
        try:
            db = DatabaseManager.get("data/dispatch_history.db")
            
            total_row = db.query_one("SELECT COUNT(*) as cnt FROM dispatch_history")
            total = total_row['cnt'] if total_row else 0
            
            route_rows = db.query("SELECT route, COUNT(*) as cnt FROM dispatch_history GROUP BY route")
            route_distribution = {r['route']: r['cnt'] for r in route_rows}
            
            intent_rows = db.query("SELECT intent_type, COUNT(*) as cnt FROM dispatch_history GROUP BY intent_type")
            intent_distribution = {r['intent_type']: r['cnt'] for r in intent_rows}
            
            avg_row = db.query_one("SELECT AVG(elapsed_ms) as avg_ms FROM dispatch_history")
            avg_elapsed = avg_row['avg_ms'] if avg_row and avg_row['avg_ms'] is not None else 0
            
            return {
                "total_decisions": total,
                "route_distribution": route_distribution,
                "intent_distribution": intent_distribution,
                "avg_elapsed_ms": avg_elapsed
            }
        except Exception as e:
            logger.error(f"分析调度模式失败: {e}")
            return {}
    
    def build_capability_prompt(self, capabilities: Dict) -> str:
        """构建能力注入提示（支持模板化配置）"""
        
        if self.prompt_template:
            try:
                return self.prompt_template.format(**capabilities)
            except Exception as e:
                logger.warning(f"模板渲染失败: {e}，使用默认格式")
        
        prompt = "\n【当前能力清单 - 实时扫描结果】\n\n"
        
        if capabilities.get("tools"):
            prompt += "可调用的工具：\n"
            for tool in capabilities["tools"][:10]:
                desc = tool.get('description', '无描述')
                prompt += f"- {tool['name']}: {desc}\n"
            prompt += "\n"
        
        if capabilities.get("models"):
            prompt += "可调用的模型：\n"
            for model in capabilities["models"]:
                prompt += f"- {model['name']}\n"
            prompt += "\n"
        
        if capabilities.get("knowledge_bases"):
            prompt += "可检索的知识库：\n"
            for kb in capabilities["knowledge_bases"]:
                prompt += f"- {kb['name']}\n"
            prompt += "\n"
        
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