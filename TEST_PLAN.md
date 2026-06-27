# 系统性测试方案

## 已修复的导入问题

### 1. 适配器层类名不匹配 ✅

**问题**：
- `adapters/__init__.py` 导入 `CLIUI`，实际类名是 `EnhancedCliUI`
- `adapters/__init__.py` 导入 `FolderProcessor`，实际类名是 `FolderBatchProcessor`

**修复**：
- `adapters/__init__.py:13` - `CLIUI` → `EnhancedCliUI`
- `adapters/__init__.py:15` - `FolderProcessor` → `FolderBatchProcessor`
- `adapters/ui/__init__.py:7` - `CLIUI` → `EnhancedCliUI`
- `adapters/input/__init__.py:8` - `FolderProcessor` → `FolderBatchProcessor`

### 2. 心跳管理器缺少start方法 ✅

**问题**：`HeartbeatManager` 没有 `start()` 方法

**修复**：`core/introspection/heartbeat.py:199-201` - 添加 `start()` 方法

### 3. 聊天功能未调用核心模块 ✅

**问题**：`/api/chat` 只返回占位文本

**修复**：`backend/main_fast.py:118-163` - 集成 `CognitiveDispatcher` 和 `MetacognitiveExecutor`

### 4. API端点缺失 ✅

**问题**：`/api/config/external` 和 `/api/models/test` 返回404

**修复**：`backend/main_fast.py:178-210` - 添加配置和测试API

### 5. 聊天超时问题 ✅

**问题**：元认知执行器卡住导致超时

**修复**：`backend/main_fast.py:118-163` - 添加超时保护和降级处理

---

## 测试步骤

### 第一步：重启服务

```bash
# 停止当前服务 (Ctrl+C)
# 重新启动
start.bat
```

### 第二步：验证服务启动

访问 http://localhost:8000/api/health

预期响应：
```json
{"status": "ok", "version": "3.1.1"}
```

### 第三步：验证API端点

#### 3.1 健康检查
```bash
curl http://localhost:8000/api/health
```

#### 3.2 统计数据
```bash
curl http://localhost:8000/api/stats
```

#### 3.3 模型列表
```bash
curl http://localhost:8000/api/models
```

#### 3.4 外置API配置
```bash
# 获取配置
curl http://localhost:8000/api/config/external

# 保存配置
curl -X POST http://localhost:8000/api/config/external \
  -H "Content-Type: application/json" \
  -d '{"apis": [{"name": "test", "url": "http://test.com"}]}'
```

### 第四步：验证聊天功能

#### 4.1 简单问候
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'
```

预期：立即返回友好问候语，不超时

#### 4.2 复杂问题
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "什么是认知科学？"}'
```

预期：返回包含意图、置信度、路由的完整响应

### 第五步：前端测试

1. 打开 http://localhost:8000
2. 测试聊天功能
3. 测试外置API配置保存
4. 测试模型选择

---

## 模块导入验证清单

### 核心模块
- [ ] `core.orchestrator.SystemOrchestrator`
- [ ] `core.cognitive_dispatcher.CognitiveDispatcher`
- [ ] `core.metacognitive_executor.MetacognitiveExecutor`
- [ ] `core.sleep_consolidator.SleepConsolidator`
- [ ] `core.canary_evaluator.CanaryEvaluator`

### 层架构
- [ ] `core.layers.l1_perception_enhanced.L1PerceptionLayer`
- [ ] `core.layers.l2_learning.L2LearningLayer`
- [ ] `core.layers.l3_integration.L3IntegrationLayer`
- [ ] `core.layers.l4_validation.L4ValidationLayer`
- [ ] `core.layers.l5_evolution.L5EvolutionLayer`
- [ ] `core.layers.l6_introspection.L6IntrospectionLayer`

### 基础设施
- [ ] `infrastructure.reflection_pipeline.ReflectionPipeline`
- [ ] `infrastructure.experience_pool.ExperiencePool`
- [ ] `infrastructure.quick_reflex.QuickReflexEngine`

### 工具层
- [ ] `tools.registry.registry`
- [ ] `tools.arbiter.ToolArbiter`

### 适配器层
- [ ] `adapters.llm.ollama_adapter.OllamaAdapter`
- [ ] `adapters.ui.cli_ui.EnhancedCliUI`
- [ ] `adapters.input.folder_processor.FolderBatchProcessor`

---

## 已知问题

### 1. 编码问题
日志输出中文乱码，但不影响功能

### 2. 启动脚本警告
```
'2]' is not recognized as an internal or external command
'认知循环' is not recognized as an internal or external command
```
这是start.bat中的echo命令编码问题，不影响功能

### 3. 存在层重复启动警告
```
WARNING | core.presence.existence_layer:start:131 - 存在层已在运行
```
这是正常的，不影响功能

---

## 性能优化建议

1. **元认知执行器优化** - 减少初始化时间，添加缓存
2. **模型加载优化** - 延迟加载，按需初始化
3. **数据库连接池** - 使用连接池减少开销
4. **异步处理** - 更多操作改为异步

---

## 下一步

1. **重启服务** - 让所有修复生效
2. **运行端到端测试** - 验证所有功能
3. **性能测试** - 测试并发和响应时间
4. **压力测试** - 测试系统稳定性