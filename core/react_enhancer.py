"""
ReAct增强器 - XGBoost风格短板聚焦

核心思想：每轮迭代精确聚焦上一轮的"短板"
- identify_gap: 识别上一轮最弱的维度（类似XGBoost的残差计算）
- generate_focused_prompt: 生成聚焦于短板的增强提示
- 与ReAct循环集成：让迭代更高效，减少无效重试

与PathWeightManager的关系：
- PathWeightManager管"路径选择"
- ReactEnhancer管"路径内的策略优化"
- 两者协同：权重低的路径 + 短板聚焦 = 精准修正
"""

import json
import time
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger


class ReactEnhancer:
    def __init__(self, db_path: str = "data/react_enhancements.db"):
        self.db_path = db_path
        self._gap_history: List[Dict] = []
        self._max_history = 100
        self._init_db()

    def _init_db(self):
        from pathlib import Path
        Path(self.db_path).parent.mkdir(exist_ok=True)
        from core.ports.adapters import get_storage_port
        get_storage_port(self.db_path).execute('''
            CREATE TABLE IF NOT EXISTS gap_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                gap_type TEXT,
                focus TEXT,
                severity REAL,
                iteration INTEGER,
                timestamp TEXT
            )
        ''')

    def identify_gap(self, previous_attempt: Dict) -> Dict:
        coverage = previous_attempt.get("coverage", {})
        if not coverage:
            scores = previous_attempt.get("scores", {})
            if scores:
                worst_dim = min(scores, key=scores.get)
                return {"gap_type": worst_dim, "focus": worst_dim,
                        "severity": 1.0 - scores.get(worst_dim, 0.5), "source": "score_based"}

        if not coverage:
            return {"gap_type": "unknown", "focus": "general", "severity": 0.5, "source": "no_data"}

        worst = min(coverage.items(), key=lambda x: x[1])
        gap = {
            "gap_type": worst[0],
            "focus": worst[0],
            "severity": round(1.0 - worst[1], 3),
            "source": "coverage_based",
        }

        self._gap_history.append({**gap, "query": previous_attempt.get("query", ""), "timestamp": time.time()})
        if len(self._gap_history) > self._max_history:
            self._gap_history = self._gap_history[-self._max_history:]

        self._save_gap(gap, previous_attempt.get("query", ""), previous_attempt.get("iteration", 0))
        return gap

    def generate_focused_prompt(self, gap: Dict, original_prompt: str) -> str:
        focus_map = {
            "missing_facts": "请重点补充以下缺失的具体事实，引用可靠来源：",
            "weak_logic": "请加强逻辑推理，确保论证链条完整，每步推导标注确定性：",
            "low_confidence": "请提供更多支撑证据，提升回答的可信度，区分事实与推测：",
            "incomplete_coverage": "请补充之前未覆盖的重要方面，确保回答全面：",
            "factual_error": "请纠正事实性错误，参考权威来源核实关键声明：",
            "shallow_depth": "请深入分析根本原因，不要停留在表面描述：",
            "unknown": "请补充之前未覆盖的方面，提供更深入的分析：",
        }
        enhancement = focus_map.get(gap.get("gap_type", "unknown"), focus_map["unknown"])
        severity = gap.get("severity", 0.5)
        if severity > 0.7:
            enhancement = f"⚠️ 这是你之前回答中最大的短板：{gap.get('focus', '未知')}。\n{enhancement}"
        return f"{original_prompt}\n\n{enhancement}"

    def get_recurring_gaps(self, limit: int = 10) -> List[Dict]:
        gap_counts: Dict[str, int] = {}
        for g in self._gap_history:
            gt = g.get("gap_type", "unknown")
            gap_counts[gt] = gap_counts.get(gt, 0) + 1
        sorted_gaps = sorted(gap_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"gap_type": g, "frequency": c} for g, c in sorted_gaps]

    def get_gap_stats(self) -> Dict:
        if not self._gap_history:
            return {"total_gaps": 0, "top_gap": None, "avg_severity": 0}
        gap_types = {}
        total_severity = 0
        for g in self._gap_history:
            gt = g.get("gap_type", "unknown")
            gap_types[gt] = gap_types.get(gt, 0) + 1
            total_severity += g.get("severity", 0)
        return {
            "total_gaps": len(self._gap_history),
            "top_gap": max(gap_types, key=gap_types.get) if gap_types else None,
            "avg_severity": round(total_severity / len(self._gap_history), 3),
            "gap_distribution": gap_types,
        }

    def _save_gap(self, gap: Dict, query: str, iteration: int):
        try:
            from core.ports.adapters import get_storage_port
            get_storage_port(self.db_path).execute('''
                INSERT INTO gap_analysis (query, gap_type, focus, severity, iteration, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (query[:200], gap.get("gap_type", ""), gap.get("focus", ""),
                  gap.get("severity", 0), iteration, datetime.now().isoformat()), commit=True)
        except Exception as e:
            logger.error(f"短板分析保存失败: {e}")


react_enhancer = ReactEnhancer()