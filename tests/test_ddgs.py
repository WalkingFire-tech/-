from ddgs import DDGS
with DDGS() as ddgs:
    results = list(ddgs.text('一年有多少个节气', max_results=3))
    print(f'搜索成功: {len(results)}条')
    if results:
        print(f'第一条: {results[0].get("title", "无标题")}')
        print(f'内容: {results[0].get("body", "")[:200]}')