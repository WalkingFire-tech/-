import sqlite3

conn = sqlite3.connect("data/experience_pool.db")
c = conn.cursor()

low_q = c.execute("SELECT COUNT(*) FROM experiences WHERE quality_score < 30").fetchone()[0]
c.execute("DELETE FROM experiences WHERE quality_score < 30")

before = c.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
c.execute("""
    DELETE FROM experiences WHERE rowid NOT IN (
        SELECT MAX(rowid) FROM experiences GROUP BY raw_input
    )
""")
after = c.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
conn.commit()
conn.close()
print(f"Low quality removed: {low_q}")
print(f"Before dedup: {before}, After: {after}, Removed: {before - after}")