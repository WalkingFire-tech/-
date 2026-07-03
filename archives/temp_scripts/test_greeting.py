import subprocess, time, requests, sys, json, threading

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
        pass

print("Backend is ready! Testing simple greeting...")
start = time.time()
try:
    r = requests.post("http://localhost:8000/api/chat/stream",
                     json={"message": "你好", "history": []},
                     stream=True, timeout=60)
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("data: "):
            data_str = line[6:]
            if data_str == "[DONE]":
                print(f"  [{time.time()-start:.1f}s] [DONE]")
                break
            try:
                data = json.loads(data_str)
                t = data.get("type", "?")
                if t == "step":
                    phase = data.get("data", {}).get("phase", "?")
                    detail = data.get("data", {}).get("detail", "?")[:60]
                    print(f"  [{time.time()-start:.1f}s] STEP: {phase} - {detail}")
                elif t == "result":
                    resp = data.get("data", {}).get("response", "")[:100]
                    print(f"  [{time.time()-start:.1f}s] RESULT: {resp}")
            except:
                print(f"  [{time.time()-start:.1f}s] RAW: {data_str[:80]}")
    elapsed = time.time() - start
    print(f"\n耗时: {elapsed:.1f}s")
except Exception as e:
    elapsed = time.time() - start
    print(f"异常: {e} | 耗时: {elapsed:.1f}s")

time.sleep(2)
try:
    r = requests.get("http://localhost:8000/api/health", timeout=5)
    print(f"后端存活: {r.json()}")
except:
    print("后端已崩溃!")
    proc.terminate()
    try:
        remaining = proc.stdout.read().decode(errors='replace')
        for line in remaining.split('\n')[-30:]:
            if line.strip():
                print(f"  {line.strip()[:150]}")
    except:
        pass