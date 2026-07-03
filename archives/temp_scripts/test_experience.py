"""端到端体验测试 - 深入体验系统表现"""
import requests
import json
import time

BASE = "http://localhost:8000"

def test_stream(query, timeout=180):
    """测试流式聊天，记录完整过程"""
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}")
    
    start = time.time()
    phases = []
    final_response = ""
    has_result = False
    
    try:
        r = requests.post(f"{BASE}/api/chat/stream",
            json={"message": query, "context": {}},
            headers={"Accept": "text/event-stream"},
            stream=True, timeout=timeout)
        
        for line in r.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    if data.get("type") == "step":
                        phase = data.get("phase", "")
                        detail = data.get("detail", "")
                        status = data.get("status", "")
                        phases.append((phase, status, detail))
                        if status in ("done", "progress"):
                            print(f"  [{phase}] {detail[:80]}")
                    elif data.get("type") == "result":
                        final_response = data.get("response", "")
                        has_result = True
                except:
                    pass
    except requests.exceptions.Timeout:
        print(f"  TIMEOUT after {timeout}s")
    except Exception as e:
        print(f"  ERROR: {str(e)[:80]}")
    
    elapsed = time.time() - start
    
    print(f"\n--- Result ({elapsed:.1f}s) ---")
    print(f"  Has result: {has_result}")
    print(f"  Phases: {len(phases)}")
    print(f"  Response length: {len(final_response)}")
    if final_response:
        print(f"  Preview: {final_response[:200]}")
    
    # 质量检查
    template_kws = ["问题本质分析", "多角度审视", "关键变量识别", "我的深度思考"]
    found_templates = [kw for kw in template_kws if kw in final_response]
    if found_templates:
        print(f"  WARNING: 检测到模板化内容: {found_templates}")
    
    return {
        "query": query,
        "elapsed": elapsed,
        "has_result": has_result,
        "phases": len(phases),
        "response_len": len(final_response),
        "template_detected": bool(found_templates),
        "response": final_response[:500],
    }

# 测试用例
results = []

# 1. 简单问候
results.append(test_stream("你好", timeout=30))

# 2. 事实性问题
results.append(test_stream("冰雹是怎么形成的", timeout=120))

# 3. 复杂建议类
results.append(test_stream("五年级升六年级暑假建议", timeout=180))

# 汇总
print(f"\n{'='*60}")
print("体验汇总")
print(f"{'='*60}")
for r in results:
    status = "OK" if r["has_result"] and not r["template_detected"] else "ISSUE"
    print(f"  [{status}] {r['query'][:20]}: {r['elapsed']:.1f}s, {r['phases']} phases, {r['response_len']} chars, template={r['template_detected']}")