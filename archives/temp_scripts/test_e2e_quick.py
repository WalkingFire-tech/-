import requests, json, time

queries = [
    ("简单问候", "你好"),
    ("事实性问题", "冰雹是怎么形成的"),
    ("建议性问题", "五年级升六年级暑假建议"),
]

for label, query in queries:
    print(f"\n===== 测试: {label} =====")
    print(f"查询: {query}")
    start = time.time()
    try:
        r = requests.post("http://localhost:8000/api/chat/stream",
                         json={"message": query, "history": []},
                         stream=True, timeout=180)
        result_text = ""
        step_count = 0
        has_result = False
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
                    if step_count <= 5:
                        phase = data.get("phase", "?")
                        detail = data.get("detail", "?")[:60]
                        print(f"  步骤: {phase} - {detail}")
                elif data.get("type") == "result":
                    has_result = True
                    resp = data.get("response", "")
                    result_text = resp[:200]
            except:
                pass
        elapsed = time.time() - start
        status = "OK" if has_result else "FAIL"
        print(f"  结果: {status} | 耗时: {elapsed:.1f}s | 步骤数: {step_count}")
        if result_text:
            print(f"  回复: {result_text}...")
        else:
            print(f"  回复: (无)")
    except Exception as e:
        elapsed = time.time() - start
        print(f"  异常: {e} | 耗时: {elapsed:.1f}s")