import requests, json
r = requests.post('http://localhost:8000/api/chat/stream', json={'message':'给我写一段二分查找的代码，我要在STM32单片机上运行'}, stream=True, timeout=120)
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
                    if len(resp) > 200:
                        print(f"Last 200 chars: {repr(resp[-200:])}")
                    else:
                        print(f"Full: {resp}")
            except Exception as e:
                print(f"JSON parse error: {e}")
if not result_event:
    print("No result event received!")