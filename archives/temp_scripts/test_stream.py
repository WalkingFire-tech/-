import asyncio
import time
from backend.chat_stream import chat_stream

async def t():
    s = time.time()
    async for chunk in chat_stream('test', {}):
        print(f'{time.time()-s:.1f}s: {chunk[:100]}')

asyncio.run(t())
