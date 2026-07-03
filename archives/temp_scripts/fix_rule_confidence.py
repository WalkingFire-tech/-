import sqlite3

conn = sqlite3.connect('data/learning_rules.db')
c = conn.cursor()

c.execute('SELECT confidence, COUNT(*) FROM learning_rules GROUP BY confidence ORDER BY confidence')
print('Before:', [r for r in c.fetchall()])

c.execute('SELECT id, condition, action, apply_count, success_count, confidence FROM learning_rules WHERE status="active" LIMIT 10')
for row in c.fetchall():
    print(f'  Rule {row[0]}: cond={row[1][:30]}, action={row[2][:30]}, apply={row[3]}, succ={row[4]}, conf={row[5]}')

c.execute("""
    UPDATE learning_rules 
    SET confidence = CASE 
        WHEN apply_count > 0 AND success_count > 0 THEN MIN(0.5 + (CAST(success_count AS REAL) / apply_count) * 0.4, 0.95)
        WHEN apply_count > 0 THEN MIN(0.5 + apply_count * 0.03, 0.8)
        ELSE 0.5
    END
    WHERE status = 'active'
""")
print(f'\nUpdated confidence for {c.rowcount} active rules')

c.execute("""
    UPDATE learning_rules 
    SET confidence = 0.3
    WHERE status = 'pending' AND apply_count = 0
""")
print(f'Set pending confidence for {c.rowcount} pending rules')

conn.commit()

c.execute('SELECT confidence, COUNT(*) FROM learning_rules GROUP BY confidence ORDER BY confidence')
print('\nAfter:', [r for r in c.fetchall()])

conn.close()
