import asyncio
import time
from backend.chat_stream import _fetch_ollama

async def test():
    query = "冰雹是怎么形成的"
    model = "qwen2.5-coder:7b"
    print(f"Testing _fetch_ollama with: {query}, model: {model}")
    start = time.time()
    try:
        result = await asyncio.wait_for(
            _fetch_ollama(query, model, timeout=60),
            timeout=90
        )
        elapsed = time.time() - start
        if result:
            print(f"OK: {elapsed:.1f}s, response: {result['response'][:100]}...")
        else:
            print(f"NO RESULT: {elapsed:.1f}s")
    except asyncio.TimeoutError:
        elapsed = time.time() - start
        print(f"TIMEOUT: {elapsed:.1f}s")
    except Exception as e:
        elapsed = time.time() - start
        print(f"ERROR: {e}, {elapsed:.1f}s")

asyncio.run(test())