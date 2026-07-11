"""
增量知识更新器 - ResNet风格残差学习

核心思想：只更新知识的"增量部分"，而非全量重写
- compute_delta: 计算新旧知识的差异（残差）
- update: 增量更新，只写入变化的部分
- 恒等映射：高度相似时直接复用，只对微小差异调整

与PathWeightManager的关系：
- PathWeightManager管"选哪条路"
- DeltaKnowledgeUpdater管"路上学到的东西怎么存"
- 两者协同：权重高的路径产生的知识增量更可信
"""

import time
import json
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger
from infrastructure.database_manager import DatabaseManager


class DeltaKnowledgeUpdater:
    def __init__(self, db_path: str = "data/delta_knowledge.db"):
        self.db_path = db_path
        self._similarity_threshold = 0.7
        self._delta_threshold = 0.3
        self._init_db()

    def _init_db(self):
        from pathlib import Path
        Path(self.db_path).parent.mkdir(exist_ok=True)
        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS knowledge_base (
                topic TEXT PRIMARY KEY,
                content TEXT,
                version INTEGER DEFAULT 1,
                last_updated TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS delta_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT,
                delta_size INTEGER,
                total_size INTEGER,
                compression_ratio REAL,
                version INTEGER,
                timestamp TEXT
            )
        ''')

    def compute_delta(self, new_knowledge: Dict, old_knowledge: Dict) -> Dict:
        delta = {}
        for key, value in new_knowledge.items():
            if key not in old_knowledge:
                delta[key] = {"type": "add", "value": value}
            else:
                sim = self._compute_similarity(str(value), str(old_knowledge[key]))
                if sim < self._similarity_threshold:
                    delta[key] = {"type": "update", "value": value, "old_value": old_knowledge[key], "similarity": round(sim, 3)}
        for key in old_knowledge:
            if key not in new_knowledge:
                delta[key] = {"type": "remove", "old_value": old_knowledge[key]}
        return delta

    def update(self, new_knowledge: Dict, topic: str) -> Dict:
        old_knowledge = self._load_topic(topic)
        if not old_knowledge:
            self._save_topic(topic, new_knowledge, version=1)
            return {"updated": True, "delta_size": len(new_knowledge), "total_size": len(new_knowledge),
                    "compression_ratio": 1.0, "version": 1, "type": "new"}

        delta = self.compute_delta(new_knowledge, old_knowledge)
        if not delta:
            return {"updated": False, "reason": "no_significant_change", "version": self._get_version(topic)}

        merged = dict(old_knowledge)
        for key, change in delta.items():
            if change["type"] == "add":
                merged[key] = change["value"]
            elif change["type"] == "update":
                merged[key] = change["value"]
            elif change["type"] == "remove":
                del merged[key]

        version = self._get_version(topic) + 1
        self._save_topic(topic, merged, version=version)
        self._save_delta(topic, delta, version)

        compression = len(delta) / max(1, len(new_knowledge))
        logger.debug(f"增量更新: {topic} v{version}, delta={len(delta)}/{len(new_knowledge)} "
                      f"compression={compression:.2f}")
        return {
            "updated": True,
            "delta_size": len(delta),
            "total_size": len(new_knowledge),
            "compression_ratio": round(compression, 3),
            "version": version,
            "type": "incremental",
            "delta_types": {t: sum(1 for d in delta.values() if d["type"] == t) for t in ["add", "update", "remove"]},
        }

    def get_topic(self, topic: str) -> Optional[Dict]:
        return self._load_topic(topic)

    def get_delta_stats(self, topic: str = "", limit: int = 20) -> List[Dict]:
        try:
            db = DatabaseManager.get(self.db_path)
            if topic:
                rows = db.query(
                    "SELECT topic, delta_size, total_size, compression_ratio, version, timestamp FROM delta_history WHERE topic=? ORDER BY id DESC LIMIT ?",
                    (topic, limit))
            else:
                rows = db.query(
                    "SELECT topic, delta_size, total_size, compression_ratio, version, timestamp FROM delta_history ORDER BY id DESC LIMIT ?",
                    (limit,))
            return [{"topic": r[0], "delta_size": r[1], "total_size": r[2],
                      "compression_ratio": r[3], "version": r[4], "timestamp": r[5]}
                    for r in rows]
        except Exception:
            return []

    def _compute_similarity(self, text_a: str, text_b: str) -> float:
        if not text_a or not text_b:
            return 0.0
        tokens_a = set(text_a.lower().split())
        tokens_b = set(text_b.lower().split())
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return len(intersection) / len(union)

    def _load_topic(self, topic: str) -> Optional[Dict]:
        try:
            db = DatabaseManager.get(self.db_path)
            row = db.query_one("SELECT content FROM knowledge_base WHERE topic=?", (topic,))
            if row:
                return json.loads(row[0])
        except Exception:
            pass
        return None

    def _save_topic(self, topic: str, knowledge: Dict, version: int = 1):
        now = datetime.now().isoformat()
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            INSERT OR REPLACE INTO knowledge_base (topic, content, version, last_updated, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (topic, json.dumps(knowledge, ensure_ascii=False), version, now, now), commit=True)

    def _get_version(self, topic: str) -> int:
        try:
            db = DatabaseManager.get(self.db_path)
            row = db.query_one("SELECT version FROM knowledge_base WHERE topic=?", (topic,))
            return row[0] if row else 0
        except Exception:
            return 0

    def _save_delta(self, topic: str, delta: Dict, version: int):
        now = datetime.now().isoformat()
        delta_size = len(delta)
        total_size = delta_size
        compression = delta_size / max(1, total_size)
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            INSERT INTO delta_history (topic, delta_size, total_size, compression_ratio, version, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (topic, delta_size, total_size, compression, version, now), commit=True)


delta_knowledge_updater = DeltaKnowledgeUpdater()