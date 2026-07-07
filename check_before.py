import sqlite3
conn = sqlite3.connect('data/learning_rules.db')
c = conn.cursor()
c.execute("SELECT id, condition, action, apply_count FROM learning_rules WHERE status='active' ORDER BY priority DESC")
print("Before test:")
for r in c.fetchall():
    print(f"  #{r[0]} apply={r[3]} | {r[1][:55]} -> {r[2]}")
conn.close()