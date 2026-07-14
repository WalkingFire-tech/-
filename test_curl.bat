@echo off
curl -X POST http://127.0.0.1:11434/api/chat -H "Content-Type: application/json" -d "{\"model\":\"gemma-4-12B\",\"messages\":[{\"role\":\"user\",\"content\":\"1+1\"}]}"