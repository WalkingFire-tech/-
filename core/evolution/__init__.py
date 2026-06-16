"""
进化模块 - 多智能体进化沙盒
"""
from core.evolution.simulated_agent import SimulatedAgent, SimulatedGenome
from core.evolution.task_pool import build_task_pool, load_existing_skills
from core.evolution.evolution_island import EvolutionIsland, run_evolution_sandbox

__all__ = [
    'SimulatedAgent',
    'SimulatedGenome',
    'EvolutionIsland',
    'build_task_pool',
    'load_existing_skills',
    'run_evolution_sandbox'
]