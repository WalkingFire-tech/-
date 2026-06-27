"""
知识检测与验证模块

提供语义驱动的知识缺失检测和推荐验证能力
"""
from core.knowledge.detector import SemanticGapDetector, semantic_detector
from core.knowledge.validator import KnowledgeBasedValidator, knowledge_validator
from core.knowledge.learner import DomainKnowledgeLearner, domain_learner

__all__ = [
    'SemanticGapDetector',
    'semantic_detector',
    'KnowledgeBasedValidator',
    'knowledge_validator',
    'DomainKnowledgeLearner',
    'domain_learner'
]