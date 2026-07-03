import sqlite3

conn = sqlite3.connect('data/experience_pool.db')
c = conn.cursor()

c.execute('UPDATE experiences SET success = 1 WHERE success = 0 AND LENGTH(response) > 20')
print(f'Updated 0->1 (response>20chars): {c.rowcount}')

conn.commit()

c.execute('SELECT success, COUNT(*) FROM experiences GROUP BY success')
print('Final:', [r for r in c.fetchall()])

conn.close()