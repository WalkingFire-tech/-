# 无CUDA环境使用LoRA模型指南

## 问题说明

训练好的LoRA模型**可以在CPU上运行**，只是推理速度较慢。

---

## 解决方案对比

### 方案1: CPU推理（最简单）✅

**优点**:
- 无需额外硬件
- 配置简单
- 立即可用

**缺点**:
- 速度慢（约10-30秒/次）
- 需要较大内存（约16GB）

**使用方法**:
```python
from adapters.llm.lora_adapter import create_lora_adapter

# 自动检测CPU/GPU
adapter = create_lora_adapter()
response = adapter.generate("你的问题")
```

**预期性能**:
- 首次加载: 2-5分钟（加载模型）
- 单次推理: 10-30秒
- 内存占用: 约15GB

---

### 方案2: 云端推理（推荐）✅

**使用AutoDL或其他云平台进行推理**

**优点**:
- 速度快（约1-2秒/次）
- 成本低（约¥0.5/小时）
- 无需本地GPU

**步骤**:
1. 启动AutoDL实例（RTX 4090约¥1.5/小时）
2. 上传LoRA权重
3. 运行推理服务
4. 本地通过API调用

**推理服务脚本**:
```python
# 在AutoDL上运行
from fastapi import FastAPI
from adapters.llm.lora_adapter import create_lora_adapter

app = FastAPI()
adapter = create_lora_adapter()

@app.post("/generate")
def generate(prompt: str):
    return {"response": adapter.generate(prompt)}
```

---

### 方案3: 量化推理（折中）✅

**使用4bit/8bit量化减少内存占用**

**优点**:
- 内存占用小（约4-8GB）
- 速度较快
- 可在CPU上运行

**配置**:
```python
adapter = create_lora_adapter(
    load_in_8bit=True  # 8bit量化
)
```

---

### 方案4: 使用Ollama（替代方案）✅

**将LoRA模型导出为GGUF格式，用Ollama运行**

**优点**:
- CPU推理速度快
- 内存占用小
- 集成简单

**步骤**:
1. 合并LoRA权重到基础模型
2. 转换为GGUF格式
3. 用Ollama加载

---

## 推荐方案

### 如果你只是测试效果
→ **方案1: CPU推理**（慢但能用）

### 如果要长期使用
→ **方案2: 云端推理**（快且便宜）

### 如果内存不足
→ **方案3: 量化推理**（折中方案）

---

## CPU推理使用指南

### 1. 安装依赖
```bash
pip install transformers peft torch --index-url https://download.pytorch.org/whl/cpu
```

### 2. 运行测试
```python
from adapters.llm.lora_adapter import create_lora_adapter

print("加载模型（首次需要2-5分钟）...")
adapter = create_lora_adapter()

print("开始推理...")
response = adapter.generate("什么是深度学习的特点？")
print(f"回答: {response}")
```

### 3. 性能优化建议

**减少生成长度**:
```python
response = adapter.generate(prompt, max_new_tokens=128)  # 默认512
```

**使用批处理**:
```python
prompts = ["问题1", "问题2", "问题3"]
responses = [adapter.generate(p, max_new_tokens=64) for p in prompts]
```

---

## 云端推理快速部署

### AutoDL推理脚本

```python
# inference_server.py
from fastapi import FastAPI
from pydantic import BaseModel
from adapters.llm.lora_adapter import create_lora_adapter
import uvicorn

app = FastAPI()
adapter = create_lora_adapter()

class Request(BaseModel):
    prompt: str
    max_tokens: int = 256

@app.post("/generate")
def generate(req: Request):
    return {"response": adapter.generate(req.prompt, max_new_tokens=req.max_tokens)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 本地调用
```python
import requests

def call_lora(prompt):
    resp = requests.post(
        "http://<AutoDL-IP>:8000/generate",
        json={"prompt": prompt}
    )
    return resp.json()["response"]
```

---

## 成本对比

| 方案 | 成本 | 速度 | 内存 |
|------|------|------|------|
| CPU推理 | 免费 | 慢(30s) | 15GB |
| 云端推理 | ¥0.5-1.5/小时 | 快(1-2s) | 云端 |
| 量化推理 | 免费 | 中(10s) | 4-8GB |
| Ollama | 免费 | 快(2-5s) | 4GB |

---

## 结论

**训练的LoRA模型绝对有用！**

即使没有本地GPU，你也可以：
1. ✅ 使用CPU推理（慢但能用）
2. ✅ 使用云端推理（快且便宜）
3. ✅ 使用量化推理（折中方案）
4. ✅ 转换为Ollama格式（CPU优化）

**推荐**: 使用云端推理（AutoDL），成本约¥0.5-1.5/小时，速度快，体验好。