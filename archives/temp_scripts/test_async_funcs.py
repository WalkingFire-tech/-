import asyncio
from backend.chat_stream import _diagnose_ollama_status, _get_available_ollama_models_async, _get_available_ollama_model_async

async def test():
    print("Testing _get_available_ollama_models_async...")
    models = await _get_available_ollama_models_async()
    print(f"Models: {models}")
    
    print("Testing _get_available_ollama_model_async...")
    model = await _get_available_ollama_model_async()
    print(f"Model: {model}")
    
    print("Testing _diagnose_ollama_status...")
    diag = await _diagnose_ollama_status()
    print(f"Diagnosis: {diag}")

asyncio.run(test())