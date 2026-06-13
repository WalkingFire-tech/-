"""测试完整的元认知处理流程"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.services.intent_parser import IntentParser
from core.services.planner import DataDrivenPlanner
from core.ports.llm_port import LLMPort

print("初始化系统组件...")
parser = IntentParser()
llm_port = LLMPort()
planner = DataDrivenPlanner(llm_port)

test_question = "你觉得如何才可以更好的理解需求？"

print(f"\n测试问题: {test_question}\n")

# 步骤1: 意图识别
intent = parser.parse(test_question)
print(f"步骤1 - 意图识别:")
print(f"  类型: {intent.type}")
print(f"  置信度: {intent.confidence:.2f}")

# 步骤2: 检查是否有元认知处理方法
if hasattr(planner, '_handle_meta_question'):
    print(f"\n步骤2 - 元认知处理:")
    try:
        response = planner._handle_meta_question(test_question)
        print(f"  ✓ 成功获取元认知响应")
        print(f"\n响应内容:")
        print(response[:500] + "..." if len(response) > 500 else response)
    except Exception as e:
        print(f"  ✗ 处理失败: {e}")
else:
    print(f"\n步骤2 - ✗ 未找到_handle_meta_question方法")