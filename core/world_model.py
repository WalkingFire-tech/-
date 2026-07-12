"""
世界模型因果预演 - 学习型因果图 + 预测验证

核心能力：
1. 因果图构建：从交互经验中学习"如果A则B"的因果关系
2. 预测：给定当前状态，预测最可能的结果
3. 预演：在执行前模拟多种路径，选择最优
4. 验证：对比预测与实际结果，更新因果边权重

设计原则：
- 与经验池/知识图谱集成，不独立存储
- 因果边权重由验证结果驱动（贝叶斯更新）
- 预演结果经棘轮门控验证
- 预测失败时坦诚表达不确定性
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from infrastructure.database_manager import DatabaseManager

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class CausalEdgeType(Enum):
    CAUSES = "causes"
    ENABLES = "enables"
    PREVENTS = "prevents"
    CORRELATES = "correlates"


@dataclass
class CausalNode:
    id: str
    node_type: str
    content: str
    properties: Dict = field(default_factory=dict)


@dataclass
class CausalEdge:
    source_id: str
    target_id: str
    edge_type: CausalEdgeType
    probability: float
    confidence: float
    evidence_count: int = 0
    last_verified: str = ""


@dataclass
class Prediction:
    predicted_state: Dict
    probability: float
    confidence: float
    causal_path: List[str]
    alternatives: List[Dict] = field(default_factory=list)


@dataclass
class PredictionResult:
    prediction: Prediction
    actual_outcome: Optional[Dict] = None
    was_correct: Optional[bool] = None
    verification_time: str = ""


class WorldModel:
    MIN_EVIDENCE = 2
    BAYESIAN_PRIOR = 0.5
    CONFIDENCE_DECAY = 0.95
    MAX_NODES = 500
    MAX_EDGES = 2000

    def __init__(self, db_path: str = "data/world_model.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        from pathlib import Path
        Path(self.db_path).parent.mkdir(exist_ok=True)

        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS causal_nodes (
                id TEXT PRIMARY KEY,
                node_type TEXT,
                content TEXT,
                properties TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS causal_edges (
                source_id TEXT,
                target_id TEXT,
                edge_type TEXT,
                probability REAL,
                confidence REAL,
                evidence_count INTEGER DEFAULT 0,
                last_verified TEXT,
                created_at TEXT,
                PRIMARY KEY (source_id, target_id, edge_type)
            );
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT,
                predicted_state TEXT,
                probability REAL,
                confidence REAL,
                causal_path TEXT,
                actual_outcome TEXT,
                was_correct BOOLEAN,
                created_at TEXT,
                verified_at TEXT
            );
            CREATE TABLE IF NOT EXISTS counterfactuals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intent TEXT,
                actual_action TEXT,
                alternative_action TEXT,
                actual_score REAL,
                alternative_score REAL,
                would_have_been_better BOOLEAN,
                lesson TEXT,
                created_at TEXT
            )
        ''')

    def add_causal_node(self, node_id: str, node_type: str, content: str, properties: Dict = None) -> bool:
        db = DatabaseManager.get(self.db_path)
        now = datetime.now().isoformat()
        db.execute(
            'INSERT OR REPLACE INTO causal_nodes (id, node_type, content, properties, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',
            (node_id, node_type, content, json.dumps(properties or {}, ensure_ascii=False), now, now),
            commit=True
        )
        return True

    def add_causal_edge(self, source_id: str, target_id: str,
                        edge_type: CausalEdgeType = CausalEdgeType.CAUSES,
                        probability: float = 0.5, confidence: float = 0.3) -> bool:
        db = DatabaseManager.get(self.db_path)
        now = datetime.now().isoformat()
        db.execute(
            'INSERT OR REPLACE INTO causal_edges (source_id, target_id, edge_type, probability, confidence, evidence_count, last_verified, created_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)',
            (source_id, target_id, edge_type.value, probability, confidence, now, now),
            commit=True
        )
        return True

    def predict(self, current_state: Dict, intent: str = "", top_k: int = 3) -> Prediction:
        query_hash = self._hash_state(current_state, intent)
        relevant_edges = self._find_relevant_edges(current_state, intent)
        
        if not relevant_edges:
            return Prediction(
                predicted_state={"outcome": "unknown", "reason": "no_causal_data"},
                probability=0.3,
                confidence=0.1,
                causal_path=[],
                alternatives=[]
            )

        sorted_edges = sorted(relevant_edges, key=lambda e: (
            1 if e.edge_type in (CausalEdgeType.CAUSES, CausalEdgeType.PREVENTS) else 0,
            e.probability * e.confidence
        ), reverse=True)
        
        top_edge = sorted_edges[0]
        target_node = self._get_node(top_edge.target_id)
        predicted_state = {
            "outcome": target_node.content if target_node else top_edge.target_id,
            "trigger": top_edge.source_id,
            "edge_type": top_edge.edge_type.value,
        }
        
        causal_path = [top_edge.source_id, top_edge.target_id]
        alternatives = []
        for edge in sorted_edges[1:top_k]:
            alt_node = self._get_node(edge.target_id)
            alternatives.append({
                "outcome": alt_node.content if alt_node else edge.target_id,
                "probability": edge.probability,
                "edge_type": edge.edge_type.value,
            })

        prediction = Prediction(
            predicted_state=predicted_state,
            probability=top_edge.probability,
            confidence=top_edge.confidence,
            causal_path=causal_path,
            alternatives=alternatives
        )

        self._save_prediction(query_hash, prediction)

        return prediction

    def _save_prediction(self, query_hash: str, prediction: Prediction):
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute(
                'INSERT INTO predictions (query_hash, predicted_state, probability, confidence, causal_path, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                (query_hash, json.dumps(prediction.predicted_state, ensure_ascii=False),
                 prediction.probability, prediction.confidence,
                 json.dumps(prediction.causal_path), datetime.now().isoformat()),
                commit=True
            )
        except Exception:
            logger.warning("操作降级跳过")

    def pre_enact(self, current_state: Dict, possible_actions: List[str], intent: str = "") -> Dict:
        results = []
        for action in possible_actions:
            state_with_action = dict(current_state)
            state_with_action["action"] = action
            pred = self.predict(state_with_action, intent)
            results.append({
                "action": action,
                "predicted_outcome": pred.predicted_state,
                "probability": pred.probability,
                "confidence": pred.confidence,
                "causal_path": pred.causal_path,
            })
        
        results.sort(key=lambda r: r["probability"] * r["confidence"], reverse=True)
        
        recommendation = results[0] if results else None
        return {
            "recommendation": recommendation,
            "alternatives": results[1:],
            "total_paths_explored": len(results),
            "has_high_confidence": recommendation and recommendation["confidence"] >= 0.5 if recommendation else False,
        }

    def multi_step_predict(self, current_state: Dict, action_sequence: List[str], intent: str = "", max_depth: int = 3) -> Dict:
        results = []
        state = dict(current_state)
        cumulative_prob = 1.0
        cumulative_conf = 1.0
        full_path = []

        for i, action in enumerate(action_sequence[:max_depth]):
            state["action"] = action
            pred = self.predict(state, intent)
            step_prob = pred.probability
            step_conf = pred.confidence
            cumulative_prob *= step_prob
            cumulative_conf *= step_conf
            full_path.extend(pred.causal_path)

            results.append({
                "step": i + 1,
                "action": action,
                "predicted_outcome": pred.predicted_state,
                "step_probability": step_prob,
                "cumulative_probability": cumulative_prob,
                "step_confidence": step_conf,
            })

            if pred.predicted_state.get("outcome") == "failure":
                break

            if pred.predicted_state.get("outcome"):
                state = {"intent": intent, "current_outcome": pred.predicted_state["outcome"]}

        return {
            "steps": results,
            "total_steps": len(results),
            "cumulative_probability": cumulative_prob,
            "cumulative_confidence": cumulative_conf,
            "full_causal_path": full_path,
            "likely_succeeds": cumulative_prob > 0.3 and cumulative_conf > 0.2,
        }

    def counterfactual(self, current_state: Dict, actual_action: str, alternative_action: str, intent: str = "") -> Dict:
        state_actual = dict(current_state)
        state_actual["action"] = actual_action
        pred_actual = self.predict(state_actual, intent)

        state_alt = dict(current_state)
        state_alt["action"] = alternative_action
        pred_alt = self.predict(state_alt, intent)

        actual_score = pred_actual.probability * pred_actual.confidence
        alt_score = pred_alt.probability * pred_alt.confidence

        return {
            "actual": {
                "action": actual_action,
                "predicted_outcome": pred_actual.predicted_state,
                "score": actual_score,
            },
            "counterfactual": {
                "action": alternative_action,
                "predicted_outcome": pred_alt.predicted_state,
                "score": alt_score,
            },
            "would_have_been_better": alt_score > actual_score,
            "advantage": alt_score - actual_score,
            "lesson": f"如果选择'{alternative_action}'而非'{actual_action}'，预期{'更优' if alt_score > actual_score else '更差'}（差异={abs(alt_score - actual_score):.3f}）"
        }

    def save_counterfactual(self, intent: str, actual_action: str, alternative_action: str,
                            actual_score: float, alt_score: float, would_be_better: bool, lesson: str) -> bool:
        db = DatabaseManager.get(self.db_path)
        db.execute(
            'INSERT INTO counterfactuals (intent, actual_action, alternative_action, actual_score, alternative_score, would_have_been_better, lesson, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (intent, actual_action, alternative_action, actual_score, alt_score, would_be_better, lesson, datetime.now().isoformat()),
            commit=True
        )
        return True

    def auto_verify(self, query_hash: str, actual_outcome: Dict) -> Optional[PredictionResult]:
        result = self.verify(query_hash, actual_outcome)
        if result.was_correct is not None and not result.was_correct:
            logger.info(f"世界模型预测偏差: 预测={result.prediction.predicted_state}, 实际={actual_outcome}")
        return result

    def verify(self, query_hash: str, actual_outcome: Dict) -> PredictionResult:
        db = DatabaseManager.get(self.db_path)
        row = db.query_one(
            'SELECT id, predicted_state, probability, confidence, causal_path FROM predictions WHERE query_hash = ? ORDER BY created_at DESC LIMIT 1',
            (query_hash,)
        )
        if not row:
            return PredictionResult(
                prediction=Prediction(predicted_state={}, probability=0, confidence=0, causal_path=[]),
                actual_outcome=actual_outcome,
                was_correct=None
            )

        pred_id, pred_state_json, prob, conf, path_json = row
        pred_state = json.loads(pred_state_json)
        causal_path = json.loads(path_json) if path_json else []
        
        was_correct = self._evaluate_prediction(pred_state, actual_outcome)
        now = datetime.now().isoformat()
        
        db.execute(
            'UPDATE predictions SET actual_outcome=?, was_correct=?, verified_at=? WHERE id=?',
            (json.dumps(actual_outcome, ensure_ascii=False), was_correct, now, pred_id),
            commit=True
        )

        if causal_path and len(causal_path) >= 2:
            self._update_edge_confidence_in_conn(causal_path[0], causal_path[-1], was_correct)

        prediction = Prediction(predicted_state=pred_state, probability=prob, confidence=conf, causal_path=causal_path)
        return PredictionResult(
            prediction=prediction,
            actual_outcome=actual_outcome,
            was_correct=was_correct,
            verification_time=now
        )

    def learn_from_experience(self, experience: Dict) -> bool:
        intent = experience.get("intent_type", "")
        action = experience.get("model_name", "")
        success = experience.get("success", False)
        quality = experience.get("quality_score", 50)

        if not intent:
            return False

        action = action if action and action != "unknown" else "internal"

        source_id = f"intent:{intent}"
        method_id = f"method:{action}"
        target_id = f"outcome:{'success' if success else 'failure'}"

        self.add_causal_node(source_id, "intent", intent)
        self.add_causal_node(method_id, "method", action)
        self.add_causal_node(target_id, "outcome", "成功" if success else "失败")

        # Edge 1: intent → method (ENABLES)
        self._upsert_edge(source_id, method_id, CausalEdgeType.ENABLES, 0.5, 0.3)

        # Edge 2: method → outcome (CAUSES/PREVENTS)
        edge_type = CausalEdgeType.CAUSES if success else CausalEdgeType.PREVENTS
        prob = quality / 100.0 if success else 1.0 - quality / 100.0
        self._upsert_edge(method_id, target_id, edge_type, prob, 0.3)

        # Edge 3: intent → outcome (direct, for quick lookup)
        self._upsert_edge(source_id, target_id, edge_type, prob * 0.8, 0.2)

        return True

    def _upsert_edge(self, source_id: str, target_id: str,
                     edge_type: CausalEdgeType, prob: float, base_conf: float):
        existing = self._get_edge(source_id, target_id, edge_type)
        if existing:
            new_prob = (existing.probability * existing.evidence_count + prob) / (existing.evidence_count + 1)
            new_conf = min(1.0, existing.confidence + 0.1)
            db = DatabaseManager.get(self.db_path)
            db.execute(
                'UPDATE causal_edges SET probability=?, confidence=?, evidence_count=evidence_count+1, last_verified=? WHERE source_id=? AND target_id=? AND edge_type=?',
                (new_prob, new_conf, datetime.now().isoformat(), source_id, target_id, edge_type.value),
                commit=True
            )
        else:
            self.add_causal_edge(source_id, target_id, edge_type, prob, base_conf)

    def get_stats(self) -> Dict:
        db = DatabaseManager.get(self.db_path)
        node_count = db.query_one('SELECT COUNT(*) FROM causal_nodes')[0]
        edge_count = db.query_one('SELECT COUNT(*) FROM causal_edges')[0]
        pred_count = db.query_one('SELECT COUNT(*) FROM predictions')[0]
        verified = db.query_one('SELECT COUNT(*) FROM predictions WHERE was_correct IS NOT NULL')[0]
        correct = db.query_one('SELECT COUNT(*) FROM predictions WHERE was_correct = 1')[0]
        
        edge_type_dist = {}
        rows = db.query('SELECT edge_type, COUNT(*), AVG(probability), AVG(confidence) FROM causal_edges GROUP BY edge_type')
        for row in rows:
            edge_type_dist[row[0]] = {"count": row[1], "avg_probability": round(row[2], 3), "avg_confidence": round(row[3], 3)}

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "prediction_count": pred_count,
            "verified_count": verified,
            "accuracy": correct / max(1, verified),
            "edge_type_distribution": edge_type_dist,
        }

    def _find_relevant_edges(self, state: Dict, intent: str = "") -> List[CausalEdge]:
        edges = []
        search_terms = []
        
        if intent:
            search_terms.append(f"intent:{intent}")
        for k, v in state.items():
            if isinstance(v, str) and len(v) > 0:
                search_terms.append(f"intent:{v}")
                search_terms.append(f"outcome:{v}")
        
        if not search_terms:
            return edges
        
        db = DatabaseManager.get(self.db_path)
        placeholders = ' OR '.join(['source_id LIKE ?' for _ in search_terms])
        params = [f'%{t}%' for t in search_terms]
        rows = db.query(
            f'SELECT source_id, target_id, edge_type, probability, confidence, evidence_count, last_verified FROM causal_edges WHERE {placeholders} ORDER BY probability * confidence DESC LIMIT 20',
            params
        )
        for row in rows:
            edges.append(CausalEdge(
                source_id=row[0], target_id=row[1],
                edge_type=CausalEdgeType(row[2]),
                probability=row[3], confidence=row[4],
                evidence_count=row[5], last_verified=row[6]
            ))

        return edges

    def _get_node(self, node_id: str) -> Optional[CausalNode]:
        db = DatabaseManager.get(self.db_path)
        row = db.query_one('SELECT id, node_type, content, properties FROM causal_nodes WHERE id = ?', (node_id,))
        if row:
            return CausalNode(id=row[0], node_type=row[1], content=row[2], properties=json.loads(row[3]) if row[3] else {})
        return None

    def _get_edge(self, source_id: str, target_id: str, edge_type: CausalEdgeType) -> Optional[CausalEdge]:
        db = DatabaseManager.get(self.db_path)
        row = db.query_one(
            'SELECT source_id, target_id, edge_type, probability, confidence, evidence_count, last_verified FROM causal_edges WHERE source_id=? AND target_id=? AND edge_type=?',
            (source_id, target_id, edge_type.value)
        )
        if row:
            return CausalEdge(source_id=row[0], target_id=row[1], edge_type=CausalEdgeType(row[2]),
                              probability=row[3], confidence=row[4], evidence_count=row[5], last_verified=row[6])
        return None

    def _update_edge_confidence(self, source_id: str, target_id: str, was_correct: bool):
        self._update_edge_confidence_in_conn(source_id, target_id, was_correct)

    def _update_edge_confidence_in_conn(self, source_id: str, target_id: str, was_correct: bool):
        db = DatabaseManager.get(self.db_path)
        row = db.query_one(
            'SELECT probability, confidence, evidence_count FROM causal_edges WHERE source_id=? AND target_id=?',
            (source_id, target_id)
        )
        if row:
            old_prob, old_conf, count = row
            if was_correct:
                new_prob = old_prob + (1.0 - old_prob) * 0.1
                new_conf = min(1.0, old_conf + 0.05)
            else:
                new_prob = old_prob * 0.9
                new_conf = max(0.1, old_conf - 0.1)
            db.execute(
                'UPDATE causal_edges SET probability=?, confidence=?, evidence_count=evidence_count+1, last_verified=? WHERE source_id=? AND target_id=?',
                (new_prob, new_conf, datetime.now().isoformat(), source_id, target_id),
                commit=True
            )

    def _evaluate_prediction(self, predicted: Dict, actual: Dict) -> bool:
        if predicted.get("outcome") == actual.get("outcome"):
            return True
        pred_outcome = str(predicted.get("outcome", "")).lower()
        actual_outcome = str(actual.get("outcome", "")).lower()
        cn_to_en = {"成功": "success", "失败": "failure"}
        pred_norm = cn_to_en.get(pred_outcome, pred_outcome)
        actual_norm = cn_to_en.get(actual_outcome, actual_outcome)
        if pred_norm == actual_norm:
            return True
        if pred_outcome in actual_outcome or actual_outcome in pred_outcome:
            return True
        if predicted.get("edge_type") == actual.get("edge_type"):
            return True
        return False

    def _hash_state(self, state: Dict, intent: str = "") -> str:
        import hashlib
        content = json.dumps(state, sort_keys=True) + intent
        return hashlib.md5(content.encode()).hexdigest()[:12]


_world_model: Optional[WorldModel] = None


def get_world_model() -> WorldModel:
    global _world_model
    if _world_model is None:
        _world_model = WorldModel()
    return _world_model
