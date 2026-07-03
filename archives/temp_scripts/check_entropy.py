import sqlite3

conn = sqlite3.connect("data/spirit_lessons.db")
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM reflections WHERE timestamp > datetime('now','-1 day')")
recent = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM reflections WHERE timestamp > datetime('now','-1 day') AND lessons LIKE '%失败%'")
failed = c.fetchone()[0]
conn.close()
print(f"recent={recent}, failed={failed}, rate={failed/recent if recent else 0:.3f}")

conn2 = sqlite3.connect("data/truths.db")
c2 = conn2.cursor()
c2.execute("SELECT COUNT(*) FROM truths WHERE is_active=1")
total = c2.fetchone()[0]
c2.execute("SELECT COUNT(*) FROM truths WHERE is_active=1 AND evidence_count < 2")
weak = c2.fetchone()[0]
conn2.close()
print(f"truths_total={total}, weak={weak}, conflict_rate={weak/total if total else 0:.3f}")

contradiction_rate = failed/recent if recent else 0
truth_conflict_rate = weak/total if total else 0
entropy = contradiction_rate * 0.4 + truth_conflict_rate * 0.3
print(f"entropy_score={entropy:.3f}")