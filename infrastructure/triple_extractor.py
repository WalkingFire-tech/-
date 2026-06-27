"""
三元组提取器
从文本中提取 (subject, predicate, object) 三元组

设计原则：
- 从"核心动词+核心宾语"开始
- 不追求全覆盖，只提取关键因果断言
- 避免太粗（失去鉴别力）或太细（无法匹配）
"""
import re
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass

try:
    import jieba
    import jieba.posseg as pseg
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False


@dataclass
class Triple:
    """三元组数据结构"""
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0
    source: str = "extracted"


class TripleExtractor:
    """
    三元组提取器
    
    使用规则+轻量NLP提取关键断言
    """
    
    def __init__(self):
        # 关键谓语模式（优先级高）
        self.key_predicates = [
            "形成", "产生", "导致", "引起", "造成",
            "是", "等于", "约为", "称为", "叫做",
            "发生在", "位于", "属于",
            "冻结", "融化", "蒸发", "凝结", "凝华", "升华",
            "上升", "下降", "增加", "减少", "升高", "降低",
            "转化为", "变成", "变为"
        ]
        
        # 科学/技术领域关键词
        self.domain_keywords = [
            "冰雹", "冰晶", "水蒸气", "过冷水", "上升气流",
            "温度", "气压", "湿度", "高度",
            "形成", "冻结", "融化", "凝华", "凝结",
            "云层", "积雨云", "对流云",
            "物理", "化学", "生物", "数学", "历史"
        ]
        
        # 否定词
        self.negation_words = ["不", "非", "无", "没", "未", "不是", "不会", "不能"]
        
        # 初始化jieba（如果可用）
        if JIEBA_AVAILABLE:
            for kw in self.domain_keywords:
                jieba.add_word(kw)
    
    def extract(self, text: str) -> List[Triple]:
        """
        从文本中提取三元组
        
        Args:
            text: 输入文本
        
        Returns:
            三元组列表
        """
        triples = []
        
        # 方法1: 规则提取（优先）
        rule_triples = self._extract_by_rules(text)
        triples.extend(rule_triples)
        
        # 方法2: NLP提取（如果jieba可用）
        if JIEBA_AVAILABLE:
            nlp_triples = self._extract_by_nlp(text)
            triples.extend(nlp_triples)
        
        # 去重
        unique_triples = self._deduplicate(triples)
        
        return unique_triples
    
    def _extract_by_rules(self, text: str) -> List[Triple]:
        """基于规则的三元组提取"""
        triples = []
        
        # 规则1: "X是Y" / "X称为Y" / "X叫做Y"
        pattern1 = r'([^，。！？\s]{2,10})(是|称为|叫做|等于|约为)([^，。！？\s]{2,20})'
        for match in re.finditer(pattern1, text):
            subj, pred, obj = match.groups()
            if self._is_valid_triple(subj, pred, obj):
                triples.append(Triple(subj, pred, obj, confidence=0.8))
        
        # 规则2: "X形成Y" / "X导致Y" / "X产生Y"
        pattern2 = r'([^，。！？\s]{2,10})(形成|产生|导致|引起|造成)([^，。！？\s]{2,20})'
        for match in re.finditer(pattern2, text):
            subj, pred, obj = match.groups()
            if self._is_valid_triple(subj, pred, obj):
                triples.append(Triple(subj, pred, obj, confidence=0.85))
        
        # 规则3: "X发生在Y" / "X位于Y"
        pattern3 = r'([^，。！？\s]{2,10})(发生在|位于|属于)([^，。！？\s]{2,20})'
        for match in re.finditer(pattern3, text):
            subj, pred, obj = match.groups()
            if self._is_valid_triple(subj, pred, obj):
                triples.append(Triple(subj, pred, obj, confidence=0.8))
        
        # 规则4: 物理过程 "X冻结" / "X融化" / "X凝华"
        pattern4 = r'([^，。！？\s]{2,10})(冻结|融化|凝华|升华|蒸发|凝结)'
        for match in re.finditer(pattern4, text):
            subj, pred = match.groups()
            if len(subj) >= 2:
                triples.append(Triple(subj, pred, "发生", confidence=0.75))
        
        # 规则5: 温度/数值 "温度X度" / "高度X米"
        pattern5 = r'(温度|高度|速度|气压|湿度)([^，。！？\s]{1,15})(升高|降低|增加|减少|上升|下降)'
        for match in re.finditer(pattern5, text):
            subj, mid, pred = match.groups()
            obj = "变化"
            triples.append(Triple(subj + mid, pred, obj, confidence=0.7))
        
        return triples
    
    def _extract_by_nlp(self, text: str) -> List[Triple]:
        """基于NLP的三元组提取（jieba）"""
        triples = []
        
        try:
            words = pseg.cut(text)
            word_list = [(w, f) for w, f in words]
            
            # 查找名词-动词-名词结构
            for i in range(len(word_list) - 2):
                w1, f1 = word_list[i]
                w2, f2 = word_list[i + 1]
                w3, f3 = word_list[i + 2]
                
                # n-v-n 结构
                if f1.startswith('n') and f2.startswith('v') and f3.startswith('n'):
                    if w2 in self.key_predicates:
                        triples.append(Triple(w1, w2, w3, confidence=0.7))
                
                # n-v 结构（不及物动词）
                elif f1.startswith('n') and f2 in self.key_predicates:
                    if len(w1) >= 2:
                        triples.append(Triple(w1, w2, "发生", confidence=0.65))
        
        except Exception:
            pass
        
        return triples
    
    def _is_valid_triple(self, subject: str, predicate: str, obj: str) -> bool:
        """验证三元组是否有效"""
        # 过滤太短或太长的成分
        if len(subject) < 2 or len(subject) > 15:
            return False
        if len(predicate) < 1 or len(predicate) > 10:
            return False
        if len(obj) < 2 or len(obj) > 30:
            return False
        
        # 过滤纯数字或标点
        if subject.isdigit() or obj.isdigit():
            return False
        
        return True
    
    def _deduplicate(self, triples: List[Triple]) -> List[Triple]:
        """去重"""
        seen = set()
        unique = []
        for t in triples:
            key = (t.subject, t.predicate, t.object)
            if key not in seen:
                seen.add(key)
                unique.append(t)
        return unique
    
    def calculate_overlap(
        self,
        extracted_triples: List[Triple],
        ground_truth: List[Dict]
    ) -> float:
        """
        计算提取的三元组与真值的重叠度
        
        Args:
            extracted_triples: 提取的三元组
            ground_truth: 真值断言列表
        
        Returns:
            匹配率 (0.0 - 1.0)
        """
        if not ground_truth:
            return 0.5  # 无真值时返回中性分
        
        if not extracted_triples:
            return 0.0  # 有真值但提取失败
        
        matches = 0
        for gt in ground_truth:
            gt_subj = gt.get('subject', '')
            gt_pred = gt.get('predicate', '')
            gt_obj = gt.get('object', '')
            
            for ext in extracted_triples:
                # 完全匹配
                if ext.subject == gt_subj and ext.predicate == gt_pred and ext.object == gt_obj:
                    matches += 1
                    break
                
                # 部分匹配（主体和谓语匹配）
                elif ext.subject == gt_subj and ext.predicate == gt_pred:
                    if gt_obj in ext.object or ext.object in gt_obj:
                        matches += 0.7
                        break
                
                # 语义近似匹配
                elif self._semantic_match(ext.subject, gt_subj) and self._semantic_match(ext.predicate, gt_pred):
                    matches += 0.5
                    break
        
        # 计算匹配率
        match_rate = matches / len(ground_truth)
        return min(1.0, match_rate)
    
    def _semantic_match(self, text1: str, text2: str) -> bool:
        """简单的语义匹配"""
        if text1 == text2:
            return True
        if text1 in text2 or text2 in text1:
            return True
        return False
    
    def check_negation_match(
        self,
        extracted_triples: List[Triple],
        negations: List[Dict]
    ) -> bool:
        """
        检查是否匹配到否定断言（错误示例）
        
        Returns:
            True if matches a negation (indicates error)
        """
        for neg in negations:
            neg_subj = neg.get('subject', '')
            neg_pred = neg.get('predicate', '')
            neg_obj = neg.get('object', '')
            
            for ext in extracted_triples:
                if ext.subject == neg_subj and ext.predicate == neg_pred and ext.object == neg_obj:
                    return True
        
        return False


triple_extractor = TripleExtractor()