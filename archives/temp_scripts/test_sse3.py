import requests, json
r = requests.post('http://localhost:8000/api/chat/stream', json={'message':'写一个冒泡排序'}, stream=True, timeout=120)
result_event = None
step_count = 0
for line in r.iter_lines(decode_unicode=True):
    if line and line.startswith('data: '):
        json_str = line[6:].strip()
        if json_str:
            try:
                event = json.loads(json_str)
                if event.get('type') == 'step':
                    step_count += 1
                elif event.get('type') == 'result':
                    result_event = event
                    resp = event.get('response', '')
                    print(f"Steps: {step_count}")
                    print(f"Result length: {len(resp)} chars")
                    print(f"Last 200 chars: {repr(resp[-200:])}")
            except Exception as e:
                print(f"JSON parse error: {e}, line[:100]={line[:100]}")
if not result_event:
    print("No result event received!")