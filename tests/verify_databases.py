"""验证数据库状态"""
import sqlite3

print('=== 数据库验证 ===')

# 事实库
conn = sqlite3.connect('data/fact_assertions.db')
total = conn.execute('SELECT COUNT(*) FROM fact_assertions').fetchone()[0]
print(f'事实库: {total} 条断言')
conn.close()

# 版本控制库
conn = sqlite3.connect('data/fact_assertions_v2.db')
total = conn.execute('SELECT COUNT(*) FROM fact_assertions').fetchone()[0]
print(f'版本控制库: {total} 条断言')
conn.close()

# 验证记录
conn = sqlite3.connect('data/injection_verifications.db')
total = conn.execute('SELECT COUNT(*) FROM injection_verifications').fetchone()[0]
print(f'验证记录: {total} 条')
conn.close()

print('\n✅ 所有数据库正常')