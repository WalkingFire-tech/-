"""
决策链记录系统
记录系统每一步思考过程，让系统从"黑盒"变成"透明盒子"
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
import json

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class DecisionStep:
    """决策步骤"""
    layer: str              # 认知层级 (L1-L5)
    layer_name: str         # 层级名称
    input_data: Any         # 输入
    output_data: Any        # 输出
    reasoning: str          # 推理过程
    confidence: float       # 置信度
    timestamp: str          # 时间戳
    metadata: Dict = field(default_factory=dict)  # 额外元数据


class DecisionChain:
    """
    决策链——记录系统每一步思考过程
    
    让系统能够回答"我是如何得出这个结论的"
    """
    
    def __init__(self):
        self.steps: List[DecisionStep] = []
        self.chain_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.created_at = datetime.now().isoformat()
        self.final_output: Optional[str] = None
        self.final_confidence: float = 0.0
    
    def add_step(
        self,
        layer: str,
        layer_name: str,
        input_data: Any,
        output_data: Any,
        reasoning: str,
        confidence: float = 1.0,
        metadata: Dict = None
    ) -> DecisionStep:
        """
        记录某个认知层级的决策过程
        
        Args:
            layer: 层级编号 (L1-L5)
            layer_name: 层级名称
            input_data: 该层的输入
            output_data: 该层的输出
            reasoning: 推理过程描述
            confidence: 置信度 (0-1)
            metadata: 额外信息
        
        Returns:
            决策步骤对象
        """
        step = DecisionStep(
            layer=layer,
            layer_name=layer_name,
            input_data=self._serialize(input_data),
            output_data=self._serialize(output_data),
            reasoning=reasoning,
            confidence=confidence,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        self.steps.append(step)
        logger.debug(f"📝 决策步骤已记录: {layer} - {layer_name}")
        
        return step
    
    def _serialize(self, data: Any) -> Any:
        """序列化数据（处理不可JSON化的对象）"""
        if data is None:
            return None
        if isinstance(data, (str, int, float, bool, list, dict)):
            return data
        if hasattr(data, '__dict__'):
            return str(data)
        return str(data)
    
    def set_final_output(self, output: str, confidence: float):
        """设置最终输出"""
        self.final_output = output
        self.final_confidence = confidence
    
    def visualize(self, detailed: bool = False) -> str:
        """
        生成可读的决策链文本
        
        Args:
            detailed: 是否显示详细信息
        
        Returns:
            可读的决策链文本
        """
        lines = []
        lines.append("=" * 70)
        lines.append(f"  决策链 #{self.chain_id}")
        lines.append(f"  创建时间: {self.created_at}")
        lines.append("=" * 70)
        
        for i, step in enumerate(self.steps, 1):
            lines.append(f"\n【步骤{i}】{step.layer} - {step.layer_name}")
            lines.append(f"  时间: {step.timestamp}")
            lines.append(f"  置信度: {step.confidence:.2f}")
            
            if detailed:
                lines.append(f"  输入: {self._truncate(str(step.input_data), 100)}")
                lines.append(f"  输出: {self._truncate(str(step.output_data), 100)}")
            
            lines.append(f"  推理: {step.reasoning}")
            
            if step.metadata and detailed:
                lines.append(f"  元数据: {json.dumps(step.metadata, ensure_ascii=False)[:200]}")
        
        if self.final_output:
            lines.append("\n" + "=" * 70)
            lines.append(f"  最终输出: {self._truncate(self.final_output, 200)}")
            lines.append(f"  最终置信度: {self.final_confidence:.2f}")
            lines.append("=" * 70)
        
        return "\n".join(lines)
    
    def _truncate(self, text: str, max_len: int) -> str:
        """截断文本"""
        if len(text) <= max_len:
            return text
        return text[:max_len] + "..."
    
    def to_dict(self) -> Dict:
        """转换为字典（用于存储）"""
        return {
            'chain_id': self.chain_id,
            'created_at': self.created_at,
            'steps': [
                {
                    'layer': step.layer,
                    'layer_name': step.layer_name,
                    'input': step.input_data,
                    'output': step.output_data,
                    'reasoning': step.reasoning,
                    'confidence': step.confidence,
                    'timestamp': step.timestamp,
                    'metadata': step.metadata
                }
                for step in self.steps
            ],
            'final_output': self.final_output,
            'final_confidence': self.final_confidence
        }
    
    def get_layer_outputs(self) -> Dict[str, Any]:
        """获取各层级的输出"""
        return {
            step.layer: step.output_data
            for step in self.steps
        }
    
    def get_confidence_trajectory(self) -> List[float]:
        """获取置信度轨迹"""
        return [step.confidence for step in self.steps]


class DecisionChainManager:
    """
    决策链管理器
    管理历史决策链，支持查询和统计
    """
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.history: List[DecisionChain] = []
        self.current_chain: Optional[DecisionChain] = None
    
    def start_new_chain(self) -> DecisionChain:
        """开始新的决策链"""
        self.current_chain = DecisionChain()
        return self.current_chain
    
    def complete_chain(self):
        """完成当前决策链，加入历史"""
        if self.current_chain:
            self.history.append(self.current_chain)
            
            # 保持历史长度限制
            if len(self.history) > self.max_history:
                self.history = self.history[-self.max_history:]
            
            logger.info(f"✅ 决策链已完成: #{self.current_chain.chain_id}")
    
    def get_last_chain(self) -> Optional[DecisionChain]:
        """获取最近的决策链"""
        if self.history:
            return self.history[-1]
        return None
    
    def get_chain_by_id(self, chain_id: str) -> Optional[DecisionChain]:
        """根据ID获取决策链"""
        for chain in self.history:
            if chain.chain_id == chain_id:
                return chain
        return None
    
    def get_statistics(self) -> Dict:
        """获取决策链统计"""
        if not self.history:
            return {
                'total_chains': 0,
                'avg_steps': 0,
                'avg_confidence': 0
            }
        
        total_steps = sum(len(chain.steps) for chain in self.history)
        avg_confidence = sum(
            chain.final_confidence 
            for chain in self.history 
            if chain.final_confidence > 0
        ) / max(1, len([c for c in self.history if c.final_confidence > 0]))
        
        return {
            'total_chains': len(self.history),
            'total_steps': total_steps,
            'avg_steps': total_steps / len(self.history),
            'avg_confidence': avg_confidence
        }


decision_chain_manager = DecisionChainManager()