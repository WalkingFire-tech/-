import requests, json
r = requests.post('http://localhost:8000/api/chat/stream', json={'message':'hello'}, stream=True, timeout=60)
result_event = None
for line in r.iter_lines(decode_unicode=True):
    if line and line.startswith('data: '):
        json_str = line[6:].strip()
        if json_str:
            try:
                event = json.loads(json_str)
                if event.get('type') == 'result':
                    result_event = event
                    resp = event.get('response', '')
                    print(f"Result length: {len(resp)} chars")
                    print(f"Last 100 chars: {resp[-100:]}")
            except:
                pass
if not result_event:
    print("No result event received!")