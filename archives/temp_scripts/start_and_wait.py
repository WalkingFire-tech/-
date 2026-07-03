import subprocess, time, requests, sys

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
            print(f"[{i+1}s] Health: {r.json()}")
            break
    except:
        if i % 10 == 9:
            print(f"[{i+1}s] Still waiting...")
            line = proc.stdout.readline()
            if line:
                print(f"  LOG: {line.decode(errors='replace').strip()[:100]}")

print("Backend is ready!")