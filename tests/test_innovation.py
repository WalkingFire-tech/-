"""
测试创新引擎
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

import asyncio
from core.innovation_engine import InnovationEngine, Thought
from loguru import logger

async def test_basic():
    """基础测试（无LLM）"""
    print("\n" + "="*60)
    print("测试1: 基础创新流程（无LLM）")
    print("="*60)
    
    engine = InnovationEngine()
    
    final_idea = await engine.innovate(
        seed_idea="多个AI智能体如何更有效地协作",
        observation="蚁群通过信息素进行高效的路径优化"
    )
    
    print(f"\n最终想法: {final_idea.content}")
    print(f"得分: {final_idea.score:.2f}")
    print(f"新颖性: {final_idea.novelty:.2f}")
    print(f"可行性: {final_idea.feasibility:.2f}")
    
    print("\n思维历史:")
    for i, thought in enumerate(engine.get_thought_history(5)):
        print(f"  {i+1}. [{thought['domain']}] {thought['content'][:50]}...")

async def test_with_knowledge_retriever():
    """测试与知识检索器集成"""
    print("\n" + "="*60)
    print("测试2: 与知识检索器集成")
    print("="*60)
    
    try:
        from core.vector_retriever import VectorRetriever
        
        retriever = VectorRetriever()
        
        engine = InnovationEngine(knowledge_retriever=retriever)
        
        final_idea = await engine.innovate(
            seed_idea="如何优化知识检索的准确性"
        )
        
        print(f"\n最终想法: {final_idea.content}")
        print(f"得分: {final_idea.score:.2f}")
        
    except Exception as e:
        print(f"⚠️ 知识检索器测试失败: {e}")
        print("   这可能是因为向量数据库未初始化")

async def test_with_llm():
    """测试与LLM集成"""
    print("\n" + "="*60)
    print("测试3: 与LLM集成")
    print("="*60)
    
    try:
        from adapters.llm.ollama_adapter import OllamaAdapter
        
        adapter = OllamaAdapter(model_name="qwen2.5:7b")
        
        engine = InnovationEngine(llm_adapter=adapter)
        
        final_idea = await engine.innovate(
            seed_idea="如何让AI系统具备自我进化能力",
            observation="生物进化通过自然选择实现适应性"
        )
        
        print(f"\n最终想法: {final_idea.content}")
        print(f"得分: {final_idea.score:.2f}")
        
    except Exception as e:
        print(f"⚠️ LLM测试失败: {e}")
        print("   这可能是因为Ollama服务未启动")

async def test_diversity():
    """测试多样性评估"""
    print("\n" + "="*60)
    print("测试4: 多样性评估")
    print("="*60)
    
    engine = InnovationEngine()
    
    thoughts = [
        Thought(content="使用遗传算法优化参数"),
        Thought(content="基于深度学习进行特征提取"),
        Thought(content="采用强化学习进行决策"),
        Thought(content="利用图神经网络建模关系"),
    ]
    
    diversity = engine.evaluate_diversity(thoughts)
    print(f"多样性评分: {diversity:.2f}")
    
    similar_thoughts = [
        Thought(content="使用遗传算法优化参数"),
        Thought(content="使用遗传算法优化参数设置"),
        Thought(content="利用遗传算法进行优化"),
    ]
    
    low_diversity = engine.evaluate_diversity(similar_thoughts)
    print(f"低多样性评分: {low_diversity:.2f}")

async def main():
    print("\n" + "="*60)
    print("创新引擎测试套件")
    print("="*60)
    
    await test_basic()
    await test_diversity()
    await test_with_knowledge_retriever()
    await test_with_llm()
    
    print("\n" + "="*60)
    print("✓ 所有测试完成")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())