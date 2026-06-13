"""简化核心验证"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("核心功能验证（简化版）")
print("=" * 60)

# 验证1: 检测器
print("\n[验证1] 检测器测试")
from infrastructure.dialogue_stream_learner import ImplicitNegationDetector

detector = ImplicitNegationDetector()
tests = ["不太对", "还是不对", "你是对的"]
for text in tests:
    result = detector.detect(text)
    status = "✓" if (result is not None) == ("不对" in text or "还是" in text) else "✗"
    print(f"  {status} '{text}' → {'检测到' if result else '未检测'}")

# 验证2: 元归纳器
print("\n[验证2] 元归纳器测试")
from meta.meta_induction import meta_inductor
print(f"  当前参数: min_support={meta_inductor.params['min_support']}")
result = meta_inductor.optimize_parameters()
print(f"  ✓ 优化{'成功' if result['success'] else '失败'}")

# 验证3: 数据库
print("\n[验证3] 数据库状态")
import sqlite3

conn = sqlite3.connect('learning_rules.db')
cur = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
active = cur.fetchone()[0]
conn.close()
print(f"  活跃规则: {active}条")

conn = sqlite3.connect('experience_pool.db')
cur = conn.execute("SELECT COUNT(*) FROM experiences")
exp = cur.fetchone()[0]
conn.close()
print(f"  经验池: {exp}条")

# 验证4: 意图识别
print("\n[验证4] 元认知意图识别")
from core.services.intent_parser import IntentParser
parser = IntentParser()

test_q = "你觉得如何才可以更好的理解需求？"
intent = parser.parse(test_q)
print(f"  '{test_q[:30]}' → {intent.type}")

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)