"""
统一Intent数据类
整合IntentParser和AutoIntentParser的Intent定义
"""
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List


@dataclass
class Intent:
    """统一意图数据类"""
    type: str
    raw_text: str
    entities: Dict
    confidence: float = 1.0
    source: str = "rule"
    reasoning: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        result = asdict(self)
        return result
    
    def is_reliable(self) -> bool:
        """判断是否可靠"""
        return self.confidence >= 0.7 and self.source != "fallback"
    
    def __str__(self) -> str:
        return f"Intent(type={self.type}, confidence={self.confidence:.2f}, source={self.source})"