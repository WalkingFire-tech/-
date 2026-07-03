import sqlite3
conn = sqlite3.connect('data/skills.db')
c = conn.cursor()
c.execute("DELETE FROM skills WHERE skill_name LIKE '%郑州%' OR skill_name LIKE '%黑龙江%' OR skill_name LIKE '%esp32明明%' OR skill_name LIKE '%火星%' OR skill_name LIKE '%写一个冒泡%' OR skill_name LIKE '%上一轮%' OR skill_name LIKE '%你确定吗%'")
conn.commit()
print(f'Deleted {c.rowcount} junk skills')
c.execute('SELECT skill_name,success_count FROM skills ORDER BY success_count DESC')
for r in c.fetchall():
    print(r)