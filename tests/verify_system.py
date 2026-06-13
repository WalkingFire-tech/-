"""
系统启动验证脚本 - 快速检查所有模块状态
"""
import sys
from pathlib import Path


def check_module(module_name: str, import_path: str) -> bool:
    """检查模块是否可导入"""
    try:
        __import__(import_path)
        print(f"  ✅ {module_name}")
        return True
    except Exception as e:
        print(f"  ❌ {module_name}: {e}")
        return False


def check_file(file_path: str) -> bool:
    """检查文件是否存在"""
    path = Path(file_path)
    if path.exists():
        print(f"  ✅ {file_path}")
        return True
    else:
        print(f"  ❌ {file_path}")
        return False


def main():
    """主验证流程"""
    print("\n" + "=" * 70)
    print("联盟拓荒者 V3.3 系统验证")
    print("=" * 70)
    
    all_passed = True
    
    # 1. 核心模块检查
    print("\n【核心模块】")
    modules = [
        ("意图解析器", "core.services.intent_parser"),
        ("规划器", "core.services.planner"),
        ("能力矩阵", "infrastructure.model_capability"),
        ("并行调度器", "infrastructure.parallel_scheduler"),
        ("模型发现器", "infrastructure.model_discovery"),
        ("任务分解器", "infrastructure.task_decomposer"),
        ("结果融合器", "infrastructure.result_fusion"),
        ("快速基准测试", "infrastructure.quick_benchmark"),
        ("自我反思报告", "infrastructure.self_reflection"),
    ]
    
    for name, path in modules:
        if not check_module(name, path):
            all_passed = False
    
    # 2. 配置文件检查
    print("\n【配置文件】")
    configs = [
        "config/settings.yaml",
        "config/model_config.yaml",
    ]
    
    for config in configs:
        if not check_file(config):
            all_passed = False
    
    # 3. 数据库文件检查
    print("\n【数据库文件】")
    databases = [
        "experience_pool.db",
        "learning_rules.db",
        "model_stats.db",
        "data/capability_matrix.db",
        "data/scheduler_stats.db",
        "data/discovered_models.db",
        "data/task_decomposition.db",
        "data/result_fusion.db",
    ]
    
    for db in databases:
        check_file(db)  # 不强制要求存在
    
    # 4. 文档文件检查
    print("\n【文档文件】")
    docs = [
        "README.md",
        "docs/ARCHITECTURE.md",
        "docs/MULTI_MODEL_FEDERATION_DECISION.md",
        "docs/MULTI_MODEL_FEDERATION_IMPLEMENTATION.md",
        "docs/P2_IMPLEMENTATION_REPORT.md",
        "docs/FINAL_EVALUATION_V3.3.md",
    ]
    
    for doc in docs:
        if not check_file(doc):
            all_passed = False
    
    # 5. 测试文件检查
    print("\n【测试文件】")
    tests = [
        "test_federation.py",
        "test_federation_integration.py",
        "test_p2_decomposition.py",
        "test_complete_integration.py",
        "tests/benchmark_federation.py",
    ]
    
    for test in tests:
        if not check_file(test):
            all_passed = False
    
    # 6. 功能验证
    print("\n【功能验证】")
    try:
        from infrastructure.model_capability import model_capability
        stats = model_capability.export_stats()
        print(f"  ✅ 能力矩阵: {stats['registered_models']}个模型, {stats['dimensions']}个维度")
    except:
        print("  ⚠️  能力矩阵未初始化")
    
    try:
        from infrastructure.parallel_scheduler import parallel_scheduler
        stats = parallel_scheduler.get_stats()
        print(f"  ✅ 并行调度器: {stats['total_calls']}次调用")
    except:
        print("  ⚠️  并行调度器未初始化")
    
    # 7. 总结
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ 系统验证通过，所有核心模块就绪")
        print("\n下一步行动:")
        print("  1. 运行基准测试: python tests/benchmark_federation.py")
        print("  2. 评估模型能力: python infrastructure/quick_benchmark.py")
        print("  3. 生成反思报告: python infrastructure/self_reflection.py")
        print("  4. 启动后端服务: python backend/main.py")
    else:
        print("⚠️  部分模块缺失，请检查上述错误")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())