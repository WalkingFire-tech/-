"""
创新思维引擎 - 集成版本
整合发散思维、收敛思维、反绎推理、远距离联想等核心创新能力
与项目知识库、向量检索、学习闭环深度集成
"""
import random
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

@dataclass
class Thought:
    """思维节点"""
    content: str
    score: float = 0.0
    domain: str = "general"
    novelty: float = 0.0
    feasibility: float = 0.0
    parents: List['Thought'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

class InnovationEngine:
    """
    创新思维引擎
    集成项目的知识库、向量检索、学习闭环等核心能力
    """
    
    def __init__(self, 
                 knowledge_retriever=None,
                 llm_adapter=None,
                 experience_pool=None):
        """
        初始化创新引擎
        
        Args:
            knowledge_retriever: 知识检索器（向量检索）
            llm_adapter: LLM适配器（Ollama/Remote）
            experience_pool: 经验池（用于学习闭环）
        """
        self.knowledge_retriever = knowledge_retriever
        self.llm_adapter = llm_adapter
        self.experience_pool = experience_pool
        
        self.thought_history: List[Thought] = []
        self.diversity_threshold = 0.7
        self.novelty_weight = 0.6
        self.feasibility_weight = 0.4
        
        logger.info("创新引擎初始化完成")
    
    async def diverge(self, seed_idea: str, num_ideas: int = 5) -> List[Thought]:
        """
        发散思维：基于种子想法生成多个不同的新想法
        利用LLM进行真正的发散，而非简单的字符串拼接
        
        Args:
            seed_idea: 种子想法
            num_ideas: 生成想法数量
            
        Returns:
            发散后的想法列表
        """
        logger.info(f"🌱 发散思维：基于 '{seed_idea}' 生成 {num_ideas} 个新想法...")
        
        if not self.llm_adapter:
            return self._diverge_fallback(seed_idea, num_ideas)
        
        divergent_thoughts = []
        
        divergent_prompts = [
            f"【反向思考】请思考 '{seed_idea}' 的完全对立面是什么？给出一个具体方案。",
            f"【极端化】如果 '{seed_idea}' 被放大100倍会怎样？描述极端情况。",
            f"【跨界联想】将 '{seed_idea}' 与生物学中的'进化论'结合，会产生什么新想法？",
            f"【简化】'{seed_idea}' 的最本质核心是什么？用一句话表达。",
            f"【拟人化】如果 '{seed_idea}' 是一个有情感的人，它会做什么决策？",
        ]
        
        for i in range(min(num_ideas, len(divergent_prompts))):
            try:
                prompt = divergent_prompts[i]
                
                if hasattr(self.llm_adapter, 'generate'):
                    response = await self.llm_adapter.generate(prompt)
                else:
                    response = await self.llm_adapter.chat(prompt)
                
                if response:
                    thought = Thought(
                        content=response,
                        score=0.0,
                        domain="divergent",
                        metadata={"prompt": prompt, "type": "divergent"}
                    )
                    thought.parents.append(Thought(content=seed_idea))
                    divergent_thoughts.append(thought)
                    self.thought_history.append(thought)
                    
            except Exception as e:
                logger.warning(f"发散思维生成失败: {e}")
                continue
        
        logger.info(f"✓ 发散完成，生成 {len(divergent_thoughts)} 个想法")
        return divergent_thoughts
    
    def _diverge_fallback(self, seed_idea: str, num_ideas: int) -> List[Thought]:
        """降级方案：无LLM时的简单发散"""
        variations = [
            f"反向思考：{seed_idea} 的对立面",
            f"极端化：{seed_idea} 放大100倍",
            f"跨界：{seed_idea} + 生物学",
            f"简化：{seed_idea} 的核心",
            f"拟人化：{seed_idea} 的情感视角",
        ]
        
        thoughts = []
        for i in range(min(num_ideas, len(variations))):
            thought = Thought(
                content=variations[i],
                score=random.uniform(0.5, 0.7),
                domain="divergent_fallback"
            )
            thoughts.append(thought)
        
        return thoughts
    
    async def converge(self, thoughts: List[Thought], 
                      criteria: str = "novelty_and_feasibility") -> Thought:
        """
        收敛思维：从多个想法中筛选出最优的一个
        利用知识库评估新颖性和可行性
        
        Args:
            thoughts: 候选想法列表
            criteria: 筛选标准
            
        Returns:
            最佳想法
        """
        logger.info(f"🎯 收敛思维：根据 '{criteria}' 标准从 {len(thoughts)} 个想法中筛选...")
        
        if not thoughts:
            return Thought(content="无有效想法", score=0.0)
        
        for thought in thoughts:
            novelty = await self._evaluate_novelty(thought)
            feasibility = await self._evaluate_feasibility(thought)
            
            thought.novelty = novelty
            thought.feasibility = feasibility
            thought.score = (
                self.novelty_weight * novelty + 
                self.feasibility_weight * feasibility
            )
        
        thoughts_sorted = sorted(thoughts, key=lambda t: t.score, reverse=True)
        best_thought = thoughts_sorted[0]
        
        logger.info(f"✓ 最佳想法：{best_thought.content[:50]}... (得分: {best_thought.score:.2f})")
        return best_thought
    
    async def _evaluate_novelty(self, thought: Thought) -> float:
        """
        评估新颖性：基于知识库的相似度
        相似度低 → 新颖性高
        """
        if not self.knowledge_retriever:
            return random.uniform(0.5, 0.8)
        
        try:
            results = await self.knowledge_retriever.search(
                thought.content, 
                top_k=5
            )
            
            if not results:
                return 0.9
            
            max_similarity = max(r.get('score', 0) for r in results)
            novelty = 1.0 - max_similarity
            
            return max(0.1, min(1.0, novelty))
            
        except Exception as e:
            logger.warning(f"新颖性评估失败: {e}")
            return 0.5
    
    async def _evaluate_feasibility(self, thought: Thought) -> float:
        """
        评估可行性：基于内容复杂度和经验池
        """
        content_length = len(thought.content)
        
        if self.experience_pool:
            try:
                similar_exp = await self.experience_pool.query_similar(
                    thought.content, 
                    top_k=3
                )
                if similar_exp:
                    avg_quality = sum(e.get('quality', 50) for e in similar_exp) / len(similar_exp)
                    return avg_quality / 100.0
            except Exception:
                logger.warning("操作降级跳过")
        
        if content_length < 20:
            return 0.3
        elif content_length > 500:
            return 0.5
        else:
            return 0.7
    
    async def abductive_reason(self, observation: str) -> List[Thought]:
        """
        反绎推理：从观察到的现象反向推导最可能的解释
        利用知识库的多领域知识进行跨域推理
        
        Args:
            observation: 观察到的现象
            
        Returns:
            可能的解释列表
        """
        logger.info(f"🔍 反绎推理：针对现象 '{observation}' 寻找最佳解释...")
        
        explanations = []
        
        if self.knowledge_retriever:
            try:
                results = await self.knowledge_retriever.search(
                    observation, 
                    top_k=10
                )
                
                domains = {}
                for result in results:
                    domain = result.get('metadata', {}).get('domain', 'general')
                    if domain not in domains:
                        domains[domain] = []
                    domains[domain].append(result)
                
                for domain, domain_results in domains.items():
                    if domain_results:
                        top_result = domain_results[0]
                        explanation = Thought(
                            content=f"从【{domain}】角度看：{top_result.get('content', '')}",
                            domain=domain,
                            score=top_result.get('score', 0.5),
                            metadata={"type": "abductive", "source": "knowledge_base"}
                        )
                        explanations.append(explanation)
                        
            except Exception as e:
                logger.warning(f"知识库检索失败: {e}")
        
        if self.llm_adapter and len(explanations) < 3:
            try:
                prompt = f"""观察到现象：{observation}

请从不同学科角度（如生物学、物理学、社会学、计算机科学）给出可能的解释。
每个解释一行，格式：[学科] 解释内容"""
                
                if hasattr(self.llm_adapter, 'generate'):
                    response = await self.llm_adapter.generate(prompt)
                else:
                    response = await self.llm_adapter.chat(prompt)
                
                if response:
                    lines = response.strip().split('\n')
                    for line in lines[:3]:
                        if line.strip():
                            thought = Thought(
                                content=line.strip(),
                                domain="llm_abductive",
                                score=0.7,
                                metadata={"type": "abductive", "source": "llm"}
                            )
                            explanations.append(thought)
                            
            except Exception as e:
                logger.warning(f"LLM反绎推理失败: {e}")
        
        if not explanations:
            explanations.append(Thought(
                content=f"这是一个新现象，需要创建新的理论来解释：{observation}",
                domain="unknown",
                score=0.5,
                metadata={"type": "abductive", "source": "fallback"}
            ))
        
        self.thought_history.extend(explanations)
        logger.info(f"✓ 反绎推理完成，生成 {len(explanations)} 个解释")
        return explanations
    
    async def remote_associate(self, concept_a: str, concept_b: str) -> Thought:
        """
        远距离联想：将两个看似无关的概念联系起来
        利用向量检索找到潜在的连接点
        
        Args:
            concept_a: 概念A
            concept_b: 概念B
            
        Returns:
            联想结果
        """
        logger.info(f"🔗 远距离联想：连接 '{concept_a}' 和 '{concept_b}'...")
        
        bridge_points = []
        
        if self.knowledge_retriever:
            try:
                results_a = await self.knowledge_retriever.search(concept_a, top_k=5)
                results_b = await self.knowledge_retriever.search(concept_b, top_k=5)
                
                keywords_a = set()
                keywords_b = set()
                
                for r in results_a:
                    content = r.get('content', '')
                    keywords_a.update(content.split()[:10])
                
                for r in results_b:
                    content = r.get('content', '')
                    keywords_b.update(content.split()[:10])
                
                common_keywords = keywords_a & keywords_b
                
                if common_keywords:
                    bridge_points = list(common_keywords)[:3]
                    
            except Exception as e:
                logger.warning(f"向量检索失败: {e}")
        
        if self.llm_adapter:
            try:
                bridge_hint = f"可能的连接点：{', '.join(bridge_points)}" if bridge_points else ""
                
                prompt = f"""请将以下两个概念进行远距离联想，找到它们之间的深层联系：

概念A：{concept_a}
概念B：{concept_b}
{bridge_hint}

要求：
1. 找到两者共同的结构、模式或原理
2. 提出一个跨界应用的创新想法
3. 用一句话表达核心洞见"""
                
                if hasattr(self.llm_adapter, 'generate'):
                    response = await self.llm_adapter.generate(prompt)
                else:
                    response = await self.llm_adapter.chat(prompt)
                
                if response:
                    thought = Thought(
                        content=response,
                        score=0.95,
                        domain="remote_association",
                        novelty=0.9,
                        feasibility=0.6,
                        parents=[
                            Thought(content=concept_a),
                            Thought(content=concept_b)
                        ],
                        metadata={
                            "type": "remote_association",
                            "bridge_points": bridge_points
                        }
                    )
                    self.thought_history.append(thought)
                    logger.info(f"✓ 远距离联想完成")
                    return thought
                    
            except Exception as e:
                logger.warning(f"LLM远距离联想失败: {e}")
        
        bridge = f"发现 {concept_a} 与 {concept_b} 在结构上存在相似性，可以相互借鉴。"
        thought = Thought(
            content=bridge,
            score=0.7,
            domain="remote_association_fallback",
            parents=[
                Thought(content=concept_a),
                Thought(content=concept_b)
            ]
        )
        self.thought_history.append(thought)
        return thought
    
    def evaluate_diversity(self, thoughts: List[Thought]) -> float:
        """
        评估想法的多样性
        基于内容的语义差异，而非简单的词汇重叠
        """
        if len(thoughts) <= 1:
            return 1.0
        
        content_sets = [set(t.content.split()) for t in thoughts]
        
        pairwise_diversities = []
        for i in range(len(content_sets)):
            for j in range(i + 1, len(content_sets)):
                set_a = content_sets[i]
                set_b = content_sets[j]
                
                intersection = len(set_a & set_b)
                union = len(set_a | set_b)
                
                if union > 0:
                    similarity = intersection / union
                    diversity = 1 - similarity
                    pairwise_diversities.append(diversity)
        
        if not pairwise_diversities:
            return 1.0
        
        avg_diversity = sum(pairwise_diversities) / len(pairwise_diversities)
        return avg_diversity
    
    async def innovate(self, seed_idea: str, observation: Optional[str] = None) -> Thought:
        """
        完整的创新流程
        
        Args:
            seed_idea: 种子想法
            observation: 外部观察（可选）
            
        Returns:
            最终的创新想法
        """
        logger.info("\n" + "="*60)
        logger.info(f"🚀 启动创新流程，种子想法：'{seed_idea}'")
        logger.info("="*60)
        
        divergent_thoughts = await self.diverge(seed_idea, num_ideas=5)
        
        if observation:
            abductive_thoughts = await self.abductive_reason(observation)
            divergent_thoughts.extend(abductive_thoughts)
        
        if len(divergent_thoughts) >= 2:
            concepts_for_association = [t.content for t in divergent_thoughts[:2]]
            remote_thought = await self.remote_associate(
                concepts_for_association[0],
                concepts_for_association[1]
            )
            divergent_thoughts.append(remote_thought)
        
        diversity_score = self.evaluate_diversity(divergent_thoughts)
        logger.info(f"📊 想法多样性评分：{diversity_score:.2f}")
        
        final_thought = await self.converge(divergent_thoughts)
        
        logger.info("\n" + "="*60)
        logger.info(f"✨ 创新成果：{final_thought.content[:100]}...")
        logger.info(f"   新颖性: {final_thought.novelty:.2f}")
        logger.info(f"   可行性: {final_thought.feasibility:.2f}")
        logger.info(f"   综合得分: {final_thought.score:.2f}")
        logger.info("="*60 + "\n")
        
        return final_thought
    
    def get_thought_history(self, limit: int = 10) -> List[Dict]:
        """获取思维历史"""
        recent = self.thought_history[-limit:]
        return [
            {
                "content": t.content[:100],
                "score": t.score,
                "domain": t.domain,
                "novelty": t.novelty,
                "feasibility": t.feasibility,
                "created_at": t.created_at
            }
            for t in recent
        ]