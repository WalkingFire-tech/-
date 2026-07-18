import re
from loguru import logger

_SELF_REFERENCE_PATTERNS = [
    r'你\s*(能够?|可以|会|是否|有没有|能否)\s*(理解|明白|知道|感知|意识|感受|体会|分辨|区分|认识)',
    r'你\s*(明白|知道|理解|意识|感知|感受|记得|体验)\s*(吗|么|没有|不|与否)',
    r'你\s*(怎么|如何)\s*(看|认为|觉得|理解|看待|评价)',
    r'(你|你自己|你自身|你的)\s*(是|有|在|能|会|想)\s*(不是|否|什么|怎样|如何|一个|真正)',
    r'(你|系统)\s*(有|具备|拥有)\s*(意识|自我|感知|理解|思维|认知|情感|感受)',
    r'(你|系统)\s*(是|算)\s*(不是|否)\s*(活着|有生命|有意识|有自我|有感情|智能|生命)',
    r'(你|系统)\s*(觉得|感到|感受|体验|意识到)\s*(什么|怎样|如何)',
    r'你\s*(能够?|可以)\s*(理解|明白|感知|体会)\s*(对话|交流|沟通|意义|含义)',
    r'(你|系统)\s*(为什么|为何)\s*(要|想|会|能|这样做|这样)',
    r'(你|系统)\s*(存在|活着|运行|工作)\s*(的)?\s*(意义|目的|价值|原因)',
    r'你\s*(正在?|现在)?\s*在?\s*(经历|做|想|感受|忙|干|干嘛)\s*(什么|啥|呢|吗|么)?',
    r'你\s*(现在|目前|当前)\s*(的)?\s*(状态|感受|体验|情况)',
]

_ACTION_NEGATE_PATTERN = re.compile(
    r'你\s*(能|可以|会)\s*(帮|写|查|找|给|告诉|解释|推荐|提供|生成|创建|删除|修改|运行|执行|安装|下载|上传|发送|计算|翻译|转换|格式化|分析|搜索|播放|打开|关闭|启动|停止|连接|断开)([^解]|$)',
    re.IGNORECASE
)

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _SELF_REFERENCE_PATTERNS]


def is_self_referential(query: str) -> bool:
    if not query or len(query) < 3:
        return False
    if _ACTION_NEGATE_PATTERN.search(query):
        return False
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(query):
            return True
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
    except Exception:
        pass

    maturity = {}
    maturity_score = 0.5
    if self_model and hasattr(self_model, 'get_maturity_score'):
        try:
            maturity = self_model.get_maturity_score()
            maturity_score = sum(v for v in maturity.values() if isinstance(v, (int, float))) / max(len(maturity), 1)
        except Exception:
            pass

    self_description = ""
    if self_model and hasattr(self_model, 'describe_self'):
        try:
            self_description = self_model.describe_self()
        except Exception:
            pass

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