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
            print(f"[{i+1}s] Health: {r.json()}")
            break
    except:
        pass

queries = [
    ("简单问候", "你好"),
    ("事实性问题", "冰雹是怎么形成的"),
    ("建议性问题", "五年级升六年级暑假建议"),
]

for label, query in queries:
    print(f"\n===== 测试: {label} =====")
    print(f"查询: {query}")
    start = time.time()
    has_result = False
    step_count = 0
    result_text = ""
    try:
        r = requests.post("http://localhost:8000/api/chat/stream",
                         json={"message": query, "history": []},
                         stream=True, timeout=180)
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
                    detail = data.get("detail", "?")[:60]
                    if step_count <= 8:
                        print(f"  [{time.time()-start:.1f}s] {phase} - {detail}")
                elif t == "result":
                    has_result = True
                    resp = data.get("response", "")[:200]
                    result_text = resp
                    print(f"  [{time.time()-start:.1f}s] RESULT!")
            except:
                pass
        elapsed = time.time() - start
        status = "OK" if has_result else "FAIL"
        print(f"  结果: {status} | 耗时: {elapsed:.1f}s | 步骤: {step_count}")
        if result_text:
            print(f"  回复: {result_text[:150]}...")
    except Exception as e:
        elapsed = time.time() - start
        print(f"  异常: {e} | 耗时: {elapsed:.1f}s")
    
    time.sleep(2)
    try:
        r = requests.get("http://localhost:8000/api/health", timeout=5)
        print(f"  后端状态: OK")
    except:
        print(f"  后端状态: 崩溃!")
        break

proc.terminate()