"""
测试反思管道 - 验证闭环是否真正激活
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from infrastructure.reflection_pipeline import get_reflection_pipeline
from loguru import logger


async def test_reflection_pipeline():
    """测试反思管道完整流程"""
    
    logger.info("=" * 60)
    logger.info("🧪 测试反思管道（闭环传动轴）")
    logger.info("=" * 60)
    
    # 1. 初始化管道
    logger.info("\n[1] 初始化反思管道...")
    pipeline = get_reflection_pipeline({
        "log_db_path": "logs/campfire_log.db",
        "jsonl_output_dir": "data/finetune/queue",
        "enable_induction": True,
        "enable_jsonl": True,
        "induction_timeout_seconds": 5,
        "min_confidence_threshold": 0.7
    })
    logger.info("✓ 管道初始化成功")
    
    # 2. 模拟一次执行上下文
    logger.info("\n[2] 模拟执行上下文...")
    execution_context = {
        "query": "什么是机器学习？",
        "plan": {
            "tasks": [
                {"type": "knowledge_retrieval", "description": "检索机器学习知识"},
                {"type": "llm_reasoning", "description": "综合推理"}
            ],
            "expected_confidence": 0.8
        },
        "tool_calls": [
            {"tool": "knowledge_search", "query": "机器学习", "success": True}
        ],
        "final_answer": "机器学习是人工智能的一个分支，它使计算机系统能够从数据中学习并改进，而无需明确编程。",
        "confidence": 0.65,  # 低于阈值，应触发JSONL生成
        "model_used": "deepseek-chat",
        "duration_ms": 2500,
        "user_id": "test_user",
        "session_id": "test_session"
    }
    logger.info(f"✓ 执行上下文: 查询='{execution_context['query']}', 置信度={execution_context['confidence']}")
    
    # 3. 触发反思管道
    logger.info("\n[3] 触发反思管道...")
    result = await pipeline.process(execution_context)
    
    logger.info(f"✓ 反思管道执行完成:")
    logger.info(f"  - 成功: {result['success']}")
    logger.info(f"  - 反思ID: {result['reflection_id']}")
    logger.info(f"  - 执行动作: {result['actions_taken']}")
    
    # 4. 验证结果
    logger.info("\n[4] 验证反思结果...")
    
    # 4.1 检查日志数据库
    import sqlite3
    with sqlite3.connect("logs/campfire_log.db") as conn:
        count = conn.execute("SELECT COUNT(*) FROM reflection_log").fetchone()[0]
        logger.info(f"  ✓ 营火日志: {count}条记录")
        
        # 读取最新记录
        latest = conn.execute(
            "SELECT query, confidence, model_used FROM reflection_log ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        if latest:
            logger.info(f"    最新: 查询='{latest[0]}', 置信度={latest[1]}, 模型={latest[2]}")
    
    # 4.2 检查JSONL文件
    jsonl_dir = Path("data/finetune/queue")
    if jsonl_dir.exists():
        jsonl_files = list(jsonl_dir.glob("*.jsonl"))
        total_samples = 0
        for f in jsonl_files:
            with open(f, 'r', encoding='utf-8') as file:
                total_samples += sum(1 for _ in file)
        logger.info(f"  ✓ JSONL样本: {total_samples}条 ({len(jsonl_files)}个文件)")
    
    # 4.3 检查经验池
    exp_pool = Path("data/experience_pool.db")
    if exp_pool.exists():
        with sqlite3.connect(str(exp_pool)) as conn:
            try:
                count = conn.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
                logger.info(f"  ✓ 经验池: {count}条经验")
            except:
                logger.info("  ⚠️ 经验池表结构不同")
    
    # 5. 获取统计信息
    logger.info("\n[5] 反思管道统计...")
    stats = pipeline.get_stats()
    for key, value in stats.items():
        logger.info(f"  - {key}: {value}")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 反思管道测试完成")
    logger.info("=" * 60)
    
    # 6. 结论
    logger.info("\n📊 测试结论:")
    if result['success'] and len(result['actions_taken']) >= 2:
        logger.info("  ✅ 反思管道工作正常")
        logger.info("  ✅ 闭环已激活（日志+归纳+微调）")
        logger.info("  ✅ 系统已从'开环'转变为'闭环'")
        return True
    else:
        logger.warning("  ⚠️ 反思管道可能存在问题")
        return False


async def test_multiple_reflections():
    """测试多次反思（模拟连续对话）"""
    
    logger.info("\n" + "=" * 60)
    logger.info("🧪 测试连续反思（模拟真实对话流）")
    logger.info("=" * 60)
    
    pipeline = get_reflection_pipeline()
    
    test_cases = [
        {
            "query": "Python如何读取文件？",
            "confidence": 0.75,
            "final_answer": "使用open()函数或with语句读取文件。"
        },
        {
            "query": "什么是深度学习？",
            "confidence": 0.60,  # 低置信度，应触发学习
            "final_answer": "深度学习是机器学习的子领域，使用神经网络..."
        },
        {
            "query": "如何优化SQL查询？",
            "confidence": 0.55,  # 低置信度
            "final_answer": "可以通过索引、查询重写、分区等方式优化..."
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        logger.info(f"\n[对话{i}] {case['query']}")
        
        context = {
            **case,
            "model_used": "deepseek-chat",
            "duration_ms": 1500 + i * 100
        }
        
        result = await pipeline.process(context)
        logger.info(f"  ✓ 反思完成: {result['actions_taken']}")
    
    # 最终统计
    stats = pipeline.get_stats()
    logger.info(f"\n📊 最终统计:")
    logger.info(f"  - 总日志: {stats['log_count']}条")
    logger.info(f"  - 总样本: {stats['jsonl_count']}条")
    
    return True


if __name__ == "__main__":
    # 运行测试
    success = asyncio.run(test_reflection_pipeline())
    
    if success:
        asyncio.run(test_multiple_reflections())
    
    logger.info("\n🎉 所有测试完成！")