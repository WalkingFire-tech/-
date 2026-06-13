"""
最终集成验证 - 验证所有集成点
"""
import sys


def verify_integration():
    """验证最终集成"""
    print("\n" + "=" * 70)
    print("最终集成验证")
    print("=" * 70)
    
    results = []
    
    # 1. 验证章程执行器集成
    print("\n【1. 章程执行器集成】")
    try:
        from infrastructure.charter_executor import charter_executor
        
        # 测试失败回顾
        tasks = charter_executor.review_failures()
        print(f"  ✅ 失败回顾功能: {len(tasks)}个学习任务")
        
        # 测试使用频率监控
        usage = charter_executor.monitor_feature_usage()
        print(f"  ✅ 使用频率监控: {len(usage.get('recommendations', []))}个建议")
        
        # 测试资源检查
        check = charter_executor.check_resource_limits()
        print(f"  ✅ 资源限制检查: {'通过' if check['within_limits'] else '超限'}")
        
        results.append(True)
    except Exception as e:
        print(f"  ❌ 章程执行器集成失败: {e}")
        results.append(False)
    
    # 2. 验证任务分解融合集成
    print("\n【2. 任务分解融合集成】")
    try:
        from infrastructure.task_decomposer import task_decomposer
        from infrastructure.result_fusion import result_fusion
        
        # 测试分解
        subtasks = task_decomposer.detect_subtasks("写一个快速排序，并解释其复杂度")
        print(f"  ✅ 任务分解: {len(subtasks)}个子任务")
        
        # 测试融合
        fused = result_fusion.fuse(
            subtasks=[{'type': 'code', 'description': 'test'}],
            results=["结果1"],
            original_intent="test",
            strategy='concat'
        )
        print(f"  ✅ 结果融合: {len(fused)}字符")
        
        results.append(True)
    except Exception as e:
        print(f"  ❌ 任务分解融合集成失败: {e}")
        results.append(False)
    
    # 3. 验证生命维持系统集成
    print("\n【3. 生命维持系统集成】")
    try:
        from infrastructure.life_support import life_support
        
        health = life_support.get_system_health()
        print(f"  ✅ 健康监控: {health['health_score']:.1f}/100")
        
        allowed = life_support.is_task_allowed(0.5)
        print(f"  ✅ 任务准入: {'允许' if allowed else '拒绝'}")
        
        results.append(True)
    except Exception as e:
        print(f"  ❌ 生命维持系统集成失败: {e}")
        results.append(False)
    
    # 4. 验证迁移协议集成
    print("\n【4. 迁移协议集成】")
    try:
        from infrastructure.migration_protocol import migration_protocol
        
        # 测试状态压缩
        state = migration_protocol.compress_state()
        print(f"  ✅ 状态压缩: {len(state.get('components', {}))}个组件")
        
        results.append(True)
    except Exception as e:
        print(f"  ❌ 迁移协议集成失败: {e}")
        results.append(False)
    
    # 5. 验证CI配置
    print("\n【5. CI配置】")
    try:
        from pathlib import Path
        ci_file = Path(".github/workflows/ci.yml")
        if ci_file.exists():
            print(f"  ✅ CI配置文件存在")
            results.append(True)
        else:
            print(f"  ❌ CI配置文件不存在")
            results.append(False)
    except Exception as e:
        print(f"  ❌ CI配置检查失败: {e}")
        results.append(False)
    
    # 总结
    print("\n" + "=" * 70)
    passed = sum(results)
    total = len(results)
    
    print(f"集成验证结果: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("✅ 所有集成点验证通过！")
        print("\n系统已完全就绪，可以：")
        print("  1. 启动后端服务")
        print("  2. 运行基准测试")
        print("  3. 开始实际使用")
        print("  4. 发布v3.3.0版本")
    else:
        print(f"⚠️ {total-passed}个集成点需要关注")
    
    print("=" * 70)
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(verify_integration())