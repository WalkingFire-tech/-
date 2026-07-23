"""
轨迹进化系统 - 将解决路径作为可进化单元

核心思想（SE-Agent启发）：
- 每次解决问题的完整路径是一个"物种"
- 通过修订(Revision)、重组(Recombination)、精炼(Refinement)三大算子进化
- 高评分轨迹的片段可被重组到新问题中

轨迹结构：
- steps: 解决路径的每一步（阶段名+成功/失败+详情+耗时）
- decision_points: 关键决策节点（如选择哪条路径、为何提前综合）
- outcome: 最终结果（质量分、置信度、响应长度）
- context: 问题特征（意图类型、复杂度、路由策略）
"""

import json
import hashlib
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from core.ports.adapters import get_storage_port

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class TrajectoryStore:
    def __init__(self, db_path: str = "data/trajectory_evolution.db"):
        self.db_path = db_path
        self._init_database()
        logger.info(f"🧬 轨迹进化系统已初始化: {db_path}")

    def _init_database(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        db = get_storage_port(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS trajectories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT NOT NULL,
                query TEXT NOT NULL,
                intent_type TEXT DEFAULT 'unknown',
                route TEXT DEFAULT 'slow',
                steps_json TEXT NOT NULL,
                decisions_json TEXT DEFAULT '[]',
                outcome_json TEXT DEFAULT '{}',
                fitness_score REAL DEFAULT 0.0,
                duration REAL DEFAULT 0.0,
                generation INTEGER DEFAULT 0,
                parent_ids TEXT DEFAULT '',
                source TEXT DEFAULT 'live',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS trajectory_fragments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trajectory_id INTEGER NOT NULL,
                phase TEXT NOT NULL,
                success BOOLEAN DEFAULT 0,
                detail TEXT DEFAULT '',
                duration_ms INTEGER DEFAULT 0,
                source_path TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (trajectory_id) REFERENCES trajectories(id)
            );
            CREATE TABLE IF NOT EXISTS recombination_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_a_id INTEGER NOT NULL,
                parent_b_id INTEGER NOT NULL,
                child_id INTEGER NOT NULL,
                strategy TEXT DEFAULT 'cross',
                improvement REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_traj_query_hash ON trajectories(query_hash);
            CREATE INDEX IF NOT EXISTS idx_traj_fitness ON trajectories(fitness_score DESC);
            CREATE INDEX IF NOT EXISTS idx_traj_intent ON trajectories(intent_type);
            CREATE INDEX IF NOT EXISTS idx_frag_traj ON trajectory_fragments(trajectory_id);
            CREATE INDEX IF NOT EXISTS idx_frag_phase ON trajectory_fragments(phase)
        ''')

    @staticmethod
    def hash_query(query: str) -> str:
        return hashlib.md5(query.encode('utf-8')).hexdigest()

    def store_trajectory(
        self,
        query: str,
        steps: List[Dict],
        decisions: List[Dict],
        outcome: Dict,
        intent_type: str = "unknown",
        route: str = "slow",
        fitness_score: float = 0.0,
        duration: float = 0.0,
        generation: int = 0,
        parent_ids: str = "",
        source: str = "live"
    ) -> int:
        query_hash = self.hash_query(query)
        steps_json = json.dumps(steps, ensure_ascii=False)
        decisions_json = json.dumps(decisions, ensure_ascii=False)
        outcome_json = json.dumps(outcome, ensure_ascii=False)

        db = get_storage_port(self.db_path)
        cur = db.execute('''
            INSERT INTO trajectories
            (query_hash, query, intent_type, route, steps_json, decisions_json,
             outcome_json, fitness_score, duration, generation, parent_ids, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (query_hash, query, intent_type, route, steps_json, decisions_json,
              outcome_json, fitness_score, duration, generation, parent_ids, source), commit=True)

        traj_id = cur.lastrowid

        for step in steps:
            db.execute('''
                INSERT INTO trajectory_fragments
                (trajectory_id, phase, success, detail, duration_ms, source_path)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (traj_id, step.get("phase", ""), step.get("success", False),
                  step.get("detail", ""), step.get("duration_ms", 0),
                  step.get("source_path", "")), commit=True)

        logger.info(f"🧬 轨迹#{traj_id}已存储: {query[:30]} | fitness={fitness_score:.0f} | {len(steps)}步 | gen={generation}")
        
        self._auto_evolve(traj_id, query, intent_type, fitness_score)
        return traj_id

    def _auto_evolve(self, traj_id: int, query: str, intent_type: str, fitness_score: float):
        """P1-8: 自动触发轨迹修订和重组"""
        try:
            if fitness_score < 40:
                better = self.find_similar_trajectories(query, min_fitness=60, limit=1)
                if better:
                    better_traj = better[0]
                    original = self.get_trajectory(traj_id)
                    if original:
                        revised_steps = []
                        for s in original.get('steps', []):
                            if s.get('success', False):
                                revised_steps.append(s)
                            else:
                                for bs in better_traj.get('steps', []):
                                    if bs.get('phase') == s.get('phase') and bs.get('success', False):
                                        revised_steps.append(bs)
                                        break
                                else:
                                    revised_steps.append(s)
                        new_fitness = min(100, fitness_score + 20)
                        self.revise_trajectory(traj_id, revised_steps, new_fitness)
                        logger.info(f"🧬 自动修订: 轨迹#{traj_id} (fitness {fitness_score:.0f}→{new_fitness:.0f})")

            if fitness_score >= 70:
                db = get_storage_port(self.db_path)
                siblings = db.query(
                    "SELECT id, fitness_score FROM trajectories "
                    "WHERE intent_type = ? AND id != ? AND fitness_score >= 60 "
                    "ORDER BY fitness_score DESC LIMIT 1",
                    (intent_type, traj_id)
                )
                if siblings:
                    sibling_id = siblings[0]['id']
                    self.recombine(traj_id, sibling_id, query, strategy="best_of")
                    logger.info(f"🧬 自动重组: 轨迹#{traj_id}+#{sibling_id}")
        except Exception as e:
            logger.warning(f"自动进化跳过: {e}")

    def get_trajectory(self, traj_id: int) -> Optional[Dict]:
        db = get_storage_port(self.db_path)
        row = db.query_one('SELECT * FROM trajectories WHERE id = ?', (traj_id,))
        if row:
            d = dict(row)
            d['steps'] = json.loads(d['steps_json'])
            d['decisions'] = json.loads(d['decisions_json'])
            d['outcome'] = json.loads(d['outcome_json'])
            return d
        return None

    def find_similar_trajectories(
        self,
        query: str,
        intent_type: str = None,
        min_fitness: float = 0.0,
        limit: int = 5
    ) -> List[Dict]:
        query_hash = self.hash_query(query)

        db = get_storage_port(self.db_path)

        exact_matches = [dict(row) for row in db.query('''
            SELECT * FROM trajectories
            WHERE query_hash = ? AND fitness_score >= ?
            ORDER BY fitness_score DESC LIMIT ?
        ''', (query_hash, min_fitness, limit))]

        if exact_matches:
            for m in exact_matches:
                m['steps'] = json.loads(m['steps_json'])
            return exact_matches

        if intent_type:
            similar = [dict(row) for row in db.query('''
                SELECT * FROM trajectories
                WHERE intent_type = ? AND fitness_score >= ?
                ORDER BY fitness_score DESC LIMIT ?
            ''', (intent_type, min_fitness, limit))]
            for s in similar:
                s['steps'] = json.loads(s['steps_json'])
            return similar

        return []

    def get_best_fragments_for_phase(
        self,
        phase: str,
        intent_type: str = None,
        limit: int = 3
    ) -> List[Dict]:
        db = get_storage_port(self.db_path)

        if intent_type:
            return [dict(row) for row in db.query('''
                SELECT f.*, t.intent_type, t.fitness_score as traj_fitness
                FROM trajectory_fragments f
                JOIN trajectories t ON f.trajectory_id = t.id
                WHERE f.phase = ? AND f.success = 1 AND t.intent_type = ?
                ORDER BY t.fitness_score DESC
                LIMIT ?
            ''', (phase, intent_type, limit))]
        else:
            return [dict(row) for row in db.query('''
                SELECT f.*, t.intent_type, t.fitness_score as traj_fitness
                FROM trajectory_fragments f
                JOIN trajectories t ON f.trajectory_id = t.id
                WHERE f.phase = ? AND f.success = 1
                ORDER BY t.fitness_score DESC
                LIMIT ?
            ''', (phase, limit))]

    def evaluate_trajectory(self, steps: List[Dict], outcome: Dict) -> float:
        if not steps:
            return 0.0

        success_count = sum(1 for s in steps if s.get("success", False))
        success_rate = success_count / len(steps) if steps else 0

        quality = outcome.get("quality_score", 50) / 100.0
        confidence = outcome.get("confidence", 0.5)
        duration_penalty = max(0, 1.0 - outcome.get("duration", 60) / 120.0)

        fitness = (
            success_rate * 0.35 +
            quality * 0.30 +
            confidence * 0.20 +
            duration_penalty * 0.15
        )

        return round(fitness * 100, 1)

    def recombine(
        self,
        parent_a_id: int,
        parent_b_id: int,
        new_query: str,
        strategy: str = "cross"
    ) -> Optional[int]:
        parent_a = self.get_trajectory(parent_a_id)
        parent_b = self.get_trajectory(parent_b_id)

        if not parent_a or not parent_b:
            return None

        steps_a = parent_a['steps']
        steps_b = parent_b['steps']

        if strategy == "cross":
            mid = len(steps_a) // 2
            child_steps = steps_a[:mid] + steps_b[mid:]
        elif strategy == "best_of":
            child_steps = []
            phases_seen = set()
            for s in steps_a + steps_b:
                phase = s.get("phase", "")
                if phase not in phases_seen:
                    if s.get("success", False):
                        child_steps.append(s)
                        phases_seen.add(phase)
            if not child_steps:
                child_steps = steps_a
        elif strategy == "success_only":
            child_steps = [s for s in steps_a + steps_b if s.get("success", False)]
            if not child_steps:
                child_steps = steps_a
        else:
            child_steps = steps_a

        child_fitness = min(parent_a['fitness_score'], parent_b['fitness_score']) * 0.9

        child_id = self.store_trajectory(
            query=new_query,
            steps=child_steps,
            decisions=parent_a.get('decisions', []),
            outcome=parent_a.get('outcome', {}),
            intent_type=parent_a.get('intent_type', 'unknown'),
            route=parent_a.get('route', 'slow'),
            fitness_score=child_fitness,
            duration=0.0,
            generation=max(parent_a.get('generation', 0), parent_b.get('generation', 0)) + 1,
            parent_ids=f"{parent_a_id},{parent_b_id}",
            source=f"recombine_{strategy}"
        )

        db = get_storage_port(self.db_path)
        db.execute('''
            INSERT INTO recombination_log
            (parent_a_id, parent_b_id, child_id, strategy, improvement)
            VALUES (?, ?, ?, ?, ?)
        ''', (parent_a_id, parent_b_id, child_id, strategy, 0.0), commit=True)

        logger.info(f"🧬 轨迹重组: #{parent_a_id}+#{parent_b_id} → #{child_id} (策略={strategy}, gen={max(parent_a.get('generation', 0), parent_b.get('generation', 0)) + 1})")
        return child_id

    def revise_trajectory(self, traj_id: int, revised_steps: List[Dict], new_fitness: float) -> int:
        original = self.get_trajectory(traj_id)
        if not original:
            return traj_id

        new_id = self.store_trajectory(
            query=original['query'],
            steps=revised_steps,
            decisions=original.get('decisions', []),
            outcome=original.get('outcome', {}),
            intent_type=original.get('intent_type', 'unknown'),
            route=original.get('route', 'slow'),
            fitness_score=new_fitness,
            duration=original.get('duration', 0.0),
            generation=original.get('generation', 0) + 1,
            parent_ids=str(traj_id),
            source="revision"
        )

        logger.info(f"🧬 轨迹修订: #{traj_id} → #{new_id} (fitness: {original['fitness_score']:.0f}→{new_fitness:.0f})")
        return new_id

    def get_evolution_stats(self) -> Dict:
        db = get_storage_port(self.db_path)
        total = db.query_one('SELECT COUNT(*) FROM trajectories')[0]
        avg_fitness = db.query_one('SELECT AVG(fitness_score) FROM trajectories')[0] or 0
        max_gen = db.query_one('SELECT MAX(generation) FROM trajectories')[0] or 0
        recombinations = db.query_one('SELECT COUNT(*) FROM recombination_log')[0]
        revisions = db.query_one("SELECT COUNT(*) FROM trajectories WHERE source LIKE 'revision%'")[0]
        live = db.query_one("SELECT COUNT(*) FROM trajectories WHERE source = 'live'")[0]

        by_intent = {}
        for row in db.query('SELECT intent_type, COUNT(*), AVG(fitness_score) FROM trajectories GROUP BY intent_type'):
            by_intent[row[0]] = {"count": row[1], "avg_fitness": round(row[2], 1)}

        return {
            "total_trajectories": total,
            "live_trajectories": live,
            "avg_fitness": round(avg_fitness, 1),
            "max_generation": max_gen,
            "recombinations": recombinations,
            "revisions": revisions,
            "by_intent_type": by_intent
        }


trajectory_store = TrajectoryStore()
