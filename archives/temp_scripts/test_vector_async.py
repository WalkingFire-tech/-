import time
import asyncio
import concurrent.futures

executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

async def test():
    print("Test: VectorRetriever init in executor...")
    start = time.time()
    try:
        from infrastructure.vector_retriever import VectorRetriever
        loop = asyncio.get_event_loop()
        retriever = await asyncio.wait_for(
            loop.run_in_executor(executor, VectorRetriever),
            timeout=15
        )
        print(f"  Init OK: {time.time()-start:.1f}s")
        
        print("Test: search_similar in executor...")
        start2 = time.time()
        results = await asyncio.wait_for(
            loop.run_in_executor(executor, lambda: retriever.search_similar("冰雹是怎么形成的", k=3, threshold=0.6)),
            timeout=10
        )
        print(f"  Search OK: {time.time()-start2:.1f}s, results={len(results) if results else 0}")
    except asyncio.TimeoutError:
        print(f"  TIMEOUT: {time.time()-start:.1f}s")
    except Exception as e:
        print(f"  ERROR: {e}, {time.time()-start:.1f}s")
        import traceback
        traceback.print_exc()

asyncio.run(test())