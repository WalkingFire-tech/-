"""
外部学习器接口规范
支持多种知识来源的统一接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class KnowledgeItem:
    """外部学习返回的知识条目"""
    content: str
    source: str
    confidence: float
    metadata: Dict = field(default_factory=dict)


class ExternalLearnerBase(ABC):
    """
    外部学习器抽象基类
    所有具体的知识源必须实现此接口
    """
    
    @abstractmethod
    def learn(
        self,
        query: str,
        context: Optional[str] = None,
        max_results: int = 5
    ) -> List[KnowledgeItem]:
        """
        根据查询从外部获取知识
        
        Args:
            query: 搜索/提问的关键词或完整问题
            context: 可选的上下文信息
            max_results: 最多返回多少条知识
        
        Returns:
            知识条目列表，按相关性降序排列
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查该学习器当前是否可用"""
        pass
    
    @abstractmethod
    def get_cost_estimate(self, query: str) -> float:
        """预估本次学习的成本（用于配额控制）"""
        pass
    
    def get_name(self) -> str:
        """获取学习器名称"""
        return self.__class__.__name__