import asyncio
import time

async def test():
    loop = asyncio.get_event_loop()
    
    def slow_func():
        time.sleep(20)
        return "done"
    
    # run_in_executor returns a coroutine, not a future
    task = loop.run_in_executor(None, slow_func)
    
    done, pending = await asyncio.wait({task}, timeout=3.0)
    print(f"After 3s: done={len(done)}, pending={len(pending)}")
    
    # Is event loop still responsive?
    start = time.time()
    await asyncio.sleep(0.1)
    print(f"Event loop responsive: {time.time()-start < 1.0}")
    
    if pending:
        t = pending.pop()
        t.cancel()
        try:
            await t
        except (asyncio.CancelledError, Exception):
            print("Task cancelled (thread still running in background but event loop is free)")
    
    print("Event loop is FREE - can process new requests")

asyncio.run(test())
