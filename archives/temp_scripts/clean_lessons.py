import sqlite3

conn = sqlite3.connect('data/spirit_lessons.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM lessons")
total = c.fetchone()[0]
print(f"Total: {total}")

c.execute("DELETE FROM lessons WHERE question IS NULL OR question = ''")
d1 = c.rowcount

c.execute("DELETE FROM lessons WHERE question LIKE '%火星%木星%'")
d2 = c.rowcount

c.execute("DELETE FROM lessons WHERE question = '测试问题'")
d3 = c.rowcount

conn.commit()
c.execute("SELECT COUNT(*) FROM lessons")
remaining = c.fetchone()[0]
conn.close()
print(f"Deleted: {d1} empty + {d2} stale-mars + {d3} test. Remaining: {remaining}")