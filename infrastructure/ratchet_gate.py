"""
棘轮门 (RatchetGate) - 主动式防回归机制

核心原则：系统整体适应度单调不减
- 维护 ratchet_level（历史最高适应度基线）
- 任何进化变更必须通过 validate() 验证
- 确认不退步才调用 promote() 提升
- 影子模式：变更先评估，确认安全才应用

参考实现：
- GenomeEvolver.promote_candidate() 的5%提升门槛
- TruthAccumulator 的渐进注入验证模式
"""

import sqlite3
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class RatchetDecision:
    approved: bool
    ratchet_level: float
    candidate_score: float
    delta: float
    reason: str
    timestamp: str


class RatchetGate:
    MIN_IMPROVEMENT_RATIO = 1.02
    MAX_REGRESSION_TOLERANCE = 0.03

    def __init__(self, db_path: str = "data/ratchet_gate.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        from pathlib import Path
        Path(self.db_path).parent.mkdir(exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS ratchet_baseline (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT,
                    ratchet_level REAL,
                    previous_level REAL,
                    promoted_at TEXT,
                    promotion_count INTEGER DEFAULT 0
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS ratchet_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT,
                    candidate_score REAL,
                    ratchet_level REAL,
                    approved BOOLEAN,
                    delta REAL,
                    reason TEXT,
                    timestamp TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS ratchet_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT,
                    snapshot_type TEXT,
                    data TEXT,
                    fitness_score REAL,
                    created_at TEXT
                )
            ''')

    def get_ratchet_level(self, domain: str = "global") -> float:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT ratchet_level FROM ratchet_baseline WHERE domain = ? ORDER BY promoted_at DESC LIMIT 1",
                (domain,)
            )
            row = cur.fetchone()
            if row:
                return row[0]

            baseline = self._compute_baseline(domain)
            if baseline > 0:
                conn.execute(
                    "INSERT INTO ratchet_baseline (domain, ratchet_level, previous_level, promoted_at, promotion_count) VALUES (?, ?, 0, ?, 1)",
                    (domain, baseline, datetime.now().isoformat())
                )
            return baseline

    def _compute_baseline(self, domain: str) -> float:
        try:
            from pathlib import Path
            genome_db = Path("data/genome.db")
            if genome_db.exists():
                with sqlite3.connect(str(genome_db)) as conn:
                    cur = conn.execute("SELECT AVG(fitness) FROM genomes WHERE fitness IS NOT NULL")
                    row = cur.fetchone()
                    if row and row[0] is not None:
                        return row[0]
        except Exception:
            pass

        try:
            from pathlib import Path
            exp_db = Path("experience_pool.db")
            if exp_db.exists():
                with sqlite3.connect(str(exp_db)) as conn:
                    cur = conn.execute("SELECT AVG(quality_score) FROM experiences")
                    row = cur.fetchone()
                    if row and row[0] is not None:
                        return min(1.0, row[0])
        except Exception:
            pass

        return 0.5

    def validate(self, candidate_score: float, domain: str = "global",
                 min_improvement: float = None) -> RatchetDecision:
        ratchet_level = self.get_ratchet_level(domain)
        min_imp = min_improvement or self.MIN_IMPROVEMENT_RATIO
        delta = candidate_score - ratchet_level

        if candidate_score >= ratchet_level * min_imp:
            approved = True
            reason = f"提升{delta:.4f}超过门槛{ratchet_level * min_imp - ratchet_level:.4f}"
        elif delta >= -self.MAX_REGRESSION_TOLERANCE:
            approved = True
            reason = f"微小回退{abs(delta):.4f}在容忍范围内"
        else:
            approved = False
            reason = f"回退{abs(delta):.4f}超过容忍度{self.MAX_REGRESSION_TOLERANCE}"

        decision = RatchetDecision(
            approved=approved,
            ratchet_level=ratchet_level,
            candidate_score=candidate_score,
            delta=delta,
            reason=reason,
            timestamp=datetime.now().isoformat(),
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO ratchet_decisions (domain, candidate_score, ratchet_level, approved, delta, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (domain, candidate_score, ratchet_level, approved, delta, reason, decision.timestamp))

        if approved:
            logger.info(f"棘轮门通过: {domain} score={candidate_score:.4f} ratchet={ratchet_level:.4f} ({reason})")
        else:
            logger.warning(f"棘轮门拒绝: {domain} score={candidate_score:.4f} ratchet={ratchet_level:.4f} ({reason})")

        return decision

    def promote(self, domain: str = "global") -> bool:
        ratchet_level = self.get_ratchet_level(domain)
        current_score = self._compute_baseline(domain)

        if current_score <= ratchet_level:
            return False

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE ratchet_baseline SET previous_level = ratchet_level WHERE domain = ?",
                (domain,)
            )
            conn.execute('''
                INSERT INTO ratchet_baseline (domain, ratchet_level, previous_level, promoted_at, promotion_count)
                VALUES (?, ?, ?, ?, 1)
            ''', (domain, current_score, ratchet_level, datetime.now().isoformat()))

        logger.info(f"棘轮门提升: {domain} {ratchet_level:.4f} -> {current_score:.4f}")
        return True

    def create_snapshot(self, domain: str, snapshot_type: str, data: Dict, fitness_score: float):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO ratchet_snapshots (domain, snapshot_type, data, fitness_score, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (domain, snapshot_type, json.dumps(data, ensure_ascii=False), fitness_score, datetime.now().isoformat()))

    def get_latest_snapshot(self, domain: str, snapshot_type: str = None) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            if snapshot_type:
                cur = conn.execute(
                    "SELECT data, fitness_score, created_at FROM ratchet_snapshots WHERE domain = ? AND snapshot_type = ? ORDER BY created_at DESC LIMIT 1",
                    (domain, snapshot_type)
                )
            else:
                cur = conn.execute(
                    "SELECT data, fitness_score, created_at FROM ratchet_snapshots WHERE domain = ? ORDER BY created_at DESC LIMIT 1",
                    (domain,)
                )
            row = cur.fetchone()
            if row:
                return {"data": json.loads(row[0]), "fitness_score": row[1], "created_at": row[2]}
        return None

    def get_stats(self) -> Dict:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT domain, ratchet_level FROM ratchet_baseline ORDER BY promoted_at DESC")
            baselines = {}
            for row in cur.fetchall():
                if row[0] not in baselines:
                    baselines[row[0]] = row[1]

            cur = conn.execute("SELECT COUNT(*) FROM ratchet_decisions WHERE approved = 1")
            approved = cur.fetchone()[0]
            cur = conn.execute("SELECT COUNT(*) FROM ratchet_decisions WHERE approved = 0")
            rejected = cur.fetchone()[0]

        return {
            "baselines": baselines,
            "total_approved": approved,
            "total_rejected": rejected,
            "approval_rate": approved / max(1, approved + rejected),
        }


ratchet_gate = RatchetGate()