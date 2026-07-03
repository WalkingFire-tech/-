import asyncio
import time

async def test():
    query = "冰雹是怎么形成的"
    
    print("Test: _fetch_experience ONLY...")
    start = time.time()
    try:
        from backend.chat_stream import _fetch_experience
        print(f"  Imported, calling...")
        result = await asyncio.wait_for(_fetch_experience(query), timeout=10)
        print(f"  OK: {time.time()-start:.1f}s, result={result is not None}")
    except asyncio.TimeoutError:
        print(f"  TIMEOUT: {time.time()-start:.1f}s")
    except Exception as e:
        import traceback
        print(f"  ERROR: {e}, {time.time()-start:.1f}s")
        traceback.print_exc()

asyncio.run(test())