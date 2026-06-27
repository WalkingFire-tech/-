"""
L4: 校验层 - 输出前的最后一道防线

职责：
1. 接收来自L3的整合知识（结构化知识图 + 核心知识）
2. 执行自我质疑：主动找出可能的问题
3. 构建信任链：说明信息来源和推理过程
4. 确定性评估：判断答案有多可靠
5. 决策：通过 → 输出；不通过 → 回退到L2重新学习

核心机制：
- 反向推演（如果我是错的，最可能错在哪里？）
- 一致性检查（整合后的知识与已有知识是否一致？）
- 边界检查（是否超出能力边界？）
- 确定性评分（0-1，决定是否输出）
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
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


class ValidationStatus(Enum):
    """校验状态"""
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"
    ERROR = "error"


class TrustLevel(Enum):
    """信任等级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


@dataclass
class Doubt:
    """质疑项"""
    description: str
    severity: str
    source: str
    resolution: Optional[str] = None


@dataclass
class TrustChainLink:
    """信任链的一环"""
    source: str
    statement: str
    confidence: float
    timestamp: str


@dataclass
class ValidationResult:
    """校验结果"""
    success: bool
    status: ValidationStatus
    trust_level: TrustLevel
    certainty_score: float
    consistency_score: float
    completeness_score: float
    doubts: List[Doubt]
    trust_chain: List[TrustChainLink]
    issues: List[str]
    warnings: List[str]
    should_fallback: bool
    fallback_reason: Optional[str]
    reasoning: List[str]
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class L4ValidationLayer:
    """L4: 校验层"""
    
    def __init__(self):
        self.reporter = LayerReporter("L4")
        self.collector = get_state_collector()
        self.heartbeat = get_heartbeat_manager()
        
        self.reporter.report_idle()
        
        self.stats = {
            'total_validations': 0,
            'pass_count': 0,
            'partial_count': 0,
            'fail_count': 0,
            'total_fallbacks': 0,
            'avg_certainty': 0.0,
            'doubt_patterns': {},
        }
        
        self.thresholds = {
            'pass': 0.75,
            'partial': 0.45,
            'fail': 0.45,
        }
        
        logger.info("🔍 L4校验层已初始化（含状态报告 + 自我质疑机制）")
        self.reporter.report_completed(
            metrics={"initialized": 1, "thresholds": len(self.thresholds)},
            confidence=1.0
        )
    
    def validate(self, integrated_knowledge: Dict, context: Optional[Dict] = None) -> ValidationResult:
        """
        执行校验
        
        输入：来自L3的整合结果（核心知识 + 知识图）
        输出：校验结果（是否通过 + 信任链 + 确定性）
        """
        self.stats['total_validations'] += 1
        start_time = datetime.now()
        
        reasoning = []
        issues = []
        warnings = []
        doubts = []
        trust_chain = []
        metrics = {}
        
        self.reporter.report_busy(
            operation="执行输出校验",
            active_tasks=["自我质疑", "信任链构建", "确定性评估"]
        )
        
        try:
            if not self.heartbeat.is_layer_alive("L3"):
                warnings.append("L3不可用，整合结果可能不完整")
            
            if not self.heartbeat.is_layer_alive("L2"):
                warnings.append("L2不可用，回退机制可能失效")
            
            core_knowledge = integrated_knowledge.get('core_knowledge', [])
            knowledge_graph = integrated_knowledge.get('knowledge_graph', {})
            
            if not core_knowledge and not knowledge_graph:
                reasoning.append("无核心知识可校验")
                return ValidationResult(
                    success=False,
                    status=ValidationStatus.FAIL,
                    trust_level=TrustLevel.UNKNOWN,
                    certainty_score=0.0,
                    consistency_score=0.0,
                    completeness_score=0.0,
                    doubts=[],
                    trust_chain=[],
                    issues=["无核心知识"],
                    warnings=warnings,
                    should_fallback=True,
                    fallback_reason="无核心知识",
                    reasoning=reasoning
                )
            
            content = core_knowledge[0].get('content', '') if core_knowledge else ''
            initial_confidence = integrated_knowledge.get('confidence', 0.5)
            
            reasoning.append(f"接收 {len(core_knowledge)} 条核心知识，初始置信度: {initial_confidence:.2f}")
            metrics['initial_confidence'] = initial_confidence
            
            logger.debug("L4: 执行自我质疑")
            doubt_results = self._perform_self_doubt(content, core_knowledge, knowledge_graph, context)
            doubts = doubt_results['doubts']
            doubt_penalty = doubt_results['penalty']
            
            reasoning.append(f"自我质疑发现 {len(doubts)} 个问题，总惩罚: {doubt_penalty:.2f}")
            metrics['doubts_count'] = len(doubts)
            metrics['doubt_penalty'] = doubt_penalty
            
            for doubt in doubts:
                pattern = doubt.description[:50]
                self.stats['doubt_patterns'][pattern] = \
                    self.stats['doubt_patterns'].get(pattern, 0) + 1
            
            logger.debug("L4: 评估确定性")
            certainty_score = self._evaluate_certainty(knowledge_graph, core_knowledge)
            certainty_score = max(0.0, certainty_score - doubt_penalty)
            reasoning.append(f"确定性评分: {certainty_score:.2f}")
            metrics['certainty_score'] = certainty_score
            
            logger.debug("L4: 检查一致性")
            consistency_score, consistency_issues = self._check_consistency(knowledge_graph)
            issues.extend(consistency_issues)
            reasoning.append(f"一致性评分: {consistency_score:.2f}, 发现 {len(consistency_issues)} 个问题")
            metrics['consistency_score'] = consistency_score
            
            logger.debug("L4: 评估完整性")
            completeness_score = self._evaluate_completeness(knowledge_graph, core_knowledge)
            reasoning.append(f"完整性评分: {completeness_score:.2f}")
            metrics['completeness_score'] = completeness_score
            
            logger.debug("L4: 构建信任链")
            trust_chain = self._build_trust_chain(core_knowledge, knowledge_graph, context)
            reasoning.append(f"构建信任链: {len(trust_chain)} 个环节")
            metrics['trust_chain_length'] = len(trust_chain)
            
            chain_bonus = min(len(trust_chain) * 0.02, 0.15)
            certainty_score = min(1.0, certainty_score + chain_bonus)
            
            logger.debug("L4: 决策")
            if certainty_score >= self.thresholds['pass']:
                status = ValidationStatus.PASS
                trust_level = TrustLevel.HIGH
                should_fallback = False
                self.stats['pass_count'] += 1
                reasoning.append("✅ 校验通过，可以输出")
            elif certainty_score >= self.thresholds['partial']:
                status = ValidationStatus.PARTIAL
                trust_level = TrustLevel.MEDIUM
                should_fallback = False
                self.stats['partial_count'] += 1
                reasoning.append("⚠️ 部分通过，将降低确定性输出")
            else:
                status = ValidationStatus.FAIL
                trust_level = TrustLevel.LOW
                should_fallback = True
                fallback_reason = f"确定性过低 ({certainty_score:.2f} < {self.thresholds['fail']:.2f})"
                self.stats['fail_count'] += 1
                self.stats['total_fallbacks'] += 1
                reasoning.append(f"❌ 校验失败，需要回退: {fallback_reason}")
            
            success = status != ValidationStatus.FAIL
            
            self.stats['avg_certainty'] = (
                (self.stats['avg_certainty'] * (self.stats['total_validations'] - 1) + certainty_score)
                / self.stats['total_validations']
            )
            
            self.reporter.report_completed(
                metrics=metrics,
                confidence=certainty_score,
                warnings=warnings if warnings else None,
                issues=issues if issues else None
            )
            
            result = ValidationResult(
                success=success,
                status=status,
                trust_level=trust_level,
                certainty_score=certainty_score,
                consistency_score=consistency_score,
                completeness_score=completeness_score,
                doubts=doubts,
                trust_chain=trust_chain,
                issues=issues,
                warnings=warnings,
                should_fallback=should_fallback,
                fallback_reason=fallback_reason if should_fallback else None,
                reasoning=reasoning
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"🔍 L4校验完成: {status.value}, "
                f"确定性={certainty_score:.2f}, "
                f"质疑={len(doubts)}个, "
                f"信任链={len(trust_chain)}环, "
                f"耗时={elapsed:.2f}s"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"L4校验异常: {str(e)}"
            logger.error(error_msg)
            
            self.reporter.report_error(
                issues=[error_msg],
                metrics=metrics
            )
            
            return ValidationResult(
                success=False,
                status=ValidationStatus.ERROR,
                trust_level=TrustLevel.UNKNOWN,
                certainty_score=0.0,
                consistency_score=0.0,
                completeness_score=0.0,
                doubts=[],
                trust_chain=[],
                issues=[error_msg],
                warnings=[],
                should_fallback=True,
                fallback_reason=error_msg,
                reasoning=[],
                error=error_msg
            )
    
    def _perform_self_doubt(self, content: str, core_knowledge: List[Dict],
                           knowledge_graph: Dict, context: Optional[Dict]) -> Dict:
        """
        执行自我质疑
        
        核心问题：如果我是错的，最可能错在哪里？
        """
        doubts = []
        penalty = 0.0
        
        if len(content) < 20:
            doubts.append(Doubt(
                description="回答内容过短，可能不完整",
                severity="major",
                source="completeness_check"
            ))
            penalty += 0.2
        
        contradictions = self._detect_contradictions(content, core_knowledge)
        if contradictions:
            for cont in contradictions[:3]:
                doubts.append(Doubt(
                    description=f"检测到矛盾: {cont}",
                    severity="critical",
                    source="consistency_check"
                ))
                penalty += 0.25
        
        uncertainty_words = ['可能', '也许', '大概', '似乎', '感觉', '猜测', '不太确定', 'maybe', 'perhaps', 'might']
        uncertainty_count = sum(1 for w in uncertainty_words if w in content.lower())
        if uncertainty_count > 2:
            doubts.append(Doubt(
                description=f"包含 {uncertainty_count} 个不确定性词汇",
                severity="minor",
                source="uncertainty_check"
            ))
            penalty += 0.05 * uncertainty_count
        
        sources = [k.get('source', 'unknown') for k in core_knowledge]
        unreliable_sources = ['blog', 'forum', 'unknown', 'external_search']
        unreliable_count = sum(1 for s in sources if s in unreliable_sources)
        
        if unreliable_count > 0 and len(sources) > 0:
            ratio = unreliable_count / len(sources)
            if ratio > 0.5:
                doubts.append(Doubt(
                    description=f"{ratio:.0%} 的知识来源不可靠 ({unreliable_count}/{len(sources)})",
                    severity="major",
                    source="source_reliability_check"
                ))
                penalty += 0.15 * ratio
        
        if context and context.get('intent'):
            domain_mismatch = self._detect_domain_mismatch(content, context.get('intent', ''))
            if domain_mismatch:
                doubts.append(Doubt(
                    description=f"领域可能不匹配: {domain_mismatch}",
                    severity="major",
                    source="domain_check"
                ))
                penalty += 0.2
        
        most_likely_error = self._reverse_reasoning(content, context)
        if most_likely_error:
            doubts.append(Doubt(
                description=f"最可能的错误: {most_likely_error}",
                severity="critical",
                source="reverse_reasoning"
            ))
            penalty += 0.3
        
        penalty = min(penalty, 1.0)
        
        return {
            'doubts': doubts,
            'penalty': penalty
        }
    
    def _detect_contradictions(self, content: str, core_knowledge: List[Dict]) -> List[str]:
        """检测矛盾"""
        contradictions = []
        
        statements = []
        for item in core_knowledge:
            text = item.get('content', '')
            if text:
                statements.append(text)
        
        for i, s1 in enumerate(statements):
            for s2 in statements[i+1:]:
                words1 = set(s1.lower().split())
                words2 = set(s2.lower().split())
                common = words1 & words2
                
                if len(common) > 3:
                    neg1 = any(w in s1.lower() for w in ['不', '不是', '并非', '错误', 'not', 'no'])
                    neg2 = any(w in s2.lower() for w in ['不', '不是', '并非', '错误', 'not', 'no'])
                    
                    if neg1 != neg2:
                        contradictions.append(f"'{s1[:30]}...' 与 '{s2[:30]}...' 矛盾")
        
        return contradictions[:3]
    
    def _detect_domain_mismatch(self, content: str, intent: str) -> Optional[str]:
        """检测领域不匹配"""
        domains = {
            '芯片': ['芯片', 'IC', '半导体', '电路', '电子'],
            '电池': ['电池', '电芯', '储能', '充放电'],
            '软件': ['代码', '程序', '算法', '函数', '类'],
            '通用': ['通用', '一般', '常见']
        }
        
        detected_domains = []
        for domain, keywords in domains.items():
            if any(kw in content.lower() for kw in keywords):
                detected_domains.append(domain)
        
        if not detected_domains:
            return None
        
        if intent:
            intent_lower = intent.lower()
            matched = any(d.lower() in intent_lower for d in detected_domains)
            
            if not matched:
                return f"检测到领域 {detected_domains}，但意图是 {intent}"
        
        return None
    
    def _reverse_reasoning(self, content: str, context: Optional[Dict]) -> Optional[str]:
        """
        反向推演：如果我是错的，最可能错在哪里？
        
        这是L4的核心能力 - 主动质疑自己
        """
        possible_errors = []
        
        numbers = re.findall(r'\b\d+\.?\d*\b', content)
        if len(numbers) > 3:
            possible_errors.append("包含多个具体数值，可能存在计算或引用错误")
        
        if '推荐' in content or '建议' in content or 'recommend' in content.lower():
            possible_errors.append("推荐可能不匹配用户实际需求")
        
        tech_terms = ['IC', '芯片', '电池', '电路', '电压', '电流', '功率', 'API', '函数']
        if any(t in content for t in tech_terms):
            possible_errors.append("技术术语可能存在混淆或使用不当")
        
        if len(content) > 500:
            possible_errors.append("内容较长，可能存在逻辑遗漏或前后不一致")
        
        if '绝对' in content or '一定' in content or '肯定' in content:
            possible_errors.append("包含绝对化表述，可能过于武断")
        
        return possible_errors[0] if possible_errors else None
    
    def _evaluate_certainty(self, knowledge_graph: Dict, core_knowledge: List[Dict]) -> float:
        """评估确定性"""
        if not knowledge_graph:
            return 0.0
        
        certainties = []
        
        for node_id, node in knowledge_graph.items():
            node_confidence = getattr(node, 'confidence', 0.5)
            quality_score = getattr(node, 'quality_score', 50)
            
            certainty = node_confidence * (quality_score / 100)
            certainties.append(certainty)
        
        if core_knowledge:
            core_certainties = [k.get('confidence', 0.5) for k in core_knowledge]
            core_avg = sum(core_certainties) / len(core_certainties)
            certainties.append(core_avg * 1.2)
        
        return min(1.0, sum(certainties) / len(certainties)) if certainties else 0.0
    
    def _check_consistency(self, knowledge_graph: Dict) -> Tuple[float, List[str]]:
        """检查一致性"""
        issues = []
        
        if len(knowledge_graph) < 2:
            return 1.0, issues
        
        nodes = list(knowledge_graph.values())
        consistent_pairs = 0
        total_pairs = 0
        
        for i, node1 in enumerate(nodes):
            for j, node2 in enumerate(nodes):
                if i >= j:
                    continue
                
                total_pairs += 1
                
                conf1 = getattr(node1, 'confidence', 0.5)
                conf2 = getattr(node2, 'confidence', 0.5)
                
                if abs(conf1 - conf2) > 0.6:
                    issues.append(f"节点 {getattr(node1, 'id', 'unknown')} 与 {getattr(node2, 'id', 'unknown')} 置信度差异过大")
                else:
                    consistent_pairs += 1
        
        consistency_score = consistent_pairs / total_pairs if total_pairs > 0 else 1.0
        
        return consistency_score, issues
    
    def _evaluate_completeness(self, knowledge_graph: Dict, core_knowledge: List[Dict]) -> float:
        """评估完整性"""
        if not knowledge_graph:
            return 0.0
        
        total_nodes = len(knowledge_graph)
        core_ratio = len(core_knowledge) / total_nodes if total_nodes > 0 else 0
        
        nodes_with_content = sum(
            1 for node in knowledge_graph.values()
            if len(getattr(node, 'content', '')) > 50
        )
        content_ratio = nodes_with_content / total_nodes if total_nodes > 0 else 0
        
        nodes_with_keywords = sum(
            1 for node in knowledge_graph.values()
            if len(getattr(node, 'keywords', [])) > 0
        )
        keyword_ratio = nodes_with_keywords / total_nodes if total_nodes > 0 else 0
        
        completeness = (core_ratio * 0.4 + content_ratio * 0.4 + keyword_ratio * 0.2)
        
        return min(1.0, completeness)
    
    def _build_trust_chain(self, core_knowledge: List[Dict], 
                          knowledge_graph: Dict,
                          context: Optional[Dict]) -> List[TrustChainLink]:
        """构建信任链"""
        chain = []
        
        for item in core_knowledge[:5]:
            chain.append(TrustChainLink(
                source=item.get('source', 'unknown'),
                statement=f"知识来源: {item.get('source', '未知')} (置信度: {item.get('confidence', 0.5):.2f})",
                confidence=item.get('confidence', 0.5),
                timestamp=item.get('created_at', datetime.now().isoformat())
            ))
        
        if knowledge_graph:
            chain.append(TrustChainLink(
                source='L3_integration',
                statement=f"已整合 {len(knowledge_graph)} 个知识节点",
                confidence=0.8,
                timestamp=datetime.now().isoformat()
            ))
        
        chain.append(TrustChainLink(
            source='L4_validation',
            statement="已通过L4校验层自我质疑",
            confidence=0.75,
            timestamp=datetime.now().isoformat()
        ))
        
        return chain
    
    def trigger_fallback_to_l2(self, reason: str, context: Optional[Dict] = None) -> Dict:
        """触发L4→L2回退"""
        logger.warning(f"🔄 L4→L2回退触发: {reason}")
        
        fallback_event = {
            'timestamp': datetime.now().isoformat(),
            'reason': reason,
            'context': context or {},
            'status': 'triggered'
        }
        
        self.stats['total_fallbacks'] += 1
        
        self.reporter.report_warning(
            warnings=[f"回退触发: {reason}"],
            metrics={'fallback': 1}
        )
        
        return fallback_event
    
    def get_validation_status(self) -> Dict:
        """获取校验状态"""
        neighbor_status = self.heartbeat.get_neighbor_status("L4")
        
        return {
            "layer": "L4",
            "stats": self.stats,
            "neighbor_status": {
                k: v.value for k, v in neighbor_status.items()
            },
            "thresholds": self.thresholds,
            "avg_certainty": self.stats['avg_certainty'],
            "fail_rate": (
                self.stats['fail_count'] / max(self.stats['total_validations'], 1)
            ),
            "common_doubts": dict(sorted(
                self.stats['doubt_patterns'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5])
        }


_l4_instance = None

def get_l4_validation() -> L4ValidationLayer:
    global _l4_instance
    if _l4_instance is None:
        _l4_instance = L4ValidationLayer()
    return _l4_instance
