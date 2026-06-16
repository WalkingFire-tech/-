"""
进化岛 - 多智能体进化沙盒

核心机制：
1. 多个智能体在模拟环境中竞争
2. 通过适应度选择优秀个体
3. 基因杂交和变异产生后代
4. 最终输出最优基因和技能
"""
import random
import time
import json
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from core.evolution.simulated_agent import SimulatedAgent, SimulatedGenome
from core.evolution.task_pool import build_task_pool, load_existing_skills, create_sample_tasks


class EvolutionIsland:
    """进化岛 - 多智能体进化沙盒"""
    
    def __init__(self, 
                 main_db_path: str,
                 num_agents: int = 8,
                 generations: int = 20,
                 tasks_per_gen: int = 30):
        """
        Args:
            main_db_path: 主数据库路径
            num_agents: 智能体数量
            generations: 进化代数
            tasks_per_gen: 每代评估任务数
        """
        self.main_db_path = main_db_path
        self.num_agents = num_agents
        self.generations = generations
        self.tasks_per_gen = tasks_per_gen
        
        # 构建任务池
        self.task_pool = build_task_pool(main_db_path, max_tasks=200)
        
        if not self.task_pool:
            logger.warning("任务池为空，使用示例任务")
            self.task_pool = create_sample_tasks()
        
        # 加载现有技能
        self.existing_skills = load_existing_skills(main_db_path)
        
        # 智能体种群
        self.agents: List[SimulatedAgent] = []
        
        # 进化历史
        self.history = []
        
        logger.info(f"进化岛初始化: {len(self.task_pool)}个任务, {len(self.existing_skills)}个技能")
    
    def _init_population(self):
        """初始化种群"""
        self.agents = []
        
        for i in range(self.num_agents):
            # 随机基因组
            genome = SimulatedGenome.random()
            
            # 随机选择初始技能
            skills = []
            if self.existing_skills:
                num_skills = random.randint(0, min(3, len(self.existing_skills)))
                skills = random.sample(self.existing_skills, num_skills)
            
            # 创建智能体
            agent = SimulatedAgent(i, genome, skills, self.task_pool)
            self.agents.append(agent)
        
        logger.info(f"种群初始化完成: {len(self.agents)}个智能体")
    
    def evaluate_agent(self, agent: SimulatedAgent, tasks: List[Dict]):
        """评估智能体"""
        agent.fitness = 0.0
        
        for task in tasks:
            score = agent.evaluate_on_task(task)
        
        # 归一化适应度
        if len(tasks) > 0:
            agent.fitness = agent.fitness / len(tasks)
    
    def evolve_generation(self, gen: int):
        """进化一代"""
        # 随机选择任务
        tasks = random.sample(
            self.task_pool, 
            min(self.tasks_per_gen, len(self.task_pool))
        )
        
        # 评估所有智能体
        for agent in self.agents:
            self.evaluate_agent(agent, tasks)
            agent.age += 1
        
        # 按适应度排序
        self.agents.sort(key=lambda a: a.fitness, reverse=True)
        
        # 记录统计
        best = self.agents[0]
        avg_fitness = sum(a.fitness for a in self.agents) / len(self.agents)
        
        self.history.append({
            'generation': gen,
            'best_fitness': best.fitness,
            'avg_fitness': avg_fitness,
            'best_genome': best.genome.to_dict()
        })
        
        logger.info(f"Gen {gen}: best={best.fitness:.3f}, avg={avg_fitness:.3f}")
        
        # 选择精英（top 30%）
        elite_count = max(2, int(self.num_agents * 0.3))
        elites = self.agents[:elite_count]
        
        # 产生后代
        new_agents = elites.copy()
        
        while len(new_agents) < self.num_agents:
            # 选择父母
            p1 = random.choice(elites)
            p2 = random.choice(elites)
            
            if p1.id != p2.id:
                # 基因杂交
                child_genome = p1.genome.crossover(p2.genome)
                child_genome = child_genome.mutate(rate=0.2)
                
                # 技能继承
                child_skills = []
                if p1.skills and random.random() < 0.5:
                    child_skills.append(random.choice(p1.skills))
                if p2.skills and random.random() < 0.5:
                    skill = random.choice(p2.skills)
                    if skill not in child_skills:
                        child_skills.append(skill)
                
                # 创建子代
                child = SimulatedAgent(
                    len(new_agents),
                    child_genome,
                    child_skills,
                    self.task_pool
                )
                
                new_agents.append(child)
        
        # 清理旧智能体
        for agent in self.agents[elite_count:]:
            agent.cleanup()
        
        self.agents = new_agents
    
    def run(self) -> Dict:
        """
        运行进化
        
        Returns:
            {
                'best_agent': SimulatedAgent,
                'best_genome': Dict,
                'best_skills': List[Dict],
                'history': List[Dict],
                'stats': Dict
            }
        """
        logger.info(f"开始进化: {self.generations}代, {self.num_agents}个智能体")
        
        # 初始化种群
        self._init_population()
        
        # 进化循环
        start_time = time.time()
        
        for gen in range(self.generations):
            self.evolve_generation(gen)
        
        elapsed = time.time() - start_time
        
        # 获取最优个体
        best = max(self.agents, key=lambda a: a.fitness)
        
        logger.info(f"进化完成: 最优适应度={best.fitness:.3f}, 耗时={elapsed:.1f}s")
        
        return {
            'best_agent': best,
            'best_genome': best.genome.to_dict(),
            'best_skills': best.skills,
            'history': self.history,
            'stats': {
                'generations': self.generations,
                'num_agents': self.num_agents,
                'tasks_per_gen': self.tasks_per_gen,
                'elapsed_seconds': elapsed,
                'final_best_fitness': best.fitness,
                'final_avg_fitness': sum(a.fitness for a in self.agents) / len(self.agents)
            }
        }
    
    def get_best_agent(self) -> SimulatedAgent:
        """获取最优智能体"""
        return max(self.agents, key=lambda a: a.fitness)
    
    def export_results(self, output_path: str):
        """导出进化结果"""
        best = self.get_best_agent()
        
        result = {
            'best_genome': best.genome.to_dict(),
            'best_skills': best.skills,
            'best_fitness': best.fitness,
            'history': self.history,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"结果已导出: {output_path}")


def run_evolution_sandbox(main_db_path: str = "data/knowledge_store.db",
                         num_agents: int = 8,
                         generations: int = 20) -> Dict:
    """
    运行进化沙盒（便捷函数）
    
    Args:
        main_db_path: 主数据库路径
        num_agents: 智能体数量
        generations: 进化代数
    
    Returns:
        进化结果
    """
    island = EvolutionIsland(
        main_db_path=main_db_path,
        num_agents=num_agents,
        generations=generations,
        tasks_per_gen=30
    )
    
    return island.run()


if __name__ == "__main__":
    # 独立运行测试
    result = run_evolution_sandbox(
        main_db_path="data/knowledge_store.db",
        num_agents=6,
        generations=10
    )
    
    print("\n" + "=" * 60)
    print("进化结果")
    print("=" * 60)
    print(f"最优适应度: {result['stats']['final_best_fitness']:.3f}")
    print(f"最优基因组: {result['best_genome']}")
    print(f"最优技能数: {len(result['best_skills'])}")
    print(f"耗时: {result['stats']['elapsed_seconds']:.1f}秒")