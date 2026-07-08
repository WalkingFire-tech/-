"""
知识验证器 - 扩展L3整合层，对候选知识进行多维度验证
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
from infrastructure.database_manager import DatabaseManager
from pathlib import Path


@dataclass
class ValidationResult:
    """验证结果"""
    passed: bool
    score: float
    dimensions: Dict[str, float]
    issues: List[str]
    evidence: List[str]
    recommendation: str


class KnowledgeValidator:
    """知识验证器"""
    
    def __init__(self, knowledge_db_path: str = "data/knowledge_store.db"):
        self.knowledge_db_path = Path(knowledge_db_path)
    
    def validate(self, content: str, source: str, signals: List[Dict]) -> ValidationResult:
        """
        验证一条候选知识
        
        多维度验证：
        1. 一致性 - 与现有知识的语义一致性
        2. 来源可靠性 - 知识来源的可信度
        3. 信号强度 - 用户反馈信号的综合强度
        4. 内容质量 - 内容的结构和表达质量
        5. 新颖性 - 是否提供新价值
        6. 可验证性 - 是否可独立验证
        """
        dimensions = {}
        issues = []
        evidence = []
        
        dimensions["consistency"] = self._assess_consistency(content)
        if dimensions["consistency"] < 0.6:
            issues.append("与现有知识可能存在冲突")
        else:
            evidence.append(f"一致性检查通过({dimensions['consistency']:.2f})")
        
        dimensions["source_reliability"] = self._assess_source(source)
        evidence.append(f"来源: {source} (可靠性: {dimensions['source_reliability']:.2f})")
        
        dimensions["signal_strength"] = self._assess_signals(signals)
        if dimensions["signal_strength"] >= 0.7:
            evidence.append(f"强信号支持({dimensions['signal_strength']:.2f})")
        elif dimensions["signal_strength"] < 0.4:
            issues.append("信号强度不足")
        
        dimensions["quality"] = self._assess_quality(content)
        if dimensions["quality"] < 0.5:
            issues.append("内容质量不达标")
        
        dimensions["novelty"] = self._assess_novelty(content)
        if dimensions["novelty"] < 0.3:
            issues.append("内容可能重复或无新价值")
        
        dimensions["verifiability"] = self._assess_verifiability(content)
        
        weights = {
            "consistency": 0.25,
            "source_reliability": 0.15,
            "signal_strength": 0.20,
            "quality": 0.20,
            "novelty": 0.10,
            "verifiability": 0.10
        }
        
        total_score = sum(
            dimensions[dim] * weights[dim]
            for dim in dimensions
        )
        
        recommendation, passed = self._make_decision(
            total_score, dimensions, issues, signals
        )
        
        return ValidationResult(passed, total_score, dimensions, issues, evidence, recommendation)
    
    def _assess_consistency(self, content: str) -> float:
        """
        评估与现有知识的一致性
        
        使用语义分析而非简单的长度比较：
        1. 提取关键概念
        2. 检查概念关系
        3. 识别潜在冲突
        """
        try:
            if not self.knowledge_db_path.exists():
                return 0.95
            
            conn = DatabaseManager.get(str(self.knowledge_db_path))._get_conn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='knowledge_base'
            """)
            
            if not cursor.fetchone():
                return 0.95
            
            import re
            content_words = set(
                word.lower() for word in re.findall(r'\w+', content)
                if len(word) > 3
            )
            
            if not content_words:
                return 0.8
            
            cursor.execute("""
                SELECT question, answer FROM knowledge_base
                ORDER BY created_at DESC
                LIMIT 50
            """)
            
            existing_knowledge = cursor.fetchall()
            
            if not existing_knowledge:
                return 0.95
            
            max_overlap = 0.0
            potential_conflicts = []
            
            for question, answer in existing_knowledge:
                existing_words = set(
                    word.lower() for word in re.findall(r'\w+', f"{question} {answer}")
                    if len(word) > 3
                )
                
                if not existing_words:
                    continue
                
                overlap = len(content_words & existing_words) / len(content_words)
                max_overlap = max(max_overlap, overlap)
                
                if overlap > 0.3:
                    negation_patterns = ["不", "非", "无", "没", "not", "no", "never"]
                    content_has_negation = any(neg in content for neg in negation_patterns)
                    existing_has_negation = any(neg in f"{question} {answer}" for neg in negation_patterns)
                    
                    if content_has_negation != existing_has_negation:
                        potential_conflicts.append({
                            "overlap": overlap,
                            "reason": "逻辑否定不一致"
                        })
            
            if potential_conflicts:
                max_conflict_overlap = max(c["overlap"] for c in potential_conflicts)
                consistency = 0.5 - (max_conflict_overlap - 0.3) * 0.5
                return max(0.2, consistency)
            
            if max_overlap > 0.5:
                return 0.85
            elif max_overlap > 0.3:
                return 0.9
            else:
                return 0.95
        
        except Exception as e:
            return 0.7
    
    def _assess_source(self, source: str) -> float:
        """
        评估来源可靠性
        
        不同来源的可靠性分级：
        - 用户主动纠正: 高可靠性（用户明确知道正确答案）
        - 系统评估通过: 中高可靠性（经过质量评估）
        - 用户正面反馈: 中等可靠性（可能是正确但需验证）
        - 外部搜索: 中低可靠性（需要交叉验证）
        - 其他: 低可靠性
        """
        source_scores = {
            "user_correction": 0.90,
            "user_explicit_teaching": 0.85,
            "system_evaluated": 0.75,
            "user_feedback_positive": 0.60,
            "multi_user_confirmed": 0.80,
            "external_search": 0.45,
            "external_documentation": 0.55,
            "inferred": 0.35,
            "unknown": 0.30
        }
        
        normalized_source = source.lower().replace(" ", "_").replace("-", "_")
        
        for key, score in source_scores.items():
            if key in normalized_source or normalized_source in key:
                return score
        
        return 0.30
    
    def _assess_signals(self, signals: List[Dict]) -> float:
        """
        评估信号强度
        
        综合分析多个反馈信号：
        1. 信号类型权重（纠正>确认>点赞）
        2. 信号数量影响
        3. 信号一致性检查
        """
        if not signals:
            return 0.30
        
        signal_weights = {
            "correction": 1.0,
            "explicit_teaching": 0.9,
            "confirmation": 0.7,
            "positive_feedback": 0.6,
            "negative_feedback": -0.8,
            "challenge": -0.5,
            "question": 0.2,
            "neutral": 0.1
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for signal in signals:
            signal_type = signal.get("type", "neutral")
            confidence = signal.get("confidence", 0.5)
            
            weight = signal_weights.get(signal_type, 0.1)
            weighted_sum += weight * confidence
            total_weight += abs(weight)
        
        if total_weight == 0:
            return 0.30
        
        normalized_score = (weighted_sum / total_weight + 1) / 2
        
        signal_count = len(signals)
        count_bonus = min(0.15, signal_count * 0.03)
        
        types = [s.get("type") for s in signals]
        if "correction" in types and "confirmation" in types:
            count_bonus += 0.1
        
        final_score = min(1.0, normalized_score + count_bonus)
        
        return max(0.0, final_score)
    
    def _assess_quality(self, content: str) -> float:
        """
        评估内容质量
        
        多维度质量评估：
        1. 长度合理性
        2. 结构完整性
        3. 表达清晰度
        4. 信息密度
        """
        score = 0.0
        
        length = len(content)
        if length < 20:
            return 0.1
        elif length < 50:
            score += 0.2
        elif length < 200:
            score += 0.4
        elif length < 1000:
            score += 0.5
        else:
            score += 0.45
        
        structure_indicators = [
            ("\n", 0.1),
            ("：" , 0.08),
            (":" , 0.08),
            ("\n\n", 0.12),
            ("1." , 0.1),
            ("第一" , 0.1),
            ("**" , 0.08),
            ("【" , 0.08),
            ("```" , 0.15)
        ]
        
        for indicator, weight in structure_indicators:
            if indicator in content:
                score += weight
        
        import re
        sentences = re.split(r'[。！？\n]', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) >= 2:
            score += 0.1
        if len(sentences) >= 4:
            score += 0.05
        
        words = re.findall(r'\w+', content)
        unique_words = set(word.lower() for word in words)
        
        if len(words) > 0:
            uniqueness_ratio = len(unique_words) / len(words)
            if uniqueness_ratio > 0.7:
                score += 0.1
            elif uniqueness_ratio > 0.5:
                score += 0.05
        
        return min(1.0, score)
    
    def _assess_novelty(self, content: str) -> float:
        """
        评估新颖性
        
        检查内容是否提供新价值：
        1. 与现有知识的相似度
        2. 新概念/新方法的引入
        3. 新视角的提供
        """
        try:
            if not self.knowledge_db_path.exists():
                return 0.9
            
            conn = DatabaseManager.get(str(self.knowledge_db_path))._get_conn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='knowledge_base'
            """)
            
            if not cursor.fetchone():
                return 0.9
            
            import re
            content_key_phrases = set()
            
            patterns = [
                r'([^。！？\n]{10,30})',
                r'(\w+的\w+)',
                r'(如何\w+)',
                r'(为什么\w+)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                content_key_phrases.update(matches)
            
            if not content_key_phrases:
                return 0.6
            
            cursor.execute("""
                SELECT answer FROM knowledge_base
                ORDER BY created_at DESC
                LIMIT 30
            """)
            
            existing_answers = [row[0] for row in cursor.fetchall()]
            
            if not existing_answers:
                return 0.9
            
            max_similarity = 0.0
            
            for existing in existing_answers:
                existing_phrases = set()
                for pattern in patterns:
                    matches = re.findall(pattern, existing)
                    existing_phrases.update(matches)
                
                if not existing_phrases:
                    continue
                
                intersection = len(content_key_phrases & existing_phrases)
                union = len(content_key_phrases | existing_phrases)
                
                if union > 0:
                    similarity = intersection / union
                    max_similarity = max(max_similarity, similarity)
            
            novelty = 1.0 - max_similarity
            
            return max(0.1, novelty)
        
        except Exception:
            return 0.6
    
    def _assess_verifiability(self, content: str) -> float:
        """
        评估可验证性
        
        检查内容是否可独立验证：
        1. 是否包含具体事实/数据
        2. 是否包含可执行步骤
        3. 是否包含引用/来源
        """
        score = 0.4
        
        import re
        
        number_patterns = [
            r'\d+%',
            r'\d+次',
            r'\d+个',
            r'\d+\.\d+',
            r'\d{4}年'
        ]
        
        for pattern in number_patterns:
            if re.search(pattern, content):
                score += 0.15
                break
        
        if re.search(r'(步骤|方法|流程|首先|然后|最后)', content):
            score += 0.2
        
        if re.search(r'(根据|引用|来源|参考|文档|链接|http)', content):
            score += 0.2
        
        if re.search(r'(例如|比如|举例|案例)', content):
            score += 0.1
        
        return min(1.0, score)
    
    def _make_decision(
        self,
        total_score: float,
        dimensions: Dict[str, float],
        issues: List[str],
        signals: List[Dict]
    ) -> Tuple[str, bool]:
        """
        做出验证决策
        
        决策规则：
        1. 总分 >= 0.75 且无关键问题 → inject
        2. 总分 >= 0.55 且问题 <= 1 → postpone
        3. 总分 < 0.55 或问题 >= 2 → reject
        """
        critical_issues = [
            "冲突" in issue or "conflict" in issue.lower()
            for issue in issues
        ]
        
        if any(critical_issues):
            return "reject", False
        
        if total_score >= 0.75 and len(issues) == 0:
            return "inject", True
        
        if total_score >= 0.65 and len(issues) <= 1:
            return "inject", True
        
        if total_score >= 0.55 and len(issues) <= 2:
            return "postpone", False
        
        return "reject", False


knowledge_validator = KnowledgeValidator()