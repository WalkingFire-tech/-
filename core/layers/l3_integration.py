"""
L3: 整合层 - 将碎片化知识整合为连贯认知结构

职责：
1. 接收来自L2的学习成果（知识碎片）
2. 识别知识之间的关联、矛盾、层次关系
3. 解决冲突（基于可信度、来源权威性、时间戳）
4. 构建结构化的知识图（不是输出，而是整合后的认知框架）
5. 为L4校验层提供"已整合"的知识

核心机制：
- 冲突检测与协调
- 知识聚类与归并
- 置信度加权汇总
- 结构化输出（供L4使用）
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
import re

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from core.introspection.layer_reporter import LayerReporter
from core.reporting.state_collector import get_state_collector
from core.introspection.heartbeat import get_heartbeat_manager
from core.state_report import LayerHealth


class KnowledgeRelation(Enum):
    """知识之间的关系"""
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    EXTENDS = "extends"
    SPECIFIES = "specifies"
    GENERALIZES = "generalizes"
    UNRELATED = "unrelated"


@dataclass
class KnowledgeNode:
    """知识节点"""
    id: str
    content: str
    source: str
    confidence: float
    quality_score: float
    timestamp: str
    keywords: List[str] = field(default_factory=list)
    relations: List[Tuple[str, KnowledgeRelation]] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content[:200] + ("..." if len(self.content) > 200 else ""),
            "source": self.source,
            "confidence": self.confidence,
            "quality_score": self.quality_score,
            "timestamp": self.timestamp,
            "keywords": self.keywords[:10],
            "relations_count": len(self.relations)
        }


@dataclass
class IntegrationResult:
    """整合结果"""
    success: bool
    knowledge_graph: Dict[str, KnowledgeNode]
    core_knowledge: List[Dict]
    resolved_conflicts: int
    total_nodes: int
    confidence: float
    reasoning: List[str]
    warnings: List[str]
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class L3IntegrationLayer:
    """L3: 整合层"""
    
    def __init__(self):
        self.reporter = LayerReporter("L3")
        self.collector = get_state_collector()
        self.heartbeat = get_heartbeat_manager()
        
        self.reporter.report_idle()
        
        self.stats = {
            'total_integrations': 0,
            'total_conflicts_resolved': 0,
            'avg_knowledge_nodes': 0,
            'total_relations_discovered': 0,
            'source_distribution': {},
        }
        
        self._graph_cache: Dict[str, KnowledgeNode] = {}
        
        logger.info("🧩 L3整合层已初始化（含状态报告）")
        self.reporter.report_completed(
            metrics={"initialized": 1},
            confidence=1.0
        )
    
    def integrate(self, knowledge_items: List[Dict], context: Optional[Dict] = None) -> IntegrationResult:
        """
        整合知识碎片
        
        输入：来自L2的知识碎片列表
        输出：结构化的知识图 + 核心知识提炼
        """
        self.stats['total_integrations'] += 1
        start_time = datetime.now()
        
        reasoning = []
        warnings = []
        issues = []
        metrics = {}
        
        self.reporter.report_busy(
            operation=f"整合 {len(knowledge_items)} 个知识碎片",
            active_tasks=[f"处理 {len(knowledge_items)} 个知识项"]
        )
        
        try:
            if not self.heartbeat.is_layer_alive("L2"):
                warnings.append("L2不可用，知识可能不完整")
            
            if not self.heartbeat.is_layer_alive("L4"):
                warnings.append("L4不可用，整合结果将跳过校验")
            
            logger.debug(f"L3: 构建 {len(knowledge_items)} 个知识节点")
            
            nodes = self._build_knowledge_nodes(knowledge_items)
            reasoning.append(f"构建了 {len(nodes)} 个知识节点")
            metrics['nodes_count'] = len(nodes)
            
            if not nodes:
                warnings.append("没有有效的知识节点可整合")
                return IntegrationResult(
                    success=True,
                    knowledge_graph={},
                    core_knowledge=[],
                    resolved_conflicts=0,
                    total_nodes=0,
                    confidence=0.5,
                    reasoning=["没有知识可整合"],
                    warnings=warnings
                )
            
            total_nodes = len(nodes)
            self.stats['avg_knowledge_nodes'] = (
                (self.stats['avg_knowledge_nodes'] * (self.stats['total_integrations'] - 1) + total_nodes)
                / self.stats['total_integrations']
            )
            
            logger.debug("L3: 识别知识间关系")
            
            relations = self._discover_relations(nodes)
            reasoning.append(f"发现 {len(relations)} 条关系")
            metrics['relations_count'] = len(relations)
            self.stats['total_relations_discovered'] += len(relations)
            
            for source_id, target_id, rel in relations:
                if source_id in nodes:
                    nodes[source_id].relations.append((target_id, rel))
            
            logger.debug("L3: 检测并协调冲突")
            
            conflicts, resolved = self._detect_and_resolve_conflicts(nodes)
            reasoning.append(f"检测到 {len(conflicts)} 个冲突，已解决 {resolved} 个")
            metrics['conflicts_detected'] = len(conflicts)
            metrics['conflicts_resolved'] = resolved
            
            self.stats['total_conflicts_resolved'] += resolved
            
            if conflicts and resolved == 0:
                warnings.append(f"{len(conflicts)} 个冲突未能自动解决，可能需要人工介入")
            
            logger.debug("L3: 提炼核心知识")
            
            core_knowledge = self._refine_core_knowledge(nodes)
            reasoning.append(f"提炼出 {len(core_knowledge)} 条核心知识")
            metrics['core_knowledge_count'] = len(core_knowledge)
            
            if nodes:
                avg_confidence = sum(n.confidence for n in nodes.values()) / len(nodes)
                unresolved_penalty = 0.1 * (len(conflicts) - resolved) / max(len(conflicts), 1)
                overall_confidence = max(0.1, avg_confidence - unresolved_penalty)
            else:
                overall_confidence = 0.5
            
            reasoning.append(f"整体置信度: {overall_confidence:.2f}")
            metrics['overall_confidence'] = overall_confidence
            
            self.reporter.report_completed(
                metrics=metrics,
                confidence=overall_confidence,
                warnings=warnings if warnings else None,
                issues=issues if issues else None
            )
            
            result = IntegrationResult(
                success=True,
                knowledge_graph=nodes,
                core_knowledge=core_knowledge,
                resolved_conflicts=resolved,
                total_nodes=total_nodes,
                confidence=overall_confidence,
                reasoning=reasoning,
                warnings=warnings
            )
            
            self._graph_cache = nodes
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"🧩 L3整合完成: {total_nodes}个节点, "
                f"{len(relations)}条关系, {resolved}个冲突已解决, "
                f"置信度: {overall_confidence:.2f}, 耗时: {elapsed:.2f}s"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"L3整合异常: {str(e)}"
            logger.error(error_msg)
            
            self.reporter.report_error(
                issues=[error_msg],
                metrics=metrics
            )
            
            return IntegrationResult(
                success=False,
                knowledge_graph={},
                core_knowledge=[],
                resolved_conflicts=0,
                total_nodes=0,
                confidence=0.0,
                reasoning=[],
                warnings=[],
                error=error_msg
            )
    
    def _build_knowledge_nodes(self, items: List[Dict]) -> Dict[str, KnowledgeNode]:
        """构建知识节点"""
        nodes = {}
        
        for item in items:
            content = item.get('answer', item.get('content', ''))
            if not content:
                continue
            
            node_id = item.get('id', f"node_{hashlib.md5(content[:100].encode()).hexdigest()[:8]}")
            
            node = KnowledgeNode(
                id=node_id,
                content=content,
                source=item.get('source', 'unknown'),
                confidence=item.get('confidence', 0.5),
                quality_score=item.get('quality_score', 50),
                timestamp=item.get('created_at', datetime.now().isoformat()),
                keywords=self._extract_keywords(content)
            )
            
            nodes[node_id] = node
            
            source = node.source
            self.stats['source_distribution'][source] = \
                self.stats['source_distribution'].get(source, 0) + 1
        
        return nodes
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简化版）"""
        words = re.findall(r'[a-zA-Z]{3,}', text)
        
        seen = set()
        keywords = []
        for w in words:
            w_lower = w.lower()
            if w_lower not in seen and len(w) > 2:
                seen.add(w_lower)
                keywords.append(w_lower)
                if len(keywords) >= 10:
                    break
        
        return keywords
    
    def _discover_relations(self, nodes: Dict[str, KnowledgeNode]) -> List[Tuple[str, str, KnowledgeRelation]]:
        """发现知识间的关系"""
        relations = []
        node_list = list(nodes.items())
        
        for i, (id1, node1) in enumerate(node_list):
            for j, (id2, node2) in enumerate(node_list):
                if i >= j:
                    continue
                
                overlap = set(node1.keywords) & set(node2.keywords)
                
                if not overlap:
                    continue
                
                overlap_ratio = len(overlap) / max(len(set(node1.keywords) | set(node2.keywords)), 1)
                
                if overlap_ratio > 0.5:
                    if len(node1.content) < len(node2.content) * 0.6:
                        relations.append((id1, id2, KnowledgeRelation.SPECIFIES))
                    else:
                        relations.append((id1, id2, KnowledgeRelation.SUPPORTS))
                elif overlap_ratio > 0.3:
                    if len(node1.content) > len(node2.content) * 1.5:
                        relations.append((id1, id2, KnowledgeRelation.GENERALIZES))
                    else:
                        relations.append((id1, id2, KnowledgeRelation.EXTENDS))
                else:
                    relations.append((id1, id2, KnowledgeRelation.UNRELATED))
        
        return relations
    
    def _detect_and_resolve_conflicts(self, nodes: Dict[str, KnowledgeNode]) -> Tuple[List[Dict], int]:
        """检测并协调冲突"""
        conflicts = []
        resolved_count = 0
        
        node_list = list(nodes.items())
        
        for i, (id1, node1) in enumerate(node_list):
            for j, (id2, node2) in enumerate(node_list):
                if i >= j:
                    continue
                
                conflict = self._detect_conflict(node1, node2)
                
                if conflict:
                    conflicts.append({
                        'node1_id': id1,
                        'node2_id': id2,
                        'description': conflict
                    })
                    
                    if self._resolve_conflict(node1, node2):
                        resolved_count += 1
        
        return conflicts, resolved_count
    
    def _detect_conflict(self, node1: KnowledgeNode, node2: KnowledgeNode) -> Optional[str]:
        """检测两个节点之间的冲突"""
        if not (set(node1.keywords) & set(node2.keywords)):
            return None
        
        neg_words = {'not', 'no', 'never', 'cannot', 'wrong', 'incorrect', 'false'}
        
        for kw in set(node1.keywords) & set(node2.keywords):
            kw_neg1 = any(neg in node1.content.lower() and kw in node1.content.lower() for neg in neg_words)
            kw_neg2 = any(neg in node2.content.lower() and kw in node2.content.lower() for neg in neg_words)
            
            if kw_neg1 != kw_neg2:
                return f"关键词 '{kw}' 的肯定/否定不一致"
        
        if abs(node1.confidence - node2.confidence) > 0.5:
            return f"置信度差异过大: {node1.confidence:.2f} vs {node2.confidence:.2f}"
        
        return None
    
    def _resolve_conflict(self, node1: KnowledgeNode, node2: KnowledgeNode) -> bool:
        """尝试解决冲突"""
        if node1.quality_score > node2.quality_score + 10:
            node2.confidence = min(node2.confidence, 0.3)
            return True
        elif node2.quality_score > node1.quality_score + 10:
            node1.confidence = min(node1.confidence, 0.3)
            return True
        
        if node1.source in ['official_documentation', 'known_manufacturer'] and node2.source not in ['official_documentation', 'known_manufacturer']:
            node2.confidence = min(node2.confidence, 0.4)
            return True
        elif node2.source in ['official_documentation', 'known_manufacturer'] and node1.source not in ['official_documentation', 'known_manufacturer']:
            node1.confidence = min(node1.confidence, 0.4)
            return True
        
        return False
    
    def _refine_core_knowledge(self, nodes: Dict[str, KnowledgeNode]) -> List[Dict]:
        """提炼核心知识"""
        if not nodes:
            return []
        
        sorted_nodes = sorted(
            nodes.values(),
            key=lambda n: (n.confidence + n.quality_score / 100),
            reverse=True
        )
        
        core_items = sorted_nodes[:min(max(1, len(sorted_nodes) // 2), 10)]
        
        core_knowledge = []
        for node in core_items:
            core_knowledge.append({
                'id': node.id,
                'content': node.content,
                'confidence': node.confidence,
                'quality_score': node.quality_score,
                'source': node.source,
                'keywords': node.keywords[:5]
            })
        
        return core_knowledge
    
    def get_integration_status(self) -> Dict:
        """获取整合状态"""
        neighbor_status = self.heartbeat.get_neighbor_status("L3")
        
        return {
            "layer": "L3",
            "stats": self.stats,
            "neighbor_status": {
                k: v.value for k, v in neighbor_status.items()
            },
            "cached_nodes": len(self._graph_cache),
            "latest_confidence": self._graph_cache and max(n.confidence for n in self._graph_cache.values()) or 0
        }


_l3_instance = None

def get_l3_integration() -> L3IntegrationLayer:
    global _l3_instance
    if _l3_instance is None:
        _l3_instance = L3IntegrationLayer()
    return _l3_instance