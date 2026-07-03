import asyncio
import time
from backend.chat_stream import (
    _fetch_experience, _fetch_knowledge, _fetch_ollama_all,
    _fetch_external_api, _fetch_external_learning, _fetch_fact_assertions, _self_reason
)

async def test():
    query = "冰雹是怎么形成的"
    conv_ctx = ""
    truth = ""
    
    print(f"Testing 8-path parallel with: {query}")
    start = time.time()
    
    exp_task = asyncio.create_task(_fetch_experience(query))
    know_task = asyncio.create_task(_fetch_knowledge(query))
    ollama_task = asyncio.create_task(_fetch_ollama_all(query, conversation_context=conv_ctx, truth_insights=truth))
    ext_task = asyncio.create_task(_fetch_external_api(query, conversation_context=conv_ctx, truth_insights=truth))
    ext_learn_task = asyncio.create_task(_fetch_external_learning(query, conv_ctx))
    fact_task = asyncio.create_task(_fetch_fact_assertions(query))
    self_reason_task = asyncio.create_task(_self_reason(query, conv_ctx, truth))
    
    print(f"  [{time.time()-start:.1f}s] All tasks created")
    
    fast_results = await asyncio.gather(exp_task, know_task, fact_task, return_exceptions=True)
    print(f"  [{time.time()-start:.1f}s] Fast results gathered")
    
    for i, r in enumerate(fast_results):
        name = ["exp", "know", "fact"][i]
        if isinstance(r, Exception):
            print(f"    {name}: EXCEPTION: {r}")
        elif r:
            print(f"    {name}: OK, response[:50]={r.get('response','')[:50]}")
        else:
            print(f"    {name}: None")
    
    pending = {ollama_task: "ollama", ext_task: "ext", ext_learn_task: "ext_learn", self_reason_task: "self_reason"}
    pending_set = set(pending.keys())
    
    while pending_set:
        print(f"  [{time.time()-start:.1f}s] Waiting for: {[pending[t] for t in pending_set]}")
        done, pending_set = await asyncio.wait(pending_set, timeout=5.0, return_when=asyncio.FIRST_COMPLETED)
        for d in done:
            name = pending.get(d, "?")
            try:
                result = d.result()
                if isinstance(result, list):
                    items = [r for r in result if isinstance(r, dict) and r.get("response")]
                    print(f"  [{time.time()-start:.1f}s] {name}: {len(items)} results")
                elif isinstance(result, dict) and result.get("response"):
                    print(f"  [{time.time()-start:.1f}s] {name}: OK, response[:50]={result['response'][:50]}")
                else:
                    print(f"  [{time.time()-start:.1f}s] {name}: None")
            except Exception as e:
                print(f"  [{time.time()-start:.1f}s] {name}: EXCEPTION: {e}")
        
        if time.time() - start > 120:
            print(f"  [{time.time()-start:.1f}s] TIMEOUT! Breaking...")
            for t in pending_set:
                t.cancel()
            break
    
    elapsed = time.time() - start
    print(f"\nDone: {elapsed:.1f}s")

asyncio.run(test())