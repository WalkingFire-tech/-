import asyncio
import time
from backend.chat_stream import _fetch_experience, _fetch_knowledge, _fetch_fact_assertions

async def test():
    query = "冰雹是怎么形成的"
    
    print(f"Testing fast paths with: {query}")
    start = time.time()
    
    exp_task = asyncio.create_task(_fetch_experience(query))
    know_task = asyncio.create_task(_fetch_knowledge(query))
    fact_task = asyncio.create_task(_fetch_fact_assertions(query))
    
    print(f"  [{time.time()-start:.1f}s] Tasks created, gathering...")
    
    try:
        fast_results = await asyncio.wait_for(
            asyncio.gather(exp_task, know_task, fact_task, return_exceptions=True),
            timeout=30
        )
        print(f"  [{time.time()-start:.1f}s] Gather done")
        for i, r in enumerate(fast_results):
            name = ["exp", "know", "fact"][i]
            if isinstance(r, Exception):
                print(f"    {name}: EXCEPTION: {r}")
            elif r:
                print(f"    {name}: OK, len={len(r.get('response',''))}")
            else:
                print(f"    {name}: None")
    except asyncio.TimeoutError:
        print(f"  [{time.time()-start:.1f}s] GATHER TIMEOUT!")
    
    elapsed = time.time() - start
    print(f"\nDone: {elapsed:.1f}s")

asyncio.run(test())