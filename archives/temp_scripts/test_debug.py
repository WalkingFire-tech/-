import requests, json, time

query = "冰雹是怎么形成的"
print(f"测试: {query}")
start = time.time()
try:
    r = requests.post("http://localhost:8000/api/chat/stream",
                     json={"message": query, "history": []},
                     stream=True, timeout=300)
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
                print(f"  [{time.time()-start:.1f}s] type={data.get('type','?')} | {json.dumps(data, ensure_ascii=False)[:120]}")
            except:
                print(f"  [{time.time()-start:.1f}s] RAW: {data_str[:120]}")
        else:
            print(f"  [{time.time()-start:.1f}s] LINE: {line[:120]}")
    elapsed = time.time() - start
    print(f"\n耗时: {elapsed:.1f}s")
except Exception as e:
    elapsed = time.time() - start
    print(f"异常: {e} | 耗时: {elapsed:.1f}s")