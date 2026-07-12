"""
贡献度归因器 - SHAP风格

核心思想：追溯每个信息来源对最终答案的贡献度
- 基于文本重叠度计算各来源的贡献
- 归一化后输出贡献度分布
- 记录归因历史供路径权重管理器使用

与PathWeightManager的关系：
- PathWeightManager = 预测性权重（事前分配）
- ContribAttributor = 解释性归因（事后分析）
- 两者形成闭环：归因结果反馈给权重管理器
"""

from infrastructure.database_manager import DatabaseManager
import time
import json
from typing import Dict, List, Tuple
from datetime import datetime
from loguru import logger


class ContribAttributor:
    def __init__(self, db_path: str = "data/contrib_attributions.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        from pathlib import Path
        Path(self.db_path).parent.mkdir(exist_ok=True)
        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS attributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT,
                final_source TEXT,
                contributions TEXT,
                top_source TEXT,
                entropy REAL,
                created_at TEXT
            )
        ''')

    def compute_contributions(self, candidates: List[Dict], final_response: str,
                               final_source: str = "", query: str = "") -> Dict:
        if not candidates or not final_response:
            return {"contributions": {}, "top_source": final_source, "entropy": 0}

        contributions = {}
        final_tokens = self._tokenize(final_response)

        for cand in candidates:
            source = cand.get("source", "unknown")
            content = cand.get("response", "") or cand.get("content", "")
            if not content or source == final_source:
                if source == final_source:
                    contributions[source] = contributions.get(source, 0) + 0.5
                continue

            cand_tokens = self._tokenize(content)
            overlap = self._compute_overlap(cand_tokens, final_tokens)
            
            retrieval_prob = cand.get("retrieval_probability")
            if retrieval_prob is not None and retrieval_prob > 0:
                overlap = overlap * (0.7 + 0.3 * retrieval_prob)
            
            contributions[source] = contributions.get(source, 0) + overlap

        total = sum(contributions.values())
        if total > 0:
            contributions = {k: v / total for k, v in contributions.items()}

        if final_source and final_source not in contributions:
            contributions[final_source] = 1.0 - sum(contributions.values())
        elif final_source:
            remaining = 1.0 - sum(v for k, v in contributions.items() if k != final_source)
            contributions[final_source] = max(contributions.get(final_source, 0), remaining)

        entropy = self._compute_entropy(contributions)
        top_source = max(contributions, key=contributions.get) if contributions else final_source

        retrieval_uncertainties = {}
        for cand in candidates:
            src = cand.get("source", "unknown")
            re = cand.get("retrieval_entropy")
            rp = cand.get("retrieval_probability")
            if re is not None or rp is not None:
                retrieval_uncertainties[src] = {
                    "retrieval_probability": round(rp, 3) if rp else None,
                    "retrieval_entropy": round(re, 3) if re else None,
                    "calibrated_confidence": round(rp * (1 - (re or 0.5)), 3) if rp else None,
                }

        result = {
            "contributions": {k: round(v, 4) for k, v in sorted(contributions.items(), key=lambda x: x[1], reverse=True)},
            "top_source": top_source,
            "entropy": round(entropy, 4),
            "num_candidates": len(candidates),
            "retrieval_uncertainties": retrieval_uncertainties if retrieval_uncertainties else None,
        }

        self._save_attribution(query, final_source, contributions, top_source, entropy)

        logger.warning(f"贡献归因: top={top_source}({contributions.get(top_source, 0) or 0:.2f}) "
                      f"entropy={entropy:.3f} candidates={len(candidates)}"
                      f"{' unc=' + str(len(retrieval_uncertainties)) + 'dims' if retrieval_uncertainties else ''}")

        return result

    def _tokenize(self, text: str) -> set:
        return set(text.lower().split())

    def _compute_overlap(self, tokens_a: set, tokens_b: set) -> float:
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        return len(intersection) / max(len(tokens_a), len(tokens_b))

    def _compute_entropy(self, distribution: Dict[str, float]) -> float:
        import math
        entropy = 0.0
        for v in distribution.values():
            if v > 0:
                entropy -= v * math.log2(max(v, 1e-10))
        return entropy

    def _save_attribution(self, query: str, final_source: str,
                           contributions: Dict, top_source: str, entropy: float):
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute('''
                INSERT INTO attributions (query, final_source, contributions, top_source, entropy, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (query[:200], final_source,
                  json.dumps(contributions, ensure_ascii=False),
                  top_source, entropy, datetime.now().isoformat()), commit=True)
        except Exception as e:
            logger.error(f"归因保存失败: {e}")

    def get_recent_attributions(self, limit: int = 20) -> List[Dict]:
        try:
            db = DatabaseManager.get(self.db_path)
            rows = db.query(
                "SELECT query, final_source, contributions, top_source, entropy, created_at FROM attributions ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return [
                {"query": r[0], "final_source": r[1], "contributions": json.loads(r[2]),
                 "top_source": r[3], "entropy": r[4], "created_at": r[5]}
                for r in rows
            ]
        except Exception:
            return []

    def get_source_reliability(self) -> Dict[str, float]:
        attributions = self.get_recent_attributions(limit=100)
        if not attributions:
            return {}
        source_scores = {}
        for attr in attributions:
            top = attr.get("top_source", "")
            if top:
                source_scores[top] = source_scores.get(top, 0) + 1
        total = sum(source_scores.values())
        if total > 0:
            source_scores = {k: round(v / total, 3) for k, v in source_scores.items()}
        return dict(sorted(source_scores.items(), key=lambda x: x[1], reverse=True))


contrib_attributor = ContribAttributor()