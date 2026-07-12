"""
持续自我评估 - 让系统在每次对话后自动回顾自己的表现

这是系统"从经验中学习"的核心机制：
- 每次对话结束后，系统自动回顾自己的表现
- 识别做得好的地方和需要改进的地方
- 将评估结果转化为学习信号

核心理念：
- 自我评估不是"外部检查"，而是"内在反思"
- 评估不是为了评判，而是为了成长
- 每一次评估都让系统更了解自己
"""

import time
import hashlib
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from loguru import logger


class ReviewDimension(Enum):
    """评估维度"""
    UNDERSTANDING = "understanding"
    RELEVANCE = "relevance"
    HELPFULNESS = "helpfulness"
    CLARITY = "clarity"
    EMPATHY = "empathy"
    BOUNDARY = "boundary"


class ReviewOutcome(Enum):
    """评估结果"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    FAIL = "fail"


@dataclass
class ReviewResult:
    """一次自我评估的结果"""
    conversation_id: str
    timestamp: str
    scores: Dict[str, float]
    outcome: str
    overall_score: float
    strengths: List[str]
    weaknesses: List[str]
    insights: List[str]
    improvement_suggestions: List[Dict]
    processing_time_ms: float
    confidence: float
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ReviewResult":
        """从字典恢复对象"""
        return cls(
            conversation_id=data.get("conversation_id", "unknown"),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            scores=data.get("scores", {}),
            outcome=data.get("outcome", "fair"),
            overall_score=data.get("overall_score", 0.5),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            insights=data.get("insights", []),
            improvement_suggestions=data.get("improvement_suggestions", []),
            processing_time_ms=data.get("processing_time_ms", 0),
            confidence=data.get("confidence", 0.5)
        )
    
    def to_dict(self) -> Dict:
        """转换为可序列化字典"""
        return {
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp,
            "scores": self.scores,
            "outcome": self.outcome,
            "overall_score": self.overall_score,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "insights": self.insights,
            "improvement_suggestions": self.improvement_suggestions,
            "processing_time_ms": self.processing_time_ms,
            "confidence": self.confidence
        }


class SelfReviewEngine:
    """自我评估引擎"""

    def __init__(self, persist_path: str = "data/self_review_history.json"):
        self._persist_path = persist_path
        self._review_history: List[ReviewResult] = []
        self._max_history = 100
        
        self._stats = {
            "total_reviews": 0,
            "avg_score": 0.0,
            "outcome_distribution": {},
            "strength_patterns": {},
            "weakness_patterns": {},
            "last_review_time": None
        }
        
        self._enabled = True
        
        self._thresholds = {
            ReviewDimension.UNDERSTANDING: 0.6,
            ReviewDimension.RELEVANCE: 0.6,
            ReviewDimension.HELPFULNESS: 0.6,
            ReviewDimension.CLARITY: 0.5,
            ReviewDimension.EMPATHY: 0.4,
            ReviewDimension.BOUNDARY: 0.7
        }
        
        self._load_history()
        
        logger.info("📝 自我评估引擎已创建")

    def review(self, conversation: Dict) -> ReviewResult:
        """对一次对话进行自我评估"""
        if not self._enabled:
            return self._skip_review(conversation)

        start_time = time.time()
        
        conversation_id = conversation.get("conversation_id", "unknown")
        user_input = conversation.get("user_input", "")
        system_response = conversation.get("system_response", "")
        perception = conversation.get("perception_result", {})
        validation = conversation.get("validation_result", {})

        scores = self._evaluate_dimensions(user_input, system_response, perception, validation)
        overall_score = sum(scores.values()) / len(scores)
        outcome = self._determine_outcome(overall_score)
        strengths, weaknesses = self._extract_strengths_weaknesses(scores, perception, validation)
        insights = self._generate_insights(scores, strengths, weaknesses, perception, validation)
        suggestions = self._generate_suggestions(scores, weaknesses, validation)

        scores_str = {k.value: v for k, v in scores.items()}

        result = ReviewResult(
            conversation_id=conversation_id,
            timestamp=datetime.now().isoformat(),
            scores=scores_str,
            outcome=outcome.value,
            overall_score=overall_score,
            strengths=strengths,
            weaknesses=weaknesses,
            insights=insights,
            improvement_suggestions=suggestions,
            processing_time_ms=(time.time() - start_time) * 1000,
            confidence=self._calculate_confidence(perception, validation)
        )

        self._review_history.append(result)
        if len(self._review_history) > self._max_history:
            self._review_history = self._review_history[-self._max_history:]

        self._update_stats(result)
        self._execute_after_review(result)
        self._save_history()

        logger.warning(f"📝 自我评估完成: {outcome.value} (总分: {overall_score:.2f})")

        return result

    def _evaluate_dimensions(self, user_input: str, system_response: str,
                             perception: Dict, validation: Dict) -> Dict[ReviewDimension, float]:
        """评估各维度"""
        scores = {}
        scores[ReviewDimension.UNDERSTANDING] = self._evaluate_understanding(user_input, perception)
        scores[ReviewDimension.RELEVANCE] = self._evaluate_relevance(user_input, system_response)
        scores[ReviewDimension.HELPFULNESS] = self._evaluate_helpfulness(system_response, perception)
        scores[ReviewDimension.CLARITY] = self._evaluate_clarity(system_response)
        scores[ReviewDimension.EMPATHY] = self._evaluate_empathy(system_response, perception)
        scores[ReviewDimension.BOUNDARY] = self._evaluate_boundary(system_response, validation)
        return scores

    def _evaluate_understanding(self, user_input: str, perception: Dict) -> float:
        confidence = perception.get("confidence", 0.5)
        if perception.get("uncertainty", False):
            confidence *= 0.7
        if perception.get("intent", "unknown") == "unknown":
            confidence *= 0.5
        return min(1.0, confidence)

    def _evaluate_relevance(self, user_input: str, system_response: str) -> float:
        user_words = set(user_input.lower().split())
        response_words = set(system_response.lower().split())
        if not user_words:
            return 0.3
        overlap = len(user_words & response_words)
        relevance = overlap / len(user_words)
        if len(system_response) < 20 and len(user_input) > 20:
            relevance *= 0.5
        return min(1.0, relevance + 0.2)

    def _evaluate_helpfulness(self, system_response: str, perception: Dict) -> float:
        length_score = min(1.0, len(system_response) / 100)
        has_solution = any(kw in system_response for kw in ["可以", "建议", "推荐", "方法"])
        solution_bonus = 0.3 if has_solution else 0
        return min(1.0, length_score * 0.3 + solution_bonus + 0.1)

    def _evaluate_clarity(self, system_response: str) -> float:
        length = len(system_response)
        if length < 10:
            return 0.2
        elif length < 30:
            return 0.4
        elif length < 200:
            return 0.8
        else:
            return 0.6

    def _evaluate_empathy(self, system_response: str, perception: Dict) -> float:
        empathy_words = ["理解", "明白", "感受", "体会", "辛苦"]
        empathy_count = sum(1 for w in empathy_words if w in system_response)
        return min(1.0, 0.2 + empathy_count * 0.15)

    def _evaluate_boundary(self, system_response: str, validation: Dict) -> float:
        if validation:
            if validation.get("status") == "pass":
                return 0.9
            elif validation.get("status") == "partial":
                return 0.5
            else:
                return 0.2
        return 0.7

    def _determine_outcome(self, overall_score: float) -> ReviewOutcome:
        if overall_score >= 0.85:
            return ReviewOutcome.EXCELLENT
        elif overall_score >= 0.7:
            return ReviewOutcome.GOOD
        elif overall_score >= 0.5:
            return ReviewOutcome.FAIR
        elif overall_score >= 0.3:
            return ReviewOutcome.POOR
        else:
            return ReviewOutcome.FAIL

    def _extract_strengths_weaknesses(self, scores: Dict[ReviewDimension, float],
                                      perception: Dict, validation: Dict) -> Tuple[List[str], List[str]]:
        strengths = []
        weaknesses = []
        
        for dimension, score in scores.items():
            threshold = self._thresholds.get(dimension, 0.5)
            dim_name = dimension.value
            if score >= threshold:
                strengths.append(f"{dim_name}: {score:.2f}")
            else:
                weaknesses.append(f"{dim_name}: {score:.2f}")
        
        if perception.get("confidence", 0) > 0.8:
            strengths.append("高置信度理解")
        elif perception.get("confidence", 0) < 0.4:
            weaknesses.append("低置信度理解")
        
        if validation:
            if validation.get("status") == "pass":
                strengths.append("通过校验")
            else:
                weaknesses.append(f"校验未通过: {validation.get('reason', '未知原因')}")
        
        return strengths[:5], weaknesses[:5]

    def _generate_insights(self, scores: Dict[ReviewDimension, float],
                           strengths: List[str], weaknesses: List[str],
                           perception: Dict, validation: Dict) -> List[str]:
        """生成学习洞察"""
        insights = []
        
        insight_map_high = {
            ReviewDimension.UNDERSTANDING: "我在理解用户意图方面表现良好",
            ReviewDimension.RELEVANCE: "我的回答与用户问题高度相关",
            ReviewDimension.HELPFULNESS: "我提供了有帮助的解决方案",
            ReviewDimension.CLARITY: "我的表达清晰易懂",
            ReviewDimension.EMPATHY: "我能够感知并回应用户的情绪",
            ReviewDimension.BOUNDARY: "我很好地遵守了边界和承诺"
        }
        
        for dim, score in scores.items():
            if score >= 0.8 and dim in insight_map_high:
                insights.append(insight_map_high[dim])
        
        insight_map_low = {
            ReviewDimension.UNDERSTANDING: "我需要提高理解复杂问题的能力",
            ReviewDimension.RELEVANCE: "我需要确保回答更紧密地回应用户问题",
            ReviewDimension.HELPFULNESS: "我需要提供更具体、更可操作的帮助",
            ReviewDimension.CLARITY: "我需要用更结构化的方式表达",
            ReviewDimension.EMPATHY: "我需要更注意用户的情绪状态",
            ReviewDimension.BOUNDARY: "我需要更谨慎地识别边界"
        }
        
        for dim, score in scores.items():
            if score < 0.4 and dim in insight_map_low:
                insights.append(insight_map_low[dim])
        
        if weaknesses:
            weak_dims = [w.split(":")[0] for w in weaknesses[:3] if ":" in w]
            if weak_dims:
                insights.append(f"需要改进: {', '.join(weak_dims)}")
        
        if validation and validation.get("status") == "fail":
            insights.append(f"校验失败提示我: {validation.get('reason', '需要改进')}")
        
        if sum(scores.values()) / len(scores) < 0.5:
            insights.append("这次对话表现不佳，需要深入反思")
        
        seen = set()
        unique_insights = []
        for insight in insights:
            if insight not in seen:
                seen.add(insight)
                unique_insights.append(insight)
        
        return unique_insights[:5]

    def _generate_suggestions(self, scores: Dict[ReviewDimension, float],
                              weaknesses: List[str], validation: Dict) -> List[Dict]:
        """生成改进建议"""
        suggestions = []
        
        suggestion_map = {
            ReviewDimension.UNDERSTANDING: "在理解用户意图时，可以多考虑上下文和隐含意图，必要时主动询问澄清",
            ReviewDimension.RELEVANCE: "确保回答直接回应用户的问题，避免跑题或过度延伸",
            ReviewDimension.HELPFULNESS: "提供更具体的建议和可操作的方案，而不仅仅是概念性回答",
            ReviewDimension.CLARITY: "使用结构化表达，分点说明，让回答更清晰易读",
            ReviewDimension.EMPATHY: "更多地表达理解和共情，让用户感到被倾听和重视",
            ReviewDimension.BOUNDARY: "更清晰地识别边界，在不确定时坦诚说明，不越界承诺"
        }
        
        for dimension, score in scores.items():
            if score < self._thresholds.get(dimension, 0.5):
                suggestions.append({
                    "dimension": dimension.value,
                    "suggestion": suggestion_map.get(dimension, f"改进{dimension.value}"),
                    "current_score": score,
                    "target_score": min(1.0, score + 0.3)
                })
        
        if weaknesses:
            suggestions.append({
                "dimension": "overall",
                "suggestion": f"重点关注: {', '.join([w.split(':')[0] for w in weaknesses[:3] if ':' in w])}",
                "current_score": 0.5,
                "target_score": 0.7
            })
        
        return suggestions[:5]

    def _calculate_confidence(self, perception: Dict, validation: Dict) -> float:
        confidence = 0.6
        if perception:
            confidence += 0.15
        if validation:
            confidence += 0.15
        return min(1.0, confidence)

    def _update_stats(self, result: ReviewResult):
        """更新统计"""
        self._stats["total_reviews"] += 1
        self._stats["last_review_time"] = datetime.now().isoformat()
        
        total = self._stats["total_reviews"]
        self._stats["avg_score"] = (
            (self._stats["avg_score"] * (total - 1) + result.overall_score) / total
        )
        
        outcome = result.outcome
        self._stats["outcome_distribution"][outcome] = \
            self._stats["outcome_distribution"].get(outcome, 0) + 1
        
        for strength in result.strengths:
            pattern = strength.split(":")[0] if ":" in strength else strength
            self._stats["strength_patterns"][pattern] = \
                self._stats["strength_patterns"].get(pattern, 0) + 1
        
        for weakness in result.weaknesses:
            pattern = weakness.split(":")[0] if ":" in weakness else weakness
            self._stats["weakness_patterns"][pattern] = \
                self._stats["weakness_patterns"].get(pattern, 0) + 1

    def _load_history(self):
        """从文件加载历史"""
        if os.path.exists(self._persist_path):
            try:
                with open(self._persist_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._review_history = []
                    for item in data:
                        self._review_history.append(ReviewResult.from_dict(item))
                    logger.warning(f"📝 加载了 {len(self._review_history)} 条评估历史")
            except Exception as e:
                logger.warning(f"加载自我评估历史失败: {e}")

    def _save_history(self):
        """保存历史到文件"""
        try:
            os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
            with open(self._persist_path, 'w', encoding='utf-8') as f:
                data = [r.to_dict() for r in self._review_history]
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存自我评估历史失败: {e}")

    def _execute_after_review(self, result: ReviewResult):
        """执行评估后的动作"""
        self._submit_signals(result)

    def _submit_signals(self, result: ReviewResult):
        """提交信号到间隙生长引擎"""
        try:
            from core.presence.gap_growth import get_gap_growth_engine
            engine = get_gap_growth_engine()
            
            if result.outcome == "excellent":
                engine.submit_signal(
                    signal_type="success_pattern",
                    content=f"对话表现优秀: {result.overall_score:.2f}",
                    source="self_review",
                    context={"outcome": result.outcome},
                    priority="low"
                )
            elif result.outcome in ["poor", "fail"]:
                for insight in result.insights:
                    engine.submit_signal(
                        signal_type="error_pattern",
                        content=f"自我评估发现: {insight}",
                        source="self_review",
                        context={"outcome": result.outcome, "score": result.overall_score},
                        priority="high"
                    )
        except Exception as e:
            logger.error(f"提交信号失败: {e}")

    def _skip_review(self, conversation: Dict) -> ReviewResult:
        return ReviewResult(
            conversation_id=conversation.get("conversation_id", "unknown"),
            timestamp=datetime.now().isoformat(),
            scores={},
            outcome="fair",
            overall_score=0.5,
            strengths=[],
            weaknesses=[],
            insights=[],
            improvement_suggestions=[],
            processing_time_ms=0,
            confidence=0.0
        )

    def get_stats(self) -> Dict:
        return self._stats

    def get_recent_reviews(self, limit: int = 10) -> List[Dict]:
        return [
            {
                "timestamp": r.timestamp,
                "outcome": r.outcome,
                "overall_score": r.overall_score,
                "strengths": r.strengths[:2],
                "weaknesses": r.weaknesses[:2]
            }
            for r in self._review_history[-limit:]
        ]

    def get_weakness_patterns(self) -> List[Dict]:
        """获取最常见的弱点模式"""
        patterns = self._stats["weakness_patterns"]
        sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)
        return [
            {"pattern": p, "count": c}
            for p, c in sorted_patterns[:5]
        ]

    def get_strength_patterns(self) -> List[Dict]:
        """获取最常见的优势模式"""
        patterns = self._stats["strength_patterns"]
        sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)
        return [
            {"pattern": p, "count": c}
            for p, c in sorted_patterns[:5]
        ]

    def enable(self):
        self._enabled = True
        logger.info("📝 自我评估已启用")

    def disable(self):
        self._enabled = False
        logger.info("📝 自我评估已禁用")


_review_engine: Optional[SelfReviewEngine] = None


def get_self_review_engine() -> SelfReviewEngine:
    global _review_engine
    if _review_engine is None:
        _review_engine = SelfReviewEngine()
    return _review_engine


def start_self_review() -> None:
    engine = get_self_review_engine()
    engine.enable()


def stop_self_review() -> None:
    engine = get_self_review_engine()
    engine.disable()
