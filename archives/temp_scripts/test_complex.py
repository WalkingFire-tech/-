import requests, json, time

query = "冰雹是怎么形成的"
print(f"测试: {query}")
start = time.time()
try:
    r = requests.post("http://localhost:8000/api/chat/stream",
                     json={"message": query, "history": []},
                     stream=True, timeout=300)
    step_count = 0
    has_result = False
    result_text = ""
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        data_str = line[6:]
        if data_str == "[DONE]":
            break
        try:
            data = json.loads(data_str)
            if data.get("type") == "step":
                step_count += 1
                phase = data.get("data", {}).get("phase", "?")
                detail = data.get("data", {}).get("detail", "?")[:80]
                print(f"  [{time.time()-start:.1f}s] 步骤: {phase} - {detail}")
            elif data.get("type") == "result":
                has_result = True
                resp = data.get("data", {}).get("response", "")
                result_text = resp[:300]
                print(f"  [{time.time()-start:.1f}s] 结果到达!")
        except:
            pass
    elapsed = time.time() - start
    status = "OK" if has_result else "FAIL"
    print(f"\n结果: {status} | 耗时: {elapsed:.1f}s | 步骤数: {step_count}")
    if result_text:
        print(f"回复: {result_text}...")
except Exception as e:
    elapsed = time.time() - start
    print(f"异常: {e} | 耗时: {elapsed:.1f}s")