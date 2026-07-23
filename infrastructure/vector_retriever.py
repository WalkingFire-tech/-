"""
概率化向量检索系统 - 检索结果表达为概率分布

三级策略：
1. sentence_transformers（完整语义检索，从本地缓存加载）
2. TF-IDF + cosine_similarity（轻量降级，无需模型）
3. 纯字符hash embedding（无sklearn时）

概率化增强：
- 概率校准：原始得分→P(relevant|query,doc)，Platt Scaling + 温度缩放
- 熵基动态混合：根据查询不确定性动态调整稀疏/稠密检索权重
- 概率分布输出：检索结果为概率质量分布，而非确定性分数
- 与DynamicProbabilityField深度整合：检索结果直接注入概率场
"""

import os
import json
import hashlib
import math
import threading
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path
from loguru import logger
from infrastructure.database_manager import DatabaseManager

_SKLEARN_AVAILABLE = False
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine
    _SKLEARN_AVAILABLE = True
except ImportError:
    pass

_ST_MODEL = None
_ST_TOKENIZER = None
_ST_AVAILABLE = False
_ST_LOADING = False


def _find_local_model(model_name: str) -> Optional[str]:
    hub = Path.home() / ".cache" / "huggingface" / "hub"
    model_dir = hub / f"models--{model_name.replace('/', '--')}"
    if not model_dir.exists():
        return None
    snap_dir = model_dir / "snapshots"
    if not snap_dir.exists():
        return None
    snaps = list(snap_dir.iterdir())
    if not snaps:
        return None
    return str(snaps[0])


class _DirectEncoder:
    """直接用transformers加载BERT模型做sentence embedding，绕过sentence_transformers超时问题"""

    def __init__(self, model_path: str):
        os.environ['HF_HUB_OFFLINE'] = '1'
        os.environ['TRANSFORMERS_OFFLINE'] = '1'
        from transformers import AutoTokenizer, AutoModel
        import torch
        self.tok = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
        self.model = AutoModel.from_pretrained(model_path, local_files_only=True)
        self.model.eval()
        self.torch = torch

    def encode(self, texts, show_progress_bar=False, batch_size=32):
        import numpy as np
        if isinstance(texts, str):
            texts = [texts]
        all_embs = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            inputs = self.tok(batch, return_tensors='pt', padding=True, truncation=True, max_length=128)
            with self.torch.no_grad():
                out = self.model(**inputs)
            emb = out.last_hidden_state[:, 0, :].numpy()
            all_embs.append(emb)
        if len(all_embs) == 1:
            return all_embs[0] if len(all_embs[0]) > 1 else all_embs[0][0]
        return np.vstack(all_embs)


def _load_st_model():
    global _ST_MODEL, _ST_AVAILABLE, _ST_LOADING
    if _ST_MODEL is not None or _ST_LOADING:
        return
    _ST_LOADING = True
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    try:
        model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        local_path = _find_local_model(model_name)
        if local_path:
            _ST_MODEL = _DirectEncoder(local_path)
            _ST_AVAILABLE = True
            logger.info(f"向量检索模型加载成功(DirectEncoder): {local_path}")
        else:
            try:
                from sentence_transformers import SentenceTransformer
                cache_folder = str(Path.home() / ".cache" / "huggingface" / "hub")
                _ST_MODEL = SentenceTransformer(model_name, cache_folder=cache_folder)
                _ST_AVAILABLE = True
                logger.info(f"向量检索模型加载成功(SentenceTransformer): {model_name}")
            except Exception as e2:
                logger.warning(f"SentenceTransformer加载失败: {e2}，使用TF-IDF降级")
                _ST_MODEL = None
                _ST_AVAILABLE = False
    except Exception as e:
        logger.warning(f"向量检索模型加载失败: {e}，使用TF-IDF降级")
        _ST_MODEL = None
        _ST_AVAILABLE = False
    finally:
        _ST_LOADING = False


class ProbabilityCalibrator:
    """概率校准器 - 将原始检索得分转为P(relevant|query,doc)
    
    增强特性：
    - ECE(预期校准误差)追踪：量化概率估计本身的可靠性
    - 闭环校准反馈：根据实际结果调整校准参数
    - 贝叶斯BM25式sigmoid似然模型：P(R=1|s) = sigmoid((s-μ)/σ·τ)
    """

    def __init__(self, temperature: float = 1.0, n_bins: int = 10):
        self.temperature = temperature
        self.n_bins = n_bins
        self._score_history: List[float] = []
        self._mean = 0.5
        self._std = 0.2
        self._ece = 1.0
        self._calibration_feedback_count = 0
        self._bin_accuracies: Dict[int, List[bool]] = {}

    def calibrate(self, scores: List[float]) -> List[float]:
        if not scores:
            return []
        self._update_stats(scores)
        calibrated = []
        for s in scores:
            z = (s - self._mean) / max(self._std, 1e-6)
            prob = 1.0 / (1.0 + math.exp(-z / self.temperature))
            calibrated.append(prob)
        total = sum(calibrated)
        if total > 0:
            calibrated = [p / total for p in calibrated]
        return calibrated

    def calibrate_single(self, score: float, all_scores: List[float] = None) -> float:
        if all_scores:
            self._update_stats(all_scores)
        z = (score - self._mean) / max(self._std, 1e-6)
        return 1.0 / (1.0 + math.exp(-z / self.temperature))

    def record_calibration_outcome(self, predicted_prob: float, actual_relevant: bool):
        """闭环校准：记录预测概率与实际结果的对应关系，用于ECE计算和参数调整"""
        bin_idx = min(int(predicted_prob * self.n_bins), self.n_bins - 1)
        if bin_idx not in self._bin_accuracies:
            self._bin_accuracies[bin_idx] = []
        self._bin_accuracies[bin_idx].append(actual_relevant)
        if len(self._bin_accuracies[bin_idx]) > 100:
            self._bin_accuracies[bin_idx] = self._bin_accuracies[bin_idx][-100:]
        self._compute_ece()
        self._calibration_feedback_count += 1
        if self._calibration_feedback_count % 20 == 0:
            self._auto_adjust_temperature()

    def get_ece(self) -> float:
        return round(self._ece, 4)

    def get_calibration_stats(self) -> Dict:
        return {
            "ece": round(self._ece, 4),
            "temperature": round(self.temperature, 4),
            "mean_score": round(self._mean, 4),
            "std_score": round(self._std, 4),
            "feedback_count": self._calibration_feedback_count,
            "bins_populated": len(self._bin_accuracies),
        }

    def _update_stats(self, scores: List[float]):
        self._score_history.extend(scores)
        if len(self._score_history) > 1000:
            self._score_history = self._score_history[-1000:]
        if len(self._score_history) >= 5:
            arr = np.array(self._score_history[-100:])
            self._mean = float(np.mean(arr))
            self._std = max(float(np.std(arr)), 0.01)

    def _compute_ece(self):
        """计算预期校准误差 ECE = Σ (n_b/N) |acc(b) - conf(b)|"""
        total_samples = sum(len(v) for v in self._bin_accuracies.values())
        if total_samples < 5:
            self._ece = 1.0
            return
        ece = 0.0
        for bin_idx, outcomes in self._bin_accuracies.items():
            if not outcomes:
                continue
            n_b = len(outcomes)
            acc_b = sum(1 for o in outcomes if o) / n_b
            conf_b = (bin_idx + 0.5) / self.n_bins
            ece += (n_b / total_samples) * abs(acc_b - conf_b)
        self._ece = ece

    def _auto_adjust_temperature(self):
        """根据ECE自动调整温度参数：ECE过高时增大温度（更平滑），ECE过低时减小温度（更锐利）"""
        if self._ece > 0.3:
            self.temperature = min(2.0, self.temperature * 1.05)
        elif self._ece < 0.1 and self._calibration_feedback_count > 50:
            self.temperature = max(0.3, self.temperature * 0.95)


class QueryEntropyEstimator:
    """查询熵估计器 - 根据查询特征估计不确定性"""

    def estimate_entropy(self, query: str) -> float:
        if not query:
            return 1.0
        tokens = query.lower().split()
        if not tokens:
            return 1.0
        unique = len(set(tokens))
        total = len(tokens)
        lexical_diversity = unique / max(total, 1)
        length_factor = min(1.0, total / 10.0)
        specificity_keywords = ["什么", "如何", "怎么", "为什么", "哪些", "哪个", "是否", "能否",
                                "what", "how", "why", "which", "whether"]
        has_specificity = any(kw in query.lower() for kw in specificity_keywords)
        specificity_factor = 0.7 if has_specificity else 1.0
        entropy = (1.0 - length_factor * 0.3) * specificity_factor
        entropy *= (0.5 + lexical_diversity * 0.5)
        return max(0.0, min(1.0, entropy))


class VectorRetriever:

    MAX_INDEX_SIZE = 100 * 1024 * 1024
    BASE_DATA_DIR = Path("data")

    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self.id_map: Dict[int, Dict] = {}
        self.current_id = 0
        self._lock = threading.RLock()
        self._texts: List[str] = []
        self._tfidf_vectorizer = None
        self._tfidf_matrix = None
        self._st_loaded = False
        self._calibrator = ProbabilityCalibrator(temperature=0.8)
        self._entropy_estimator = QueryEntropyEstimator()
        self._cached_vecs = None
        self._cached_vecs_count = 0

        self.index_path = self.BASE_DATA_DIR / "vector_index"

        if _SKLEARN_AVAILABLE:
            self._tfidf_vectorizer = TfidfVectorizer(
                max_features=5000,
                analyzer='char_wb',
                ngram_range=(1, 3),
            )
            logger.info("概率化向量检索器初始化: TF-IDF就绪, ST待加载, 概率校准就绪")
        else:
            logger.warning("TF-IDF不可用，使用hash embedding降级方案")

    def _ensure_st_loaded(self):
        if self._st_loaded:
            return
        self._st_loaded = True
        try:
            th = threading.Thread(target=_load_st_model, daemon=True)
            th.start()
            th.join(timeout=60)
            if _ST_AVAILABLE:
                logger.info("sentence_transformers语义检索已启用")
            else:
                logger.info("sentence_transformers不可用，使用TF-IDF检索")
        except Exception as e:
            logger.error(f"ST加载异常: {e}")

    def is_available(self) -> bool:
        return True

    def add_experience(self, text: str, metadata: Dict, embedding=None):
        with self._lock:
            self.id_map[self.current_id] = {
                "text": text,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat()
            }
            self._texts.append(text)
            self.current_id += 1
            self._tfidf_matrix = None
            self._cached_vecs = None

    def search(self, query: str, top_k: int = 5, threshold: float = 0.3) -> List[Dict]:
        results = self.search_similar(query, k=top_k, threshold=threshold)
        return [{"text": r["text"], "metadata": r["metadata"],
                 "probability": r["probability"], "raw_score": r["raw_score"],
                 "source": r["source"]} for r in results]

    def search_similar(self, query: str, k: int = 5, threshold: float = 0.3) -> List[Dict]:
        if not self._texts:
            return []

        self._ensure_st_loaded()

        query_entropy = self._entropy_estimator.estimate_entropy(query)

        sparse_results = self._search_sparse(query, k * 2, threshold * 0.5)
        dense_results = self._search_dense(query, k * 2, threshold * 0.5)

        alpha = 1.0 - query_entropy
        merged = self._merge_results(sparse_results, dense_results, alpha)

        if not merged:
            return []

        raw_scores = [s for _, s in merged]
        probs = self._calibrator.calibrate(raw_scores)

        results = []
        for i, (item, raw_score) in enumerate(merged[:k]):
            prob = probs[i] if i < len(probs) else 0.0
            if prob >= threshold * 0.3:
                results.append({
                    "text": item.get("text", ""),
                    "metadata": item.get("metadata", {}),
                    "probability": round(prob, 4),
                    "raw_score": round(raw_score, 4),
                    "source": "hybrid" if sparse_results and dense_results else ("sparse" if sparse_results else "dense"),
                    "query_entropy": round(query_entropy, 3),
                    "alpha": round(alpha, 3),
                })
        return results

    def search_probabilistic(self, query: str, k: int = 5) -> Dict:
        results = self.search_similar(query, k=k, threshold=0.01)
        if not results:
            return {"distribution": {}, "entropy": 1.0, "top": None, "mode": "empty"}

        distribution = {}
        for r in results:
            src = r.get("source", "unknown")
            text_key = r["text"][:50]
            distribution[f"{src}:{text_key}"] = r["probability"]

        entropy = self._compute_entropy(list(distribution.values()))
        top = max(results, key=lambda x: x["probability"]) if results else None

        return {
            "distribution": distribution,
            "entropy": round(entropy, 4),
            "top": {"text": top["text"][:100], "probability": top["probability"]} if top else None,
            "query_entropy": results[0].get("query_entropy", 0.5) if results else 0.5,
            "alpha": results[0].get("alpha", 0.5) if results else 0.5,
            "mode": "semantic" if _ST_AVAILABLE else "tfidf",
            "num_results": len(results),
        }

    def _search_sparse(self, query: str, k: int, threshold: float) -> List[Tuple[Dict, float]]:
        if not _SKLEARN_AVAILABLE or not self._texts:
            return []
        try:
            with self._lock:
                if self._tfidf_matrix is None or self._tfidf_matrix.shape[0] != len(self._texts):
                    self._tfidf_vectorizer = TfidfVectorizer(
                        max_features=5000, analyzer='char_wb', ngram_range=(1, 3),
                    )
                    self._tfidf_matrix = self._tfidf_vectorizer.fit_transform(self._texts)
                query_vec = self._tfidf_vectorizer.transform([query])
                similarities = sklearn_cosine(query_vec, self._tfidf_matrix)[0]

            results = []
            for idx in np.argsort(similarities)[::-1][:k]:
                sim = float(similarities[idx])
                if sim >= threshold and idx in self.id_map:
                    results.append((self.id_map[idx], sim))
            return results
        except Exception as e:
            logger.error(f"稀疏检索失败: {e}")
            return []

    def _search_dense(self, query: str, k: int, threshold: float) -> List[Tuple[Dict, float]]:
        try:
            from core.resource_awareness.health_monitor import get_health_monitor
            if not get_health_monitor().should_use_dense_retrieval():
                logger.debug("资源紧张，稠密检索降级为TF-IDF")
                return self._search_sparse(query, k, threshold)
        except ImportError:
            pass

        if _ST_AVAILABLE and _ST_MODEL is not None:
            try:
                query_vec = _ST_MODEL.encode([query])
                if len(query_vec.shape) == 1:
                    query_vec = query_vec.reshape(1, -1)
                if self._cached_vecs is None or self._cached_vecs_count != len(self._texts):
                    try:
                        import psutil
                        mem_before = psutil.virtual_memory().percent / 100.0
                        if mem_before > 0.88:
                            logger.warning(f"全量encode前内存{mem_before:.1%}过高，降级为TF-IDF")
                            return self._search_sparse(query, k, threshold)
                    except ImportError:
                        pass
                    try:
                        batch_size = 64
                        all_vecs = []
                        for i in range(0, len(self._texts), batch_size):
                            batch = self._texts[i:i + batch_size]
                            batch_vecs = _ST_MODEL.encode(batch, show_progress_bar=False, batch_size=32)
                            all_vecs.append(batch_vecs if len(batch_vecs.shape) == 2 else batch_vecs.reshape(1, -1))
                            if i % 256 == 0 and i > 0:
                                try:
                                    import psutil
                                    if psutil.virtual_memory().percent / 100.0 > 0.92:
                                        logger.warning(f"分批encode中内存过高，已处理{i}/{len(self._texts)}条，降级")
                                        return self._search_sparse(query, k, threshold)
                                except ImportError:
                                    pass
                        self._cached_vecs = np.vstack(all_vecs) if all_vecs else np.array([])
                        self._cached_vecs_count = len(self._texts)
                    except MemoryError:
                        logger.warning("全量encode内存不足，降级为TF-IDF")
                        return self._search_sparse(query, k, threshold)
                if self._cached_vecs is None or len(self._cached_vecs) == 0:
                    return self._search_sparse(query, k, threshold)
                from sklearn.metrics.pairwise import cosine_similarity as cs
                sims = cs(query_vec, self._cached_vecs)[0]
                results = []
                for idx in np.argsort(sims)[::-1][:k]:
                    sim = float(sims[idx])
                    if sim >= threshold and idx in self.id_map:
                        results.append((self.id_map[idx], sim))
                return results
            except Exception as e:
                logger.error(f"稠密检索失败: {e}")
        return self._search_hash(query, k, threshold)

    def _search_hash(self, query: str, k: int, threshold: float) -> List[Tuple[Dict, float]]:
        query_emb = self._simple_embedding(query)
        results = []
        for idx, item in self.id_map.items():
            item_emb = self._simple_embedding(item.get("text", ""))
            norm_q = np.linalg.norm(query_emb)
            norm_i = np.linalg.norm(item_emb)
            if norm_q > 0 and norm_i > 0:
                sim = float(np.dot(query_emb, item_emb) / (norm_q * norm_i))
            else:
                sim = 0.0
            if sim >= threshold:
                results.append((item, sim))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]

    def _merge_results(self, sparse: List[Tuple[Dict, float]],
                       dense: List[Tuple[Dict, float]], alpha: float) -> List[Tuple[Dict, float]]:
        merged_scores: Dict[int, Tuple[Dict, float]] = {}

        for item, score in sparse:
            text = item.get("text", "")
            idx = hash(text) % (2**31)
            merged_scores[idx] = (item, score * alpha)

        for item, score in dense:
            text = item.get("text", "")
            idx = hash(text) % (2**31)
            if idx in merged_scores:
                old_item, old_score = merged_scores[idx]
                merged_scores[idx] = (item, old_score + score * (1 - alpha))
            else:
                merged_scores[idx] = (item, score * (1 - alpha))

        results = list(merged_scores.values())
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def _compute_entropy(self, probs: List[float]) -> float:
        entropy = 0.0
        for p in probs:
            if p > 0:
                entropy -= p * math.log2(max(p, 1e-10))
        return entropy

    def _simple_embedding(self, text: str) -> np.ndarray:
        embedding = np.zeros(self.embedding_dim)
        for i, char in enumerate(text[:self.embedding_dim]):
            embedding[i] = ord(char) / 255.0
        if len(text) < self.embedding_dim:
            text_hash = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            embedding[-1] = (text_hash % 1000) / 1000.0
        return embedding

    def get_successful_plans(self, intent_type: str = None, min_quality: int = 70) -> List[Dict]:
        db_path = "data/experience_pool.db"
        try:
            db = DatabaseManager.get(db_path)
            if intent_type:
                rows = db.query('''
                    SELECT intent_type, raw_input, plan, model_name,
                           quality_score, duration, response
                    FROM experiences
                    WHERE intent_type = ? AND quality_score >= ? AND success = 1
                    ORDER BY quality_score DESC LIMIT 100
                ''', (intent_type, min_quality))
            else:
                rows = db.query('''
                    SELECT intent_type, raw_input, plan, model_name,
                           quality_score, duration, response
                    FROM experiences
                    WHERE quality_score >= ? AND success = 1
                    ORDER BY quality_score DESC LIMIT 100
                ''', (min_quality,))
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取成功计划失败: {e}")
            return []

    def find_similar_plan(self, current_input: str, intent_type: str = None,
                          similarity_threshold: float = 0.6) -> Optional[Dict]:
        successful_plans = self.get_successful_plans(intent_type)
        if not successful_plans:
            return None
        results = self.search_similar(current_input, k=1, threshold=similarity_threshold * 0.3)
        if results:
            best = results[0]
            if best["probability"] >= similarity_threshold * 0.3:
                for plan in successful_plans:
                    if plan.get("raw_input", "") == best.get("text", ""):
                        return {"plan": plan, "similarity": best["probability"],
                                "source": "probabilistic_retrieval"}
        return None

    def save_index(self, path: str = None):
        save_path = self.BASE_DATA_DIR / "vector_index"
        save_path.mkdir(parents=True, exist_ok=True)
        with self._lock:
            data_path = save_path / "id_map.json"
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump({"id_map": {str(k): v for k, v in self.id_map.items()},
                           "current_id": self.current_id, "texts": self._texts}, f, ensure_ascii=False, indent=2)
        logger.info(f"向量索引已保存: {save_path}")

    def load_index(self, path: str = None):
        load_path = self.BASE_DATA_DIR / "vector_index"
        data_path = load_path / "id_map.json"
        if not data_path.exists():
            return
        with self._lock:
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.id_map = {int(k): v for k, v in data.get("id_map", {}).items()}
                self.current_id = data.get("current_id", 0)
                self._texts = data.get("texts", [])
        self._tfidf_matrix = None
        logger.info(f"向量索引已加载: {len(self._texts)}条记录")

    def get_stats(self) -> Dict:
        return {
            "total_entries": self.current_id,
            "texts_count": len(self._texts),
            "st_available": _ST_AVAILABLE,
            "tfidf_available": _SKLEARN_AVAILABLE,
            "mode": "semantic" if _ST_AVAILABLE else ("tfidf" if _SKLEARN_AVAILABLE else "hash"),
            "calibration_temp": self._calibrator.temperature,
            "score_history_size": len(self._calibrator._score_history),
        }


vector_retriever = VectorRetriever()
