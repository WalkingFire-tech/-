import time
import threading

def test_vector():
    print(f"[{threading.current_thread().name}] Starting VectorRetriever init...")
    start = time.time()
    try:
        from infrastructure.vector_retriever import VectorRetriever
        print(f"[{time.time()-start:.1f}s] Import done")
        retriever = VectorRetriever()
        print(f"[{time.time()-start:.1f}s] Init done")
        results = retriever.search_similar("冰雹", k=3, threshold=0.6)
        print(f"[{time.time()-start:.1f}s] Search done, results={len(results) if results else 0}")
    except Exception as e:
        print(f"[{time.time()-start:.1f}s] ERROR: {e}")

import concurrent.futures
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
future = executor.submit(test_vector)
print("Submitted to executor, waiting (max 30s)...")
try:
    future.result(timeout=30)
    print("Done!")
except concurrent.futures.TimeoutError:
    print("TIMEOUT after 30s!")
except Exception as e:
    print(f"ERROR: {e}")