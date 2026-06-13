"""
验证持续学习单元功能
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from loguru import logger


def test_web_search_tool():
    """测试网络搜索工具"""
    logger.info("=" * 50)
    logger.info("测试1: 网络搜索工具")
    logger.info("=" * 50)
    
    try:
        from tools.web_search import WebSearchTool, QuickSearchTool
        from tools.registry import registry
        
        # 注册工具
        web_search = WebSearchTool()
        quick_search = QuickSearchTool()
        
        registry.register(web_search, overwrite=True)
        registry.register(quick_search, overwrite=True)
        
        logger.info("✓ 工具注册成功")
        
        # 测试快速搜索
        logger.info("测试快速搜索...")
        result = quick_search.execute(query="Python async await best practices")
        
        if result.success:
            logger.info(f"✓ 搜索成功，返回 {len(result.output.get('sources', []))} 条结果")
            logger.info(f"  摘要预览: {result.output.get('summary', '')[:100]}...")
            return True
        else:
            logger.error(f"✗ 搜索失败: {result.error}")
            return False
            
    except Exception as e:
        logger.error(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_active_learner():
    """测试主动学习器"""
    logger.info("\n" + "=" * 50)
    logger.info("测试2: 主动学习器")
    logger.info("=" * 50)
    
    try:
        from infrastructure.active_learner import active_learner, LearningTrigger
        
        # 检查初始化
        stats = active_learner.get_statistics()
        logger.info(f"✓ 学习器已初始化")
        logger.info(f"  总活动数: {stats['total_activities']}")
        logger.info(f"  总知识数: {stats['total_knowledge']}")
        logger.info(f"  暂停状态: {stats['is_paused']}")
        
        # 测试事件记录
        logger.info("\n测试事件记录...")
        active_learner.record_event("intent_failure", {
            "intent": "test_intent",
            "query": "test query for learning",
            "error": "test error"
        })
        logger.info("✓ 事件记录成功")
        
        # 测试手动触发学习
        logger.info("\n测试手动触发学习...")
        import asyncio
        
        async def test_trigger():
            activity = await active_learner.trigger_learning(
                LearningTrigger.MANUAL,
                "如何优化Python异步性能"
            )
            return activity
        
        activity = asyncio.run(test_trigger())
        
        if activity.status.value == "completed":
            logger.info(f"✓ 学习完成")
            logger.info(f"  活动ID: {activity.id}")
            logger.info(f"  影响分: {activity.impact_score:.2f}")
            logger.info(f"  知识预览: {activity.knowledge[:100]}...")
            return True
        else:
            logger.error(f"✗ 学习失败: {activity.status.value}")
            return False
            
    except Exception as e:
        logger.error(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_learning_api():
    """测试学习API"""
    logger.info("\n" + "=" * 50)
    logger.info("测试3: 学习API")
    logger.info("=" * 50)
    
    try:
        import asyncio
        from infrastructure.active_learner import active_learner
        
        # 测试获取学习日志
        logger.info("测试获取学习日志...")
        activities = active_learner.get_activities(limit=5)
        logger.info(f"✓ 获取到 {len(activities)} 条学习活动")
        
        # 测试获取知识
        logger.info("\n测试获取知识...")
        knowledge = active_learner.get_knowledge(limit=5)
        logger.info(f"✓ 获取到 {len(knowledge)} 条知识")
        
        # 测试暂停/恢复
        logger.info("\n测试暂停/恢复...")
        active_learner.pause()
        assert active_learner.is_paused() == True
        logger.info("✓ 暂停成功")
        
        active_learner.resume()
        assert active_learner.is_paused() == False
        logger.info("✓ 恢复成功")
        
        # 测试统计
        logger.info("\n测试统计...")
        stats = active_learner.get_statistics()
        logger.info(f"✓ 统计信息:")
        logger.info(f"  总活动数: {stats['total_activities']}")
        logger.info(f"  按状态分布: {stats['by_status']}")
        logger.info(f"  总知识数: {stats['total_knowledge']}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """测试集成"""
    logger.info("\n" + "=" * 50)
    logger.info("测试4: 集成测试")
    logger.info("=" * 50)
    
    try:
        # 检查规划器集成
        logger.info("检查规划器集成...")
        from core.services.planner import DataDrivenPlanner
        logger.info("✓ 规划器已导入")
        
        # 检查章程执行器集成
        logger.info("\n检查章程执行器集成...")
        from infrastructure.charter_executor import CharterExecutor
        executor = CharterExecutor()
        logger.info("✓ 章程执行器已导入")
        
        # 检查工具注册
        logger.info("\n检查工具注册...")
        from tools.builtin import register_builtin_tools
        register_builtin_tools()
        
        from tools.registry import registry
        tools = registry.list_tools()
        logger.info(f"✓ 已注册 {len(tools)} 个工具")
        
        web_search = registry.get("web_search")
        quick_search = registry.get("quick_search")
        
        if web_search and quick_search:
            logger.info("✓ 网络搜索工具已注册")
        else:
            logger.warning("⚠ 网络搜索工具未注册")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    logger.info("=" * 70)
    logger.info("持续学习单元功能验证")
    logger.info("=" * 70)
    
    results = {}
    
    # 运行测试
    results["网络搜索工具"] = test_web_search_tool()
    results["主动学习器"] = test_active_learner()
    results["学习API"] = test_learning_api()
    results["集成测试"] = test_integration()
    
    # 汇总结果
    logger.info("\n" + "=" * 70)
    logger.info("测试结果汇总")
    logger.info("=" * 70)
    
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        logger.info(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    
    logger.info(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        logger.info("\n🎉 所有测试通过！持续学习单元已就绪。")
        return 0
    else:
        logger.error(f"\n⚠️  {total - passed} 个测试失败，请检查错误日志。")
        return 1


if __name__ == "__main__":
    exit(main())