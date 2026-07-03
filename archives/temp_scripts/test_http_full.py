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

queries = [
    ("简单问候", "你好"),
    ("事实性问题", "冰雹是怎么形成的"),
]

for label, query in queries:
    print(f"\n===== {label}: {query} =====")
    start = time.time()
    has_result = False
    step_count = 0
    try:
        r = requests.post("http://localhost:8000/api/chat/stream",
                         json={"message": query, "history": []},
                         stream=True, timeout=120)
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data_str = line[6:]
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
                t = data.get("type", "?")
                if t == "step":
                    step_count += 1
                    phase = data.get("phase", "?")
                    detail = data.get("detail", "?")[:50]
                    if step_count <= 5 or step_count % 5 == 0:
                        print(f"  [{time.time()-start:.1f}s] {phase} - {detail}")
                elif t == "result":
                    has_result = True
                    resp = data.get("response", "")[:100]
                    print(f"  [{time.time()-start:.1f}s] RESULT: {resp}...")
            except:
                pass
        elapsed = time.time() - start
        print(f"  => {'OK' if has_result else 'FAIL'} | {elapsed:.1f}s | {step_count} steps")
    except Exception as e:
        elapsed = time.time() - start
        print(f"  => EXCEPTION: {e} | {elapsed:.1f}s")
    
    time.sleep(2)
    try:
        r = requests.get("http://localhost:8000/api/health", timeout=5)
        print(f"  Backend: alive")
    except:
        print(f"  Backend: DEAD!")
        break

print("\nDone. Keeping backend alive for 10s...")
time.sleep(10)
proc.terminate()