"""
CBNR核心枢纽 - 三层集成

将L1认知规范化、L2认知瓶颈、L3认知残差整合为统一的处理管道。
所有认知活动都经过 L1→L2→L3 的标准化处理流程。

核心问句驱动：
- L1: "我是否已重置到正确的基准状态？"
- L2: "这个问题的本质是什么？我可以安全地忽略什么？"
- L3: "这个问题与我处理过的哪些问题相似？我能在旧方案上只调整差异？"
"""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from core.cbnr.cognitive_normalization import CognitiveNormalization, NormalizationResult
from core.cbnr.cognitive_bottleneck import CognitiveBottleneck, BottleneckResult, ConflictMode
from core.cbnr.cognitive_residual import CognitiveResidual, ResidualResult


@dataclass
class CBNRResult:
    l1_normalization: Optional[NormalizationResult] = None
    l2_bottleneck: Optional[BottleneckResult] = None
    l3_residual: Optional[ResidualResult] = None
    final_output: Dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    questions_asked: Dict[str, str] = field(default_factory=dict)


class CBNRHub:
    """
    CBNR核心枢纽
    
    统一的处理管道：
    输入 → L1认知规范化 → L2认知瓶颈 → L3认知残差 → 输出
    
    每一层都有明确的关键问句，让系统的思考过程变得可追踪、可调试。
    """

    def __init__(self):
        self._l1 = CognitiveNormalization()
        self._l2 = CognitiveBottleneck()
        self._l3 = CognitiveResidual()
        self._process_count = 0
        self._total_time = 0.0
        self._last_l1_result: Optional[NormalizationResult] = None
        self._last_l2_result: Optional[BottleneckResult] = None
        self._last_l3_result: Optional[ResidualResult] = None

    def process(self, input_stream: Dict[str, Any], context: Dict[str, Any] = None) -> CBNRResult:
        start = time.time()
        context = context or {}
        self._process_count += 1
        
        result = CBNRResult()
        
        result.questions_asked = {
            "L1": "我是否已重置到正确的基准状态？",
            "L2": "这个问题的本质是什么？我可以安全地忽略什么？",
            "L3": "这个问题与我处理过的哪些问题相似？我能在旧方案上只调整差异？",
        }
        
        try:
            l1_result = self._l1.normalize(input_stream, context)
            result.l1_normalization = l1_result
            normalized = l1_result.normalized_input
        except Exception as e:
            logger.warning(f"CBNR L1失败: {e}")
            normalized = dict(input_stream)
        
        try:
            l2_result = self._l2.process(normalized)
            result.l2_bottleneck = l2_result
            bottleneck_output = l2_result.reconstructed_output
        except Exception as e:
            logger.warning(f"CBNR L2失败: {e}")
            bottleneck_output = dict(normalized)
        
        try:
            l3_result = self._l3.process(normalized, bottleneck_output)
            result.l3_residual = l3_result
            final = l3_result.new_state
        except Exception as e:
            logger.warning(f"CBNR L3失败: {e}")
            final = dict(bottleneck_output)
            final["_fallback_used"] = True
        
        result.final_output = self._build_final_output(result, input_stream)
        
        elapsed = (time.time() - start) * 1000
        result.processing_time_ms = elapsed
        self._total_time += elapsed
        
        l1_unc = result.l1_normalization.uncertainty if result.l1_normalization else 0
        l2_delta = result.l2_bottleneck.conflict_delta if result.l2_bottleneck else 0
        l3_reuse = result.l3_residual.state_reuse_rate if result.l3_residual else 0
        logger.info(f"CBNR处理完成: {elapsed:.1f}ms, 不确定性={l1_unc:.2f}, 冲突ΔF={l2_delta:.2f}, 复用率={l3_reuse:.1%}")
        
        try:
            from infrastructure.ratchet_gate import guard_change
            cbnr_quality = 1.0 - l1_unc * 0.3 + (1.0 - min(l2_delta, 1.0)) * 0.3 + l3_reuse * 0.4
            guard_change("cbnr", cbnr_quality, f"CBNR#{self._process_count} unc={l1_unc:.2f} ΔF={l2_delta:.2f} reuse={l3_reuse:.1%}")
        except Exception:
            logger.warning("操作降级跳过")
        
        return result

    def process_l1(self, input_stream: Dict[str, Any], context: Dict[str, Any] = None) -> NormalizationResult:
        """分散调用：仅执行L1，返回normalized_input供后续使用"""
        context = context or {}
        try:
            self._last_l1_result = self._l1.normalize(input_stream, context)
        except Exception as e:
            logger.warning(f"CBNR L1失败: {e}")
            from core.cbnr.cognitive_normalization import NormalizationResult
            self._last_l1_result = NormalizationResult(
                input_hash="", uncertainty=0.5, normalization_strength=0.5,
                normalized_input=dict(input_stream), timestamp=time.time()
            )
        return self._last_l1_result

    def process_l2(self, normalized_input: Dict[str, Any]) -> BottleneckResult:
        """分散调用：仅执行L2，接收L1的normalized_input"""
        try:
            self._last_l2_result = self._l2.process(normalized_input)
        except Exception as e:
            logger.warning(f"CBNR L2失败: {e}")
            from core.cbnr.cognitive_bottleneck import BottleneckResult, ConflictMode
            self._last_l2_result = BottleneckResult(
                core_essence={}, conflict_mode=ConflictMode.INTERFERENCE,
                reconstructed_output=dict(normalized_input), timestamp=time.time()
            )
        return self._last_l2_result

    def process_l3(self, normalized_input: Dict[str, Any], bottleneck_output: Dict[str, Any]) -> ResidualResult:
        """分散调用：仅执行L3，接收L1 normalized + L2 bottleneck输出"""
        try:
            self._last_l3_result = self._l3.process(normalized_input, bottleneck_output)
        except Exception as e:
            logger.warning(f"CBNR L3失败: {e}")
            from core.cbnr.cognitive_residual import ResidualResult
            self._last_l3_result = ResidualResult(
                new_state=dict(bottleneck_output), fallback_used=True, timestamp=time.time()
            )
        return self._last_l3_result

    def finalize_distributed(self) -> Dict[str, Any]:
        """分散调用完成后：汇总统计、触发棘轮门控、返回最终输出"""
        self._process_count += 1
        
        l1_unc = self._last_l1_result.uncertainty if self._last_l1_result else 0
        l2_delta = self._last_l2_result.conflict_delta if self._last_l2_result else 0
        l3_reuse = self._last_l3_result.state_reuse_rate if self._last_l3_result else 0
        
        logger.info(f"CBNR分散处理完成: 不确定性={l1_unc:.2f}, 冲突ΔF={l2_delta:.2f}, 复用率={l3_reuse:.1%}")
        
        try:
            from infrastructure.ratchet_gate import guard_change
            cbnr_quality = 1.0 - l1_unc * 0.3 + (1.0 - min(l2_delta, 1.0)) * 0.3 + l3_reuse * 0.4
            guard_change("cbnr", cbnr_quality, f"CBNR#{self._process_count} unc={l1_unc:.2f} ΔF={l2_delta:.2f} reuse={l3_reuse:.1%}")
        except Exception:
            logger.warning("操作降级跳过")
        
        result = CBNRResult(
            l1_normalization=self._last_l1_result,
            l2_bottleneck=self._last_l2_result,
            l3_residual=self._last_l3_result,
        )
        return self._build_final_output(result, self._last_l1_result.normalized_input if self._last_l1_result else {})

    def _build_final_output(self, result: CBNRResult, original_input: Dict) -> Dict[str, Any]:
        output = {}
        
        if result.l1_normalization:
            output["uncertainty"] = result.l1_normalization.uncertainty
            output["normalization_strength"] = result.l1_normalization.normalization_strength
            output["biases_cleared"] = result.l1_normalization.bias_cleared
            output["principles_applied"] = result.l1_normalization.principles_anchored
            output["predictions"] = len(result.l1_normalization.predictions)
        
        if result.l2_bottleneck:
            output["compression_ratio"] = result.l2_bottleneck.compression_ratio
            output["conflict_delta"] = result.l2_bottleneck.conflict_delta
            output["conflict_mode"] = result.l2_bottleneck.conflict_mode.value
            output["core_topic"] = result.l2_bottleneck.core_essence.get("topic", "")
            output["core_entities"] = result.l2_bottleneck.core_essence.get("entities", [])
            output["question_type"] = result.l2_bottleneck.core_essence.get("question_type", "")
        
        if result.l3_residual:
            output["state_reuse_rate"] = result.l3_residual.state_reuse_rate
            output["search_tree_size"] = result.l3_residual.search_tree_size
            output["fallback_used"] = result.l3_residual.fallback_used
            output["has_experience_base"] = result.l3_residual.new_state.get("_has_experience_base", False)
        
        output["cbnr_processing_time_ms"] = result.processing_time_ms
        output["cbnr_questions"] = result.questions_asked
        
        return output

    def get_stats(self) -> Dict[str, Any]:
        return {
            "process_count": self._process_count,
            "avg_processing_time_ms": self._total_time / max(self._process_count, 1),
            "l1": self._l1.get_stats(),
            "l2": self._l2.get_stats(),
            "l3": self._l3.get_stats(),
        }


_cbnr_hub: Optional[CBNRHub] = None


def get_cbnr_hub() -> CBNRHub:
    global _cbnr_hub
    if _cbnr_hub is None:
        _cbnr_hub = CBNRHub()
    return _cbnr_hub