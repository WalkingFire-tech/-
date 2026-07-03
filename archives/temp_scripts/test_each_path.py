import asyncio
import time

async def test():
    query = "冰雹是怎么形成的"
    
    print("Test 1: _fetch_experience...")
    start = time.time()
    try:
        from backend.chat_stream import _fetch_experience
        result = await asyncio.wait_for(_fetch_experience(query), timeout=10)
        print(f"  OK: {time.time()-start:.1f}s, result={result is not None}")
    except asyncio.TimeoutError:
        print(f"  TIMEOUT: {time.time()-start:.1f}s")
    except Exception as e:
        print(f"  ERROR: {e}, {time.time()-start:.1f}s")
    
    print("Test 2: _fetch_knowledge...")
    start = time.time()
    try:
        from backend.chat_stream import _fetch_knowledge
        result = await asyncio.wait_for(_fetch_knowledge(query), timeout=10)
        print(f"  OK: {time.time()-start:.1f}s, result={result is not None}")
    except asyncio.TimeoutError:
        print(f"  TIMEOUT: {time.time()-start:.1f}s")
    except Exception as e:
        print(f"  ERROR: {e}, {time.time()-start:.1f}s")
    
    print("Test 3: _fetch_fact_assertions...")
    start = time.time()
    try:
        from backend.chat_stream import _fetch_fact_assertions
        result = await asyncio.wait_for(_fetch_fact_assertions(query), timeout=10)
        print(f"  OK: {time.time()-start:.1f}s, result={result is not None}")
    except asyncio.TimeoutError:
        print(f"  TIMEOUT: {time.time()-start:.1f}s")
    except Exception as e:
        print(f"  ERROR: {e}, {time.time()-start:.1f}s")

asyncio.run(test())