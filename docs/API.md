# API文档

## 基础信息

- **Base URL**: `http://localhost:8000`
- **API文档**: `http://localhost:8000/docs`
- **健康检查**: `GET /api/health`

---

## 学习API

### GET /api/learning/log

查看学习活动日志

**参数**：
- `limit` (int, optional): 返回数量，默认20

**响应**：
```json
{
  "success": true,
  "activities": [
    {
      "id": 1,
      "trigger": "manual",
      "query": "Python异步编程",
      "status": "completed",
      "impact_score": 0.9,
      "created_at": "2026-06-13T18:30:44",
      "completed_at": "2026-06-13T18:30:56"
    }
  ],
  "total": 10
}
```

**示例**：
```bash
curl "http://localhost:8000/api/learning/log?limit=5"
```

---

### GET /api/learning/knowledge

查询知识库

**参数**：
- `topic` (str, optional): 主题关键词
- `limit` (int, optional): 返回数量，默认20

**响应**：
```json
{
  "success": true,
  "knowledge": [
    {
      "id": 1,
      "topic": "Python异步编程",
      "content": "...",
      "source": "web_search",
      "usefulness_score": 0.5,
      "access_count": 0
    }
  ],
  "total": 5
}
```

**示例**：
```bash
# 查询所有知识
curl "http://localhost:8000/api/learning/knowledge"

# 查询特定主题
curl "http://localhost:8000/api/learning/knowledge?topic=async"
```

---

### POST /api/learning/trigger

手动触发学习

**参数**：
- `query` (str, required): 学习查询
- `trigger_type` (str, optional): 触发类型，默认"manual"

**触发类型**：
- `manual` - 手动触发
- `user_question` - 用户提问
- `intent_failure` - 意图失败
- `capability_low` - 能力低迷
- `aphi_decline` - APHI下降

**响应**：
```json
{
  "success": true,
  "activity": {
    "id": 1,
    "trigger": "manual",
    "query": "Python异步编程最佳实践",
    "status": "completed",
    "impact_score": 0.9
  }
}
```

**示例**：
```bash
curl -X POST "http://localhost:8000/api/learning/trigger?query=Python异步编程最佳实践"
```

---

### POST /api/learning/pause

暂停学习器

**响应**：
```json
{
  "success": true,
  "message": "学习器已暂停"
}
```

**示例**：
```bash
curl -X POST "http://localhost:8000/api/learning/pause"
```

---

### POST /api/learning/resume

恢复学习器

**响应**：
```json
{
  "success": true,
  "message": "学习器已恢复"
}
```

**示例**：
```bash
curl -X POST "http://localhost:8000/api/learning/resume"
```

---

### POST /api/learning/rollback/{activity_id}

回滚学习活动

**参数**：
- `activity_id` (int, required): 学习活动ID

**响应**：
```json
{
  "success": true,
  "message": "已回滚学习活动 3"
}
```

**示例**：
```bash
curl -X POST "http://localhost:8000/api/learning/rollback/3"
```

---

### GET /api/learning/stats

获取学习统计

**响应**：
```json
{
  "success": true,
  "stats": {
    "total_activities": 10,
    "by_status": {
      "completed": 8,
      "failed": 2
    },
    "total_knowledge": 15,
    "is_paused": false
  }
}
```

**示例**：
```bash
curl "http://localhost:8000/api/learning/stats"
```

---

## 规则管理API

### GET /api/rules

列出学习规则

**参数**：
- `status` (str, optional): 规则状态（active/pending/all）
- `limit` (int, optional): 返回数量

**响应**：
```json
{
  "rules": [
    {
      "id": 1,
      "condition": "intent_type == 'code_generation'",
      "action": "use_model: qwen2.5-coder",
      "confidence": 0.85,
      "status": "active"
    }
  ],
  "total": 50
}
```

---

### POST /api/rules/{rule_id}/approve

批准规则

**示例**：
```bash
curl -X POST "http://localhost:8000/api/rules/1/approve"
```

---

### POST /api/rules/{rule_id}/reject

拒绝规则

**示例**：
```bash
curl -X POST "http://localhost:8000/api/rules/1/reject"
```

---

## 模型管理API

### GET /api/models

列出所有模型

**响应**：
```json
{
  "models": [
    {
      "name": "mindchat",
      "available": true,
      "type": "local"
    }
  ]
}
```

---

### GET /api/models/{model_name}/health

获取模型健康状态

**响应**：
```json
{
  "model": "mindchat",
  "health": {
    "status": "healthy",
    "success_rate": 0.95,
    "avg_latency": 2.5,
    "last_failure": null
  }
}
```

---

### POST /api/models/add

添加新模型

**参数**：
```json
{
  "name": "new-model",
  "type": "ollama",
  "endpoint": "http://localhost:11434"
}
```

---

## 能力矩阵API

### GET /api/capability_matrix

获取能力矩阵

**响应**：
```json
{
  "matrix": {
    "mindchat": {
      "code_generation": 0.85,
      "math_reasoning": 0.75,
      "creative_writing": 0.90
    }
  }
}
```

---

### GET /api/capability_matrix/rank/{task_type}

获取任务类型的能力排名

**示例**：
```bash
curl "http://localhost:8000/api/capability_matrix/rank/code_generation"
```

---

## 统计API

### GET /api/stats

获取系统统计

**响应**：
```json
{
  "total_calls": 1000,
  "success_rate": 0.85,
  "avg_response_time": 3.2,
  "by_intent": {
    "code_generation": 500,
    "math_calculation": 200
  }
}
```

---

## 反馈API

### POST /api/feedback

提交用户反馈

**参数**：
```json
{
  "call_id": 123,
  "rating": 1,  // 1=正面, -1=负面
  "comment": "回答很有帮助"
}
```

---

## 优化API

### POST /api/optimize

触发贝叶斯优化

**参数**：
```json
{
  "n_calls": 20
}
```

---

### POST /api/induction

触发归纳总结

**参数**：
```json
{
  "days": 7
}
```

---

## 错误响应

所有API在出错时返回统一格式：

```json
{
  "success": false,
  "error": "错误描述"
}
```

**常见错误码**：
- `400` - 参数错误
- `404` - 资源不存在
- `500` - 服务器内部错误

---

## 认证

当前版本无需认证，生产环境建议添加API Key认证。

---

## 速率限制

建议在生产环境添加速率限制，例如：
- 学习API: 10次/分钟
- 查询API: 60次/分钟