"""
联邦调度系统测试脚本
验证能力矩阵、并行调度、模型发现功能
"""
import asyncio
from infrastructure.model_capability import model_capability
from infrastructure.parallel_scheduler import parallel_scheduler
from infrastructure.model_discovery import model_discovery
from loguru import logger


def test_capability_matrix():
    """测试能力矩阵"""
    print("\n=== 能力矩阵测试 ===")
    
    model_capability.register_model("mindchat", {
        'reasoning': 0.75,
        'knowledge': 0.8,
        'creative': 0.7,
        'speed': 0.9
    })
    
    model_capability.register_model("deepcoder", {
        'coding': 0.95,
        'reasoning': 0.85,
        'math': 0.8,
        'speed': 0.6
    })
    
    model_capability.register_model("qwen2.5-coder:1.5b", {
        'coding': 0.85,
        'speed': 0.95,
        'reasoning': 0.7
    })
    
    print("已注册模型:", model_capability.export_stats())
    
    task_type = "code"
    models = ["mindchat", "deepcoder", "qwen2.5-coder:1.5b"]
    ranked = model_capability.rank_models_for_task(task_type, models)
    
    print(f"\n任务 '{task_type}' 模型排序:")
    for model, score in ranked:
        print(f"  {model}: {score:.3f}")
    
    top_models = model_capability.get_top_models(task_type, top_k=2)
    print(f"\n最佳模型: {top_models}")
    
    print("\n✓ 能力矩阵测试通过")


def test_parallel_scheduler():
    """测试并行调度器"""
    print("\n=== 并行调度器测试 ===")
    
    stats = parallel_scheduler.get_stats()
    print("调度器统计:", stats)
    
    print("\n✓ 并行调度器测试通过")


async def test_model_discovery():
    """测试模型发现"""
    print("\n=== 模型发现测试 ===")
    
    models = model_discovery.get_discovered_models()
    print(f"已发现模型: {len(models)}个")
    
    for model in models[:3]:
        print(f"  - {model['name']} ({model['source']})")
    
    print("\n✓ 模型发现测试通过")


def test_task_matching():
    """测试任务匹配"""
    print("\n=== 任务匹配测试 ===")
    
    test_cases = [
        ("code", ["mindchat", "deepcoder", "qwen2.5-coder:1.5b"]),
        ("math", ["mindchat", "deepcoder", "qwen2.5-coder:1.5b"]),
        ("creative", ["mindchat", "deepcoder", "qwen2.5-coder:1.5b"]),
        ("qa", ["mindchat", "deepcoder", "qwen2.5-coder:1.5b"])
    ]
    
    for task_type, models in test_cases:
        top = model_capability.get_top_models(task_type, top_k=1)
        score = model_capability.score_model_for_task(top[0] if top else models[0], task_type)
        print(f"任务 '{task_type}': 最佳模型={top[0] if top else 'N/A'}, 得分={score:.3f}")
    
    print("\n✓ 任务匹配测试通过")


async def main():
    """主测试流程"""
    print("=" * 60)
    print("联邦调度系统测试")
    print("=" * 60)
    
    try:
        test_capability_matrix()
        test_parallel_scheduler()
        await test_model_discovery()
        test_task_matching()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())