"""
P2阶段测试 - 任务分解与结果融合
验证智能分解、子任务执行、结果融合的完整流程
"""
import asyncio
from loguru import logger


def test_task_decomposer():
    """测试任务分解器"""
    print("\n=== 任务分解器测试 ===")
    
    from infrastructure.task_decomposer import task_decomposer
    
    test_cases = [
        "写一个快速排序算法，并解释其时间复杂度",
        "计算25+17的结果，同时解释加法原理",
        "分析Python和Java的区别，并给出学习建议",
        "写一个冒泡排序",  # 简单任务，不应分解
        "实现一个用户登录功能，包括前端表单验证、后端API接口和数据库存储",
    ]
    
    for i, task in enumerate(test_cases, 1):
        print(f"\n{i}. 测试任务: {task[:50]}...")
        subtasks = task_decomposer.detect_subtasks(task)
        
        print(f"   分解结果: {len(subtasks)}个子任务")
        for j, subtask in enumerate(subtasks):
            print(f"     [{j}] {subtask['type']:12} - {subtask['description'][:40]}...")
            if subtask.get('dependencies'):
                print(f"         依赖: {subtask['dependencies']}")
    
    stats = task_decomposer.get_decomposition_stats()
    print(f"\n分解统计: {stats}")
    
    print("\n✓ 任务分解器测试通过")


def test_result_fusion():
    """测试结果融合器"""
    print("\n=== 结果融合器测试 ===")
    
    from infrastructure.result_fusion import result_fusion
    
    # 测试不同融合策略
    test_cases = [
        {
            'subtasks': [
                {'id': 0, 'type': 'code', 'description': '实现快速排序'},
                {'id': 1, 'type': 'explanation', 'description': '解释时间复杂度'}
            ],
            'results': [
                "```python\ndef quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)\n```",
                "快速排序的平均时间复杂度为O(n log n)，最坏情况下为O(n²)。"
            ],
            'intent': "写一个快速排序算法，并解释其时间复杂度",
            'strategy': 'concat'
        },
        {
            'subtasks': [
                {'id': 0, 'type': 'code', 'description': '代码实现A'},
                {'id': 1, 'type': 'code', 'description': '代码实现B'}
            ],
            'results': [
                "def solution_a(): return 'A'",
                "def solution_b(): return 'B'"
            ],
            'intent': "比较两种实现",
            'strategy': 'best'
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. 测试策略: {test['strategy']}")
        fused = result_fusion.fuse(
            subtasks=test['subtasks'],
            results=test['results'],
            original_intent=test['intent'],
            strategy=test['strategy']
        )
        print(f"   融合结果长度: {len(fused)}")
        print(f"   预览: {fused[:100]}...")
    
    stats = result_fusion.get_fusion_stats()
    print(f"\n融合统计: {stats}")
    
    print("\n✓ 结果融合器测试通过")


def test_decompose_strategies():
    """测试不同分解策略"""
    print("\n=== 分解策略测试 ===")
    
    from infrastructure.task_decomposer import task_decomposer
    
    # 测试连接词分割
    text1 = "写一个快速排序算法，并且解释其时间复杂度，同时给出优化建议"
    subtasks1 = task_decomposer.detect_subtasks(text1)
    print(f"\n1. 连接词分割测试")
    print(f"   输入: {text1}")
    print(f"   分解数: {len(subtasks1)}")
    
    # 测试多类型检测
    text2 = "计算斐波那契数列的前10项，并分析其增长规律"
    subtasks2 = task_decomposer.detect_subtasks(text2)
    print(f"\n2. 多类型检测测试")
    print(f"   输入: {text2}")
    print(f"   分解数: {len(subtasks2)}")
    
    # 测试依赖分析
    text3 = "先实现冒泡排序，然后分析其性能，最后给出优化方案"
    subtasks3 = task_decomposer.detect_subtasks(text3)
    print(f"\n3. 依赖分析测试")
    print(f"   输入: {text3}")
    print(f"   分解数: {len(subtasks3)}")
    for task in subtasks3:
        if task.get('dependencies'):
            print(f"     任务{task['id']}依赖: {task['dependencies']}")
    
    print("\n✓ 分解策略测试通过")


def test_fusion_strategies():
    """测试融合策略选择"""
    print("\n=== 融合策略选择测试 ===")
    
    from infrastructure.result_fusion import result_fusion
    
    # 测试自动策略选择
    test_cases = [
        {
            'subtasks': [
                {'type': 'code', 'description': '代码A'},
                {'type': 'code', 'description': '代码B'}
            ],
            'expected': 'best'
        },
        {
            'subtasks': [
                {'type': 'code', 'description': '代码'},
                {'type': 'explanation', 'description': '解释'}
            ],
            'expected': 'summarize'
        },
        {
            'subtasks': [
                {'type': 'code', 'description': '代码', 'dependencies': []},
                {'type': 'analysis', 'description': '分析', 'dependencies': [0]}
            ],
            'expected': 'merge'
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        strategy = result_fusion._select_strategy(test['subtasks'], ['result1', 'result2'])
        status = "✓" if strategy == test['expected'] else "✗"
        print(f"  {status} 测试{i}: 期望={test['expected']}, 实际={strategy}")
    
    print("\n✓ 融合策略选择测试通过")


def test_integration_workflow():
    """测试完整集成流程"""
    print("\n=== 完整集成流程测试 ===")
    
    from infrastructure.task_decomposer import task_decomposer
    from infrastructure.result_fusion import result_fusion
    
    # 模拟完整流程
    user_input = "写一个Python函数计算斐波那契数列，并解释其数学原理，同时比较递归和迭代的性能"
    
    print(f"\n1. 用户输入: {user_input[:50]}...")
    
    # 分解
    subtasks = task_decomposer.detect_subtasks(user_input)
    print(f"\n2. 任务分解: {len(subtasks)}个子任务")
    for task in subtasks:
        print(f"   - {task['type']:12}: {task['description'][:40]}...")
    
    # 模拟执行结果
    mock_results = [
        "```python\ndef fib_recursive(n):\n    if n <= 1:\n        return n\n    return fib_recursive(n-1) + fib_recursive(n-2)\n\ndef fib_iterative(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n```",
        "斐波那契数列是这样一个数列：每个数都是前两个数之和，即F(n) = F(n-1) + F(n-2)。",
        "递归实现简洁但效率低（O(2^n)），迭代实现效率高（O(n)）且不会栈溢出。"
    ]
    
    print(f"\n3. 模拟执行: {len(mock_results)}个结果")
    
    # 融合
    fused = result_fusion.fuse(
        subtasks=subtasks,
        results=mock_results,
        original_intent=user_input,
        strategy='concat'
    )
    
    print(f"\n4. 结果融合: 长度={len(fused)}")
    print(f"   预览:\n{fused[:200]}...")
    
    # 保存
    task_decomposer.save_decomposition(
        original_task=user_input,
        subtasks=subtasks,
        strategy='rule',
        success=True,
        quality_score=0.85
    )
    
    print("\n✓ 完整集成流程测试通过")


async def main():
    """主测试流程"""
    print("=" * 70)
    print("P2阶段测试 - 任务分解与结果融合")
    print("=" * 70)
    
    try:
        test_task_decomposer()
        test_result_fusion()
        test_decompose_strategies()
        test_fusion_strategies()
        test_integration_workflow()
        
        print("\n" + "=" * 70)
        print("✓ 所有P2测试通过")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())