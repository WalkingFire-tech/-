"""
快速验证v3.4里程碑成果
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*60)
print("v3.4 里程碑验证")
print("="*60)

# 1. 意图识别
print("\n1️⃣ 意图识别测试")
from core.services.intent_parser import IntentParser
parser = IntentParser()

test_cases = [
    ("你的能力边界在哪里？", "meta"),
    ("你如何决策？", "meta"),
    ("回顾对话历史", "meta"),
]

for question, expected in test_cases:
    intent = parser.parse(question)
    status = "✅" if intent.type == expected else "❌"
    print(f"  {status} {question[:20]:20s} -> {intent.type} (期望: {expected})")

# 2. 元认知回答
print("\n2️⃣ 元认知回答测试")
try:
    from infrastructure.health_dashboard import health_dashboard
    metrics = health_dashboard.calculate_aphi()
    print(f"  ✅ APHI计算成功: {metrics['aphi']}")
except Exception as e:
    print(f"  ❌ APHI计算失败: {e}")

# 3. 知识注入
print("\n3️⃣ 知识注入系统测试")
try:
    from infrastructure.knowledge_injector import knowledge_injector
    stats = knowledge_injector.get_statistics()
    print(f"  ✅ 知识库已就绪: {stats['total_knowledge']}条知识")
except Exception as e:
    print(f"  ❌ 知识库初始化失败: {e}")

# 4. 反事实模拟器
print("\n4️⃣ 反事实模拟器测试")
try:
    from infrastructure.counterfactual_simulator import counterfactual_simulator
    stats = counterfactual_simulator.get_statistics()
    print(f"  ✅ 反事实模拟器已就绪")
except Exception as e:
    print(f"  ❌ 反事实模拟器初始化失败: {e}")

print("\n" + "="*60)
print("验证完成！")
print("="*60)
print("\n💡 下一步：")
print("  1. 重启后端服务: python backend/main.py")
print("  2. 在CLI中输入: 你的能力边界在哪里？")
print("  3. 期望看到结构化的能力边界报告")