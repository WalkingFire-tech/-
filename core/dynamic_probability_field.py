"""
动态概率场 - 异步概率计算的核心

核心思想：从"确定性输出"到"概率分布"
- 同时保留多个候选解释，而非早期舍弃低概率选项
- 根据新证据（贝叶斯更新）动态调整概率分布
- 熵值追踪系统不确定度，指导后续探索方向

与PathWeightManager的关系：
- PathWeightManager = 路径级权重（哪条路更可信）
- DynamicProbabilityField = 候选级概率（哪个答案更可能对）
- 两者协同：路径权重影响先验概率，概率场更新反馈给路径权重
"""

import math
import time
import json
from core.ports.adapters import get_storage_port
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger


class DynamicProbabilityField:
    """
    动态概率场 - 异步概率计算的核心
    
    核心思想：从"确定性输出"到"概率分布"
    - 同时保留多个候选解释，而非早期舍弃低概率选项
    - 根据新证据（贝叶斯更新）动态调整概率分布
    - 熵值追踪系统不确定度，指导后续探索方向
    
    增强特性：
    - 闭环校准反馈：概率场预测vs实际结果的校准误差反馈给ProbabilityCalibrator
    - 不确定性驱动的行动路由：高/中/低不确定性触发不同处理深度
    - 与PathWeightManager协同：路径权重影响先验概率，概率场更新反馈给路径权重
    """
    
    UNCERTAINTY_HIGH = 0.8
    UNCERTAINTY_MEDIUM = 0.5

    def __init__(self, db_path: str = "data/probability_field.db"):
        self.db_path = db_path
        self._candidates: Dict[str, dict] = {}
        self._entropy = 1.0
        self._evidence_count = 0
        self._prior_strength = 0.3
        self._init_db()
        self._calibration_history: List[Dict] = []
        self._last_query = ""

    def _init_db(self):
        from pathlib import Path
        Path(self.db_path).parent.mkdir(exist_ok=True)
        db = get_storage_port(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS probability_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                distribution TEXT,
                entropy REAL,
                top_candidate TEXT,
                top_probability REAL,
                evidence_count INTEGER,
                timestamp TEXT
            )
        ''')

    def initialize(self, candidates: List[Dict], path_weights: Dict[str, float] = None) -> Dict:
        self._candidates = {}
        self._evidence_count = 0

        if not candidates:
            return {"status": "empty", "entropy": 1.0}

        prior = 1.0 / len(candidates)
        for i, cand in enumerate(candidates):
            source = cand.get("source", f"unknown_{i}")
            base_prob = prior
            if path_weights and source in path_weights:
                base_prob = prior * (0.5 + path_weights[source])
            content = cand.get("response", "") or cand.get("content", "")
            self._candidates[f"cand_{i}"] = {
                "content": content[:500],
                "source": source,
                "probability": base_prob,
                "score": cand.get("score", 50),
                "evidence_for": 0,
                "evidence_against": 0,
                "retrieval_probability": cand.get("retrieval_probability"),
                "retrieval_entropy": cand.get("retrieval_entropy"),
            }

        self._normalize()
        self._entropy = self._compute_entropy()
        return self.get_distribution()

    def update(self, evidence: Dict) -> Dict:
        if not self._candidates:
            return {"status": "empty"}

        evidence_type = evidence.get("type", "neutral")
        confidence = evidence.get("confidence", 0.5)
        source = evidence.get("source", "")
        content = evidence.get("content", "")

        for cid, cand in self._candidates.items():
            likelihood = self._compute_likelihood(cand, evidence)
            cand["probability"] *= likelihood

        self._normalize()
        self._entropy = self._compute_entropy()
        self._evidence_count += 1

        if self._evidence_count % 3 == 0:
            self._prune_low_probability()

        try:
            from core.presence.probability_field import get_probability_field
            pf = get_probability_field()
            pf.update(signal=confidence)
        except Exception:
            pass

        return self.get_distribution()

    def batch_update(self, evidences: List[Dict]) -> Dict:
        for ev in evidences:
            self.update(ev)
        return self.get_distribution()

    def get_distribution(self) -> Dict:
        if not self._candidates:
            return {"candidates": {}, "entropy": 1.0, "top": None, "evidence_count": 0}

        sorted_cands = sorted(self._candidates.items(), key=lambda x: x[1]["probability"], reverse=True)
        top_id, top_cand = sorted_cands[0]

        return {
            "candidates": {
                cid: {
                    "source": c["source"],
                    "probability": round(c["probability"], 4),
                    "score": c.get("score", 0),
                }
                for cid, c in sorted_cands
            },
            "entropy": round(self._entropy, 4),
            "top": {"id": top_id, "source": top_cand["source"], "probability": round(top_cand["probability"], 4)},
            "evidence_count": self._evidence_count,
            "confidence_level": self._get_confidence_level(),
        }

    def get_top_response(self) -> Optional[str]:
        if not self._candidates:
            return None
        top = max(self._candidates.items(), key=lambda x: x[1]["probability"])
        return top[1]["content"]

    def should_explore(self) -> bool:
        base = self._entropy > 0.8 and self._evidence_count < 5
        try:
            from core.presence.probability_decision_bridge import get_probability_decision_bridge
            _bridge = get_probability_decision_bridge()
            _decision = _bridge.get_decision_context().get("decision_params", {})
            _diversity = _decision.get("path_diversity", 0.5)
            if _diversity > 0.6:
                return True
            if _diversity < 0.4:
                return False
        except Exception:
            pass
        return base

    def get_exploration_guidance(self) -> Dict:
        if not self._candidates:
            return {"action": "initialize", "reason": "no_candidates"}
        sorted_cands = sorted(self._candidates.items(), key=lambda x: x[1]["probability"])
        weakest = sorted_cands[0]
        return {
            "action": "explore_weak",
            "target_source": weakest[1]["source"],
            "target_probability": round(weakest[1]["probability"], 4),
            "entropy": round(self._entropy, 4),
            "reason": f"low_prob_source={weakest[1]['source']}, entropy={self._entropy:.2f}",
        }

    def save_snapshot(self, query: str = ""):
        dist = self.get_distribution()
        try:
            db = get_storage_port(self.db_path)
            db.execute('''
                INSERT INTO probability_snapshots
                (query, distribution, entropy, top_candidate, top_probability, evidence_count, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (query[:200], json.dumps(dist["candidates"], ensure_ascii=False),
                  dist["entropy"], dist.get("top", {}).get("source", ""),
                  dist.get("top", {}).get("probability", 0),
                  dist["evidence_count"], datetime.now().isoformat()), commit=True)
        except Exception as e:
            logger.error(f"概率场快照保存失败: {e}")

    def get_recent_snapshots(self, limit: int = 20) -> List[Dict]:
        try:
            db = get_storage_port(self.db_path)
            rows = db.query(
                "SELECT query, distribution, entropy, top_candidate, top_probability, evidence_count, timestamp FROM probability_snapshots ORDER BY id DESC LIMIT ?",
                (limit,))
            return [
                {"query": r[0], "distribution": json.loads(r[1]), "entropy": r[2],
                 "top_candidate": r[3], "top_probability": r[4],
                 "evidence_count": r[5], "timestamp": r[6]}
                for r in rows
            ]
        except Exception:
            return []

    def _compute_likelihood(self, candidate: Dict, evidence: Dict) -> float:
        ev_type = evidence.get("type", "neutral")
        confidence = evidence.get("confidence", 0.5)
        source = evidence.get("source", "")
        content = evidence.get("content", "")

        likelihood = 1.0

        if ev_type == "support" and source == candidate.get("source"):
            likelihood = 1.0 + confidence * 0.5
        elif ev_type == "contradict" and source == candidate.get("source"):
            likelihood = max(0.1, 1.0 - confidence * 0.5)
        elif ev_type == "quality_boost":
            cand_score = candidate.get("score", 50)
            if cand_score >= 70:
                likelihood = 1.0 + confidence * 0.3
            elif cand_score < 40:
                likelihood = max(0.2, 1.0 - confidence * 0.3)
        elif ev_type == "essence_pass":
            if candidate.get("score", 0) >= 60:
                likelihood = 1.0 + confidence * 0.2
        elif ev_type == "essence_fail":
            if candidate.get("score", 0) < 60:
                likelihood = max(0.3, 1.0 - confidence * 0.4)

        if content and candidate.get("content"):
            overlap = self._text_overlap(content, candidate["content"])
            if overlap > 0.3:
                likelihood *= (1.0 + overlap * 0.2)

        return likelihood

    def _normalize(self):
        total = sum(c["probability"] for c in self._candidates.values())
        if total > 0:
            for c in self._candidates.values():
                c["probability"] /= total

    def _compute_entropy(self) -> float:
        entropy = 0.0
        for c in self._candidates.values():
            p = c["probability"]
            if p > 0:
                entropy -= p * math.log2(max(p, 1e-10))
        return entropy

    def _get_confidence_level(self) -> str:
        if self._entropy < 0.5:
            return "high"
        elif self._entropy < 1.0:
            return "medium"
        else:
            return "low"

    def _prune_low_probability(self, threshold: float = 0.02):
        to_remove = [cid for cid, c in self._candidates.items() if c["probability"] < threshold]
        for cid in to_remove:
            del self._candidates[cid]
        if to_remove:
            self._normalize()

    def _text_overlap(self, text_a: str, text_b: str) -> float:
        if not text_a or not text_b:
            return 0.0
        tokens_a = set(text_a.lower().split())
        tokens_b = set(text_b.lower().split())
        if not tokens_a or not tokens_b:
            return 0.0
        return len(tokens_a & tokens_b) / max(len(tokens_a | tokens_b), 1)

    def record_outcome(self, chosen_source: str, actual_quality: float):
        """闭环校准反馈：记录概率场预测与实际结果的对应关系
        
        核心思想：将概率场的预测（哪个候选概率最高）与实际结果（适应度评分）对比，
        计算校准误差，反馈给ProbabilityCalibrator调整温度参数。
        """
        if not self._candidates:
            return
        
        for cid, cand in self._candidates.items():
            predicted_prob = cand["probability"]
            is_relevant = (cand["source"] == chosen_source and actual_quality >= 60)
            try:
                from infrastructure.vector_retriever import vector_retriever
                vector_retriever._calibrator.record_calibration_outcome(predicted_prob, is_relevant)
            except Exception:
                logger.warning("操作降级跳过")
        
        self._calibration_history.append({
            "chosen_source": chosen_source,
            "actual_quality": actual_quality,
            "predicted_top": max(self._candidates.items(), key=lambda x: x[1]["probability"])[1]["source"] if self._candidates else "",
            "entropy": self._entropy,
            "timestamp": time.time() if 'time' in dir() else 0,
        })
        if len(self._calibration_history) > 200:
            self._calibration_history = self._calibration_history[-200:]

    def get_uncertainty_action(self) -> Dict:
        """不确定性驱动的行动路由：根据当前熵值推荐处理深度
        
        - 高不确定性(entropy>0.8)：触发更多检索路径或ReAct迭代，进行"主动探索"
        - 中等不确定性(0.5<entropy<=0.8)：利用现有分布生成回答，标注不确定性
        - 低不确定性(entropy<=0.5)：快速回答，精力用于后台反思与学习
        """
        if self._entropy > self.UNCERTAINTY_HIGH:
            return {
                "action": "explore",
                "depth": "deep",
                "reason": f"高不确定性(entropy={self._entropy:.2f})，建议启动全部路径+ReAct迭代",
                "recommended_paths": "all",
                "should_react": True,
                "should_explore_external": True,
            }
        elif self._entropy > self.UNCERTAINTY_MEDIUM:
            return {
                "action": "utilize",
                "depth": "moderate",
                "reason": f"中等不确定性(entropy={self._entropy:.2f})，利用现有分布，标注不确定性",
                "recommended_paths": "top_3",
                "should_react": False,
                "should_explore_external": False,
                "uncertainty_label": self._get_uncertainty_label(),
            }
        else:
            return {
                "action": "fast_answer",
                "depth": "shallow",
                "reason": f"低不确定性(entropy={self._entropy:.2f})，快速回答，后台反思",
                "recommended_paths": "top_1",
                "should_react": False,
                "should_explore_external": False,
            }

    def _get_uncertainty_label(self) -> str:
        top_prob = max((c["probability"] for c in self._candidates.values()), default=0)
        source_count = len(set(c.get("source", "") for c in self._candidates.values()))
        if top_prob >= 0.7:
            if source_count >= 2:
                return "比较有把握（多源一致）"
            return "比较有把握"
        elif top_prob >= 0.4:
            if source_count >= 2:
                return "把握不算大（来源有分歧）"
            return "把握不算大（单来源）"
        else:
            return "把握不太大"

    def get_calibration_summary(self) -> Dict:
        """获取校准反馈摘要"""
        if not self._calibration_history:
            return {"total": 0, "accuracy": 0}
        correct = sum(1 for h in self._calibration_history 
                      if h["chosen_source"] == h["predicted_top"])
        total = len(self._calibration_history)
        return {
            "total": total,
            "accuracy": round(correct / total, 3) if total > 0 else 0,
            "avg_quality_when_correct": round(
                sum(h["actual_quality"] for h in self._calibration_history 
                    if h["chosen_source"] == h["predicted_top"]) / max(correct, 1), 1),
            "avg_quality_when_wrong": round(
                sum(h["actual_quality"] for h in self._calibration_history 
                    if h["chosen_source"] != h["predicted_top"]) / max(total - correct, 1), 1),
        }


dynamic_probability_field = DynamicProbabilityField()