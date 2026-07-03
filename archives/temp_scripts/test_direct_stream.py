import asyncio
import time
import json

async def test():
    from backend.chat_stream import chat_stream
    
    query = "冰雹是怎么形成的"
    print(f"Testing chat_stream directly: {query}")
    start = time.time()
    step_count = 0
    has_result = False
    result_text = ""
    
    try:
        async for chunk in chat_stream(query, {"history": []}):
            elapsed = time.time() - start
            if elapsed > 120:
                print(f"  [{elapsed:.1f}s] TIMEOUT! Breaking...")
                break
            
            if chunk.startswith("data: "):
                data_str = chunk[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    t = data.get("type", "?")
                    if t == "step":
                        step_count += 1
                        phase = data.get("phase", "?")
                        detail = data.get("detail", "?")[:60]
                        if step_count <= 15 or step_count % 10 == 0:
                            print(f"  [{elapsed:.1f}s] STEP #{step_count}: {phase} - {detail}")
                    elif t == "result":
                        has_result = True
                        resp = data.get("response", "")[:200]
                        result_text = resp
                        print(f"  [{elapsed:.1f}s] RESULT!")
                except:
                    pass
    except Exception as e:
        elapsed = time.time() - start
        print(f"  [{elapsed:.1f}s] EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
    
    elapsed = time.time() - start
    status = "OK" if has_result else "FAIL"
    print(f"\n结果: {status} | 耗时: {elapsed:.1f}s | 步骤: {step_count}")
    if result_text:
        print(f"回复: {result_text[:150]}...")

asyncio.run(test())