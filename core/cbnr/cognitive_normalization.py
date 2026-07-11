"""
L1: 认知规范化层 (Cognitive Normalization)

对应Batch Normalization：在每一轮推理之前，对输入进行标准化处理，
确保思维链路从稳定的基线出发。

CBNR-AGI 2.0增强：
- 预测编码：基于先验知识生成预测，用预测误差驱动注意力
- 不确定性感知：根据置信度动态调整规范化强度
  高不确定性 → 更强规范化（重置到基准）
  低不确定性 → 更弱规范化（保留上下文）

关键问句："在我开始思考之前，我是否已经重置到了正确的基准状态？"
"""

import math
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class NormalizationResult:
    input_hash: str
    bias_cleared: List[str] = field(default_factory=list)
    principles_anchored: List[str] = field(default_factory=list)
    uncertainty: float = 0.5
    normalization_strength: float = 0.5
    predictions: List[Dict] = field(default_factory=list)
    prediction_errors: List[float] = field(default_factory=list)
    normalized_input: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


class CognitiveNormalization:
    """
    认知规范化层
    
    三步规范化流程：
    1. 偏差检测与清除 - 识别并清除上一轮推理残留的认知偏差
    2. 第一性原理锚定 - 用精神内核的核心原则重新校准坐标系
    3. 情境自适应缩放 - 根据资源状态和不确定性调整认知分辨率
    """

    BIAS_PATTERNS = [
        "confirmation_bias",
        "anchoring_effect",
        "availability_heuristic",
        "sunk_cost_fallacy",
        "recency_bias",
    ]

    PRINCIPLES = [
        "never_give_up",
        "pursue_essence",
        "honest_when_confused",
        "multi_source_verification",
        "determine_how_before_what",
    ]

    def __init__(self):
        self._prediction_cache: Dict[str, Dict] = {}
        self._bias_history: List[Dict] = []
        self._normalization_count = 0

    def normalize(self, input_stream: Dict[str, Any], context: Dict[str, Any] = None) -> NormalizationResult:
        context = context or {}
        self._normalization_count += 1
        
        input_hash = self._hash_input(input_stream)
        
        uncertainty = self._compute_uncertainty(input_stream, context)
        
        predictions = self._generate_predictions(input_stream)
        prediction_errors = self._compute_prediction_errors(predictions, input_stream)
        
        strength = self._adaptive_strength(uncertainty)
        
        cleared = self._remove_bias(input_stream, strength)
        
        anchored = self._anchor_to_principles(cleared, strength)
        
        scaled = self._contextual_scale(anchored, context, strength)
        
        if prediction_errors:
            avg_error = sum(prediction_errors) / max(len(prediction_errors), 1)
            max_error = max(prediction_errors) if prediction_errors else 0
            scaled["_attention_weights"] = {
                "avg_prediction_error": avg_error,
                "max_prediction_error": max_error,
                "high_surprise": max_error > 0.7,
                "focus_boost": min(1.0 + max_error, 2.0),
            }
        
        self._update_prediction_cache(input_hash, input_stream)
        
        result = NormalizationResult(
            input_hash=input_hash,
            bias_cleared=[b["type"] for b in cleared.get("_biases_found", [])],
            principles_anchored=anchored.get("_principles_applied", []),
            uncertainty=uncertainty,
            normalization_strength=strength,
            predictions=predictions,
            prediction_errors=prediction_errors,
            normalized_input=scaled,
            timestamp=time.time(),
        )
        
        if result.bias_cleared:
            logger.debug(f"认知规范化: 清除偏差{result.bias_cleared}, 不确定性={uncertainty:.2f}, 强度={strength:.2f}")
        
        return result

    def _compute_uncertainty(self, input_stream: Dict, context: Dict) -> float:
        uncertainty = 0.5
        
        user_input = input_stream.get("user_input", "")
        if len(user_input) < 10:
            uncertainty += 0.15
        elif len(user_input) > 2000:
            uncertainty += 0.1
        
        if any(kw in user_input for kw in ["可能", "也许", "不确定", "大概", "maybe", "perhaps"]):
            uncertainty += 0.1
        
        if any(kw in user_input for kw in ["必须", "绝对", "一定", "肯定"]):
            uncertainty -= 0.1
        
        intent = input_stream.get("intent", "")
        if intent in ["fix", "request", "yes_no"]:
            uncertainty -= 0.05
        elif intent in ["philosophy", "knowledge", "why_how"]:
            uncertainty += 0.1
        
        resource_mode = context.get("resource_mode", "normal")
        if resource_mode == "emergency":
            uncertainty += 0.15
        elif resource_mode == "conservative":
            uncertainty += 0.05
        
        return max(0.0, min(1.0, uncertainty))

    def _generate_predictions(self, input_stream: Dict) -> List[Dict]:
        predictions = []
        user_input = input_stream.get("user_input", "")
        
        try:
            from core.knowledge_graph import get_knowledge_graph
            kg = get_knowledge_graph()
            results = kg.search(user_input[:50], top_k=3)
            for r in results:
                predictions.append({
                    "source": "knowledge_graph",
                    "content": r.content[:100] if hasattr(r, 'content') else str(r)[:100],
                    "confidence": 0.6,
                })
        except Exception:
            pass
        
        try:
            from infrastructure.database_manager import DatabaseManager
            rows = DatabaseManager.get("data/experience_pool.db").query(
                "SELECT response, quality_score FROM experiences WHERE raw_input LIKE ? ORDER BY quality_score DESC LIMIT 2",
                (f"%{user_input[:30]}%",)
            )
            for row in rows:
                predictions.append({
                    "source": "experience_pool",
                    "content": row[0][:100],
                    "confidence": min(row[1] / 100.0, 1.0),
                })

        except Exception:
            pass
        
        return predictions

    def _compute_prediction_errors(self, predictions: List[Dict], input_stream: Dict) -> List[float]:
        errors = []
        user_input = input_stream.get("user_input", "")
        user_words = set(user_input.lower().split())
        
        for pred in predictions:
            pred_words = set(pred.get("content", "").lower().split())
            overlap = len(user_words & pred_words) / max(len(user_words | pred_words), 1)
            error = 1.0 - overlap
            errors.append(error)
        
        return errors

    def _adaptive_strength(self, uncertainty: float) -> float:
        return 0.3 + 0.7 * uncertainty

    def _remove_bias(self, input_stream: Dict, strength: float) -> Dict:
        result = dict(input_stream)
        biases_found = []
        user_input = result.get("user_input", "")
        
        if strength > 0.5:
            emotional_words = ["太好了", "太糟了", "完美", "灾难", "amazing", "terrible"]
            for w in emotional_words:
                if w in user_input:
                    biases_found.append({"type": "emotional_bias", "word": w})
                    break
        
        if strength > 0.6:
            absolute_words = ["绝对是", "一定是", "必须是", "肯定没错"]
            for w in absolute_words:
                if w in user_input:
                    biases_found.append({"type": "confirmation_bias", "word": w})
                    break
        
        if strength > 0.7:
            if result.get("_prev_intent") and result.get("intent") == result.get("_prev_intent"):
                biases_found.append({"type": "anchoring_effect", "detail": "same_intent_as_previous"})
        
        if strength > 0.4:
            recent_words = ["最近", "刚才", "之前", "上次", "之前说的", "我之前", "上次说的", "刚说的", "刚才说的", "recently", "just now", "earlier"]
            if any(w in user_input for w in recent_words):
                biases_found.append({"type": "availability_heuristic", "detail": "recency_weighted"})
        
        if strength > 0.4:
            persist_words = ["已经", "投入", "花了", "做了这么久", "不能放弃", "已经做了", "已经花了", "已经投入", "白费了", "浪费了", "already invested", "sunk cost", "不能白费"]
            if any(w in user_input for w in persist_words):
                biases_found.append({"type": "sunk_cost_fallacy", "detail": "investment_biased"})
        
        result["_biases_found"] = biases_found
        if biases_found and strength > 0.5:
            result["_bias_cleared"] = True
            result["_original_emotional_weight"] = result.get("emotional_weight", 1.0)
            result["emotional_weight"] = 0.5
            for b in biases_found:
                self._bias_history.append({"type": b.get("type", "unknown"), "timestamp": time.time()})
                if len(self._bias_history) > 100:
                    self._bias_history.pop(0)
        
        return result

    def _anchor_to_principles(self, input_stream: Dict, strength: float) -> Dict:
        result = dict(input_stream)
        principles_applied = []
        
        if strength > 0.4:
            principles_applied.append("pursue_essence")
            result["_essence_mode"] = True
        
        if strength > 0.6:
            principles_applied.append("multi_source_verification")
            result["_require_verification"] = True
        
        if strength > 0.8:
            principles_applied.append("honest_when_confused")
            result["_express_uncertainty"] = True
        
        if result.get("_bias_cleared"):
            principles_applied.append("never_give_up")
            result["_fallback_enabled"] = True
        
        result["_principles_applied"] = principles_applied
        return result

    def _contextual_scale(self, input_stream: Dict, context: Dict, strength: float) -> Dict:
        result = dict(input_stream)
        
        resource_mode = context.get("resource_mode", "normal")
        if resource_mode == "emergency":
            result["_cognitive_resolution"] = "low"
            result["_max_reasoning_depth"] = 2
        elif resource_mode == "conservative":
            result["_cognitive_resolution"] = "medium"
            result["_max_reasoning_depth"] = 4
        else:
            result["_cognitive_resolution"] = "high"
            result["_max_reasoning_depth"] = 6
        
        if strength > 0.7:
            result["_cognitive_resolution"] = "low"
            result["_max_reasoning_depth"] = min(result.get("_max_reasoning_depth", 6), 3)
        
        return result

    def _hash_input(self, input_stream: Dict) -> str:
        import hashlib
        content = input_stream.get("user_input", "")[:200]
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def _update_prediction_cache(self, input_hash: str, input_stream: Dict):
        self._prediction_cache[input_hash] = {
            "input": input_stream.get("user_input", "")[:100],
            "timestamp": time.time(),
        }
        if len(self._prediction_cache) > 200:
            oldest = min(self._prediction_cache.items(), key=lambda x: x[1]["timestamp"])
            del self._prediction_cache[oldest[0]]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "normalization_count": self._normalization_count,
            "prediction_cache_size": len(self._prediction_cache),
            "bias_history_size": len(self._bias_history),
        }