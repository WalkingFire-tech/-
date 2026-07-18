"""
知识冲突解决器

从L3整合层提取的核心能力：检测并解决知识节点之间的冲突。
与knowledge_graph互补——knowledge_graph负责存储和检索，conflict_resolver负责一致性和冲突解决。
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


@dataclass
class ConflictRecord:
    node1_id: str
    node2_id: str
    conflict_type: str
    description: str
    resolution: Optional[str] = None
    resolved: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ConflictResolver:
    """知识冲突检测与解决"""

    AUTHORITATIVE_SOURCES = frozenset([
        'official_documentation', 'known_manufacturer',
        'verified_source', 'peer_reviewed',
    ])

    NEGATION_WORDS_EN = frozenset(['not', 'no', 'never', 'cannot', 'wrong', 'incorrect', 'false'])
    NEGATION_WORDS_CN = frozenset(['不', '不是', '并非', '错误', '否', '无', '没', '不能', '不会'])

    def __init__(self):
        self._history: List[ConflictRecord] = []
        self._stats = {
            'total_conflicts_detected': 0,
            'total_conflicts_resolved': 0,
            'resolution_methods': {},
        }

    def detect_conflicts(self, nodes: Dict[str, Dict]) -> List[ConflictRecord]:
        """检测知识节点之间的冲突

        Args:
            nodes: {node_id: {"content": str, "confidence": float, "source": str, "keywords": List[str]}}

        Returns:
            冲突记录列表
        """
        conflicts = []
        node_list = list(nodes.items())

        for i, (id1, n1) in enumerate(node_list):
            for j, (id2, n2) in enumerate(node_list):
                if i >= j:
                    continue

                conflict = self._detect_pair_conflict(id1, n1, id2, n2)
                if conflict:
                    conflicts.append(conflict)
                    self._stats['total_conflicts_detected'] += 1

        self._history.extend(conflicts)
        if len(self._history) > 500:
            self._history = self._history[-500:]

        return conflicts

    def resolve_conflicts(self, conflicts: List[ConflictRecord],
                          nodes: Dict[str, Dict]) -> int:
        """尝试解决冲突，返回解决数量

        解决策略：
        1. 质量分差>10：低质量方置信度降至0.3
        2. 权威源优先：非权威源置信度降至0.4
        3. 无法自动解决：标记为待人工审查
        """
        resolved = 0

        for conflict in conflicts:
            if conflict.resolved:
                continue

            n1 = nodes.get(conflict.node1_id, {})
            n2 = nodes.get(conflict.node2_id, {})

            method = None

            q1 = n1.get('quality_score', 50)
            q2 = n2.get('quality_score', 50)
            if abs(q1 - q2) > 10:
                loser_id = conflict.node1_id if q1 < q2 else conflict.node2_id
                nodes[loser_id]['confidence'] = min(nodes[loser_id].get('confidence', 0.5), 0.3)
                method = 'quality_score'

            elif self._is_authoritative(n1.get('source', '')) and not self._is_authoritative(n2.get('source', '')):
                nodes[conflict.node2_id]['confidence'] = min(n2.get('confidence', 0.5), 0.4)
                method = 'authoritative_source'
            elif self._is_authoritative(n2.get('source', '')) and not self._is_authoritative(n1.get('source', '')):
                nodes[conflict.node1_id]['confidence'] = min(n1.get('confidence', 0.5), 0.4)
                method = 'authoritative_source'

            if method:
                conflict.resolution = method
                conflict.resolved = True
                resolved += 1
                self._stats['total_conflicts_resolved'] += 1
                self._stats['resolution_methods'][method] = \
                    self._stats['resolution_methods'].get(method, 0) + 1

        return resolved

    def _detect_pair_conflict(self, id1: str, n1: Dict, id2: str, n2: Dict) -> Optional[ConflictRecord]:
        """检测两个节点之间的冲突"""
        kw1 = set(n1.get('keywords', []))
        kw2 = set(n2.get('keywords', []))
        overlap = kw1 & kw2

        if not overlap:
            return None

        c1 = n1.get('content', '')
        c2 = n2.get('content', '')

        for kw in overlap:
            neg1 = self._has_negation(c1, kw)
            neg2 = self._has_negation(c2, kw)
            if neg1 != neg2:
                return ConflictRecord(
                    node1_id=id1, node2_id=id2,
                    conflict_type='negation_mismatch',
                    description=f"关键词 '{kw}' 的肯定/否定不一致",
                )

        conf1 = n1.get('confidence', 0.5)
        conf2 = n2.get('confidence', 0.5)
        if abs(conf1 - conf2) > 0.5:
            return ConflictRecord(
                node1_id=id1, node2_id=id2,
                conflict_type='confidence_divergence',
                description=f"置信度差异过大: {conf1:.2f} vs {conf2:.2f}",
            )

        return None

    def _has_negation(self, text: str, keyword: str) -> bool:
        """检查文本中关键词是否被否定"""
        text_lower = text.lower()
        if keyword.lower() not in text_lower:
            return False
        all_neg = self.NEGATION_WORDS_EN | self.NEGATION_WORDS_CN
        return any(neg in text_lower for neg in all_neg)

    def _is_authoritative(self, source: str) -> bool:
        return source in self.AUTHORITATIVE_SOURCES

    def get_stats(self) -> Dict:
        return {
            **self._stats,
            'pending_conflicts': sum(1 for c in self._history if not c.resolved),
            'recent_conflicts': len(self._history[-20:]),
        }


conflict_resolver = ConflictResolver()