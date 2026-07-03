import os
import time

now = time.time()
dbs = [f for f in os.listdir("data") if f.endswith(".db")]
test_dbs = [f for f in dbs if f.startswith("test_") or f.startswith("e2e_")]
old_dbs = []
for f in dbs:
    if f in test_dbs:
        continue
    mtime = os.path.getmtime(os.path.join("data", f))
    if (now - mtime) > 14 * 86400:
        old_dbs.append(f)

print(f"Test DBs ({len(test_dbs)}):")
for f in sorted(test_dbs):
    print(f"  {f}")
print(f"\nOld DBs (>14d, {len(old_dbs)}):")
for f in sorted(old_dbs):
    print(f"  {f}")