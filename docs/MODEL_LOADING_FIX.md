# 模型加载问题修复报告

## 问题

用户有3个Ollama模型，但系统只识别到2个：
```
ollama list:
- qwen2.5-coder:1.5b
- deepcoder:latest  ← 缺失
- mindchat:latest
```

## 原因

`backend/main.py`只尝试加载了2个Ollama模型：
- mindchat
- qwen2.5-coder:1.5b

缺少`deepcoder:latest`的加载代码。

## 解决方案

在`backend/main.py`中添加deepcoder加载：

```python
# 修改前
try:
    adapters["code_light"] = OllamaAdapter(model_name="qwen2.5-coder:1.5b")
    logger.info("Loaded code model")
except Exception as e:
    logger.warning(f"Code model unavailable: {e}")

# 修改后
try:
    adapters["code_light"] = OllamaAdapter(model_name="qwen2.5-coder:1.5b")
    logger.info("Loaded code_light (qwen2.5-coder:1.5b)")
except Exception as e:
    logger.warning(f"Code light model unavailable: {e}")

try:
    adapters["deepcoder"] = OllamaAdapter(model_name="deepcoder")
    logger.info("Loaded DeepCoder")
except Exception as e:
    logger.warning(f"DeepCoder unavailable: {e}")
```

## 验证结果

```
测试加载Ollama模型:
✓ mindchat 加载成功
✓ qwen2.5-coder:1.5b 加载成功
✓ deepcoder 加载成功

成功加载: 3个模型
```

## 当前模型配置

### Ollama模型（本地）

| 别名 | 模型名称 | 大小 | 用途 |
|------|----------|------|------|
| mindchat | mindchat:latest | 3.7 GB | 心理咨询、情感对话 |
| code_light | qwen2.5-coder:1.5b | 986 MB | 轻量级代码生成 |
| deepcoder | deepcoder:latest | 9.0 GB | 专业代码生成 |

### 远程模型（可选）

| 别名 | 模型名称 | 条件 |
|------|----------|------|
| remote_gpt4 | gpt-4o-mini | OPENAI_API_KEY存在 |
| deepseek-chat | deepseek-chat | DEEPSEEK_API_KEY或OPENAI_API_KEY存在 |

## 模型选择建议

### 代码任务
- **轻量快速**: code_light (qwen2.5-coder:1.5b) - 986MB
- **专业深度**: deepcoder - 9.0GB

### 对话任务
- **心理咨询**: mindchat - 3.7GB
- **通用对话**: remote_gpt4 或 deepseek-chat

### 路由策略
系统会根据统计库自动选择最佳模型：
- 质量、速度、成本权重可配置
- 用户可在前端手动选择模型
- 支持自动选择模式

## 启动后验证

重启后端服务后，访问 `/api/models` 应看到：

```json
{
  "models": [
    {"name": "mindchat", "type": "OllamaAdapter"},
    {"name": "code_light", "type": "OllamaAdapter"},
    {"name": "deepcoder", "type": "OllamaAdapter"},
    // 如果配置了API密钥
    {"name": "remote_gpt4", "type": "RemoteAdapter"},
    {"name": "deepseek-chat", "type": "RemoteAdapter"}
  ]
}
```

## 总结

✅ 已添加deepcoder模型加载  
✅ 所有3个Ollama模型都能成功加载  
✅ 后端配置已更新  
✅ 前端模型选择器将显示所有模型  

**重启后端服务即可生效。**