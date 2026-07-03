from pathlib import Path

ROOT_DIR = Path('.')
frontend_index = ROOT_DIR / 'frontend' / 'index.html'

print(f'ROOT_DIR: {ROOT_DIR.absolute()}')
print(f'frontend_index: {frontend_index.absolute()}')
print(f'exists: {frontend_index.exists()}')

if frontend_index.exists():
    with open(frontend_index, 'r', encoding='utf-8') as f:
        content = f.read(100)
    print(f'content preview: {content[:50]}...')
else:
    print('ERROR: frontend/index.html not found!')