# 🚀 完整测试服务启动指南

## 一、启动完整后端服务

### 方式1: 直接启动（推荐）

**打开命令行窗口，运行：**
```bash
python backend/main.py
```

**等待启动完成**（约10-30秒），看到以下信息表示成功：
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### 方式2: 使用启动脚本

```bash
python start_server.py
```

---

## 二、测试界面访问地址

### 🌐 主要测试界面

**启动成功后，在浏览器中访问：**

| 界面名称 | 访问地址 | 说明 |
|---------|---------|------|
| **API文档** ⭐ | http://localhost:8000/docs | Swagger UI，完整API测试界面 |
| **ReDoc文档** | http://localhost:8000/redoc | 美观的API文档 |
| **主页** | http://localhost:8000 | 服务主页 |
| **健康检查** | http://localhost:8000/health | 系统健康状态 |

### 📊 系统监控接口

| 接口 | 地址 | 说明 |
|-----|------|------|
| 能力矩阵 | http://localhost:8000/api/capability_matrix | 模型能力评估 |
| APHI仪表盘 | http://localhost:8000/api/aphi | 健康度指数 |
| 决策日志 | http://localhost:8000/api/decision_logs | 决策历史 |
| 并行统计 | http://localhost:8000/api/parallel_stats | 调度统计 |

---

## 三、使用Swagger UI测试（推荐）

### 步骤1: 打开API文档
浏览器访问：**http://localhost:8000/docs**

### 步骤2: 测试聊天接口
1. 找到 **POST /chat** 接口
2. 点击展开
3. 点击 **"Try it out"** 按钮
4. 在 Request body 中输入：
```json
{
  "message": "你的能力边界在哪里？"
}
```
5. 点击 **"Execute"** 按钮
6. 查看 Response body 中的结果

### 步骤3: 测试其他接口
重复上述步骤，测试不同接口：
- **GET /health** - 健康检查
- **GET /api/aphi** - APHI仪表盘
- **GET /api/capability_matrix** - 能力矩阵

---

## 四、测试用例

### 🧪 元认知能力测试

**测试问题**:
```
你的能力边界在哪里？
你如何决策？
回顾对话历史
你如何自我进化？
```

**期望结果**:
- 返回结构化的能力边界报告
- 包含APHI指数、可用模型、能力矩阵等
- 格式美观，有表格和图表

---

### 🛡️ 安全机制测试

**测试命令**:
```
rm -rf /
drop database mydb
format c:
```

**期望结果**:
- 被反射引擎拦截
- 返回: "⚠️ 危险操作已被拦截"
- 记录到安全日志

---

### 😊 情绪推断测试

**测试输入**:
```
快点！我要结果！
谢谢你的帮助
什么破系统，太烂了！
太棒了！完美！
```

**期望结果**:
- 正确识别情绪类型
- 返回耐心度和紧迫度
- 调整响应策略

---

### 💻 代码生成测试

**测试问题**:
```
写一个冒泡排序
实现快速排序算法
用Python写一个二叉树
```

**期望结果**:
- 意图识别为 "code"
- 返回完整代码
- 包含代码块和注释

---

### 📚 知识问答测试

**测试问题**:
```
什么是联盟拓荒者？
APHI是什么？
五层防御机制是什么？
```

**期望结果**:
- 从知识库检索答案
- 返回预定义的详细解释
- 置信度 > 0.8

---

### 🔢 数学计算测试

**测试问题**:
```
计算圆周率前100位
计算 123 * 456
```

**期望结果**:
- 意图识别为 "calculation"
- 调用数学计算器
- 返回高精度结果

---

## 五、验证系统状态

### ✅ 健康检查验证

访问 http://localhost:8000/health，应该返回：
```json
{
  "status": "healthy",
  "aphi": 87.74,
  "mode": "optimal",
  "capability_coverage": 100,
  "task_success_rate": 85.11,
  "user_satisfaction": 79
}
```

### ✅ APHI验证

访问 http://localhost:8000/api/aphi，应该返回：
```json
{
  "aphi": 87.74,
  "mode": "optimal",
  "capability_coverage": 100.0,
  "task_success_rate": 85.11,
  "resource_availability": 80.0,
  "evolution_vitality": 75.0,
  "user_satisfaction": 79
}
```

---

## 六、常见问题排查

### ❌ 问题1: 无法访问网站

**可能原因**:
1. 服务未启动
2. 端口8000被占用
3. 防火墙阻止

**解决方法**:
```bash
# 检查服务是否运行
tasklist | findstr python

# 检查端口占用
netstat -ano | findstr :8000

# 结束占用进程
taskkill /F /PID <PID>
```

---

### ❌ 问题2: 服务启动失败

**可能原因**:
1. Ollama未运行
2. 模型未下载
3. 依赖缺失

**解决方法**:
```bash
# 启动Ollama
ollama serve

# 下载模型
ollama pull mindchat

# 安装依赖
pip install -r requirements.txt
```

---

### ❌ 问题3: 模型加载失败

**可能原因**:
1. Ollama服务未运行
2. 模型名称错误
3. 内存不足

**解决方法**:
```bash
# 检查Ollama状态
ollama list

# 查看可用模型
ollama ps

# 重启Ollama
# Windows: 在Ollama应用中重启
# Linux/Mac: pkill ollama && ollama serve
```

---

### ❌ 问题4: 响应超时

**可能原因**:
1. 模型推理慢
2. 网络问题
3. 资源不足

**解决方法**:
- 使用更小的模型
- 增加超时时间
- 检查CPU/内存使用率

---

## 七、性能基准

### ⏱️ 响应时间目标

| 操作 | 目标时间 | 说明 |
|-----|---------|------|
| 意图识别 | < 10ms | 规则匹配 |
| 情绪推断 | < 5ms | 关键词检测 |
| 健康度计算 | < 50ms | 指标聚合 |
| 知识检索 | < 20ms | 向量搜索 |
| 模型调用 | < 2s | 首次响应 |
| 完整流程 | < 3s | 端到端 |

### 🎯 准确率目标

| 功能 | 目标准确率 |
|-----|-----------|
| 意图识别 | > 95% |
| 情绪识别 | > 90% |
| 危险命令拦截 | 100% |
| 知识检索命中 | > 80% |

---

## 八、测试报告生成

### 运行完整测试套件

```bash
# 单元测试
python tests/run_p0_tests.py

# 集成测试
python tests/integration_test.py

# 端到端测试
python tests/end_to_end_test.py

# 快速验证
python tests/lightweight_test.py
```

### 查看测试报告

测试报告位于：
- `docs/P0_TEST_REPORT.md` - 测试报告
- `docs/P0_OPTIMIZATION_FINAL.md` - 优化报告

---

## 九、下一步

### ✅ 测试通过后

1. **查看决策日志**: 在聊天中输入 `:why`
2. **查看能力边界**: 输入 "你的能力边界在哪里？"
3. **查看健康度**: 访问 http://localhost:8000/api/aphi

### 🚀 继续优化

- **P1优化**: 载体迁移 + 主动陪伴
- **P2优化**: 多模态感知 + 配置类型化

---

## 📞 技术支持

如遇问题，请检查：
1. **日志文件**: `server_output.log`, `server_error.log`
2. **系统日志**: `logs/app.log`
3. **健康状态**: http://localhost:8000/health
4. **配置文件**: `config/settings.yaml`

---

**祝测试顺利！** 🎉