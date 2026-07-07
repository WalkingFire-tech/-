"""
动态输入处理器 — 分层提炼而非硬性截断

核心理念：像人一样处理长文本
- 第一层：快速扫描（提取骨架）— 主题、实体、问题类型、核心句子
- 第二层：渐进式提炼（根据资源状态+认知策略）— 双维度决策
- 第三层：整合输出 — 按优先级分配token预算，保证核心内容不丢失

双维度决策矩阵：
- 资源维度：normal / conservative / emergency — 系统能力
- 认知策略维度：learning / immediate — 任务需要什么方式

学习模式(learning)：分层提炼，可跨多轮深化，容许延迟处理
  → why_how, what, comparison, analysis, philosophy, knowledge
即时模式(immediate)：快速定位，一次性输出，精准解决
  → fix, request, yes_no, create, code

与 resource_awareness 协同：
- normal 模式：保留全部
- conservative 模式：压缩到60%
- emergency 模式：只保留骨架+核心句子
"""

import re
import math
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class KnowledgeConnection:
    node_id: str = ""
    content: str = ""
    relevance: float = 0.0
    connection_type: str = "related"

    def to_dict(self) -> Dict:
        return {
            "node_id": self.node_id,
            "content": self.content[:100],
            "relevance": round(self.relevance, 2),
            "connection_type": self.connection_type,
        }


@dataclass
class ConflictSignal:
    existing_fact: str = ""
    input_claim: str = ""
    conflict_type: str = "potential"
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "existing_fact": self.existing_fact[:100],
            "input_claim": self.input_claim[:100],
            "conflict_type": self.conflict_type,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class InputSkeleton:
    topic: str = ""
    entities: List[str] = field(default_factory=list)
    question_type: str = "unknown"
    core_sentences: List[str] = field(default_factory=list)
    length: int = 0
    paragraph_count: int = 0
    has_question: bool = False
    has_code: bool = False
    language: str = "mixed"
    knowledge_connections: List[KnowledgeConnection] = field(default_factory=list)
    conflict_signals: List[ConflictSignal] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "topic": self.topic,
            "entities": self.entities[:10],
            "question_type": self.question_type,
            "core_sentences": self.core_sentences[:5],
            "length": self.length,
            "paragraph_count": self.paragraph_count,
            "has_question": self.has_question,
            "has_code": self.has_code,
            "language": self.language,
            "knowledge_connections": [c.to_dict() for c in self.knowledge_connections[:5]],
            "conflict_signals": [c.to_dict() for c in self.conflict_signals[:3]],
        }


@dataclass
class ProcessedInput:
    skeleton: InputSkeleton = field(default_factory=InputSkeleton)
    distilled: str = ""
    mode: str = "normal"
    cognitive_strategy: str = "immediate"
    original_length: int = 0
    distilled_length: int = 0
    compression_ratio: float = 1.0
    was_distilled: bool = False
    removed_details: List[str] = field(default_factory=list)
    deferred_for_learning: bool = False

    def to_dict(self) -> Dict:
        return {
            "skeleton": self.skeleton.to_dict(),
            "mode": self.mode,
            "cognitive_strategy": self.cognitive_strategy,
            "original_length": self.original_length,
            "distilled_length": self.distilled_length,
            "compression_ratio": round(self.compression_ratio, 2),
            "was_distilled": self.was_distilled,
            "deferred_for_learning": self.deferred_for_learning,
        }


_QUESTION_PATTERNS = [
    (r'(?:为什么|为何|干嘛|怎么|如何|怎样)', 'why_how'),
    (r'(?:是什么|什么是|啥是|啥意思)', 'what'),
    (r'(?:能不能|可以|是否|行不行|可否)', 'yes_no'),
    (r'(?:帮我|请|麻烦|能不能帮我)', 'request'),
    (r'(?:对比|区别|差异|不同|比较)', 'comparison'),
    (r'(?:分析|评估|判断|评价|看法)', 'analysis'),
    (r'(?:修复|解决|debug|修|改|报错|错误|bug)', 'fix'),
    (r'(?:设计|实现|创建|开发|写|构建)', 'create'),
]

_TOPIC_KEYWORDS = {
    'code': ['代码', '函数', '类', '模块', 'API', '接口', '变量', '参数', 'import', 'def', 'class', 'async', 'return'],
    'system': ['系统', '架构', '模块', '服务', '进程', '线程', '部署', '配置', '性能', '内存', 'CPU'],
    'knowledge': ['知识', '学习', '理解', '认知', '推理', '记忆', '经验', '真谛', '规则'],
    'emotion': ['感觉', '心情', '焦虑', '开心', '难过', '压力', '疲惫', '无聊', '烦'],
    'philosophy': ['本质', '意义', '价值', '存在', '意识', '自由', '道德', '伦理', '真理'],
}

_ENTITY_PATTERN = re.compile(
    r'(?:[\u4e00-\u9fff]{2,8})|'
    r'(?:[A-Z][a-z]+(?:[A-Z][a-z]+)*)|'
    r'(?:[a-z_][a-z0-9_]*)'
)

_CODE_PATTERN = re.compile(r'(?:```|def |class |import |function |var |const |let |async |await |return |if \(|for \(|while \()')

_SENTENCE_ENDERS = re.compile(r'[。！？\n；;]')


_LEARNING_TYPES = {'why_how', 'what', 'comparison', 'analysis'}
_IMMEDIATE_TYPES = {'fix', 'request', 'yes_no', 'create'}
_LEARNING_TOPICS = {'knowledge', 'philosophy'}


class InputProcessor:
    """动态输入处理器 — 分层提炼而非硬性截断"""

    MAX_TOKENS_NORMAL = 4000
    MAX_TOKENS_CONSERVATIVE = 2400
    MAX_TOKENS_EMERGENCY = 1200

    PRIORITY_WEIGHTS = {
        "query": 1.0,
        "conversation_context": 0.8,
        "truth_insights": 0.6,
        "essence_prompt": 0.5,
        "experience_context": 0.3,
    }

    LEARNING_PRIORITY_WEIGHTS = {
        "query": 1.0,
        "truth_insights": 0.9,
        "essence_prompt": 0.8,
        "conversation_context": 0.5,
        "experience_context": 0.4,
    }

    def __init__(self):
        self._cache: Dict[str, InputSkeleton] = {}
        self._cache_max = 50
        self._deferred_inputs: List[Dict] = []
        self._deferred_max = 100

    def process(self, user_input: str, memory_usage: float = 0.5,
                mode: str = "normal") -> ProcessedInput:
        original_len = len(user_input)

        skeleton = self._extract_skeleton(user_input)

        cognitive_strategy = self._determine_cognitive_strategy(skeleton)

        if mode == "emergency" or memory_usage > 0.85:
            budget = self.MAX_TOKENS_EMERGENCY
            compression_level = "emergency"
        elif mode == "conservative" or memory_usage > 0.70:
            budget = self.MAX_TOKENS_CONSERVATIVE
            compression_level = "conservative"
        else:
            budget = self.MAX_TOKENS_NORMAL
            compression_level = "normal"

        if cognitive_strategy == "learning":
            budget = int(budget * 1.2)
            budget = min(budget, self.MAX_TOKENS_NORMAL * 2)

        estimated_tokens = self._estimate_tokens(user_input)

        if estimated_tokens <= budget:
            return ProcessedInput(
                skeleton=skeleton,
                distilled=user_input,
                mode=compression_level,
                cognitive_strategy=cognitive_strategy,
                original_length=original_len,
                distilled_length=original_len,
                compression_ratio=1.0,
                was_distilled=False,
            )

        distilled, removed = self._distill(user_input, skeleton, budget)

        distilled_len = len(distilled)
        actual_ratio = distilled_len / max(1, original_len)

        deferred = False
        if cognitive_strategy == "learning" and actual_ratio < 0.5:
            deferred = self._defer_for_later(user_input, skeleton, actual_ratio)

        logger.info(
            f"输入提炼: {original_len}→{distilled_len}字符 "
            f"(压缩率{actual_ratio:.1%}, 模式={compression_level}, "
            f"策略={cognitive_strategy}, 主题={skeleton.topic}, "
            f"问题类型={skeleton.question_type})"
        )

        return ProcessedInput(
            skeleton=skeleton,
            distilled=distilled,
            mode=compression_level,
            cognitive_strategy=cognitive_strategy,
            original_length=original_len,
            distilled_length=distilled_len,
            compression_ratio=actual_ratio,
            was_distilled=True,
            removed_details=removed[:5],
            deferred_for_learning=deferred,
        )

    def distill_prompt_parts(self, parts: List[Tuple[str, str, float]],
                             budget: int = 4000,
                             cognitive_strategy: str = "immediate") -> str:
        """
        按优先级分配token预算，构造最终prompt

        Args:
            parts: [(name, content, priority_weight), ...]
            budget: 总token预算
            cognitive_strategy: learning时真谛/本质推理优先级提升
        """
        if cognitive_strategy == "learning":
            adjusted_parts = []
            for name, content, weight in parts:
                adjusted = self.LEARNING_PRIORITY_WEIGHTS.get(name, weight)
                adjusted_parts.append((name, content, adjusted))
            parts = adjusted_parts

        total_priority = sum(w for _, _, w in parts if _[1])
        if total_priority == 0:
            return ""

        result_parts = []
        remaining_budget = budget

        sorted_parts = sorted(parts, key=lambda x: x[2], reverse=True)

        for name, content, weight in sorted_parts:
            if not content or not content.strip():
                continue

            content_tokens = self._estimate_tokens(content)
            allocated = int(budget * weight / total_priority)
            allocated = min(allocated, remaining_budget, content_tokens)

            if allocated <= 0:
                continue

            if content_tokens <= allocated:
                result_parts.append(content)
                remaining_budget -= content_tokens
            else:
                truncated = self._truncate_to_tokens(content, allocated)
                result_parts.append(truncated)
                remaining_budget -= allocated

            if remaining_budget <= 100:
                break

        return "\n\n".join(result_parts)

    def _extract_skeleton(self, text: str) -> InputSkeleton:
        cache_key = str(hash(text[:500]))
        if cache_key in self._cache:
            return self._cache[cache_key]

        topic = self._extract_topic(text)
        entities = self._extract_entities(text)
        question_type = self._classify_question(text)
        core_sentences = self._extract_core_sentences(text)
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

        has_question = bool(re.search(r'[？?]', text))
        has_code = bool(_CODE_PATTERN.search(text))

        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        if chinese_chars > english_chars * 2:
            language = "chinese"
        elif english_chars > chinese_chars * 2:
            language = "english"
        else:
            language = "mixed"

        skeleton = InputSkeleton(
            topic=topic,
            entities=entities,
            question_type=question_type,
            core_sentences=core_sentences,
            length=len(text),
            paragraph_count=len(paragraphs),
            has_question=has_question,
            has_code=has_code,
            language=language,
        )

        skeleton.knowledge_connections = self._find_knowledge_connections(text, entities, topic)
        skeleton.conflict_signals = self._detect_conflicts(text, entities)

        if len(self._cache) >= self._cache_max:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[cache_key] = skeleton

        return skeleton

    def _extract_topic(self, text: str) -> str:
        scores: Dict[str, int] = {}
        text_lower = text.lower()

        for topic, keywords in _TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw.lower() in text_lower)
            if score > 0:
                scores[topic] = score

        if not scores:
            return "general"

        return max(scores, key=scores.get)

    def _extract_entities(self, text: str) -> List[str]:
        matches = _ENTITY_PATTERN.findall(text)

        stop_words = {
            '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都',
            '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你',
            '会', '着', '没有', '看', '好', '自己', '这', '他', '她', '它',
            'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'shall', 'can',
            'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'into', 'through',
        }

        freq: Dict[str, int] = {}
        for m in matches:
            m_stripped = m.strip()
            if m_stripped.lower() not in stop_words and len(m_stripped) >= 2:
                freq[m_stripped] = freq.get(m_stripped, 0) + 1

        sorted_entities = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [e for e, _ in sorted_entities[:15]]

    def _classify_question(self, text: str) -> str:
        for pattern, q_type in _QUESTION_PATTERNS:
            if re.search(pattern, text):
                return q_type
        return "statement"

    def _extract_core_sentences(self, text: str) -> List[str]:
        sentences = _SENTENCE_ENDERS.split(text)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]

        if not sentences:
            return []

        scored: List[Tuple[str, float]] = []
        for i, sent in enumerate(sentences):
            score = 0.0

            if re.search(r'[？?]', sent):
                score += 3.0

            entity_count = sum(1 for e in _ENTITY_PATTERN.findall(sent) if len(e) >= 2)
            score += min(entity_count * 0.3, 2.0)

            if i < 2:
                score += 1.5
            elif i < 4:
                score += 0.8

            if re.search(r'(?:关键|核心|重要|本质|根本|必须|一定|务必)', sent):
                score += 2.0

            if re.search(r'(?:但是|然而|不过|但是|可是|却)', sent):
                score += 1.0

            if _CODE_PATTERN.search(sent):
                score += 1.5

            if re.search(r'(?:因为|所以|因此|由于|导致|引起)', sent):
                score += 1.0

            scored.append((sent, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        top = [s for s, _ in scored[:8]]

        top_set = set(top)
        ordered = [s for s in sentences if s in top_set]

        return ordered[:8]

    def _distill(self, text: str, skeleton: InputSkeleton,
                 budget: int) -> Tuple[str, List[str]]:
        """
        三层提炼：
        1. 保留核心句子（骨架层）
        2. 按段落重要性填充剩余预算（填充层）
        3. 超出预算时逐句裁剪（精炼层）
        """
        removed_details = []

        core_text = "\n".join(skeleton.core_sentences)
        core_tokens = self._estimate_tokens(core_text)

        if core_tokens >= budget:
            distilled = self._truncate_to_tokens(core_text, budget)
            removed_details.append(f"原始{len(text)}字符→骨架{len(distilled)}字符")
            return distilled, removed_details

        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        core_set = set(skeleton.core_sentences)

        scored_paragraphs: List[Tuple[str, float]] = []
        for i, para in enumerate(paragraphs):
            if para in core_set:
                continue

            score = self._score_paragraph(para, i, len(paragraphs), skeleton)
            scored_paragraphs.append((para, score))

        scored_paragraphs.sort(key=lambda x: x[1], reverse=True)

        result_parts = list(skeleton.core_sentences)
        remaining_tokens = budget - core_tokens

        for para, score in scored_paragraphs:
            para_tokens = self._estimate_tokens(para)
            if para_tokens <= remaining_tokens:
                result_parts.append(para)
                remaining_tokens -= para_tokens
            else:
                if remaining_tokens > 100:
                    truncated_para = self._truncate_to_tokens(para, remaining_tokens)
                    result_parts.append(truncated_para)
                    removed_details.append(para[:50] + "...")
                else:
                    removed_details.append(para[:50] + "...")
                break

        para_order = {p: i for i, p in enumerate(paragraphs)}
        result_parts.sort(key=lambda p: para_order.get(p, 999))

        distilled = "\n".join(result_parts)

        if self._estimate_tokens(distilled) > budget:
            distilled = self._truncate_to_tokens(distilled, budget)

        return distilled, removed_details

    def _score_paragraph(self, paragraph: str, position: int,
                         total: int, skeleton: InputSkeleton) -> float:
        score = 0.0

        if position < 2:
            score += 2.0
        elif position < 4:
            score += 1.0

        if position >= total - 2:
            score += 1.0

        if skeleton.topic != "general":
            topic_keywords = _TOPIC_KEYWORDS.get(skeleton.topic, [])
            keyword_hits = sum(1 for kw in topic_keywords if kw.lower() in paragraph.lower())
            score += min(keyword_hits * 0.5, 3.0)

        for entity in skeleton.entities[:5]:
            if entity in paragraph:
                score += 0.5

        if _CODE_PATTERN.search(paragraph):
            score += 1.5

        if re.search(r'[？?]', paragraph):
            score += 2.0

        if re.search(r'(?:关键|核心|重要|本质|根本|必须|注意|务必)', paragraph):
            score += 1.5

        if re.search(r'(?:因为|所以|因此|由于|导致|结论|结果)', paragraph):
            score += 1.0

        para_len = len(paragraph)
        if 20 < para_len < 200:
            score += 0.5
        elif para_len >= 200:
            score += 0.3

        return score

    def _find_knowledge_connections(self, text: str, entities: List[str],
                                    topic: str) -> List[KnowledgeConnection]:
        """
        连接生成：在知识图谱中查找与当前输入相关的已有知识节点

        对应人类顶尖学习者的"这个观点让我想起……"能力
        """
        connections = []
        try:
            from core.knowledge_graph import get_knowledge_graph
            kg = get_knowledge_graph()
            search_queries = [text[:100]]
            if entities:
                search_queries.append(" ".join(entities[:5]))
            if topic != "general":
                search_queries.append(topic)

            seen_ids = set()
            for query in search_queries:
                nodes = kg.search(query, top_k=3)
                for node in nodes:
                    if node.id not in seen_ids:
                        seen_ids.add(node.id)
                        connections.append(KnowledgeConnection(
                            node_id=node.id,
                            content=node.content,
                            relevance=min(1.0, node.importance * 0.5),
                            connection_type="related",
                        ))
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"知识连接查找失败: {e}")

        return connections[:8]

    def _detect_conflicts(self, text: str, entities: List[str]) -> List[ConflictSignal]:
        """
        批判性思考：检测输入内容与已有真谛/事实的潜在冲突

        对应人类顶尖学习者的"哪些是与我已有认知冲突的？"能力
        """
        conflicts = []
        try:
            from infrastructure.fact_store import fact_store
            fs = fact_store

            for entity in entities[:5]:
                if len(entity) < 2:
                    continue
                results = fs.search_by_keywords(entity, limit=2)
                for fact in results:
                    fact_text = f"{fact.get('subject', '')} {fact.get('predicate', '')} {fact.get('object', '')}"
                    if not fact_text.strip():
                        continue
                    overlap = self._text_overlap(text, fact_text)
                    if overlap > 0.3:
                        negations = fs.get_negations(fact.get('question', entity))
                        if negations:
                            for neg in negations[:1]:
                                conflicts.append(ConflictSignal(
                                    existing_fact=fact_text[:100],
                                    input_claim=text[:100],
                                    conflict_type="negation_exists",
                                    confidence=0.7,
                                ))
                        contradiction_markers = ['不是', '并非', '错误', '不对', '相反', '其实不是']
                        for marker in contradiction_markers:
                            if marker in text and overlap > 0.2:
                                conflicts.append(ConflictSignal(
                                    existing_fact=fact_text[:100],
                                    input_claim=text[:100],
                                    conflict_type="contradiction_marker",
                                    confidence=0.5,
                                ))
                                break
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"冲突检测失败: {e}")

        return conflicts[:5]

    def _text_overlap(self, text1: str, text2: str) -> float:
        """计算两段文本的词汇重叠度"""
        words1 = set(re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{2,}', text1.lower()))
        words2 = set(re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{2,}', text2.lower()))
        if not words1 or not words2:
            return 0.0
        return len(words1 & words2) / max(len(words1 | words2), 1)

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        other_chars = len(text) - chinese_chars
        return int(chinese_chars * 2 + other_chars * 0.5)

    def _truncate_to_tokens(self, text: str, token_budget: int) -> str:
        if self._estimate_tokens(text) <= token_budget:
            return text

        sentences = _SENTENCE_ENDERS.split(text)
        result = []
        current_tokens = 0

        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            sent_tokens = self._estimate_tokens(sent)
            if current_tokens + sent_tokens <= token_budget:
                result.append(sent)
                current_tokens += sent_tokens
            else:
                remaining = token_budget - current_tokens
                if remaining > 50:
                    char_budget = int(remaining / 1.5)
                    result.append(sent[:char_budget])
                break

        return "。".join(result)

    def _determine_cognitive_strategy(self, skeleton: InputSkeleton) -> str:
        """
        根据任务类型和主题决定认知策略

        学习模式(learning)：分层提炼，可跨多轮深化
          → why_how, what, comparison, analysis + knowledge/philosophy主题
        即时模式(immediate)：快速定位，一次性输出
          → fix, request, yes_no, create + 其他主题
        """
        if skeleton.question_type in _LEARNING_TYPES:
            return "learning"
        if skeleton.topic in _LEARNING_TOPICS:
            return "learning"
        if skeleton.question_type in _IMMEDIATE_TYPES:
            return "immediate"
        if skeleton.has_code:
            return "immediate"
        if skeleton.length > 2000 and skeleton.question_type == "statement":
            return "learning"
        return "immediate"

    def _defer_for_later(self, original_input: str,
                         skeleton: InputSkeleton,
                         compression_ratio: float) -> bool:
        """
        学习模式下，如果压缩率过低（丢失太多信息），
        将原始输入存入延迟队列，等待资源充足时后台深度处理
        """
        if len(self._deferred_inputs) >= self._deferred_max:
            oldest = self._deferred_inputs.pop(0)
        self._deferred_inputs.append({
            "input": original_input,
            "skeleton": skeleton.to_dict(),
            "compression_ratio": compression_ratio,
            "timestamp": time.time(),
        })
        logger.info(
            f"学习模式延迟: 压缩率{compression_ratio:.1%}过低，"
            f"原始输入已存入延迟队列(当前{len(self._deferred_inputs)}条)"
        )
        return True

    def get_deferred_inputs(self, limit: int = 10) -> List[Dict]:
        """获取待深度处理的延迟输入"""
        return self._deferred_inputs[:limit]

    def remove_deferred_input(self, item: Dict) -> bool:
        """移除已处理的延迟输入"""
        try:
            self._deferred_inputs.remove(item)
            return True
        except ValueError:
            return False

    def get_stats(self) -> Dict:
        return {
            "cache_size": len(self._cache),
            "deferred_inputs": len(self._deferred_inputs),
            "learning_priority_weights": self.LEARNING_PRIORITY_WEIGHTS,
            "immediate_priority_weights": self.PRIORITY_WEIGHTS,
        }


_input_processor: Optional[InputProcessor] = None


def get_input_processor() -> InputProcessor:
    global _input_processor
    if _input_processor is None:
        _input_processor = InputProcessor()
    return _input_processor