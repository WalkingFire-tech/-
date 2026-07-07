import re

with open('backend/chat_stream.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines, 1):
    stripped = line.strip()
    if 'except' in stripped and ('pass' in stripped or 'return None' in stripped):
        # find enclosing function
        func = "?"
        for j in range(i-1, max(0, i-30), -1):
            m = re.match(r'\s*(async )?def (\w+)', lines[j-1])
            if m:
                func = m.group(2)
                break
        print(f"L{i}: {stripped[:80]}  [{func}]")