import time

print("Test 1: Import sentence_transformers...")
start = time.time()
try:
    from sentence_transformers import SentenceTransformer
    print(f"  Import OK: {time.time()-start:.1f}s")
except Exception as e:
    print(f"  Import FAILED: {e}, {time.time()-start:.1f}s")
    print("  Skipping model load test")
    exit(0)

print("Test 2: Load model...")
start = time.time()
try:
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    print(f"  Load OK: {time.time()-start:.1f}s")
except Exception as e:
    print(f"  Load FAILED: {e}, {time.time()-start:.1f}s")