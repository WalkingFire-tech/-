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
    MAX_RATCHET_LEVEL = 0.85
    DECAY_RATE = 0.02
    DECAY_COOLDOWN_HOURS = 6

    def __init__(self, db_path: str = "data/ratchet_gate.db"):
        self.db_path = db_path
        self._init_db()

    def _is_system_degraded(self) -> bool:
        try:
            from core.resource_awareness.adaptive_governor import get_adaptive_governor
            governor = get_adaptive_governor()
            mode = governor.get_effective_mode()
            return mode in ("conservative", "emergency")
        except Exception:
            pass
        try:
            from core.self.model import get_self_model
            sm = get_self_model()
            directive = sm.behavioral_directive()
            return directive.get("pathway_state") == "DEGRADED"
        except Exception:
            pass
        return False

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
            "SELECT ratchet_level, promoted_at FROM ratchet_baseline WHERE domain = ? ORDER BY promoted_at DESC LIMIT 1",
            (domain,)
        )
        if row:
            ratchet_level = row[0]
            promoted_at = row[1]
            ratchet_level = min(ratchet_level, self.MAX_RATCHET_LEVEL)
            try:
                from datetime import datetime as _dt
                promoted_dt = _dt.fromisoformat(promoted_at)
                hours_since = (_dt.now() - promoted_dt).total_seconds() / 3600
                if hours_since > self.DECAY_COOLDOWN_HOURS:
                    decay_steps = int(hours_since / self.DECAY_COOLDOWN_HOURS)
                    decayed = ratchet_level - self.DECAY_RATE * decay_steps
                    ratchet_level = max(decayed, 0.3)
                    if decayed < ratchet_level + self.DECAY_RATE * decay_steps:
                        logger.info(f"棘轮衰减: {domain} {ratchet_level + self.DECAY_RATE * decay_steps:.4f} -> {ratchet_level:.4f} (闲置{hours_since:.0f}h)")
            except Exception:
                pass
            return ratchet_level

        baseline = self._compute_baseline(domain)
        baseline = min(baseline, self.MAX_RATCHET_LEVEL)
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
            logger.warning("操作降级跳过")

        try:
            from pathlib import Path
            exp_db = Path("data/experience_pool.db")
            if exp_db.exists():
                db = DatabaseManager.get(str(exp_db))
                row = db.query_one("SELECT AVG(quality_score) FROM experiences")
                if row and row[0] is not None:
                    return min(1.0, row[0])
        except Exception:
            logger.warning("操作降级跳过")

        return 0.5

    def validate(self, candidate_score: float, domain: str = "global",
                 min_improvement: float = None) -> RatchetDecision:
        ratchet_level = self.get_ratchet_level(domain)
        min_imp = min_improvement or self.MIN_IMPROVEMENT_RATIO
        delta = candidate_score - ratchet_level

        tolerance = self.MAX_REGRESSION_TOLERANCE
        degraded = self._is_system_degraded()
        if degraded:
            tolerance = self.MAX_REGRESSION_TOLERANCE * 5
            if delta >= -tolerance:
                reason_prefix = "[降级通道] "
            else:
                reason_prefix = "[降级通道] "
        else:
            reason_prefix = ""

        if candidate_score >= ratchet_level * min_imp:
            approved = True
            reason = f"{reason_prefix}提升{delta:.4f}超过门槛{ratchet_level * min_imp - ratchet_level:.4f}"
        elif delta >= -tolerance:
            approved = True
            reason = f"{reason_prefix}微小回退{abs(delta):.4f}在容忍范围内(tol={tolerance:.2f})"
        else:
            approved = False
            reason = f"{reason_prefix}回退{abs(delta):.4f}超过容忍度{tolerance:.2f}"

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

    def promote(self, domain: str = "global", candidate_score: float = None) -> bool:
        ratchet_level = self.get_ratchet_level(domain)

        if candidate_score is not None:
            new_level = candidate_score
        else:
            new_level = self._compute_baseline(domain)

        if new_level <= ratchet_level:
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
        ''', (domain, new_level, ratchet_level, datetime.now().isoformat()), commit=True)

        logger.info(f"棘轮门提升: {domain} {ratchet_level:.4f} -> {new_level:.4f}")
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

_promotion_cooldown = {}

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
    
    import time as _time
    now = _time.time()
    last_promotion = _promotion_cooldown.get(domain, 0)
    if decision.delta > 0.05 and (now - last_promotion) > 3600:
        ratchet_gate.promote(domain, candidate_score=decision.candidate_score)
        _promotion_cooldown[domain] = now
    
    return True, decision