"""
认知表示管理器 — Dict 结构化认知状态的低秩近似

核心理念迁移：
- 向量低秩近似 → 字段级掩码（Field-Level Masking）
- SVD 降维 → 选择性更新字段子集
- 稀疏掩码作用于向量维度 → 稀疏掩码作用于字典键（keys）
- 认知梯度 = 向量方向截断 → 认知梯度 = 只更新最相关的字段
- 校准 = 余弦距离 → 校准 = 字典结构一致性校验

三级模式：
- dense（全量）：更新所有字段，全量语义检索
- lowrank（近似）：只更新高优先级字段，候选数量限制
- keyword（极简）：只保留核心认知连续性字段，跳过 embedding
"""
from typing import Optional, Dict, Any, Set
from loguru import logger


class CognitiveStateManager:
    """认知表示管理器：基于字段级掩码的结构化低秩近似"""

    DENSE = "dense"
    LOWRANK = "lowrank"
    KEYWORD = "keyword"

    _FIELD_PRIORITY: Dict[str, Set[str]] = {
        "keyword": {"confidence", "topic", "_incremental"},
        "lowrank": {"confidence", "topic", "hypotheses", "_incremental", "_base_quality", "causal_chain"},
        "dense": None,  # None = 全部字段
    }

    def __init__(
        self,
        calibration_interval: int = 30,
        error_threshold: float = 0.15,
        hypothesis_budget_map: Optional[Dict[str, float]] = None,
    ):
        self.calibration_interval = calibration_interval
        self.error_threshold = error_threshold

        self.mode: str = self.DENSE
        self._embedding_cache: Dict[str, Any] = {}
        self._steps_since_calibration = 0
        self._error_accumulator = 0.0
        self._last_retrieval_quality = 1.0
        self._calibration_count = 0
        self._approximation_log: list = []

        self._hypothesis_budget = hypothesis_budget_map or {
            self.DENSE: 1.0,
            self.LOWRANK: 0.6,
            self.KEYWORD: 0.2,
        }

    def get_allowed_fields(self) -> Optional[Set[str]]:
        """返回当前模式允许更新的字段集合（None=全部）"""
        return self._FIELD_PRIORITY.get(self.mode)

    def filter_delta(self, delta: Dict[str, Any]) -> Dict[str, Any]:
        """字段级掩码：根据模式过滤 delta 中允许更新的字段"""
        allowed = self.get_allowed_fields()
        if allowed is None:
            return delta

        filtered = {}
        skipped = set()
        for key, value in delta.items():
            if key in allowed or key.startswith("_"):
                filtered[key] = value
            else:
                skipped.add(key)

        if skipped:
            self._approximation_log.append({
                "mode": self.mode,
                "skipped_keys": skipped,
            })
            if len(self._approximation_log) > 100:
                self._approximation_log = self._approximation_log[-50:]

        return filtered

    def truncate_list_field(self, items: list) -> list:
        """字段内部梯度截断：根据预算截断列表型字段"""
        budget = self._hypothesis_budget.get(self.mode, 1.0)
        if budget >= 1.0 or not items:
            return items
        keep = max(1, int(len(items) * budget))
        return items[:keep]

    def should_use_semantic_retrieve(self) -> bool:
        return self.mode != self.KEYWORD

    def get_max_candidates(self) -> int:
        if self.mode == self.DENSE:
            return 0
        elif self.mode == self.LOWRANK:
            return 50
        else:
            return 10

    def update(self, retrieval_quality: float) -> None:
        self._last_retrieval_quality = retrieval_quality
        self._steps_since_calibration += 1
        self._check_calibration_need()

    def set_mode(self, mode: str) -> None:
        if mode == self.mode:
            return
        old = self.mode
        self.mode = mode
        logger.info(f"🧠 认知表示模式切换: {old} → {mode} (字段: {self.get_allowed_fields() or '全部'})")
        if mode == self.DENSE:
            self._calibrate()

    def set_mode_from_budget(self, budget: float) -> None:
        if budget > 0.7:
            target = self.DENSE
        elif budget > 0.35:
            target = self.LOWRANK
        else:
            target = self.KEYWORD
        self.set_mode(target)

    def cache_embedding(self, key: str, embedding: Any) -> None:
        self._embedding_cache[key] = embedding
        if len(self._embedding_cache) > 200:
            oldest_key = next(iter(self._embedding_cache))
            del self._embedding_cache[oldest_key]

    def get_cached_embedding(self, key: str) -> Optional[Any]:
        return self._embedding_cache.get(key)

    def _check_calibration_need(self) -> None:
        if self.mode != self.DENSE:
            if (self._steps_since_calibration >= self.calibration_interval or
                self._error_accumulator > self.error_threshold or
                self._last_retrieval_quality < 0.3):
                self._calibrate()

    def _calibrate(self) -> None:
        self._steps_since_calibration = 0
        self._error_accumulator = 0.0
        self._calibration_count += 1

    def check_dict_consistency(self, true_state: Dict, approx_state: Dict) -> bool:
        """字典结构一致性校验：检查关键字段是否偏离"""
        critical_fields = {"confidence", "topic"}
        for field in critical_fields:
            if field in true_state and field in approx_state:
                if true_state[field] != approx_state[field]:
                    return False
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "allowed_fields": list(self.get_allowed_fields() or ["ALL"]),
            "steps_since_calibration": self._steps_since_calibration,
            "calibration_count": self._calibration_count,
            "error_accumulator": round(self._error_accumulator, 4),
            "last_retrieval_quality": round(self._last_retrieval_quality, 3),
            "embedding_cache_size": len(self._embedding_cache),
            "approximation_log_size": len(self._approximation_log),
        }
