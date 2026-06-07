# DeepSeek API 接入指南

## 概述

联盟拓荒者现已支持DeepSeek API,包括:
- **DeepSeek Chat** - 通用对话模型,适合日常对话和问答
- **DeepSeek Coder** - 代码专用模型,适合代码生成和编程任务

## 快速开始

### 1. 获取DeepSeek API Key

访问 [DeepSeek官网](https://www.deepseek.com/) 注册并获取API Key。

### 2. 配置环境变量

#### 方法一: 使用.env文件(推荐)

1. 复制环境变量示例文件:
```bash
cp .env.example .env
```

2. 编辑`.env`文件,填入你的DeepSeek API Key:
```env
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
```

#### 方法二: 设置系统环境变量

**Windows (PowerShell)**:
```powershell
$env:DEEPSEEK_API_KEY="sk-your-deepseek-api-key-here"
```

**Linux/macOS**:
```bash
export DEEPSEEK_API_KEY="sk-your-deepseek-api-key-here"
```

### 3. 运行程序

```bash
python main.py
```

启动时会看到:
```
Loaded DeepSeek Chat
Loaded DeepSeek Coder
```

## 配置说明

### 模型配置 (config/settings.yaml)

```yaml
models:
  remote:
    models:
      deepseek-chat:
        description: "DeepSeek Chat - 通用对话模型"
        temperature: 0.7
        max_tokens: 4096
        base_url: "https://api.deepseek.com/v1"
      deepseek-coder:
        description: "DeepSeek Coder - 代码专用模型"
        temperature: 0.3
        max_tokens: 4096
        base_url: "https://api.deepseek.com/v1"
```

### 路由策略

DeepSeek模型已自动集成到路由策略中:

```yaml
routing:
  task_model_mapping:
    code:
      preferred: ["code_light", "deepseek-coder", "deepcoder", "remote_gpt4"]
      # DeepSeek Coder优先用于代码任务
    chat:
      preferred: ["mindchat", "deepseek-chat", "remote_gpt4"]
      # DeepSeek Chat用于对话任务
    question:
      preferred: ["mindchat", "deepseek-chat", "remote_gpt4"]
      # DeepSeek Chat用于问答任务
```

## 使用示例

### 代码生成 (自动使用DeepSeek Coder)

```
用户: 写一段快速排序的代码
拓荒者: [DeepSeek Coder生成代码]
```

### 日常对话 (自动使用DeepSeek Chat)

```
用户: 什么是相对论?
拓荒者: [DeepSeek Chat回答]
```

## API Key优先级

系统按以下优先级获取API Key:

1. **DeepSeek模型**: `DEEPSEEK_API_KEY` → `OPENAI_API_KEY`
2. **OpenAI模型**: `OPENAI_API_KEY`

这意味着:
- 如果你只设置了`OPENAI_API_KEY`,DeepSeek模型也会使用它
- 如果你同时设置了两个Key,DeepSeek模型会优先使用`DEEPSEEK_API_KEY`

## 性能对比

| 模型 | 适用场景 | 优势 | 温度 |
|:---|:---|:---|:---:|
| DeepSeek Chat | 通用对话、问答 | 中文理解好,响应快 | 0.7 |
| DeepSeek Coder | 代码生成、编程 | 代码质量高,专业性强 | 0.3 |
| GPT-4o-mini | 通用任务 | 能力均衡 | 0.7 |

## 故障排查

### 问题1: "未设置API Key环境变量"

**解决方案**:
- 检查`.env`文件是否存在且包含`DEEPSEEK_API_KEY`
- 或设置环境变量: `export DEEPSEEK_API_KEY="your-key"`

### 问题2: "无法连接到远程API"

**解决方案**:
- 检查网络连接
- 确认DeepSeek API服务正常: https://api.deepseek.com/v1
- 检查API Key是否有效

### 问题3: "API Key无效或未授权"

**解决方案**:
- 确认API Key正确无误
- 检查DeepSeek账户余额
- 确认API Key未过期

## 成本优化建议

1. **优先使用本地模型**: 对于简单任务,使用本地Ollama模型
2. **合理配置路由**: 在`config/settings.yaml`中调整模型优先级
3. **监控使用量**: 定期查看`model_stats.db`中的调用统计

## 进阶配置

### 自定义DeepSeek模型参数

编辑`config/settings.yaml`:

```yaml
models:
  remote:
    models:
      deepseek-coder:
        temperature: 0.2  # 降低随机性,提高代码准确性
        max_tokens: 8192  # 增加最大输出长度
```

### 添加自定义DeepSeek模型

```yaml
models:
  remote:
    models:
      deepseek-custom:
        description: "自定义DeepSeek模型"
        temperature: 0.5
        max_tokens: 4096
        base_url: "https://api.deepseek.com/v1"
```

然后在`main.py`中加载:
```python
adapters["deepseek-custom"] = RemoteAdapter(model_name="deepseek-custom")
```

## 总结

DeepSeek API已完全集成到联盟拓荒者中,提供:
- ✅ 自动路由到最适合的模型
- ✅ 智能重试和错误处理
- ✅ 配置驱动的灵活管理
- ✅ 与本地模型无缝协作

开始使用DeepSeek,让拓荒者更智能! 🔥