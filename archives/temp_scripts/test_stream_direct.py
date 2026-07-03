import asyncio
import time
from backend.chat_stream import chat_stream

async def test():
    query = "冰雹是怎么形成的"
    print(f"Testing chat_stream with: {query}")
    start = time.time()
    step_count = 0
    has_result = False
    try:
        async for chunk in chat_stream(query, {"history": []}):
            elapsed = time.time() - start
            if '"type": "step"' in chunk:
                step_count += 1
                if step_count <= 10:
                    print(f"  [{elapsed:.1f}s] STEP chunk")
            elif '"type": "result"' in chunk:
                has_result = True
                print(f"  [{elapsed:.1f}s] RESULT chunk")
            if step_count % 20 == 0 and step_count > 0:
                print(f"  [{elapsed:.1f}s] ... {step_count} steps so far")
    except Exception as e:
        elapsed = time.time() - start
        print(f"  [{elapsed:.1f}s] EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
    
    elapsed = time.time() - start
    print(f"\nDone: result={'YES' if has_result else 'NO'}, steps={step_count}, time={elapsed:.1f}s")

asyncio.run(test())