import subprocess, time, requests, sys, json

proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.main_fast:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd=r"C:\Users\Administrator\alliance_pioneer",
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)

print(f"Started PID: {proc.pid}")

for i in range(60):
    time.sleep(1)
    try:
        r = requests.get("http://localhost:8000/api/health", timeout=2)
        if r.status_code == 200:
            print(f"[{i+1}s] Backend ready")
            break
    except:
        pass

print("\nTesting complex query...")
query = "冰雹是怎么形成的"
start = time.time()
try:
    r = requests.post("http://localhost:8000/api/chat/stream",
                     json={"message": query, "history": []},
                     stream=True, timeout=120)
    chunk_count = 0
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        chunk_count += 1
        elapsed = time.time() - start
        if chunk_count <= 3 or chunk_count % 5 == 0:
            print(f"  [{elapsed:.1f}s] chunk #{chunk_count}: {line[:80]}")
    elapsed = time.time() - start
    print(f"  => Stream ended | {elapsed:.1f}s | {chunk_count} chunks")
except Exception as e:
    elapsed = time.time() - start
    print(f"  => EXCEPTION: {e} | {elapsed:.1f}s")

time.sleep(3)
try:
    r = requests.get("http://localhost:8000/api/health", timeout=5)
    print(f"Backend: alive")
except:
    print(f"Backend: DEAD! Reading logs...")
    proc.terminate()
    try:
        remaining = proc.stdout.read().decode(errors='replace')
        lines = remaining.split('\n')
        for line in lines[-40:]:
            if line.strip():
                print(f"  {line.strip()[:150]}")
    except:
        pass