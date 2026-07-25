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

import threading
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from core.ports.adapters import get_storage_port

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
        self._db = get_storage_port(self.db_path)
        self._init_db()

    def _init_db(self):
        from pathlib import Path
        Path(self.db_path).parent.mkdir(exist_ok=True)

        db = self._db
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
        db = self._db
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
        db = self._db
        now = datetime.now().isoformat()
        db.execute(
            'INSERT OR REPLACE INTO causal_edges (source_id, target_id, edge_type, probability, confidence, evidence_count, last_verified, created_at) VALUES (?, ?, ?, ?, ?, 1, ?, ?)',
            (source_id, target_id, edge_type.value, probability, confidence, now, now),
            commit=True
        )
        return True

    def predict(self, current_state: Dict, intent: str = "", top_k: int = 3,
                injected_edges: List = None) -> Prediction:
        query_hash = self._hash_state(current_state, intent)
        relevant_edges = self._find_relevant_edges(current_state, intent)

        if injected_edges:
            existing_keys = {(e.source_id, e.target_id, e.edge_type if isinstance(e, CausalEdge) else CausalEdgeType(e.get("edge_type", "causes"))) for e in relevant_edges}
            converted = []
            for ie in injected_edges:
                if isinstance(ie, dict):
                    ie = CausalEdge(
                        source_id=ie.get("source_id", ""),
                        target_id=ie.get("target_id", ""),
                        edge_type=CausalEdgeType(ie.get("edge_type", "causes")),
                        probability=ie.get("probability", 0.5),
                        confidence=ie.get("confidence", 0.3),
                        evidence_count=1,
                        last_verified=datetime.now().isoformat(),
                    )
                converted.append(ie)
            for ie in converted:
                key = (ie.source_id, ie.target_id, ie.edge_type)
                if key not in existing_keys:
                    ie._injected = True
                    relevant_edges.insert(0, ie)
        
        if not relevant_edges:
            return Prediction(
                predicted_state={"outcome": "unknown", "reason": "no_causal_data"},
                probability=0.3,
                confidence=0.1,
                causal_path=[],
                alternatives=[]
            )

        sorted_edges = sorted(relevant_edges, key=lambda e: (
            2 if getattr(e, '_injected', False) else (1 if e.edge_type in (CausalEdgeType.CAUSES, CausalEdgeType.PREVENTS) else 0),
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
            db = self._db
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
            "has_high_confidence": (recommendation is not None and recommendation.get("confidence", 0) >= 0.5),
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
        db = self._db
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
        db = self._db
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

        if not was_correct and causal_path and len(causal_path) >= 2:
            try:
                self._generate_counterfactual_from_failure(causal_path, pred_state, actual_outcome)
            except Exception:
                pass

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
        plan = experience.get("plan", "")
        duration = experience.get("duration", 0.0)
        user_feedback = experience.get("user_feedback", 0)
        raw_input = experience.get("raw_input", "")
        response = experience.get("response", "")

        if not intent:
            return False

        action = action if action and action != "unknown" else "internal"

        strategy = self._extract_strategy(plan, action)

        source_id = f"intent:{intent}"
        method_id = f"method:{action}"
        strategy_id = f"strategy:{strategy}" if strategy and strategy != action else None

        if quality >= 80 and duration < 5:
            outcome_label = "high_quality_fast"
        elif quality >= 80 and duration >= 5:
            outcome_label = "high_quality_slow"
        elif quality >= 50:
            outcome_label = "medium_quality"
        elif success:
            outcome_label = "low_quality_success"
        else:
            outcome_label = "failure"
        target_id = f"outcome:{outcome_label}"

        self.add_causal_node(source_id, "intent", intent)
        self.add_causal_node(method_id, "method", action)
        if strategy_id:
            self.add_causal_node(strategy_id, "strategy", strategy)
        self.add_causal_node(target_id, "outcome", outcome_label)

        self._upsert_edge(source_id, method_id, CausalEdgeType.ENABLES, 0.5, 0.3)

        if strategy_id:
            self._upsert_edge(method_id, strategy_id, CausalEdgeType.ENABLES, 0.6, 0.3)
            _s_edge = CausalEdgeType.CAUSES if success else CausalEdgeType.PREVENTS
            self._upsert_edge(strategy_id, target_id, _s_edge,
                              quality / 100.0 if success else 1.0 - quality / 100.0, 0.3)

        edge_type = CausalEdgeType.CAUSES if success else CausalEdgeType.PREVENTS
        prob = quality / 100.0 if success else 1.0 - quality / 100.0

        if duration > 0:
            prob = prob * max(0.3, 1.0 - duration / 30.0)

        if user_feedback and user_feedback < 0:
            edge_type = CausalEdgeType.PREVENTS
            prob = max(prob, 0.6)

        self._upsert_edge(method_id, target_id, edge_type, prob, 0.3)
        self._upsert_edge(source_id, target_id, edge_type, prob * 0.8, 0.2)

        self._extract_content_causal_entities(raw_input, response, source_id, method_id, target_id, success, quality, outcome_label)

        return True

    def _extract_content_causal_entities(self, raw_input: str, response: str,
                                          source_id: str, method_id: str, target_id: str,
                                          success: bool, quality: int, outcome_label: str):
        """从经验内容中提取因果实体——让因果图从真实数据中生长"""
        if not raw_input and not response:
            return

        input_keywords = set()
        for word in raw_input.lower().split():
            if len(word) > 3 and word not in ("what", "how", "why", "that", "this", "with", "from", "the"):
                input_keywords.add(word[:20])
        for kw in list(input_keywords)[:5]:
            topic_id = f"topic:{kw}"
            self.add_causal_node(topic_id, "topic", kw)
            self._upsert_edge(topic_id, source_id, CausalEdgeType.CORRELATES, 0.3, 0.1)

        if response and len(response) > 50:
            resp_preview = response[:100].replace("\n", " ").strip()
            resp_id = f"response:{hash(resp_preview) % 10000}"
            self.add_causal_node(resp_id, "response", resp_preview[:80])
            self._upsert_edge(method_id, resp_id, CausalEdgeType.CAUSES if success else CausalEdgeType.PREVENTS,
                              quality / 100.0, 0.15)
            self._upsert_edge(resp_id, target_id, CausalEdgeType.CORRELATES, 0.3, 0.1)

        if success and quality >= 80 and raw_input:
            pattern_id = f"pattern:{source_id}_{method_id}_{outcome_label}"
            try:
                self.add_causal_node(pattern_id, "success_pattern",
                                     f"{source_id}+{method_id}→{target_id}")
                self._upsert_edge(source_id, pattern_id, CausalEdgeType.ENABLES, quality / 100.0, 0.2)
                self._upsert_edge(pattern_id, target_id, CausalEdgeType.CAUSES, quality / 100.0, 0.2)
            except Exception:
                pass

    def _extract_strategy(self, plan: str, fallback: str) -> str:
        if not plan or plan == "{}":
            return fallback
        try:
            import json
            p = json.loads(plan) if isinstance(plan, str) else plan
            if isinstance(p, dict):
                return p.get("strategy", p.get("approach", p.get("method", fallback)))
        except Exception:
            pass
        if len(plan) < 30:
            return plan
        return fallback

    def bridge_from_knowledge_graph(self, kg=None) -> Dict:
        if kg is None:
            try:
                from core.knowledge_graph import KnowledgeGraph
                kg = KnowledgeGraph()
            except Exception:
                return {"bridged": 0, "error": "knowledge_graph_unavailable"}
        bridged = 0
        try:
            db = get_storage_port(kg.db_path) if hasattr(kg, 'db_path') else None
            if db is None:
                return {"bridged": 0, "error": "no_db"}
            concept_rows = db.query(
                "SELECT id, content, importance FROM nodes WHERE node_type = 'concept' LIMIT 200"
            )
            for row in concept_rows:
                kg_id, content, importance = row[0], row[1], row[2]
                topic_id = f"topic:{content[:20]}"
                existing = self._db.query_one(
                    "SELECT id FROM causal_nodes WHERE id = ?", (topic_id,)
                )
                if not existing:
                    self.add_causal_node(topic_id, "topic", content)
                    bridged += 1
                conn_rows = db.query(
                    "SELECT target_id, connection_type, strength FROM connections WHERE source_id = ?",
                    (kg_id,)
                )
                for cr in conn_rows:
                    target_row = db.query_one("SELECT content FROM nodes WHERE id = ?", (cr[0],))
                    if target_row:
                        target_topic_id = f"topic:{target_row[0][:20]}"
                        existing_target = self._db.query_one(
                            "SELECT id FROM causal_nodes WHERE id = ?", (target_topic_id,)
                        )
                        if not existing_target:
                            self.add_causal_node(target_topic_id, "topic", target_row[0])
                            bridged += 1
                        edge_type = CausalEdgeType.CORRELATES
                        if cr[1] == "depends_on":
                            edge_type = CausalEdgeType.ENABLES
                        elif cr[1] == "contradicts":
                            edge_type = CausalEdgeType.PREVENTS
                        self._upsert_edge(topic_id, target_topic_id, edge_type,
                                          cr[2] if cr[2] else 0.3, 0.15)
            pattern_rows = db.query(
                "SELECT id, content, importance FROM nodes WHERE node_type = 'pattern' LIMIT 100"
            )
            for row in pattern_rows:
                kg_id, content, importance = row[0], row[1], row[2]
                pattern_id = f"pattern:kg_{kg_id}"
                existing = self._db.query_one(
                    "SELECT id FROM causal_nodes WHERE id = ?", (pattern_id,)
                )
                if not existing:
                    self.add_causal_node(pattern_id, "success_pattern", content)
                    bridged += 1
            truth_rows = db.query(
                "SELECT id, content, importance FROM nodes WHERE node_type = 'truth' LIMIT 300"
            )
            for row in truth_rows:
                kg_id, content, importance = row[0], row[1], row[2]
                truth_id = f"truth:kg_{kg_id}"
                existing = self._db.query_one(
                    "SELECT id FROM causal_nodes WHERE id = ?", (truth_id,)
                )
                if not existing:
                    self.add_causal_node(truth_id, "truth", content[:200])
                    bridged += 1
                conn_rows = db.query(
                    "SELECT target_id, connection_type, strength FROM connections WHERE source_id = ?",
                    (kg_id,)
                )
                for cr in conn_rows[:5]:
                    target_row = db.query_one("SELECT content, node_type FROM nodes WHERE id = ?", (cr[0],))
                    if target_row and target_row[1] == 'truth':
                        target_truth_id = f"truth:kg_{cr[0]}"
                        existing_target = self._db.query_one(
                            "SELECT id FROM causal_nodes WHERE id = ?", (target_truth_id,)
                        )
                        if not existing_target:
                            self.add_causal_node(target_truth_id, "truth", target_row[0][:200])
                            bridged += 1
                        edge_type = CausalEdgeType.CORRELATES
                        if cr[1] == "extends":
                            edge_type = CausalEdgeType.ENABLES
                        elif cr[1] == "contradicts":
                            edge_type = CausalEdgeType.PREVENTS
                        self._upsert_edge(truth_id, target_truth_id, edge_type,
                                          cr[2] if cr[2] else 0.3, 0.15)
        except Exception as e:
            logger.warning(f"知识图谱桥接部分失败: {e}")
        return {"bridged": bridged}

    def mine_causal_patterns_from_pool(self, sample_size: int = 500) -> Dict:
        """
        从经验池主动挖掘因果模式——'拉模式'，让因果图从真实数据中生长。
        统计条件概率 P(success|intent=X, method=Y)，发现非模板因果边。
        """
        try:
            db = get_storage_port("data/experience_pool.db")
            rows = db.query(
                "SELECT intent_type, model_name, success, quality_score, duration "
                "FROM experiences ORDER BY ROWID DESC LIMIT ?",
                (sample_size,)
            )
            if not rows:
                return {"patterns_found": 0}

            pair_stats = {}
            for row in rows:
                intent, method, success, quality, duration = row
                method = method if method and method != "unknown" else "internal"
                key = (intent, method)
                if key not in pair_stats:
                    pair_stats[key] = {"total": 0, "success": 0, "quality_sum": 0, "duration_sum": 0.0}
                pair_stats[key]["total"] += 1
                if success:
                    pair_stats[key]["success"] += 1
                pair_stats[key]["quality_sum"] += quality or 50
                pair_stats[key]["duration_sum"] += duration or 0.0

            patterns_found = 0
            for (intent, method), stats in pair_stats.items():
                if stats["total"] < 3:
                    continue
                success_rate = stats["success"] / stats["total"]
                avg_quality = stats["quality_sum"] / stats["total"]
                avg_duration = stats["duration_sum"] / stats["total"]

                source_id = f"intent:{intent}"
                method_id = f"method:{method}"

                if success_rate > 0.8 and avg_quality >= 70:
                    target_id = "outcome:high_quality_fast" if avg_duration < 5 else "outcome:high_quality_slow"
                    self._upsert_edge(source_id, method_id, CausalEdgeType.ENABLES, success_rate, 0.5)
                    self._upsert_edge(method_id, target_id, CausalEdgeType.CAUSES, avg_quality / 100.0, 0.4)
                    patterns_found += 1
                elif success_rate < 0.3:
                    target_id = "outcome:failure"
                    self._upsert_edge(method_id, target_id, CausalEdgeType.PREVENTS, 1.0 - success_rate, 0.4)
                    patterns_found += 1

                if avg_quality < 50 and stats["total"] >= 5:
                    weak_id = f"weakness:{intent}_{method}"
                    self.add_causal_node(weak_id, "weakness", f"{intent}+{method} avg_q={avg_quality:.0f}")
                    self._upsert_edge(method_id, weak_id, CausalEdgeType.CORRELATES, 0.4, 0.2)
                    patterns_found += 1

            logger.info(f"⛏️ 因果模式挖掘: {patterns_found}个模式从{len(pair_stats)}个(intent,method)对中发现")
            return {"patterns_found": patterns_found, "pairs_analyzed": len(pair_stats)}
        except Exception as e:
            logger.warning(f"因果模式挖掘跳过: {e}")
            return {"patterns_found": 0, "error": str(e)}

    def _upsert_edge(self, source_id: str, target_id: str,
                     edge_type: CausalEdgeType, prob: float, base_conf: float):
        existing = self._get_edge(source_id, target_id, edge_type)
        if existing:
            new_prob = (existing.probability * existing.evidence_count + prob) / (existing.evidence_count + 1)
            new_conf = min(1.0, existing.confidence + 0.1)
            db = self._db
            db.execute(
                'UPDATE causal_edges SET probability=?, confidence=?, evidence_count=evidence_count+1, last_verified=? WHERE source_id=? AND target_id=? AND edge_type=?',
                (new_prob, new_conf, datetime.now().isoformat(), source_id, target_id, edge_type.value),
                commit=True
            )
        else:
            self.add_causal_edge(source_id, target_id, edge_type, prob, base_conf)

    def get_related_nodes(self, node_id: str, max_depth: int = 2, max_results: int = 10) -> List[Dict]:
        discovered = []
        visited = {node_id}
        frontier = [node_id]
        db = self._db

        for depth in range(max_depth):
            next_frontier = []
            placeholders = ','.join(['?' for _ in frontier])
            rows = db.query(
                f'SELECT source_id, target_id, edge_type, probability, confidence FROM causal_edges WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders})',
                frontier + frontier
            )
            for row in rows:
                src, tgt, etype, prob, conf = row
                neighbor = tgt if src in visited else src
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.append(neighbor)
                    node = self._get_node(neighbor)
                    discovered.append({
                        "id": neighbor,
                        "content": node.content if node else neighbor,
                        "node_type": node.node_type if node else "unknown",
                        "relation": etype,
                        "probability": prob,
                        "confidence": conf,
                        "depth": depth + 1,
                    })
                    if len(discovered) >= max_results:
                        return discovered
            frontier = next_frontier
            if not frontier:
                break

        return discovered

    def simulate(self, current_state: Dict, hypothetical_changes: Dict, intent: str = "") -> Dict:
        original_edges = self._find_relevant_edges(current_state, intent)
        original_pred = self.predict(current_state, intent)

        modified_state = dict(current_state)
        modified_state.update(hypothetical_changes)

        override_edges = []
        for key, value in hypothetical_changes.items():
            source_id = f"intent:{key}" if not key.startswith(("intent:", "method:", "outcome:")) else key
            target_id = f"outcome:{value}" if not str(value).startswith(("intent:", "method:", "outcome:")) else str(value)
            override_edges.append({
                "source_id": source_id,
                "target_id": target_id,
                "edge_type": "causes",
                "probability": 0.7,
                "confidence": 0.5,
            })

        modified_pred = self.predict(modified_state, intent, injected_edges=override_edges)

        delta_prob = modified_pred.probability - original_pred.probability
        delta_conf = modified_pred.confidence - original_pred.confidence

        return {
            "original_prediction": {
                "outcome": original_pred.predicted_state,
                "probability": original_pred.probability,
                "confidence": original_pred.confidence,
            },
            "simulated_prediction": {
                "outcome": modified_pred.predicted_state,
                "probability": modified_pred.probability,
                "confidence": modified_pred.confidence,
            },
            "hypothetical_changes": hypothetical_changes,
            "delta_probability": round(delta_prob, 4),
            "delta_confidence": round(delta_conf, 4),
            "improves_outcome": delta_prob > 0 and delta_conf > 0,
            "risk_level": "low" if delta_prob >= -0.1 else ("medium" if delta_prob >= -0.3 else "high"),
            "override_edges_applied": len(override_edges),
        }

    def find_causal_paths(self, source_id: str, target_id: str, max_depth: int = 4) -> List[Dict]:
        paths = []
        visited_edges = set()
        db = self._db

        def _bfs(current_path, current_prob, current_conf):
            current_node = current_path[-1]
            if len(current_path) > max_depth + 1:
                return
            if current_node == target_id and len(current_path) > 1:
                paths.append({
                    "path": list(current_path),
                    "probability": round(current_prob, 4),
                    "confidence": round(current_conf, 4),
                    "score": round(current_prob * current_conf, 4),
                    "length": len(current_path) - 1,
                })
                return

            rows = db.query(
                'SELECT target_id, edge_type, probability, confidence FROM causal_edges WHERE source_id = ?',
                (current_node,)
            )
            for row in rows:
                next_node, etype, prob, conf = row
                edge_key = (current_node, next_node, etype)
                if edge_key in visited_edges:
                    continue
                if next_node in current_path:
                    continue
                visited_edges.add(edge_key)
                mult = prob if etype in ("causes", "enables") else (1.0 - prob)
                _bfs(current_path + [next_node], current_prob * mult, current_conf * conf)
                visited_edges.discard(edge_key)

        _bfs([source_id], 1.0, 1.0)
        paths.sort(key=lambda p: p["score"], reverse=True)
        return paths[:5]

    def trace_with_spirit(self, query: str, context_type: str = "query") -> Dict:
        """
        P5-3a: 精神共振驱动的因果追溯
        
        当共振检测到PURSUE_ESSENCE/LOGICAL_SELF_CONSISTENT时，
        自动触发深层因果链追溯，而非停留在表面预测。
        
        Returns:
            {"resonances": list, "causal_paths": list, "deep_trace": dict, "truth_feedback": dict}
        """
        spirit_resonances = []
        try:
            from core.spirit_core import spirit_core
            spirit_resonances = spirit_core.resonate(query, context_type=context_type)
        except Exception:
            pass

        top_principles = [r["principle"] for r in spirit_resonances[:3]] if spirit_resonances else []

        deep_trace = None
        causal_paths = []
        search_terms = self._extract_causal_seeds(query)

        if "PURSUE_ESSENCE" in top_principles:
            _outcome_targets = ["outcome:success", "outcome:high_quality_fast", "outcome:medium_quality"]
            for seed in search_terms[:3]:
                for target in _outcome_targets:
                    paths = self.find_causal_paths(seed, target, max_depth=4)
                    causal_paths.extend(paths)
            if causal_paths:
                best = max(causal_paths, key=lambda p: p["score"]) if causal_paths else None
                deep_trace = {
                    "trigger": "PURSUE_ESSENCE",
                    "seed_nodes": search_terms[:3],
                    "best_path": best,
                    "total_paths_found": len(causal_paths),
                }
            else:
                deep_trace = {
                    "trigger": "PURSUE_ESSENCE",
                    "seed_nodes": search_terms[:3],
                    "best_path": None,
                    "total_paths_found": 0,
                    "guidance": self._generate_essence_guidance(query, search_terms),
                }

        if "LOGICAL_SELF_CONSISTENT" in top_principles and not deep_trace:
            contradictions = []
            for seed in search_terms[:2]:
                success_paths = []
                failure_paths = []
                for target in ["outcome:success", "outcome:high_quality_fast"]:
                    success_paths.extend(self.find_causal_paths(seed, target, max_depth=3))
                for target in ["outcome:failure"]:
                    failure_paths.extend(self.find_causal_paths(seed, target, max_depth=3))
                if success_paths and failure_paths:
                    contradictions.append({
                        "seed": seed,
                        "success_path": success_paths[0]["path"],
                        "failure_path": failure_paths[0]["path"],
                    })
            if contradictions:
                deep_trace = {
                    "trigger": "LOGICAL_SELF_CONSISTENT",
                    "contradictions": contradictions,
                }
            else:
                deep_trace = {
                    "trigger": "LOGICAL_SELF_CONSISTENT",
                    "contradictions": [],
                    "guidance": self._generate_consistency_guidance(query),
                }

        if not deep_trace and spirit_resonances:
            deep_trace = {
                "trigger": spirit_resonances[0]["principle"],
                "seed_nodes": search_terms[:3],
                "best_path": None,
                "total_paths_found": 0,
                "guidance": f"共振原则'{spirit_resonances[0]['principle']}'建议方向: {spirit_resonances[0]['drive_direction']}",
            }

        truth_feedback = self._compute_truth_feedback(spirit_resonances, causal_paths)

        try:
            from core.monitoring.runtime_trigger_monitor import trigger_monitor
            trigger_monitor.record("trace_with_spirit", triggered=True)
            trigger_monitor.record("trace_with_spirit.deep_trace", triggered=deep_trace is not None)
            trigger_monitor.record("trace_with_spirit.causal_paths", triggered=len(causal_paths) > 0, empty_result=len(causal_paths) == 0)
            trigger_monitor.record("trace_with_spirit.guidance", triggered=deep_trace is not None and "guidance" in (deep_trace or {}), degraded=deep_trace is not None and deep_trace.get("best_path") is None)
        except Exception:
            pass

        return {
            "resonances": spirit_resonances[:3],
            "causal_paths": causal_paths[:5],
            "deep_trace": deep_trace,
            "truth_feedback": truth_feedback,
        }

    def _extract_causal_seeds(self, query: str) -> List[str]:
        seeds = []
        stop_words = {"为什么", "怎么", "如何", "什么", "哪里", "哪个", "怎样", "的是", "可以", "应该", "需要", "能够", "已经", "可能", "就是", "因为", "所以", "但是", "而且", "或者", "如果", "那么", "虽然", "不过", "然而", "你", "我", "他", "她", "的", "了", "是", "在", "有", "和", "与", "也", "都", "这", "那", "个", "吗", "呢", "吧", "啊", "么", "如何", "什么", "怎样", "你的", "我的", "他的"}
        keywords = []
        try:
            import re
            full_match = re.findall(r'[\u4e00-\u9fff]+', query)
            for segment in full_match:
                for i in range(len(segment) - 1):
                    word = segment[i:i+2]
                    if word not in stop_words:
                        keywords.append(word)
        except Exception:
            keywords.append(query[:10])

        keywords = list(dict.fromkeys(keywords))[:8]

        intent_map = {
            "理解": ["self_reference", "metacognitive", "deep_thinking"],
            "自己": ["self_reference", "self_reflection", "autonomous_reflection"],
            "学习": ["learning_trigger", "self_reflection"],
            "认知": ["metacognitive", "metacognitive_background", "deep_thinking"],
            "思考": ["deep_thinking", "pattern_essence_reasoning"],
            "反思": ["self_reflection", "autonomous_reflection"],
            "感受": ["self_reference", "background_collect"],
            "优化": ["learning_trigger", "pattern_code_generation"],
            "知道": ["general", "deep_thinking"],
            "能力": ["learning_trigger", "pattern_code_generation"],
            "过程": ["metacognitive", "deep_thinking"],
            "最近": ["background_collect", "self_reflection"],
            "学到": ["learning_trigger", "self_reflection"],
            "成长": ["learning_trigger", "autonomous_reflection"],
            "改变": ["learning_trigger", "pattern_code_generation"],
            "本质": ["deep_thinking", "pattern_essence_reasoning"],
            "意义": ["deep_thinking", "pattern_essence_reasoning"],
        }

        for kw in keywords[:5]:
            mapped_intents = intent_map.get(kw, [])
            found = False
            for mi in mapped_intents:
                candidate = f"intent:{mi}"
                existing = self._db.query_one("SELECT id FROM causal_nodes WHERE id = ?", (candidate,))
                if existing:
                    seeds.append(candidate)
                    found = True
            if not found:
                prefix = f"intent:{kw}"
                existing = self._db.query_one("SELECT id FROM causal_nodes WHERE id = ?", (prefix,))
                if existing:
                    seeds.append(prefix)
                else:
                    like_pattern = f"%{kw}%"
                    matches = self._db.query(
                        "SELECT id FROM causal_nodes WHERE (id LIKE ? OR content LIKE ?) LIMIT 3",
                        (like_pattern, like_pattern)
                    )
                    for m in matches:
                        seeds.append(m[0])
                    if not matches:
                        seeds.append(prefix)

        if not seeds:
            seeds.append(f"intent:general")
        return seeds[:5]

    def _generate_essence_guidance(self, query: str, seeds: List[str]) -> str:
        """P5-3a: 因果图为空时，基于追求本质原则生成方向性指引"""
        keywords = "、".join(s.replace("intent:", "") for s in seeds[:3])
        return f"因果图尚无'{keywords}'的因果链数据。建议追溯方向：从'{keywords}'的根因出发，分析其与成功/失败结果的因果关系，并将经验注入因果图"

    def _generate_consistency_guidance(self, query: str) -> str:
        """P5-3a: 因果图为空时，基于逻辑自洽原则生成方向性指引"""
        return f"因果图尚无矛盾路径数据。建议检测方向：对比查询中涉及的因果路径是否存在成功路径与失败路径的矛盾，若发现矛盾则坦诚标注"

    def _compute_truth_feedback(self, resonances: list, causal_paths: list) -> Dict:
        """
        P5-3a: 因果验证结果反馈到真谛权重
        
        当因果路径的累积置信度高于阈值时，增强相关真谛的证据计数。
        """
        if not causal_paths:
            resonance_boost = False
            if resonances:
                top = resonances[0]
                if top.get("strength", 0) >= 0.4:
                    resonance_boost = True
            return {
                "action": "resonance_guided" if resonance_boost else "none",
                "reason": "no_causal_paths" + ("_but_resonance_suggests_direction" if resonance_boost else ""),
                "resonance_principle": resonances[0]["principle"] if resonance_boost else None,
            }

        best_path = max(causal_paths, key=lambda p: p.get("score", 0))
        path_confidence = best_path.get("confidence", 0)

        if path_confidence >= 0.7:
            return {
                "action": "boost_evidence",
                "reason": "high_confidence_causal_path",
                "path_confidence": path_confidence,
                "path": best_path.get("path", []),
            }
        elif path_confidence >= 0.4:
            return {
                "action": "neutral",
                "reason": "moderate_confidence",
                "path_confidence": path_confidence,
            }
        else:
            return {
                "action": "flag_uncertainty",
                "reason": "low_confidence_causal_path",
                "path_confidence": path_confidence,
            }

    def get_stats(self) -> Dict:
        db = self._db
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

        db = self._db
        placeholders = ' OR '.join(['source_id LIKE ?' for _ in search_terms])
        params = [f'%{t}%' for t in search_terms]
        rows = db.query(
            f'SELECT source_id, target_id, edge_type, probability, confidence, evidence_count, last_verified FROM causal_edges WHERE {placeholders} ORDER BY probability * confidence DESC LIMIT 20',
            params
        )
        direct_targets = set()
        for row in rows:
            edges.append(CausalEdge(
                source_id=row[0], target_id=row[1],
                edge_type=CausalEdgeType(row[2]),
                probability=row[3], confidence=row[4],
                evidence_count=row[5], last_verified=row[6]
            ))
            direct_targets.add(row[1])

        if direct_targets and len(edges) < 10:
            ph = ','.join(['?' for _ in direct_targets])
            indirect_rows = db.query(
                f'SELECT source_id, target_id, edge_type, probability, confidence, evidence_count, last_verified FROM causal_edges WHERE source_id IN ({ph}) ORDER BY probability * confidence DESC LIMIT 10',
                list(direct_targets)
            )
            existing = {(e.source_id, e.target_id, e.edge_type) for e in edges}
            for row in indirect_rows:
                key = (row[0], row[1], row[2])
                if key not in existing:
                    edges.append(CausalEdge(
                        source_id=row[0], target_id=row[1],
                        edge_type=CausalEdgeType(row[2]),
                        probability=row[3] * 0.8,
                        confidence=row[4] * 0.8,
                        evidence_count=row[5], last_verified=row[6]
                    ))
                    existing.add(key)

        return edges

    def _get_node(self, node_id: str) -> Optional[CausalNode]:
        db = self._db
        row = db.query_one('SELECT id, node_type, content, properties FROM causal_nodes WHERE id = ?', (node_id,))
        if row:
            return CausalNode(id=row[0], node_type=row[1], content=row[2], properties=json.loads(row[3]) if row[3] else {})
        return None

    def _get_edge(self, source_id: str, target_id: str, edge_type: CausalEdgeType) -> Optional[CausalEdge]:
        db = self._db
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
        db = self._db
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

    def _generate_counterfactual_from_failure(self, causal_path: list, predicted: Dict, actual: Dict):
        pred_outcome = predicted.get("outcome", "unknown")
        actual_outcome = actual.get("outcome", "unknown")
        if len(causal_path) >= 2:
            actual_action = causal_path[-1] if causal_path[-1].startswith("method:") else causal_path[0]
            alternatives = self._db.query(
                "SELECT target_id FROM causal_edges WHERE source_id = ? AND target_id != ? LIMIT 3",
                (causal_path[0], causal_path[-1])
            )
            for alt in alternatives:
                alt_action = alt[0]
                lesson = f"预测{pred_outcome}但实际{actual_outcome}，若选{alt_action}替代{actual_action}可能改善"
                self.save_counterfactual(
                    intent=causal_path[0],
                    actual_action=actual_action,
                    alternative_action=alt_action,
                    actual_score=0.0,
                    alt_score=0.5,
                    would_be_better=True,
                    lesson=lesson
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

        return False

    def _hash_state(self, state: Dict, intent: str = "") -> str:
        import hashlib
        content = json.dumps(state, sort_keys=True) + intent
        return hashlib.md5(content.encode()).hexdigest()[:12]


_world_model: Optional[WorldModel] = None
_world_model_lock = threading.Lock()


def get_world_model() -> WorldModel:
    global _world_model
    if _world_model is None:
        with _world_model_lock:
            if _world_model is None:
                instance = WorldModel()
                _world_model = instance
    return _world_model
