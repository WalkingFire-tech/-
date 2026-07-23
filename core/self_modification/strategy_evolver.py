"""
L5策略进化器 — 根据修改历史优化自身的修改策略

核心思路：
- 从l5_audit.db中分析历史修改的成功率
- 按类别/文件/置信度维度学习
- 修改失败→降低该类别自动批准阈值
- 修改成功→提升置信度，扩大自动批准范围

策略参数：
- template_threshold: 模板补丁的自动批准置信度阈值
- llm_threshold: LLM补丁的自动批准置信度阈值
- auto_approve_categories: 允许自动批准的缺陷类别
- priority_files: 优先修改的文件列表
- self_mod_confidence_bonus: 自修改的额外置信度奖励/惩罚

设计原则：
- R3: 始于本心 — 策略进化不改变安全底线，只调整效率参数
- 数据驱动 — 没有足够样本时不调整策略
- 渐进调整 — 每次调整幅度不超过10%
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from core.explainability.l5_explainer import L5Explainer as _L5E
except ImportError:
    _L5E = None


@dataclass
class StrategyParams:
    template_threshold: float = 0.9
    llm_threshold: float = 0.95
    auto_approve_categories: List[str] = field(default_factory=lambda: ["exception_handling"])
    priority_files: List[str] = field(default_factory=list)
    self_mod_confidence_bonus: float = -0.1
    min_samples_for_adjustment: int = 5
    max_adjustment_per_cycle: float = 0.1


@dataclass
class CategoryStats:
    category: str
    total: int = 0
    success: int = 0
    failed: int = 0
    success_rate: float = 0.0
    avg_confidence: float = 0.0
    self_mod_total: int = 0
    self_mod_success: int = 0


class StrategyEvolver:
    """
    L5策略进化器
    
    从修改历史中学习，优化修改策略参数
    """

    def __init__(self, db_path: str = "data/l5_audit.db"):
        self.db_path = db_path
        self.params = StrategyParams()
        self._adjustment_history: List[Dict] = []

    def evolve_modification_strategy(self) -> Dict[str, Any]:
        """
        根据修改历史优化策略参数
        
        Returns: 调整报告
        """
        stats = self._analyze_history()
        if not stats:
            return {"status": "no_data", "message": "无足够修改历史，策略不变"}

        adjustments = []

        for cat_stat in stats:
            if cat_stat.total < self.params.min_samples_for_adjustment:
                continue

            old_threshold = self._get_threshold_for_category(cat_stat.category)

            if cat_stat.success_rate >= 0.8:
                new_threshold = max(0.7, old_threshold - self.params.max_adjustment_per_cycle)
                if new_threshold != old_threshold:
                    adjustments.append({
                        "category": cat_stat.category,
                        "direction": "lower_threshold",
                        "old": old_threshold,
                        "new": new_threshold,
                        "reason": f"成功率{cat_stat.success_rate:.0%}>=80%，降低阈值",
                    })
                    self._set_threshold_for_category(cat_stat.category, new_threshold)

            elif cat_stat.success_rate < 0.5:
                new_threshold = min(1.0, old_threshold + self.params.max_adjustment_per_cycle)
                if new_threshold != old_threshold:
                    adjustments.append({
                        "category": cat_stat.category,
                        "direction": "raise_threshold",
                        "old": old_threshold,
                        "new": new_threshold,
                        "reason": f"成功率{cat_stat.success_rate:.0%}<50%，提高阈值",
                    })
                    self._set_threshold_for_category(cat_stat.category, new_threshold)

            if cat_stat.self_mod_total >= 3:
                self_mod_rate = cat_stat.self_mod_success / cat_stat.self_mod_total if cat_stat.self_mod_total > 0 else 0
                if self_mod_rate >= 0.7:
                    if self.params.self_mod_confidence_bonus < 0:
                        old_bonus = self.params.self_mod_confidence_bonus
                        self.params.self_mod_confidence_bonus = min(0.0, old_bonus + 0.05)
                        adjustments.append({
                            "param": "self_mod_confidence_bonus",
                            "old": old_bonus,
                            "new": self.params.self_mod_confidence_bonus,
                            "reason": f"自修改成功率{self_mod_rate:.0%}>=70%，减少惩罚",
                        })

        priority_updates = self._update_priority_files(stats)
        if priority_updates:
            adjustments.extend(priority_updates)

        report = {
            "status": "adjusted" if adjustments else "no_change",
            "adjustments": adjustments,
            "current_params": {
                "template_threshold": self.params.template_threshold,
                "llm_threshold": self.params.llm_threshold,
                "self_mod_confidence_bonus": self.params.self_mod_confidence_bonus,
                "auto_approve_categories": self.params.auto_approve_categories,
                "priority_files": self.params.priority_files[:5],
            },
            "stats_summary": [
                {"category": s.category, "total": s.total, "rate": f"{s.success_rate:.0%}"}
                for s in stats
            ],
        }

        if adjustments:
            self._adjustment_history.append({
                "timestamp": datetime.now().isoformat(),
                "adjustments": adjustments,
            })
            logger.info(f"🧬 策略进化: {len(adjustments)}项调整")

        if _L5E:
            _L5E.explain_strategy_evolution(adjustments=adjustments, current_params=report.get("current_params"))

        return report

    def get_effective_confidence(self, patch_confidence: float, defect_category: str,
                                  is_self_mod: bool = False) -> float:
        """获取考虑策略参数后的有效置信度"""
        effective = patch_confidence
        if is_self_mod:
            effective += self.params.self_mod_confidence_bonus
        return max(0.0, min(1.0, effective))

    def should_auto_approve(self, confidence: float, defect_category: str,
                             is_self_mod: bool = False) -> bool:
        """判断是否应该自动批准"""
        if defect_category not in self.params.auto_approve_categories:
            return False
        threshold = self._get_threshold_for_category(defect_category)
        if is_self_mod:
            threshold -= self.params.self_mod_confidence_bonus
        return confidence >= threshold

    def _analyze_history(self) -> List[CategoryStats]:
        """从审计日志分析修改历史"""
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port(self.db_path)
            rows = db.query(
                "SELECT defect_category, result_status, patch_confidence, is_self_modification "
                "FROM l5_audit_log ORDER BY timestamp DESC LIMIT 200"
            )
        except Exception as e:
            logger.debug(f"策略进化分析跳过: {e}")
            return []

        cat_map: Dict[str, CategoryStats] = {}
        for row in rows:
            if isinstance(row, dict):
                category = row.get("defect_category", "unknown")
                status = row.get("result_status", "")
                confidence = row.get("patch_confidence", 0.0)
                is_self_mod = row.get("is_self_modification", 0)
            else:
                category = row[0] if len(row) > 0 else "unknown"
                status = row[1] if len(row) > 1 else ""
                confidence = row[2] if len(row) > 2 else 0.0
                is_self_mod = row[3] if len(row) > 3 else 0

            if category not in cat_map:
                cat_map[category] = CategoryStats(category=category)

            stat = cat_map[category]
            stat.total += 1
            stat.avg_confidence = (stat.avg_confidence * (stat.total - 1) + confidence) / stat.total

            if status in ("completed", "sandbox_passed"):
                stat.success += 1
            else:
                stat.failed += 1

            if is_self_mod:
                stat.self_mod_total += 1
                if status in ("completed", "sandbox_passed"):
                    stat.self_mod_success += 1

        for stat in cat_map.values():
            stat.success_rate = stat.success / stat.total if stat.total > 0 else 0.0

        return sorted(cat_map.values(), key=lambda s: s.total, reverse=True)

    def _get_threshold_for_category(self, category: str) -> float:
        if category == "exception_handling":
            return self.params.template_threshold
        return self.params.llm_threshold

    def _set_threshold_for_category(self, category: str, value: float):
        if category == "exception_handling":
            self.params.template_threshold = value
        else:
            self.params.llm_threshold = value

    def _update_priority_files(self, stats: List[CategoryStats]) -> List[Dict]:
        """根据成功率更新优先修改文件列表"""
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port(self.db_path)
            rows = db.query(
                "SELECT file_path, COUNT(*) as cnt, "
                "SUM(CASE WHEN result_status IN ('completed','sandbox_passed') THEN 1 ELSE 0 END) as ok "
                "FROM l5_audit_log GROUP BY file_path HAVING cnt >= 3 ORDER BY ok DESC LIMIT 10"
            )
        except Exception:
            return []

        new_priority = []
        adjustments = []
        for row in rows:
            if isinstance(row, dict):
                fp = row.get("file_path", "")
                cnt = row.get("cnt", 0)
                ok = row.get("ok", 0)
            else:
                fp = row[0] if len(row) > 0 else ""
                cnt = row[1] if len(row) > 1 else 0
                ok = row[2] if len(row) > 2 else 0

            if fp and cnt >= 3 and ok / cnt >= 0.7:
                new_priority.append(fp)

        if new_priority != self.params.priority_files:
            old = self.params.priority_files[:5]
            self.params.priority_files = new_priority
            adjustments.append({
                "param": "priority_files",
                "old": old,
                "new": new_priority[:5],
                "reason": "根据成功率更新优先文件",
            })

        return adjustments


strategy_evolver = StrategyEvolver()