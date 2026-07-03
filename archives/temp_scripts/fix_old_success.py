import sqlite3

conn = sqlite3.connect('data/experience_pool.db')
c = conn.cursor()

c.execute('SELECT success, COUNT(*) FROM experiences GROUP BY success')
print('Before:', [r for r in c.fetchall()])

c.execute('UPDATE experiences SET success = 1 WHERE success IS NULL AND quality_score >= 70')
print(f'Updated NULL->1 (quality>=70): {c.rowcount}')

c.execute('UPDATE experiences SET success = 0 WHERE success IS NULL')
print(f'Updated NULL->0 (quality<70): {c.rowcount}')

c.execute('UPDATE experiences SET success = 1 WHERE success = 0 AND quality_score >= 70')
print(f'Updated 0->1 (quality>=70): {c.rowcount}')

conn.commit()

c.execute('SELECT success, COUNT(*) FROM experiences GROUP BY success')
print('After:', [r for r in c.fetchall()])

conn.close()