import asyncio
import time
from backend.chat_stream import chat_stream

async def t():
    s = time.time()
    count = 0
    async for chunk in chat_stream('test', {}):
        count += 1
        elapsed = time.time() - s
        print(f'{elapsed:.1f}s #{count}: {chunk[:100]}')
        if count > 20 or elapsed > 25:
            print('BREAK: too many chunks or too slow')
            break

asyncio.run(t())
