# 外部知识源配置系统 - 使用指南

## 概述

本系统实现了一个**统一的外部知识源管理器**，支持从多种权威知识来源获取信息，特别针对国内网络环境优化。

---

## 一、支持的知识源

### 1. LLM API（大模型接口）

| 知识源 | 状态 | 特点 | 配置方式 |
|--------|------|------|----------|
| **DeepSeek** | ✅ 推荐 | 国内可用、速度快、成本低 | `DEEPSEEK_API_KEY` |
| OpenAI | 可选 | 通用知识强、创意生成 | `OPENAI_API_KEY`（需VPN） |

### 2. 搜索引擎

| 知识源 | 状态 | 特点 | 配置方式 |
|--------|------|------|----------|
| **DuckDuckGo** | ✅ 默认 | 无需API密钥、隐私保护 | 无需配置 |
| 百度搜索 | 可选 | 国内优化、中文结果 | `BAIDU_API_KEY` |
| Bing搜索 | 可选 | 国际化结果 | `BING_API_KEY` |

### 3. 知识库

| 知识源 | 状态 | 特点 | 权威性 |
|--------|------|------|--------|
| **维基百科（中文）** | ✅ 启用 | 百科知识、历史、科学 | ⭐⭐⭐⭐⭐ |
| **维基百科（英文）** | ✅ 启用 | 技术文档、学术论文 | ⭐⭐⭐⭐⭐ |
| **百度百科** | ✅ 启用 | 中文知识、流行文化 | ⭐⭐⭐⭐ |

### 4. 开发者资源

| 知识源 | 状态 | 特点 | 配置方式 |
|--------|------|------|----------|
| **GitHub** | ✅ 启用 | 开源代码、项目搜索 | `GITHUB_TOKEN`（可选） |
| **Stack Overflow** | ✅ 启用 | 编程问答、最佳实践 | `STACKOVERFLOW_KEY`（可选） |
| **CSDN** | ✅ 启用 | 中文技术文章、教程 | 无需配置 |

### 5. 学术资源

| 知识源 | 状态 | 特点 | 权威性 |
|--------|------|------|--------|
| **arXiv** | ✅ 启用 | AI/ML论文、学术研究 | ⭐⭐⭐⭐⭐ |
| **知乎** | ✅ 启用 | 专业知识、经验分享 | ⭐⭐⭐⭐ |
| Google Scholar | 可选 | 学术搜索（需VPN） | ⭐⭐⭐⭐⭐ |

### 6. 官方文档

| 知识源 | 状态 | 特点 |
|--------|------|------|
| **Python官方文档** | ✅ 启用 | Python语法、标准库 |
| **PyTorch官方文档** | ✅ 启用 | 深度学习框架 |
| **TensorFlow官方文档** | ✅ 启用 | 机器学习框架 |

---

## 二、配置文件

### 配置文件位置

```
config/knowledge_sources.json
```

### 配置示例

```json
{
  "knowledge_sources": {
    "llm_apis": {
      "deepseek": {
        "enabled": true,
        "priority": 1,
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat"
      }
    },
    "search_engines": {
      "duckduckgo": {
        "enabled": true,
        "priority": 1
      }
    }
  }
}
```

---

## 三、环境变量配置

### 必需配置（DeepSeek）

```bash
# Windows (PowerShell)
$env:DEEPSEEK_API_KEY="your-deepseek-api-key"

# Linux/Mac
export DEEPSEEK_API_KEY="your-deepseek-api-key"
```

### 可选配置

```bash
# GitHub（提升速率限制）
export GITHUB_TOKEN="your-github-token"

# Stack Overflow（提升速率限制）
export STACKOVERFLOW_KEY="your-stackoverflow-key"

# 百度搜索
export BAIDU_API_KEY="your-baidu-api-key"

# Bing搜索
export BING_API_KEY="your-bing-api-key"
```

---

## 四、智能路由规则

系统会根据问题类型自动选择最佳知识源：

| 问题类型 | 关键词 | 优先知识源 |
|----------|--------|------------|
| 编程问题 | 代码、编程、实现 | GitHub、Stack Overflow、CSDN |
| 学术问题 | 论文、研究、学术 | arXiv、维基百科 |
| 概念问题 | 是什么、定义、概念 | 维基百科、百度百科、知乎 |
| 技术框架 | Python、PyTorch | 官方文档、Stack Overflow |

---

## 五、使用方法

### 基础用法

```python
from core.knowledge_source_manager import get_knowledge_source_manager

manager = get_knowledge_source_manager()

# 自动路由
result = manager.query("什么是机器学习？")

# 指定类型
result = manager.query("Python如何实现快速排序？", source_type="search")

# 查询LLM
result = manager.query("解释量子计算原理", source_type="llm")
```

### 结果格式

```python
{
    "success": True,
    "source": "deepseek",  # 实际使用的知识源
    "data": "...",         # 查询结果
    "confidence": 0.85,    # 置信度
    "metadata": {
        "source_type": "llm",
        "reliability": "high",
        "timestamp": "2026-06-20T08:00:00"
    }
}
```

---

## 六、降级策略

系统采用多级降级策略，确保总能返回结果：

```
1. 知识源管理器（配置的优先源）
    ↓ 失败
2. DuckDuckGo搜索（无需API）
    ↓ 失败
3. Google搜索（需API）
    ↓ 失败
4. 模拟结果（提示用户配置）
```

---

## 七、缓存机制

### 配置

```json
{
  "cache_config": {
    "enabled": true,
    "ttl_hours": 24,
    "max_entries": 1000,
    "db_path": "data/knowledge_cache.db"
  }
}
```

### 特性

- **自动缓存**: 查询结果自动缓存24小时
- **避免重复**: 相同问题不重复查询
- **持久化**: 重启后缓存仍然有效

---

## 八、速率限制

### 配置

```json
{
  "rate_limiting": {
    "requests_per_minute": 60,
    "requests_per_hour": 1000,
    "retry_after_seconds": 60
  }
}
```

### 作用

- 防止API滥用
- 避免触发知识源的速率限制
- 自动等待和重试

---

## 九、管理操作

### 查看可用知识源

```python
manager = get_knowledge_source_manager()
sources = manager.get_available_sources()

# 输出:
{
    "llm_apis": ["deepseek"],
    "search_engines": ["duckduckgo"],
    "knowledge_bases": ["wikipedia_zh", "wikipedia_en", "baike_baidu"],
    "developer_resources": ["github", "stackoverflow", "csdn"],
    "academic_sources": ["arxiv", "zhihu"]
}
```

### 启用/禁用知识源

```python
# 启用
manager.enable_source("arxiv")

# 禁用
manager.disable_source("google_scholar")
```

---

## 十、国内网络优化

### 推荐配置（无需VPN）

```json
{
  "knowledge_sources": {
    "llm_apis": {
      "deepseek": {"enabled": true, "priority": 1}
    },
    "search_engines": {
      "duckduckgo": {"enabled": true, "priority": 1}
    },
    "knowledge_bases": {
      "wikipedia_zh": {"enabled": true},
      "baike_baidu": {"enabled": true}
    },
    "developer_resources": {
      "github": {"enabled": true},
      "csdn": {"enabled": true}
    },
    "academic_sources": {
      "arxiv": {"enabled": true},
      "zhihu": {"enabled": true}
    }
  }
}
```

### 避免使用（需VPN）

- Google搜索
- Google Scholar
- OpenAI API（如无国内镜像）

---

## 十一、最佳实践

### 1. 优先使用DeepSeek

```bash
# 配置DeepSeek API
export DEEPSEEK_API_KEY="sk-xxx"
```

DeepSeek在国内网络环境下表现优秀，速度快、成本低。

### 2. 启用多个知识源

不要只依赖单一知识源，启用多个源可以提高查询成功率。

### 3. 定期清理缓存

```bash
# 清理过期缓存
sqlite3 data/knowledge_cache.db "DELETE FROM knowledge_cache WHERE expires_at < datetime('now')"
```

### 4. 监控速率限制

如果频繁触发速率限制，考虑：
- 降低 `requests_per_minute`
- 配置更多API密钥轮换
- 启用缓存减少查询

---

## 十二、故障排查

### 问题1: DeepSeek API调用失败

**检查**:
```bash
# 检查环境变量
echo $DEEPSEEK_API_KEY

# 测试API
curl https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY"
```

### 问题2: DuckDuckGo搜索失败

**解决**:
```bash
# 安装依赖
pip install duckduckgo-search

# 或使用百度/Bing作为替代
```

### 问题3: 知识源全部不可用

**检查配置**:
```python
manager = get_knowledge_source_manager()
print(manager.get_available_sources())
```

---

## 十三、扩展知识源

### 添加新知识源

编辑 `config/knowledge_sources.json`:

```json
{
  "knowledge_sources": {
    "custom_sources": {
      "my_api": {
        "enabled": true,
        "priority": 1,
        "type": "api",
        "base_url": "https://my-api.com/search",
        "api_key_env": "MY_API_KEY",
        "description": "自定义知识源"
      }
    }
  }
}
```

然后在 `KnowledgeSourceManager` 中实现查询方法。

---

## 总结

本系统提供了：
- ✅ **多种知识源**: LLM、搜索、百科、开发者资源、学术资源
- ✅ **智能路由**: 根据问题类型自动选择最佳源
- ✅ **国内优化**: DeepSeek、百度百科、CSDN等国内可用源
- ✅ **降级策略**: 多级降级确保总能返回结果
- ✅ **缓存机制**: 避免重复查询，提升响应速度
- ✅ **速率限制**: 防止API滥用
- ✅ **易于扩展**: 配置文件驱动，轻松添加新源

配置一次，终身受益！🎉