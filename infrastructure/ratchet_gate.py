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


import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from loguru import logger
from infrastructure.database_manager import DatabaseManager


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

        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS ratchet_baseline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT,
                ratchet_level REAL,
                previous_level REAL,
                promoted_at TEXT,
                promotion_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS ratchet_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT,
                candidate_score REAL,
                ratchet_level REAL,
                approved BOOLEAN,
                delta REAL,
                reason TEXT,
                timestamp TEXT
            );
            CREATE TABLE IF NOT EXISTS ratchet_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT,
                snapshot_type TEXT,
                data TEXT,
                fitness_score REAL,
                created_at TEXT
            );
        ''')

    def get_ratchet_level(self, domain: str = "global") -> float:
        db = DatabaseManager.get(self.db_path)
        row = db.query_one(
            "SELECT ratchet_level FROM ratchet_baseline WHERE domain = ? ORDER BY promoted_at DESC LIMIT 1",
            (domain,)
        )
        if row:
            return row[0]

        baseline = self._compute_baseline(domain)
        if baseline > 0:
            db.execute(
                "INSERT INTO ratchet_baseline (domain, ratchet_level, previous_level, promoted_at, promotion_count) VALUES (?, ?, 0, ?, 1)",
                (domain, baseline, datetime.now().isoformat()),
                commit=True
            )
        return baseline

    def _compute_baseline(self, domain: str) -> float:
        try:
            from pathlib import Path
            genome_db = Path("data/genome.db")
            if genome_db.exists():
                db = DatabaseManager.get(str(genome_db))
                row = db.query_one("SELECT AVG(fitness) FROM genomes WHERE fitness IS NOT NULL")
                if row and row[0] is not None:
                    return row[0]
        except Exception:
            pass

        try:
            from pathlib import Path
            exp_db = Path("experience_pool.db")
            if exp_db.exists():
                db = DatabaseManager.get(str(exp_db))
                row = db.query_one("SELECT AVG(quality_score) FROM experiences")
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

        db = DatabaseManager.get(self.db_path)
        db.execute('''
            INSERT INTO ratchet_decisions (domain, candidate_score, ratchet_level, approved, delta, reason, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (domain, candidate_score, ratchet_level, approved, delta, reason, decision.timestamp), commit=True)

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

        db = DatabaseManager.get(self.db_path)
        db.execute(
            "UPDATE ratchet_baseline SET previous_level = ratchet_level WHERE domain = ?",
            (domain,),
            commit=True
        )
        db.execute('''
            INSERT INTO ratchet_baseline (domain, ratchet_level, previous_level, promoted_at, promotion_count)
            VALUES (?, ?, ?, ?, 1)
        ''', (domain, current_score, ratchet_level, datetime.now().isoformat()), commit=True)

        logger.info(f"棘轮门提升: {domain} {ratchet_level:.4f} -> {current_score:.4f}")
        return True

    def create_snapshot(self, domain: str, snapshot_type: str, data: Dict, fitness_score: float):
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            INSERT INTO ratchet_snapshots (domain, snapshot_type, data, fitness_score, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (domain, snapshot_type, json.dumps(data, ensure_ascii=False), fitness_score, datetime.now().isoformat()), commit=True)

    def get_latest_snapshot(self, domain: str, snapshot_type: str = None) -> Optional[Dict]:
        db = DatabaseManager.get(self.db_path)
        if snapshot_type:
            row = db.query_one(
                "SELECT data, fitness_score, created_at FROM ratchet_snapshots WHERE domain = ? AND snapshot_type = ? ORDER BY created_at DESC LIMIT 1",
                (domain, snapshot_type)
            )
        else:
            row = db.query_one(
                "SELECT data, fitness_score, created_at FROM ratchet_snapshots WHERE domain = ? ORDER BY created_at DESC LIMIT 1",
                (domain,)
            )
        if row:
            return {"data": json.loads(row[0]), "fitness_score": row[1], "created_at": row[2]}
        return None

    def get_stats(self) -> Dict:
        db = DatabaseManager.get(self.db_path)
        rows = db.query("SELECT domain, ratchet_level FROM ratchet_baseline ORDER BY promoted_at DESC")
        baselines = {}
        for row in rows:
            if row[0] not in baselines:
                baselines[row[0]] = row[1]

        approved = db.query_one("SELECT COUNT(*) FROM ratchet_decisions WHERE approved = 1")[0]
        rejected = db.query_one("SELECT COUNT(*) FROM ratchet_decisions WHERE approved = 0")[0]

        return {
            "baselines": baselines,
            "total_approved": approved,
            "total_rejected": rejected,
            "approval_rate": approved / max(1, approved + rejected),
        }


ratchet_gate = RatchetGate()


def guard_change(domain: str, quality_score: float, description: str = "",
                 block_on_reject: bool = False) -> Tuple[bool, RatchetDecision]:
    """
    全链路棘轮守卫 — 在关键变更前调用
    
    Args:
        domain: 变更域 (cbnr/knowledge_graph/truth/experience/genome/chat_response)
        quality_score: 变更的质量分数 [0, 1]
        description: 变更描述
        block_on_reject: True=拒绝时阻断变更, False=影子模式(仅记录)
    
    Returns:
        (proceed, decision) — proceed=True表示可以继续, decision包含详细信息
    """
    decision = ratchet_gate.validate(quality_score, domain=domain)
    
    if not decision.approved:
        if block_on_reject:
            logger.warning(f"棘轮守卫阻断: {domain} | {description[:60]} | {decision.reason}")
            return False, decision
        else:
            logger.info(f"棘轮守卫影子记录: {domain} | {description[:60]} | {decision.reason}")
            return True, decision
    
    ratchet_gate.promote(domain)
    return True, decision