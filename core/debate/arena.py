"""
辩论场 — 多智能体辩论的核心编排器

流程：
1. 接收问题 + 上下文
2. 每个角色独立推理（注入角色偏见提示）
3. 角色之间交叉质询（可选）
4. 仲裁器加权融合

设计原则：
- 复用现有推理基础设施（self_reason / ollama），不新建推理引擎
- 辩论是"视角的互补"，不是"谁对谁错"
- 轻量：辩论过程不产生额外LLM调用，而是用已有候选结果+角色提示重新评估
"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from core.debate.personas import Persona, PRAGMATIST, IDEALIST, SKEPTIC, ALL_PERSONAS
from core.debate.arbitrator import Arbitrator, ArbitrationResult

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class DebateResult:
    query: str
    positions: Dict[str, str]
    arbitration: ArbitrationResult
    elapsed: float = 0.0
    rounds: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query[:100],
            "positions": self.positions,
            "arbitration": self.arbitration.to_dict(),
            "elapsed": round(self.elapsed, 1),
            "rounds": self.rounds,
        }


class DebateArena:
    """
    辩论场 — 让不同视角碰撞，涌现更优方案
    
    使用方式：
        arena = DebateArena()
        result = await arena.debate(
            query="如何优化系统性能？",
            context="当前系统响应时间3秒...",
            candidates=[...],  # 已有的候选答案
        )
    """

    def __init__(self, personas: List[Persona] = None, arbitrator: Arbitrator = None):
        self.personas = personas or ALL_PERSONAS
        self.arbitrator = arbitrator or Arbitrator()

    async def debate(
        self,
        query: str,
        context: str = "",
        candidates: List[Dict[str, Any]] = None,
        spirit_resonances: List[Dict[str, Any]] = None,
        max_rounds: int = 1,
    ) -> DebateResult:
        """
        执行多智能体辩论
        
        Args:
            query: 问题
            context: 上下文
            candidates: 已有候选答案（来自parallel_router）
            spirit_resonances: SpiritCore共振结果
            max_rounds: 辩论轮数（1=仅立场陈述，2+=含交叉质询）
        """
        start = time.time()

        positions = await self._gather_positions(query, context, candidates)

        if max_rounds > 1 and len(positions) > 1:
            positions = await self._cross_examine(query, positions)

        arbitration = self.arbitrator.arbitrate(
            query=query,
            positions=positions,
            spirit_resonances=spirit_resonances,
        )

        elapsed = time.time() - start
        logger.info(
            f"🏟️ 辩论完成: {len(positions)}方参与, "
            f"共识={arbitration.consensus_level}, "
            f"置信度={arbitration.confidence:.2f}, "
            f"耗时={elapsed:.1f}s"
        )

        return DebateResult(
            query=query,
            positions=positions,
            arbitration=arbitration,
            elapsed=elapsed,
            rounds=max_rounds,
        )

    async def _gather_positions(
        self,
        query: str,
        context: str,
        candidates: List[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """每个角色独立形成立场"""
        positions = {}

        for persona in self.personas:
            position = self._form_position(persona, query, context, candidates)
            if position:
                positions[persona.role] = position

        return positions

    def _form_position(
        self,
        persona: Persona,
        query: str,
        context: str,
        candidates: List[Dict[str, Any]] = None,
    ) -> str:
        """基于角色偏见从候选答案中形成立场"""
        if not candidates:
            return f"[{persona.name}视角] {persona.focus}：需要更多信息才能给出立场"

        scored = []
        for c in candidates:
            resp = c.get("response", "")
            source = c.get("source", "unknown")
            quality = c.get("quality", 50)

            role_score = quality
            for criterion in persona.evaluation_criteria:
                if criterion == "feasibility" and source in ("experience", "rule"):
                    role_score += 10
                elif criterion == "depth" and source in ("self_reasoning", "knowledge"):
                    role_score += 10
                elif criterion == "risk_level" and len(resp) > 200:
                    role_score += 5
                elif criterion == "innovation" and source == "ollama":
                    role_score += 8
                elif criterion == "blind_spots" and quality < 60:
                    role_score += 5
                elif criterion == "assumption_validity":
                    role_score += 3

            scored.append((role_score, source, resp))

        scored.sort(key=lambda x: x[0], reverse=True)

        if scored:
            best_score, best_source, best_resp = scored[0]
            return f"[{persona.name}视角] 偏好来源={best_source}(角色评分{best_score})。{best_resp[:300]}"

        return ""

    async def _cross_examine(
        self,
        query: str,
        positions: Dict[str, str],
    ) -> Dict[str, str]:
        """交叉质询：每个角色对其他角色的立场提出质疑"""
        refined = dict(positions)

        for persona in self.personas:
            if persona.role not in positions:
                continue

            challenges = []
            for other_role, other_pos in positions.items():
                if other_role == persona.role:
                    continue
                challenges.append(f"{other_role}认为: {other_pos[:100]}")

            if challenges:
                original = positions[persona.role]
                challenge_summary = "; ".join(challenges[:2])
                refined[persona.role] = (
                    f"{original}\n"
                    f"[质询回应] 对其他立场的看法: "
                    f"基于{persona.focus}的视角，"
                    f"我认为{challenge_summary[:150]}需要进一步验证。"
                )

        return refined


debate_arena = DebateArena()