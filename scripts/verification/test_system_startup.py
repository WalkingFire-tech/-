import sys
sys.path.insert(0, '.')

print('=== 系统启动测试 ===\n')

errors = []
success = []

try:
    from core.layers.l1_perception_enhanced import L1PerceptionLayer
    l1 = L1PerceptionLayer()
    result = l1.perceive('你好，我想问一个问题')
    print(f'✓ L1感知层: 情绪={result["emotional_state"].primary_emotion}, 意图={result["intent"]}')
    success.append('L1感知层')
except Exception as e:
    print(f'✗ L1感知层: {e}')
    errors.append(f'L1: {e}')

try:
    from core.layers.l2_learning import L2LearningLayer
    l2 = L2LearningLayer()
    print('✓ L2学习层初始化成功')
    success.append('L2学习层')
except Exception as e:
    print(f'✗ L2学习层: {e}')
    errors.append(f'L2: {e}')

try:
    from core.layers.l3_integration import L3IntegrationLayer
    l3 = L3IntegrationLayer()
    print('✓ L3整合层初始化成功')
    success.append('L3整合层')
except Exception as e:
    print(f'✗ L3整合层: {e}')
    errors.append(f'L3: {e}')

try:
    from core.layers.l4_validation import L4ValidationLayer
    l4 = L4ValidationLayer()
    print('✓ L4校验层初始化成功')
    success.append('L4校验层')
except Exception as e:
    print(f'✗ L4校验层: {e}')
    errors.append(f'L4: {e}')

try:
    from core.layers.l5_evolution import L5EvolutionLayer
    l5 = L5EvolutionLayer()
    print('✓ L5进化层初始化成功')
    success.append('L5进化层')
except Exception as e:
    print(f'✗ L5进化层: {e}')
    errors.append(f'L5: {e}')

try:
    from core.layers.l6_introspection import L6IntrospectionLayer
    l6 = L6IntrospectionLayer()
    print('✓ L6内省层初始化成功')
    success.append('L6内省层')
except Exception as e:
    print(f'✗ L6内省层: {e}')
    errors.append(f'L6: {e}')

try:
    from core.learning.feedback_loop import LearningFeedbackLoop
    loop = LearningFeedbackLoop()
    print('✓ 经验反馈回路初始化成功')
    success.append('经验反馈回路')
except Exception as e:
    print(f'✗ 经验反馈回路: {e}')
    errors.append(f'FeedbackLoop: {e}')

try:
    from core.learning.tool_builder import ToolSelfBuilder
    builder = ToolSelfBuilder()
    print('✓ 工具自我构建初始化成功')
    success.append('工具自我构建')
except Exception as e:
    print(f'✗ 工具自我构建: {e}')
    errors.append(f'ToolBuilder: {e}')

print(f'\n=== 结果 ===')
print(f'成功: {len(success)}/{len(success)+len(errors)}')
if errors:
    print(f'错误:')
    for e in errors:
        print(f'  - {e}')
else:
    print('✓ 所有模块加载成功！')