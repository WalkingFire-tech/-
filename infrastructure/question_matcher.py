"""
智能问题匹配器
将用户问题转换为可能的知识查询格式
"""
import re
from typing import List

class QuestionMatcher:
    """问题格式转换器"""
    
    @staticmethod
    def normalize_question(question: str) -> List[str]:
        """
        将问题转换为多种可能的查询格式
        
        Args:
            question: 用户原始问题
            
        Returns:
            可能的查询格式列表
        """
        question = question.strip()
        variants = [question]  # 原始问题
        
        # 提取核心概念
        # "什么是机器学习?" -> "机器学习"
        # "机器学习是什么?" -> "机器学习"
        concept_match = re.search(r'什么(?:是|叫)?(.+?)[\?？]?$', question)
        if concept_match:
            concept = concept_match.group(1).strip()
            if len(concept) > 1:  # 确保概念有实际内容
                variants.append(f"{concept}的定义")
                variants.append(f"{concept}是什么")
                variants.append(f"什么是{concept}")
                variants.append(concept)
        
        # "机器学习是什么?" -> 提取概念
        is_match = re.search(r'(.+?)是(?:什么|啥)[\?？]?$', question)
        if is_match:
            concept = is_match.group(1).strip()
            if len(concept) > 1:
                variants.append(f"什么是{concept}")
                variants.append(f"{concept}的定义")
                variants.append(concept)
        
        # "机器学习的定义" -> "机器学习"
        definition_match = re.search(r'(.+?)的(?:定义|意思|含义)', question)
        if definition_match:
            concept = definition_match.group(1).strip()
            if len(concept) > 1:
                variants.append(f"什么是{concept}")
                variants.append(f"{concept}是什么")
                variants.append(concept)
        
        # "Python什么时候发布的?" -> "Python的发布时间"
        when_match = re.search(r'(.+?)(?:什么时候|何时)(.+?)[\?？]?$', question)
        if when_match:
            concept = when_match.group(1).strip()
            action = when_match.group(2).strip() if when_match.group(2) else "发布"
            if len(concept) > 1:
                variants.append(f"{concept}的{action}时间")
                variants.append(f"{concept}什么时候{action}")
        
        # 去重
        unique_variants = []
        for v in variants:
            if v not in unique_variants:
                unique_variants.append(v)
        
        return unique_variants
    
    @staticmethod
    def extract_keywords(question: str) -> List[str]:
        """提取问题中的关键词"""
        # 移除常见疑问词
        stop_words = ['什么', '是', '叫', '的', '吗', '呢', '？', '?', '如何', '怎么', '为什么', '哪', '谁', '何时', '多少']
        
        cleaned = question
        for word in stop_words:
            cleaned = cleaned.replace(word, ' ')
        
        # 分词（简单空格分割）
        keywords = [k.strip() for k in cleaned.split() if k.strip() and len(k.strip()) > 1]
        
        return keywords


if __name__ == "__main__":
    matcher = QuestionMatcher()
    
    test_questions = [
        "什么是机器学习?",
        "机器学习是什么?",
        "机器学习的定义",
        "Python什么时候发布的?",
        "监督学习的特点",
    ]
    
    for q in test_questions:
        variants = matcher.normalize_question(q)
        print(f"\n问题: {q}")
        print(f"变体: {variants}")