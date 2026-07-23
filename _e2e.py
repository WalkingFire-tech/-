import subprocess, time, urllib.request, sys, json, re

p = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.main_fast:app", "--host", "127.0.0.1", "--port", "8000"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)

ready = False
for i in range(20):
    time.sleep(5)
    try:
        r = urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=3)
        if r.status == 200:
            print(f"READY in {(i+1)*5}s")
            ready = True
            break
    except:
        pass

if not ready:
    print("FAIL: server not ready")
    p.terminate()
    sys.exit(1)

tests = [
    ("1+1等于几", "simple"),
    ("自我提升知识能力的途径有哪些", "complex"),
]

for msg, label in tests:
    data = json.dumps({"message": msg, "conversation_id": f"e2e_{label}"}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/chat/stream",
        data=data, headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        r = urllib.request.urlopen(req, timeout=90)
        full = r.read().decode()
        has_result = '"type": "result"' in full or '"type":"result"' in full
        is_fallback = "永不放弃" in full or "敷衍性语言" in full
        has_deepseek = "DeepSeek" in full
        types = re.findall(r'"type":\s*"([^"]+)"', full)
        resp = ""
        if has_result:
            idx = full.find('"response"')
            if idx >= 0:
                resp = full[idx+12:idx+212].replace("\\n", " ")[:150]
        status = "FALLBACK" if is_fallback else ("OK" if has_result else "NO_RESULT")
        print(f"[{label}] {status} | len={len(full)} deepseek={has_deepseek} types={types[:8]}")
        if resp:
            print(f"  resp: {resp[:120]}")
    except Exception as e:
        print(f"[{label}] ERROR: {e}")

p.terminate()
print("DONE")