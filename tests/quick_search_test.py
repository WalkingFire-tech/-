"""快速测试搜索功能"""
import threading

print("\n测试ddgs搜索...")

search_results = None

def search_task():
    global search_results
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            search_results = list(ddgs.text('二十四节气', max_results=3))
    except Exception as e:
        print(f"错误: {e}")

thread = threading.Thread(target=search_task, daemon=True)
thread.start()
thread.join(timeout=10)

if thread.is_alive():
    print("❌ 搜索超时（10秒）")
elif search_results:
    print(f"✅ 搜索成功: {len(search_results)}条")
    for i, sr in enumerate(search_results, 1):
        print(f"\n{i}. {sr.get('title', '无标题')}")
        print(f"   {sr.get('body', '')[:150]}...")
else:
    print("❌ 无搜索结果")