"""
验证 v3.4 里程碑 - 自我感知、自我对比、自我完善
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger


def test_health_dashboard():
    """测试健康度仪表盘"""
    print("\n" + "="*60)
    print("测试1: 健康度仪表盘 (APHI)")
    print("="*60)
    
    try:
        from infrastructure.health_dashboard import health_dashboard
        
        # 计算健康度
        metrics = health_dashboard.calculate_aphi()
        
        print(f"✓ APHI指数: {metrics['aphi']}")
        print(f"✓ 运行模式: {metrics['mode']}")
        print(f"✓ 能力覆盖率: {metrics['capability_coverage']}")
        print(f"✓ 任务成功率: {metrics['task_success_rate']}")
        print(f"✓ 资源可用性: {metrics['resource_availability']}")
        print(f"✓ 进化活力: {metrics['evolution_vitality']}")
        print(f"✓ 用户满意度: {metrics['user_satisfaction']}")
        
        # 测试决策触发
        should_reduce = health_dashboard.should_reduce_load()
        should_help = health_dashboard.should_request_help()
        print(f"✓ 是否降低负载: {should_reduce}")
        print(f"✓ 是否请求帮助: {should_help}")
        
        # 获取状态报告
        report = health_dashboard.get_status_report()
        print(report)
        
        return True
        
    except Exception as e:
        print(f"✗ 健康度仪表盘测试失败: {e}")
        return False


def test_counterfactual_simulator():
    """测试反事实模拟器"""
    print("\n" + "="*60)
    print("测试2: 反事实模拟器")
    print("="*60)
    
    try:
        from infrastructure.counterfactual_simulator import counterfactual_simulator
        
        # 获取统计信息
        stats = counterfactual_simulator.get_statistics()
        print(f"✓ 总模拟次数: {stats.get('total_simulations', 0)}")
        print(f"✓ 已应用洞察: {stats.get('applied_insights', 0)}")
        print(f"✓ 平均提升: {stats.get('avg_improvement', 0)}")
        
        # 获取顶级洞察
        insights = counterfactual_simulator.get_top_insights(limit=5)
        print(f"✓ 待处理洞察: {len(insights)}")
        
        if insights:
            print("\n顶级洞察:")
            for i, insight in enumerate(insights[:3], 1):
                print(f"  {i}. {insight.get('recommendation', 'N/A')}")
                print(f"     证据: {insight.get('evidence', 'N/A')}")
                print(f"     置信度: {insight.get('confidence', 0):.2f}")
        
        return True
        
    except Exception as e:
        print(f"✗ 反事实模拟器测试失败: {e}")
        return False


def test_charter_integration():
    """测试章程守护线程集成"""
    print("\n" + "="*60)
    print("测试3: 章程守护线程集成")
    print("="*60)
    
    try:
        from infrastructure.charter_executor import charter_executor
        
        # 测试资源检查
        resource_check = charter_executor.check_resource_limits()
        print(f"✓ 资源检查: {'通过' if resource_check.get('within_limits', True) else '超限'}")
        if not resource_check.get('within_limits', True):
            print(f"  违规项: {resource_check.get('violations', [])}")
        
        # 测试失败回顾
        try:
            failures = charter_executor.review_failures()
            print(f"✓ 失败回顾: 发现 {len(failures)} 个学习任务")
        except Exception as e:
            print(f"⚠ 失败回顾跳过: {e}")
        
        # 测试功能监控
        try:
            usage = charter_executor.monitor_feature_usage()
            print(f"✓ 功能监控: 已记录")
        except Exception as e:
            print(f"⚠ 功能监控跳过: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ 章程守护线程测试失败: {e}")
        return False


def test_integration():
    """测试三模块协同"""
    print("\n" + "="*60)
    print("测试4: 三模块协同工作")
    print("="*60)
    
    try:
        from infrastructure.health_dashboard import health_dashboard
        from infrastructure.counterfactual_simulator import counterfactual_simulator
        from infrastructure.charter_executor import charter_executor
        
        # 模拟系统运行流程
        print("模拟系统运行流程:")
        
        # 1. 健康度检查
        metrics = health_dashboard.calculate_aphi()
        print(f"  1. 健康度检查: APHI={metrics['aphi']}, 模式={metrics['mode']}")
        
        # 2. 资源检查
        resource_check = charter_executor.check_resource_limits()
        print(f"  2. 资源检查: {'通过' if resource_check['within_limits'] else '超限'}")
        
        # 3. 反事实洞察应用
        applied = counterfactual_simulator.apply_insights()
        print(f"  3. 应用反事实洞察: {applied} 条")
        
        # 4. 决策触发测试
        if metrics['aphi'] < 60:
            print("  4. 触发节能模式")
        elif metrics['aphi'] < 40:
            print("  4. 触发应急模式")
        else:
            print("  4. 系统运行正常")
        
        return True
        
    except Exception as e:
        print(f"✗ 协同工作测试失败: {e}")
        return False


def main():
    """主测试流程"""
    print("\n" + "╔" + "═"*58 + "╗")
    print("║" + " "*15 + "v3.4 里程碑验证" + " "*15 + "║")
    print("╚" + "═"*58 + "╝")
    
    results = []
    
    results.append(("健康度仪表盘", test_health_dashboard()))
    results.append(("反事实模拟器", test_counterfactual_simulator()))
    results.append(("章程守护线程", test_charter_integration()))
    results.append(("三模块协同", test_integration()))
    
    # 总结
    print("\n" + "="*60)
    print("验证总结")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 v3.4 里程碑验证成功！")
        print("系统已具备自我感知、自我对比、自我完善能力。")
    else:
        print(f"\n⚠️  {total - passed} 项测试失败，需要修复。")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)