"""
信任链构建器

从L4校验层提取的核心能力：为输出构建可追溯的信任链，
说明信息来源、推理过程和每一步的置信度。
与self_verifier互补——self_verifier负责内容验证，trust_chain负责来源可追溯性。
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger


@dataclass
class TrustLink:
    source: str
    statement: str
    confidence: float
    link_type: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TrustChainResult:
    chain: List[TrustLink]
    overall_trust: float
    weakest_link: Optional[TrustLink]
    chain_length: int


class TrustChainBuilder:
    """信任链构建器"""

    LINK_TYPES = frozenset([
        'source', 'reasoning', 'validation', 'integration', 'output',
    ])

    def __init__(self):
        self._chain_cache: List[TrustChainResult] = []

    def build_chain(self, core_knowledge: List[Dict],
                    integration_info: Optional[Dict] = None,
                    validation_info: Optional[Dict] = None) -> TrustChainResult:
        """构建信任链

        Args:
            core_knowledge: 核心知识项列表，每项含source/confidence/content
            integration_info: 整合层信息，含nodes_count/relations_count
            validation_info: 校验层信息，含certainty/consistency/completeness

        Returns:
            信任链结果
        """
        chain: List[TrustLink] = []

        for item in core_knowledge[:5]:
            chain.append(TrustLink(
                source=item.get('source', 'unknown'),
                statement=f"知识来源: {item.get('source', '未知')} (置信度: {item.get('confidence', 0.5):.2f})",
                confidence=item.get('confidence', 0.5),
                link_type='source',
            ))

        if integration_info:
            chain.append(TrustLink(
                source='integration',
                statement=f"已整合 {integration_info.get('nodes_count', 0)} 个知识节点, "
                          f"{integration_info.get('relations_count', 0)} 条关系",
                confidence=0.8,
                link_type='integration',
            ))

        if validation_info:
            certainty = validation_info.get('certainty', 0.5)
            consistency = validation_info.get('consistency', 0.5)
            completeness = validation_info.get('completeness', 0.5)
            val_conf = (certainty + consistency + completeness) / 3
            chain.append(TrustLink(
                source='validation',
                statement=f"校验通过: 确定性={certainty:.2f}, 一致性={consistency:.2f}, 完整性={completeness:.2f}",
                confidence=val_conf,
                link_type='validation',
            ))

        chain.append(TrustLink(
            source='output',
            statement="输出已构建信任链",
            confidence=0.75,
            link_type='output',
        ))

        if not chain:
            overall_trust = 0.0
            weakest = None
        else:
            confidences = [link.confidence for link in chain]
            overall_trust = min(confidences) * 0.6 + (sum(confidences) / len(confidences)) * 0.4
            weakest = min(chain, key=lambda l: l.confidence)

        result = TrustChainResult(
            chain=chain,
            overall_trust=overall_trust,
            weakest_link=weakest,
            chain_length=len(chain),
        )

        self._chain_cache.append(result)
        if len(self._chain_cache) > 100:
            self._chain_cache = self._chain_cache[-100:]

        return result

    def build_simple_chain(self, source: str, content: str,
                           confidence: float) -> TrustChainResult:
        """构建简单信任链（单来源场景）

        用于外部API或Ollama等单路径响应
        """
        chain = [
            TrustLink(
                source=source,
                statement=f"来源: {source}",
                confidence=confidence,
                link_type='source',
            ),
            TrustLink(
                source='output',
                statement="输出已构建信任链",
                confidence=confidence * 0.9,
                link_type='output',
            ),
        ]

        return TrustChainResult(
            chain=chain,
            overall_trust=confidence * 0.95,
            weakest_link=chain[-1],
            chain_length=len(chain),
        )

    def get_stats(self) -> Dict:
        if not self._chain_cache:
            return {'total_chains': 0, 'avg_trust': 0.0, 'avg_length': 0}

        trusts = [c.overall_trust for c in self._chain_cache]
        lengths = [c.chain_length for c in self._chain_cache]
        return {
            'total_chains': len(self._chain_cache),
            'avg_trust': sum(trusts) / len(trusts),
            'avg_length': sum(lengths) / len(lengths),
        }


trust_chain_builder = TrustChainBuilder()