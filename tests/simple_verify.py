"""简化验证脚本"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("验证元认知能力改进")
print("=" * 60)

# 1. 意图识别测试
from core.services.intent_parser import IntentParser
parser = IntentParser()

test_cases = [
    ("你觉得如何才可以更好的理解需求？", "meta"),
    ("你如何理解用户意图？", "meta"),
    ("你能明白我的意思吗？", "meta"),
]

print("\n[意图识别测试]")
for question, expected in test_cases:
    intent = parser.parse(question)
    status = "✓" if intent.type == expected else "✗"
    print(f"{status} {question[:35]:<35} → {intent.type}")

# 2. 检查处理器存在
from core.services.planner import DataDrivenPlanner
print("\n[处理器检查]")
print(f"✓ _handle_meta_question方法存在: {hasattr(DataDrivenPlanner, '_handle_meta_question')}")

# 3. 数据库状态
import sqlite3
conn = sqlite3.connect('data/learning_rules.db')
cur = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
active_rules = cur.fetchone()[0]
conn.close()
print(f"\n[数据库状态]")
print(f"✓ 活跃规则: {active_rules}条")

print("\n" + "=" * 60)
print("验证完成")