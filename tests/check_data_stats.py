import sqlite3
import os

db_path = 'data/interaction_data.db'
if not os.path.exists(db_path):
    print("数据库不存在")
    exit(0)

conn = sqlite3.connect(db_path)

# 总交互数
cursor = conn.execute('SELECT COUNT(*) FROM interactions')
total = cursor.fetchone()[0]

# 高质量数据（客观分 >= 70）
cursor = conn.execute('SELECT COUNT(*) FROM interactions WHERE objective_score >= 70')
high_quality = cursor.fetchone()[0]

# 纠错数
cursor = conn.execute("SELECT COUNT(*) FROM interactions WHERE feedback_type='correction'")
corrections = cursor.fetchone()[0]

# 正反馈数
cursor = conn.execute("SELECT COUNT(*) FROM interactions WHERE feedback_type='positive'")
positive = cursor.fetchone()[0]

print(f"📊 数据采集统计:")
print(f"  总交互数: {total}")
print(f"  高质量数据: {high_quality}")
print(f"  正反馈: {positive}")
print(f"  纠错: {corrections}")
print(f"\n💡 建议:")
if total < 100:
    print(f"  需要积累更多数据（当前{total}条，建议100+条）")
else:
    print(f"  数据量充足，可以开始SFT微调")

conn.close()