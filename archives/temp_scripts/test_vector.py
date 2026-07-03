import time

print("Test: VectorRetriever initialization...")
start = time.time()
try:
    from infrastructure.vector_retriever import VectorRetriever
    print(f"  Import: {time.time()-start:.1f}s")
    retriever = VectorRetriever()
    print(f"  Init: {time.time()-start:.1f}s")
    results = retriever.search_similar("冰雹是怎么形成的", k=3, threshold=0.6)
    print(f"  Search: {time.time()-start:.1f}s, results={len(results) if results else 0}")
except Exception as e:
    print(f"  ERROR: {e}, {time.time()-start:.1f}s")
    import traceback
    traceback.print_exc()