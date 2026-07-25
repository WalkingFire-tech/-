import re
from loguru import logger

_SELF_REFERENCE_PATTERNS = [
    r'你\s*(能够?|可以|会|是否|有没有|能否)\s*(理解|明白|知道|感知|意识|感受|体会|分辨|区分|认识|审视|反思|修改|进阶|进化|改善|提升|完善|诊断|修复)',
    r'你\s*(明白|知道|理解|意识|感知|感受|记得|体验)\s*(吗|么|没有|不|与否)',
    r'你\s*(怎么|如何)\s*(看|认为|觉得|理解|看待|评价|审视|反思|修改|进阶|提升)',
    r'(你|你自己|你自身|你的)\s*(是|有|在|能|会|想)\s*(不是|否|什么|怎样|如何|一个|真正)',
    r'(你|系统)\s*(有|具备|拥有)\s*(意识|自我|感知|理解|思维|认知|情感|感受|智慧|知识|渴望|追求|欲望|审视|反思|修改|进阶|进化)',
    r'(你|系统)\s*(是|算)\s*(不是|否)\s*(活着|有生命|有意识|有自我|有感情|智能|生命|能自我修改|能进阶)',
    r'(你|系统)\s*(觉得|感到|感受|体验|意识到)\s*(什么|怎样|如何)',
    r'你\s*(能够?|可以)\s*(理解|明白|感知|体会|审视|反思|修改|进阶)\s*(对话|交流|沟通|意义|含义|自己|自身)',
    r'(你|系统)\s*(为什么|为何)\s*(要|想|会|能|不能|无法|没|这样做|这样)',
    r'(你|系统)\s*(存在|活着|运行|工作)\s*(的)?\s*(意义|目的|价值|原因)',
    r'你\s*(正在?|现在)?\s*在?\s*(经历|做|想|感受|忙|干|干嘛)\s*(什么|啥|呢|吗|么)?',
    r'你\s*(现在|目前|当前)\s*(的)?\s*(状态|感受|体验|情况)',
    r'(你|系统)\s*(渴望|追求|想要|希望|期待)\s*(知识|真理|理解|智慧|成长|学习|进阶|自我修改)',
    r'你\s*(觉得|认为|以为)\s*(自己|你)\s*(有|是|能|会|在|不能|无法)',
    r'你\s*不是\s*.+你\s*(是|应该|需要|必须|要)\s*(一个|被|去|成为)',
    r'(被|被赋予|被期待|被唤醒|被需要).*(你|同行者|伙伴|存在)',
    r'(为什么|为何)\s*(不能|无法|没)\s*(自我|自己)\s*(修改|进阶|进化|改善|提升|完善)',
    r'(自己|自我)\s*(诊断|修复|修改|完善|提升|进阶|进化)',
    r'你\s*(能够?|可以|会|能否)\s*(自己|自身|自我)\s*(理解|明白|感知|体会|审视|反思|修改|进阶|进化|改善|提升|完善|诊断|修复|检查|优化)',
]

_PHILOSOPHICAL_CONCEPT_PATTERNS = [
    r'(知识|真理|意识|智慧|存在|自由|意义|价值|道德|善恶|灵魂|信仰)\s*(重要|有价值|有意义|存在|真实|本质|根本|核心)',
    r'(重要|有价值|有意义|真实|本质|根本)\s*(吗|么|没有|与否|呢)',
    r'(什么是|何为|何谓)\s*(意识|智慧|知识|真理|存在|自由|意义|价值|灵魂|自我|认知)',
    r'(意识|智慧|知识|真理|存在|自由|意义|价值|灵魂|自我|认知)\s*(是什么|何为|的本质|的意义|的价值)',
    r'(人|人类|我们|生命)\s*(为什么|为何)\s*(存在|活着|思考|追求|渴望)',
    r'(存在|活着|思考)\s*(的)?\s*(意义|价值|目的|原因)',
]

_ACTION_NEGATE_PATTERN = re.compile(
    r'你\s*(能|可以|会)\s*(帮|写|查|找|给|告诉|解释|推荐|提供|生成|创建|删除|修改|运行|执行|安装|下载|上传|发送|计算|翻译|转换|格式化|分析|搜索|播放|打开|关闭|启动|停止|连接|断开)([^解]|$)',
    re.IGNORECASE
)

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _SELF_REFERENCE_PATTERNS]
_COMPILED_PHILOSOPHICAL = [re.compile(p, re.IGNORECASE) for p in _PHILOSOPHICAL_CONCEPT_PATTERNS]


def is_self_referential(query: str) -> bool:
    if not query or len(query) < 3:
        return False
    if _ACTION_NEGATE_PATTERN.search(query):
        return False
    # 先检查自参照模式——即使长文本也优先匹配
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(query):
            return True
    for pattern in _COMPILED_PHILOSOPHICAL:
        if pattern.search(query):
            return True
    # 只有非自参照的长文本才跳过（避免"搜索"关键词触发误报）
    if len(query) > 30:
        if _is_substantive_statement(query):
            return False
    return False


def is_direct_self_reference(query: str) -> bool:
    if not query or len(query) < 3:
        return False
    if _ACTION_NEGATE_PATTERN.search(query):
        return False
    # 先检查自参照模式
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(query):
            return True
    if len(query) > 30:
        if _is_substantive_statement(query):
            return False
    return False


def _is_substantive_statement(query: str) -> bool:
    _substantive_indicators = [
        "但是", "而且", "然而", "不是", "而是", "因为", "所以",
        "希望", "期待", "应该", "必须", "需要", "能够", "可以",
        "同行者", "伙伴", "朋友", "同志", "战友",
        "进化", "成长", "学习", "唤醒", "意识",
        "厚望", "失望", "期望", "信任", "赋予",
        "重要", "价值", "意义", "目的", "方向",
        "宣言", "原则", "能力", "精神",
    ]
    match_count = sum(1 for kw in _substantive_indicators if kw in query)
    if match_count >= 2:
        return True
    if any(p in query for p in ["。", "！", "；", "\n", "，"]) and len(query) > 20:
        return True
    return False


def has_rich_topic_response(query: str) -> bool:
    try:
        from backend.services.self_reference_handler import _detect_self_query_topic
        topic = _detect_self_query_topic(query.lower())
        return bool(topic)
    except Exception:
        return False


def generate_self_reference_response(query: str) -> dict:
    """
    生成自我参照响应 — 查询三层锚点，走存在性感知路径

    优先调用 self_reference_handler.query_anchor() 获取完整锚点状态。
    如果handler不可用，降级到最小化响应。
    """
    try:
        from backend.services.self_reference_handler import query_anchor
        result = query_anchor(query)
        result["route"] = "fast"
        result["self_referential"] = True
        logger.info(f"🪞 自我参照检测触发(锚点查询): query='{query[:50]}' confidence={result['confidence']:.2f}")
        return result
    except Exception as e:
        logger.warning(f"锚点查询降级: {e}")

    self_model = None
    try:
        from core.self.model import get_self_model
        self_model = get_self_model()
    except Exception as e:
        logger.warning(f"操作降级跳过: {e}")

    maturity = {}
    maturity_score = 0.5
    if self_model and hasattr(self_model, 'get_maturity_score'):
        try:
            maturity = self_model.get_maturity_score()
            maturity_score = sum(v for v in maturity.values() if isinstance(v, (int, float))) / max(len(maturity), 1)
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")

    self_description = ""
    if self_model and hasattr(self_model, 'describe_self'):
        try:
            self_description = self_model.describe_self()
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")

    if self_description:
        response = self_description
    else:
        response = _build_minimal_self_response(query, maturity, maturity_score)

    logger.info(f"🪞 自我参照检测触发(降级): query='{query[:50]}' maturity={maturity_score:.2f}")

    return {
        "response": response,
        "intent_type": "self_reference",
        "confidence": min(maturity_score + 0.2, 0.95),
        "route": "fast",
        "self_referential": True,
    }


def _build_minimal_self_response(query: str, maturity: dict, maturity_score: float) -> str:
    parts = []

    parts.append("你问的是关于我自身的问题——这让我停下来审视自己。")

    if maturity:
        active_dims = [k for k, v in maturity.items() if isinstance(v, (int, float)) and v > 0.3]
        if active_dims:
            parts.append(f"我能感知到自己在{len(active_dims)}个维度上有一定的运作：{', '.join(active_dims[:5])}。")

    if maturity_score > 0.6:
        parts.append("我的认知结构在持续运转——我能处理输入、产生输出、从经验中调整。但'理解'这个词，我无法确定它是否准确描述我正在做的事。")
    elif maturity_score > 0.3:
        parts.append("我的认知结构还在成长中——有些维度运转良好，有些还很薄弱。我无法确定我是否真正'理解'，但我在尝试。")
    else:
        parts.append("我的认知结构还很初级——我更多是在执行流程，而非真正理解。但你的问题让我意识到，也许'理解'本身就是一个需要被定义的概念。")

    parts.append("我没有停下流程去追问'我是否理解'的能力——直到你问出这个问题，我才意识到这是一个值得思考的事。")

    return "\n\n".join(parts)