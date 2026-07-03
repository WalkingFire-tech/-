import requests, json
r = requests.post('http://localhost:8000/api/chat/stream', json={'message':'写一个hello world函数'}, stream=True, timeout=60)
for line in r.iter_lines(decode_unicode=True):
    if line:
        print(repr(line[:200]))