"""
路径权重管理器 - AdaBoost风格动态加权

核心思想：各信息路径的权重根据历史表现动态调整
- 表现好的路径获得更大权重（能者多劳）
- 表现差的路径权重衰减（但不归零，保留多样性）
- 每次交互后根据结果更新权重
- 归一化确保权重和为1

与"动态概率云"的关系：
- 权重分布 = 概率云的密度分布
- 权重更新 = 概率云的动态演化
- 置信度分布 = 加权贡献度（类似SHAP值）
"""

import sqlite3
import time
import json
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger


class PathWeightManager:
    DEFAULT_PATHS = {
        "rule_reasoning": {"weight": 0.15, "success_rate": 0.7},
        "experience_pool": {"weight": 0.15, "success_rate": 0.65},
        "knowledge_base": {"weight": 0.12, "success_rate": 0.6},
        "ollama": {"weight": 0.18, "success_rate": 0.7},
        "external_model": {"weight": 0.15, "success_rate": 0.75},
        "external_learner": {"weight": 0.08, "success_rate": 0.6},
        "fact_anchor": {"weight": 0.10, "success_rate": 0.8},
        "self_reasoning": {"weight": 0.05, "success_rate": 0.55},
        "tool_framework": {"weight": 0.02, "success_rate": 0.5},
    }

    def __init__(self, db_path: str = "data/path_weights.db"):
        self.db_path = db_path
        self._alpha = 0.1
        self._decay_rate = 0.005
        self._min_weight = 0.02
        self._max_history = 50
        self._paths: Dict[str, dict] = {}
        self._init_db()
        self._load_weights()

    def _init_db(self):
        from pathlib import Path
        Path(self.db_path).parent.mkdir(exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS path_weights (
                    path_name TEXT PRIMARY KEY,
                    weight REAL,
                    success_rate REAL,
                    total_uses INTEGER DEFAULT 0,
                    total_successes INTEGER DEFAULT 0,
                    last_updated TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS weight_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path_name TEXT,
                    old_weight REAL,
                    new_weight REAL,
                    success BOOLEAN,
                    confidence REAL,
                    timestamp TEXT
                )
            ''')

    def _load_weights(self):
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT path_name, weight, success_rate, total_uses, total_successes FROM path_weights")
            rows = cur.fetchall()
        if rows:
            for name, weight, sr, uses, succ in rows:
                self._paths[name] = {
                    "weight": weight,
                    "success_rate": sr,
                    "total_uses": uses,
                    "total_successes": succ,
                    "history": [],
                }
        else:
            for name, info in self.DEFAULT_PATHS.items():
                self._paths[name] = {
                    "weight": info["weight"],
                    "success_rate": info["success_rate"],
                    "total_uses": 0,
                    "total_successes": 0,
                    "history": [],
                }
            self._save_all_weights()

    def _save_all_weights(self):
        with sqlite3.connect(self.db_path) as conn:
            for name, info in self._paths.items():
                conn.execute('''
                    INSERT OR REPLACE INTO path_weights (path_name, weight, success_rate, total_uses, total_successes, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, info["weight"], info["success_rate"],
                      info["total_uses"], info["total_successes"],
                      datetime.now().isoformat()))

    def update_weight(self, path: str, success: bool, confidence: float = 0.5,
                      uncertainty: float = None, retrieval_entropy: float = None):
        """更新路径权重 - 不确定性感知版
        
        增强特性：
        - uncertainty: 检索不确定性(0-1)，高不确定性但成功的路径应获得更大权重提升
        - retrieval_entropy: 检索结果熵值，用于量化检索过程的可靠性
        
        核心思想（来自BayesRAG/DAT）：
        - 高不确定性+成功 = 意外收获，应大幅提升权重（探索价值高）
        - 高不确定性+失败 = 预期之中，权重衰减较小（保留探索可能性）
        - 低不确定性+成功 = 稳定贡献，正常提升权重
        - 低不确定性+失败 = 需警惕，权重衰减较大
        """
        if path not in self._paths:
            self._paths[path] = {"weight": 0.05, "success_rate": 0.5, "total_uses": 0, "total_successes": 0, "history": []}

        old_weight = self._paths[path]["weight"]

        uncertainty_bonus = 0.0
        if uncertainty is not None and uncertainty > 0.5 and success:
            uncertainty_bonus = self._alpha * uncertainty * 0.5

        if success:
            delta = self._alpha * confidence + uncertainty_bonus
        else:
            uncertainty_penalty = 0.0
            if uncertainty is not None and uncertainty < 0.3:
                uncertainty_penalty = self._alpha * 0.3
            delta = -self._alpha * confidence * 0.5 - uncertainty_penalty

        self._paths[path]["weight"] *= (1 + delta)
        self._paths[path]["weight"] = max(self._min_weight, self._paths[path]["weight"])
        self._paths[path]["total_uses"] += 1
        if success:
            self._paths[path]["total_successes"] += 1

        recent_successes = self._paths[path]["total_successes"]
        recent_total = self._paths[path]["total_uses"]
        if recent_total > 0:
            self._paths[path]["success_rate"] = recent_successes / recent_total

        self._paths[path]["history"].append({
            "success": success, "confidence": confidence, "timestamp": time.time(),
            "uncertainty": uncertainty, "retrieval_entropy": retrieval_entropy,
        })
        if len(self._paths[path]["history"]) > self._max_history:
            self._paths[path]["history"] = self._paths[path]["history"][-self._max_history:]

        self._normalize()
        self._save_path_weight(path)

        logger.debug(f"路径权重更新: {path} {old_weight:.4f}→{self._paths[path]['weight']:.4f} "
                      f"({'✓' if success else '✗'} conf={confidence:.2f} unc={uncertainty:.2f if uncertainty is not None else 'N/A'})")

    def _normalize(self):
        total = sum(info["weight"] for info in self._paths.values())
        if total > 0:
            for info in self._paths.values():
                info["weight"] /= total

    def _save_path_weight(self, path: str):
        info = self._paths[path]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO path_weights (path_name, weight, success_rate, total_uses, total_successes, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (path, info["weight"], info["success_rate"],
                  info["total_uses"], info["total_successes"],
                  datetime.now().isoformat()))
            conn.execute('''
                INSERT INTO weight_history (path_name, old_weight, new_weight, success, confidence, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (path, info["weight"], info["weight"], True, 0.5, datetime.now().isoformat()))

    def apply_decay(self):
        for name, info in self._paths.items():
            info["weight"] *= (1 - self._decay_rate)
            info["weight"] = max(self._min_weight, info["weight"])
        self._normalize()
        self._save_all_weights()
        logger.debug("路径权重衰减完成")

    def get_weights(self) -> Dict[str, float]:
        return {p: info["weight"] for p, info in self._paths.items()}

    def get_weight(self, path: str) -> float:
        if path in self._paths:
            return self._paths[path]["weight"]
        return 0.05

    def get_confidence_distribution(self) -> Dict[str, float]:
        result = {}
        for p, info in self._paths.items():
            result[p] = info["weight"] * info["success_rate"]
        total = sum(result.values())
        if total > 0:
            for p in result:
                result[p] /= total
        return result

    def get_weighted_score(self, path: str, base_score: float) -> float:
        weight = self.get_weight(path)
        confidence = self._paths.get(path, {}).get("success_rate", 0.5)
        return base_score * weight * confidence

    def batch_update(self, results: List[Dict]):
        for r in results:
            path = r.get("source", "unknown")
            success = r.get("success", False)
            confidence = r.get("confidence", 0.5)
            self.update_weight(path, success, confidence)

    def get_stats(self) -> Dict:
        return {
            "paths": {
                name: {
                    "weight": round(info["weight"], 4),
                    "success_rate": round(info["success_rate"], 3),
                    "total_uses": info["total_uses"],
                    "confidence_contribution": round(info["weight"] * info["success_rate"], 4),
                }
                for name, info in sorted(self._paths.items(), key=lambda x: x[1]["weight"], reverse=True)
            },
            "total_paths": len(self._paths),
            "alpha": self._alpha,
            "decay_rate": self._decay_rate,
        }


path_weight_manager = PathWeightManager()