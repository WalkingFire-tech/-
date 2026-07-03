import time

print("Test: import backend.main_fast...")
start = time.time()
try:
    from backend.main_fast import _executor
    print(f"  OK: {time.time()-start:.1f}s, executor={_executor}")
except Exception as e:
    print(f"  ERROR: {e}, {time.time()-start:.1f}s")
    import traceback
    traceback.print_exc()