import sqlite3

conn = sqlite3.connect("data/experience_pool.db")
c = conn.cursor()

c.execute("SELECT COUNT(*), AVG(quality_score) FROM experiences WHERE timestamp > datetime('now', '-24 hours')")
r = c.fetchone()
print("24h experiences: count={}, avg_quality={:.1f}".format(r[0], r[1] if r[1] else 0))

c.execute("SELECT COUNT(*), AVG(quality_score) FROM experiences WHERE timestamp > datetime('now', '-1 hour')")
r = c.fetchone()
print("1h experiences: count={}, avg_quality={:.1f}".format(r[0], r[1] if r[1] else 0))

c.execute("SELECT intent_type, COUNT(*), AVG(quality_score) FROM experiences WHERE timestamp > datetime('now', '-24 hours') GROUP BY intent_type ORDER BY COUNT(*) DESC LIMIT 10")
for r in c.fetchall():
    print("  {}: count={}, avg_q={:.1f}".format(r[0], r[1], r[2] if r[2] else 0))
conn.close()

try:
    conn2 = sqlite3.connect("data/knowledge_store.db")
    c2 = conn2.cursor()
    c2.execute("SELECT COUNT(*), AVG(quality_score) FROM knowledge_items WHERE status='active'")
    r2 = c2.fetchone()
    print("knowledge_store: count={}, avg_quality={:.1f}".format(r2[0], r2[1] if r2[1] else 0))
    c2.execute("SELECT COUNT(*) FROM knowledge_items WHERE created_at > datetime('now', '-24 hours')")
    r3 = c2.fetchone()
    print("24h new knowledge: {}".format(r3[0]))
    conn2.close()
except Exception as e:
    print("knowledge_store error:", e)

try:
    conn3 = sqlite3.connect("data/reflection_journal.db")
    c3 = conn3.cursor()
    c3.execute("SELECT COUNT(*) FROM reflections WHERE timestamp > datetime('now', '-24 hours')")
    r4 = c3.fetchone()
    print("24h reflections: {}".format(r4[0]))
    c3.execute("SELECT note FROM reflections ORDER BY timestamp DESC LIMIT 3")
    for r in c3.fetchall():
        print("  reflection: {}...".format(r[0][:80] if r[0] else ""))
    conn3.close()
except Exception as e:
    print("reflection error:", e)

try:
    conn4 = sqlite3.connect("data/learning_rules.db")
    c4 = conn4.cursor()
    c4.execute("SELECT status, COUNT(*) FROM learning_rules GROUP BY status")
    for r in c4.fetchall():
        print("learning_rules {}: {}".format(r[0], r[1]))
    conn4.close()
except Exception as e:
    print("learning_rules error:", e)

try:
    conn5 = sqlite3.connect("data/genome.db")
    c5 = conn5.cursor()
    c5.execute("SELECT COUNT(*), MAX(generation) FROM genomes")
    r5 = c5.fetchone()
    print("genome generations: {} genomes, max_gen={}".format(r5[0], r5[1] if r5[1] else 0))
    c5.execute("SELECT fitness FROM genomes WHERE is_active=1")
    r6 = c5.fetchone()
    print("active genome fitness: {}".format(r6[0] if r6 else "none"))
    conn5.close()
except Exception as e:
    print("genome error:", e)

try:
    conn6 = sqlite3.connect("data/probability_field.db")
    c6 = conn6.cursor()
    c6.execute("SELECT COUNT(*) FROM probability_snapshots WHERE timestamp > datetime('now', '-24 hours')")
    r7 = c6.fetchone()
    print("24h probability snapshots: {}".format(r7[0]))
    conn6.close()
except Exception as e:
    print("prob_field error:", e)

import os
for f in ["logs/server_2026-07-22.log", "logs/server.log"]:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print("log {}: {}KB".format(f, size // 1024))