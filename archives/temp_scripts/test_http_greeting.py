import requests, json, time

start = time.time()
r = requests.post('http://localhost:8000/api/chat/stream',
                  json={'message': '你好', 'history': []},
                  stream=True, timeout=30)
for line in r.iter_lines(decode_unicode=True):
    if line:
        elapsed = time.time() - start
        print(f'[{elapsed:.1f}s] {line[:100]}')
print(f'Done: {time.time()-start:.1f}s')