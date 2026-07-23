"""
多智能体辩论模块 (Debate Module)

让系统通过不同"性格"智能体辩论后仲裁整合，
从"单一推理路径"进化为"群体智能涌现"。

核心设计哲学：
- 不是"谁对谁错"，而是"不同视角的互补"
- 务实派关注可行性，理想派追求最优解，质疑派暴露盲区
- 仲裁不是投票，而是基于SpiritCore共振的加权融合

三角色设计：
1. 务实派(Pragmatist) — 关注可行性、资源约束、快速落地
2. 理想派(Idealist) — 追求本质、最优解、长期价值
3. 质疑派(Skeptic) — 暴露盲区、挑战假设、防止确认偏差
"""

from .arena import DebateArena, DebateResult
from .personas import Persona, PRAGMATIST, IDEALIST, SKEPTIC
from .arbitrator import Arbitrator, ArbitrationResult

__all__ = [
    'DebateArena',
    'DebateResult',
    'Persona',
    'PRAGMATIST',
    'IDEALIST',
    'SKEPTIC',
    'Arbitrator',
    'ArbitrationResult',
]