"""
L3: 认知残差层 (Cognitive Residual)

对应ResNet残差连接：输出 = 输入 + 学习的残差
新认知 = 旧状态 + 增量变化，保持连续性，防止退化。

CBNR-AGI 2.0增强：
- 树搜索工作记忆：维护显式的假设搜索树作为共享工作记忆
- 多智能体制衡：Orchestrator(探索)与Critic(验证)协同
  任何一方都不能单方面驱动系统

关键问句："这个问题与我处理过的哪些问题相似？我能在旧方案上只调整差异？"
"""

import time
import hashlib

import json as _json
import numpy as np
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from core.ports.adapters import get_storage_port


class NodeType(Enum):
    HYPOTHESIS = "hypothesis"
    EVIDENCE = "evidence"
    DECISION = "decision"
    DEAD_END = "dead_end"


@dataclass
class SearchNode:
    node_id: str
    node_type: NodeType
    content: str
    confidence: float
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    score: float = 0.0
    explored: bool = False


@dataclass
class ResidualResult:
    previous_state_id: Optional[str]
    delta: Dict[str, Any] = field(default_factory=dict)
    new_state: Dict[str, Any] = field(default_factory=dict)
    state_reuse_rate: float = 0.0
    search_tree_size: int = 0
    orchestrator_hypotheses: int = 0
    critic_rejections: int = 0
    fallback_used: bool = False
    timestamp: float = 0.0


class SearchTree:
    """
    树搜索工作记忆 - 维护显式的假设搜索树
    对应Arbor架构：作为多智能体间的共享工作记忆
    """

    def __init__(self, max_size: int = 50):
        self._nodes: Dict[str, SearchNode] = {}
        self._root_id: Optional[str] = None
        self._max_size = max_size

    def add_node(self, content: str, node_type: NodeType, parent_id: Optional[str] = None, confidence: float = 0.5) -> str:
        node_id = hashlib.md5(f"{content}{time.time()}".encode()).hexdigest()[:10]
        node = SearchNode(
            node_id=node_id,
            node_type=node_type,
            content=content,
            confidence=confidence,
            parent_id=parent_id,
        )
        
        if parent_id and parent_id in self._nodes:
            self._nodes[parent_id].children_ids.append(node_id)
        
        if not self._root_id:
            self._root_id = node_id
        
        self._nodes[node_id] = node
        
        if len(self._nodes) > self._max_size:
            self._prune()
        
        return node_id

    def get_best_path(self) -> List[SearchNode]:
        if not self._root_id:
            return []
        
        path = []
        current_id = self._root_id
        
        while current_id:
            node = self._nodes.get(current_id)
            if not node:
                break
            path.append(node)
            
            if not node.children_ids:
                break
            
            best_child = max(
                [self._nodes[cid] for cid in node.children_ids if cid in self._nodes],
                key=lambda n: n.score,
                default=None,
            )
            current_id = best_child.node_id if best_child else None
        
        return path

    def update_scores(self, node_id: str, score_delta: float):
        if node_id in self._nodes:
            self._nodes[node_id].score += score_delta
            self._nodes[node_id].explored = True

    def size(self) -> int:
        return len(self._nodes)

    def _prune(self):
        dead_ends = [nid for nid, n in self._nodes.items() if n.node_type == NodeType.DEAD_END]
        for nid in dead_ends[:10]:
            self._remove_node(nid)

    def _remove_node(self, node_id: str):
        node = self._nodes.pop(node_id, None)
        if node and node.parent_id and node.parent_id in self._nodes:
            parent = self._nodes[node.parent_id]
            parent.children_ids = [c for c in parent.children_ids if c != node_id]


class OrchestratorAgent:
    """
    探索驱动智能体 - 提出假设、探索可能性
    对应Arbor架构的Orchestrator
    """

    def explore(self, core_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        hypotheses = []
        topic = core_result.get("topic", "")
        entities = core_result.get("entities", [])
        causal_chain = core_result.get("causal_chain", [])
        counterfactuals = core_result.get("counterfactuals", [])
        
        for chain in causal_chain[:2]:
            hypotheses.append({
                "type": "causal_hypothesis",
                "content": chain.get("effect", ""),
                "confidence": chain.get("confidence", 0.5),
                "source": chain.get("source", "causal_model"),
            })
        
        for cf in counterfactuals[:2]:
            hypotheses.append({
                "type": "counterfactual_hypothesis",
                "content": cf.get("required_conditions", ""),
                "confidence": cf.get("confidence", 0.5),
                "source": cf.get("source", "counterfactual_model"),
            })
        
        try:
            from core.world_model import get_world_model
            wm = get_world_model()
            for entity in entities[:2]:
                try:
                    related = wm.get_related_nodes(entity)
                    if related:
                        for node in related[:2]:
                            hypotheses.append({
                                "type": "world_model_hypothesis",
                                "content": f"{entity}与{node}存在关联",
                                "confidence": 0.6,
                                "source": "world_model",
                            })
                except Exception:
                    logger.warning("操作降级跳过")
        except Exception:
            logger.warning("操作降级跳过")
        
        if not hypotheses:
            hypotheses.append({
                "type": "default_hypothesis",
                "content": f"关于「{topic[:30]}」的直接推理",
                "confidence": 0.5,
                "source": "default",
            })
        
        return hypotheses


class CriticAgent:
    """
    验证制衡智能体 - 审查假设、拒绝低质量推理
    对应Arbor架构的Critic
    """

    MIN_CONFIDENCE = 0.3
    MAX_HYPOTHESES = 5

    def validate(self, hypotheses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        validated = []
        rejected = 0
        seen_contents = set()
        
        for h in hypotheses:
            if h.get("confidence", 0) < self.MIN_CONFIDENCE:
                rejected += 1
                continue
            
            content = h.get("content", "")
            if len(content) < 3:
                rejected += 1
                continue
            
            if h.get("source") == "fallback" and h.get("confidence", 0) < 0.5:
                rejected += 1
                continue
            
            generic_phrases = ["的因果后果", "的前提条件", "直接推理"]
            if any(p in content for p in generic_phrases) and h.get("confidence", 0) < 0.6:
                rejected += 1
                continue
            
            content_key = content[:30].strip()
            if content_key in seen_contents:
                rejected += 1
                continue
            seen_contents.add(content_key)
            
            if h.get("type") == "causal_hypothesis":
                topic_words = set(w for w in content if '\u4e00' <= w <= '\u9fff')
                if len(topic_words) < 2 and h.get("confidence", 0) < 0.5:
                    rejected += 1
                    continue
            
            if h.get("type") == "counterfactual_hypothesis":
                if content.startswith("实现") and "前提条件" in content and h.get("confidence", 0) < 0.5:
                    rejected += 1
                    continue
            
            validated.append(h)
            
            if len(validated) >= self.MAX_HYPOTHESES:
                break
        
        return validated


class CognitiveResidual:
    """
    认知残差层
    
    四步残差处理：
    1. 检索历史状态 - 从记忆层检索相关的历史认知状态
    2. 计算增量 - 只学习与历史状态不同的部分
    3. 残差连接 - 输出 = 历史状态 + 增量
    4. 状态更新 - 缓存新状态供未来复用
    """

    def __init__(self):
        self._search_tree = SearchTree()
        self._orchestrator = OrchestratorAgent()
        self._critic = CriticAgent()
        self._state_cache: Dict[str, Dict] = {}
        self._process_count = 0
        self._reuse_count = 0
        self._db_path = "data/cbnr_l3_state.db"
        self._embedding_available: Optional[bool] = None
        self._state_manager = None
        self._css_selector = None
        self._load_search_tree()
        try:
            from core.cognitive_state.manager import CognitiveStateManager
            self._state_manager = CognitiveStateManager()
        except Exception as e:
            logger.warning(f"认知状态管理器初始化降级: {e}")
        try:
            from core.cognitive_state.embedding_cache import EmbeddingCache, CSSSelector
            self._css_selector = CSSSelector(EmbeddingCache(), subset_size=30)
            logger.info("🧮 CSS列选择器已初始化")
        except Exception as e:
            logger.warning(f"CSS选择器初始化降级: {e}")

    def process(self, current_input: Dict[str, Any], bottleneck_result: Dict[str, Any]) -> ResidualResult:
        self._process_count += 1
        
        previous = self._retrieve_previous_state(current_input)
        
        hypotheses = self._orchestrator.explore(bottleneck_result)
        orchestrator_count = len(hypotheses)
        
        validated = self._critic.validate(hypotheses)
        critic_rejections = orchestrator_count - len(validated)
        
        for h in validated:
            node_type = NodeType.HYPOTHESIS if h["type"] == "causal_hypothesis" else NodeType.EVIDENCE
            node_id = self._search_tree.add_node(
                content=h["content"],
                node_type=node_type,
                confidence=h.get("confidence", 0.5),
            )
            self._search_tree.update_scores(node_id, h.get("confidence", 0.5))
        
        delta = self._compute_delta(previous, bottleneck_result, validated)
        
        new_state = self._residual_add(previous, delta)

        topic = current_input.get("topic", "") or bottleneck_result.get("topic", "")
        if topic:
            topic_emb = self._compute_embedding(topic)
            if topic_emb is not None:
                new_state["_topic_embedding_dim"] = len(topic_emb)
                new_state["_embedding_source"] = "shared_embedding"

        fallback_used = False
        if not new_state.get("has_meaningful_output"):
            new_state = self._fallback_path(current_input, previous)
            fallback_used = True
        
        state_id = self._update_state(new_state)
        
        reuse_rate = 0.0
        if previous:
            self._reuse_count += 1
            reused_keys = len(set(previous.keys()) & set(new_state.keys()))
            total_keys = max(len(set(previous.keys()) | set(new_state.keys())), 1)
            reuse_rate = reused_keys / total_keys
        
        result = ResidualResult(
            previous_state_id=previous.get("_state_id") if previous else None,
            delta=delta,
            new_state=new_state,
            state_reuse_rate=reuse_rate,
            search_tree_size=self._search_tree.size(),
            orchestrator_hypotheses=orchestrator_count,
            critic_rejections=critic_rejections,
            fallback_used=fallback_used,
            timestamp=time.time(),
        )
        
        logger.warning(f"认知残差: 复用率={reuse_rate:.1%}, 搜索树={self._search_tree.size()}, 假设={orchestrator_count}, 拒绝={critic_rejections}")
        
        if self._state_manager:
            quality = result.quality_score if hasattr(result, 'quality_score') else 0.5
            self._state_manager.update(quality)
        
        return result

    def _retrieve_previous_state(self, input_data: Dict) -> Optional[Dict]:
        topic = input_data.get("topic", "")
        if not topic:
            return None

        semantic_result = self._semantic_retrieve(topic)
        if semantic_result:
            if semantic_result.get("_sensing_mode") == "blind":
                logger.warning(f"场域失明: embedding不可用, 降级为关键词匹配")
            return semantic_result

        try:
            db = get_storage_port("data/experience_pool.db")
            row = db.query_one(
                "SELECT raw_input, response, quality_score FROM experiences WHERE raw_input LIKE ? ORDER BY quality_score DESC LIMIT 1",
                (f"%{topic[:30]}%",)
            )
            if row:
                return {
                    "_state_id": "retrieved_from_experience",
                    "similar_input": row[0][:100],
                    "previous_response": row[1][:100],
                    "previous_quality": row[2],
                }
        except Exception:
            logger.warning("操作降级跳过")
        
        return None

    def _compute_embedding(self, text: str) -> Optional[np.ndarray]:
        if self._embedding_available is False:
            return None
        try:
            from core.shared_embedding import get_embeddings
            emb = get_embeddings([text])
            if emb is not None and len(emb) > 0:
                self._embedding_available = True
                return emb[0]
            self._embedding_available = False
            return None
        except Exception as e:
            logger.warning(f"语义向量计算降级: {e}")
            self._embedding_available = False
            return None

    def _semantic_retrieve(self, topic: str) -> Optional[Dict]:
        if self._state_manager and not self._state_manager.should_use_semantic_retrieve():
            return {
                "_state_id": "keyword_fallback",
                "_sensing_mode": "blind",
                "_blind_reason": "low_budget_keyword_mode",
                "similar_input": None,
                "previous_response": None,
                "previous_quality": 0,
                "semantic_similarity": 0.0,
            }

        query_emb = self._compute_embedding(topic)
        if query_emb is None:
            return {
                "_state_id": "keyword_fallback",
                "_sensing_mode": "blind",
                "_blind_reason": "embedding_unavailable",
                "similar_input": None,
                "previous_response": None,
                "previous_quality": 0,
                "semantic_similarity": 0.0,
            }

        if self._state_manager:
            self._state_manager.cache_embedding(f"query:{topic[:50]}", query_emb)

        if self._css_selector:
            result = self._semantic_retrieve_css(query_emb)
            if result:
                return result

        return self._semantic_retrieve_fallback(query_emb)

    def _semantic_retrieve_css(self, query_emb: np.ndarray) -> Optional[Dict]:
        """CSS路径：用预计算的代表性子集做检索，O(K) embedding比较"""
        try:
            texts, embeddings = self._css_selector.get_subset()
            if not embeddings:
                return None

            best_idx = -1
            best_sim = 0.4
            query_norm = np.linalg.norm(query_emb)

            for i, emb in enumerate(embeddings):
                emb_norm = np.linalg.norm(emb)
                if emb_norm < 1e-8:
                    continue
                cos_sim = float(np.dot(query_emb, emb) / (query_norm * emb_norm + 1e-8))
                if cos_sim > best_sim:
                    best_sim = cos_sim
                    best_idx = i

            if best_idx < 0:
                return None

            try:
                db = get_storage_port("data/experience_pool.db")
                row = db.query_one(
                    "SELECT raw_input, response, quality_score FROM experiences WHERE raw_input LIKE ? LIMIT 1",
                    (f"%{texts[best_idx][:30]}%",)
                )
                if row:
                    return {
                        "_state_id": "css_retrieved",
                        "similar_input": row[0][:100],
                        "previous_response": row[1][:100],
                        "previous_quality": row[2],
                        "semantic_similarity": best_sim,
                        "_retrieval_path": "css_subset",
                    }
            except Exception:
                pass

            return {
                "_state_id": "css_embedding_only",
                "similar_input": texts[best_idx][:100],
                "previous_response": None,
                "previous_quality": 0,
                "semantic_similarity": best_sim,
                "_retrieval_path": "css_subset",
            }
        except Exception as e:
            logger.warning(f"CSS检索降级: {e}")
            return None

    def _semantic_retrieve_fallback(self, query_emb: np.ndarray) -> Optional[Dict]:
        """降级路径：实时计算 embedding（原有逻辑）"""
        try:
            db = get_storage_port("data/experience_pool.db")
            max_candidates = self._state_manager.get_max_candidates() if self._state_manager else 0
            if max_candidates > 0:
                rows = db.query(
                    "SELECT raw_input, response, quality_score FROM experiences ORDER BY quality_score DESC LIMIT ?",
                    (max_candidates,)
                )
            else:
                rows = db.query(
                    "SELECT raw_input, response, quality_score FROM experiences ORDER BY quality_score DESC LIMIT 50"
                )
            if not rows:
                return None

            best_row = None
            best_sim = 0.4

            for row in rows:
                text = row[0] or ""
                if not text:
                    continue
                row_emb = self._compute_embedding(text[:200])
                if row_emb is None:
                    continue
                cos_sim = float(np.dot(query_emb, row_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(row_emb) + 1e-8))
                if cos_sim > best_sim:
                    best_sim = cos_sim
                    best_row = row

            if best_row:
                return {
                    "_state_id": "semantic_retrieved",
                    "similar_input": best_row[0][:100],
                    "previous_response": best_row[1][:100],
                    "previous_quality": best_row[2],
                    "semantic_similarity": best_sim,
                }
        except Exception as e:
            logger.warning(f"语义检索降级: {e}")

        return None

    def _compute_delta(self, previous: Optional[Dict], bottleneck_result: Dict, validated_hypotheses: List[Dict]) -> Dict[str, Any]:
        delta = {
            "hypotheses": validated_hypotheses,
            "causal_chain": bottleneck_result.get("causal_chain", []),
            "counterfactuals": bottleneck_result.get("counterfactuals", []),
            "resolution_mode": bottleneck_result.get("resolution_mode", "unknown"),
            "topic": bottleneck_result.get("topic", ""),
            "entities": bottleneck_result.get("entities", []),
        }
        
        if previous:
            delta["_incremental"] = True
            delta["_base_quality"] = previous.get("previous_quality", 0)
        else:
            delta["_incremental"] = False
            delta["_base_quality"] = 0
        
        return delta

    def _residual_add(self, previous: Optional[Dict], delta: Dict) -> Dict[str, Any]:
        if self._state_manager:
            delta = self._state_manager.filter_delta(delta)
            if "hypotheses" in delta:
                delta["hypotheses"] = self._state_manager.truncate_list_field(delta["hypotheses"])

        new_state = dict(delta)
        
        if previous:
            new_state["_previous_context"] = previous.get("similar_input", "")
            new_state["_previous_quality"] = previous.get("previous_quality", 0)
            new_state["_has_experience_base"] = True
        else:
            new_state["_has_experience_base"] = False
        
        best_path = self._search_tree.get_best_path()
        if best_path:
            new_state["_best_reasoning_path"] = [n.content[:50] for n in best_path]
            new_state["_path_confidence"] = best_path[-1].confidence if best_path else 0.5
        
        new_state["has_meaningful_output"] = bool(delta.get("hypotheses") or delta.get("topic"))
        
        return new_state

    def _fallback_path(self, input_data: Dict, previous: Optional[Dict]) -> Dict[str, Any]:
        fallback = {
            "has_meaningful_output": True,
            "_fallback_used": True,
            "topic": input_data.get("topic", ""),
            "hypotheses": [{
                "type": "fallback",
                "content": "基于基础推理的保底响应",
                "confidence": 0.3,
                "source": "fallback_path",
            }],
        }
        
        if previous:
            fallback["_previous_context"] = previous.get("similar_input", "")
            fallback["_reusing_previous"] = True
        
        return fallback

    def _update_state(self, new_state: Dict) -> str:
        state_id = hashlib.md5(f"{new_state.get('topic', '')}{time.time()}".encode()).hexdigest()[:10]
        new_state["_state_id"] = state_id
        self._state_cache[state_id] = new_state
        
        if len(self._state_cache) > 100:
            oldest = min(self._state_cache.items(), key=lambda x: x[1].get("timestamp", 0))
            del self._state_cache[oldest[0]]
        
        if self._process_count % 5 == 0:
            self._save_search_tree()
        
        return state_id

    def _load_search_tree(self):
        try:
            db = get_storage_port(self._db_path)
            db.executescript('''CREATE TABLE IF NOT EXISTS search_nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT,
                content TEXT,
                confidence REAL,
                parent_id TEXT,
                score REAL,
                explored INTEGER
            )''')
            rows = db.query("SELECT node_id, node_type, content, confidence, parent_id, score, explored FROM search_nodes ORDER BY rowid")
            for row in rows:
                node_id, ntype, content, confidence, parent_id, score, explored = row
                node = SearchNode(
                    node_id=node_id,
                    node_type=NodeType(ntype),
                    content=content,
                    confidence=confidence,
                    parent_id=parent_id,
                    score=score,
                    explored=bool(explored),
                )
                self._search_tree._nodes[node_id] = node
                if parent_id and parent_id in self._search_tree._nodes:
                    if node_id not in self._search_tree._nodes[parent_id].children_ids:
                        self._search_tree._nodes[parent_id].children_ids.append(node_id)
                if not self._search_tree._root_id:
                    self._search_tree._root_id = node_id
            if self._search_tree.size() > 0:
                logger.warning(f"L3搜索树从数据库加载: {self._search_tree.size()}个节点")
        except Exception as e:
            logger.error(f"L3搜索树加载失败(首次运行正常): {e}")

    def _save_search_tree(self):
        try:
            db = get_storage_port(self._db_path)
            db.executescript('''CREATE TABLE IF NOT EXISTS search_nodes (
                node_id TEXT PRIMARY KEY,
                node_type TEXT,
                content TEXT,
                confidence REAL,
                parent_id TEXT,
                score REAL,
                explored INTEGER
            )''')
            db.execute("DELETE FROM search_nodes", commit=True)
            for nid, node in self._search_tree._nodes.items():
                db.execute(
                    "INSERT INTO search_nodes (node_id, node_type, content, confidence, parent_id, score, explored) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (nid, node.node_type.value, node.content, node.confidence, node.parent_id, node.score, int(node.explored)),
                    commit=True
                )
        except Exception as e:
            logger.error(f"L3搜索树保存失败: {e}")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "process_count": self._process_count,
            "reuse_count": self._reuse_count,
            "state_cache_size": len(self._state_cache),
            "search_tree_size": self._search_tree.size(),
        }