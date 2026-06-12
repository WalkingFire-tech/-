# 桌面应用使用说明

## 🖥️ 两种使用方式

### 方式1: 桌面应用（推荐）⭐

**启动方式**:
```powershell
# Windows: 双击运行
启动.bat

# 或命令行
python -m uvicorn api:app --reload --port 8000
```

**访问地址**: http://localhost:8000/

**特点**:
- ✅ 现代化Web界面
- ✅ 实时状态监控
- ✅ 可视化操作
- ✅ 多功能面板

---

### 方式2: CLI命令行模式

**启动方式**:
```powershell
python main.py
```

**特点**:
- ✅ 交互式命令行
- ✅ 直接输入指令
- ✅ 适合快速测试

---

## 🎯 功能对比

| 功能 | 桌面应用 | CLI模式 |
|------|---------|---------|
| 聊天对话 | ✅ | ✅ |
| 系统状态 | ✅ 可视化 | ✅ 文本 |
| 快捷操作 | ✅ 按钮 | ✅ 命令 |
| 历史记录 | ✅ 界面显示 | ✅ 数据库 |
| API文档 | ✅ /docs | ❌ |
| 多媒体支持 | ✅ | ❌ |

---

## 📊 当前状态

```
版本: v3.1.1
经验池: 59条
活跃规则: 2条
待激活规则: 35条
模型: mindchat, code_light
```

---

## 🔧 配置选项

### 使用Ollama（本地模型）
```powershell
# 启动Ollama服务
ollama serve

# 拉取模型
ollama pull mindchat
ollama pull qwen2.5-coder:1.5b
```

### 使用远程模型
```powershell
# 设置API密钥
$env:OPENAI_API_KEY="your-key"
$env:DEEPSEEK_API_KEY="your-key"
```

### 使用Mock适配器（默认）
无需配置，系统自动降级。

---

## 📝 快速测试

### 桌面应用测试
```powershell
# 1. 启动
.\启动.bat

# 2. 浏览器自动打开，或手动访问
http://localhost:8000/

# 3. 在界面中输入问题测试
```

### CLI模式测试
```powershell
# 1. 启动
python main.py

# 2. 输入问题
你好，请介绍一下你自己

# 3. 查看响应
```

---

## 🌐 API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 前端界面 |
| `/api/health` | GET | 健康检查 |
| `/api/models` | GET | 模型列表 |
| `/api/stats` | GET | 统计信息 |
| `/api/chat` | POST | 聊天接口 |
| `/api/optimize` | POST | 运行优化 |
| `/api/induction` | POST | 归纳总结 |
| `/docs` | GET | API文档 |

---

## 🎨 界面功能

### 左侧面板
- **系统状态**: 经验池、规则、模型数量
- **可用模型**: 已加载的模型列表
- **快捷操作**: 
  - 🎯 运行优化
  - 📚 归纳总结

### 聊天区域
- 输入问题或任务
- Enter发送，Shift+Enter换行
- 查看AI响应

### 顶部状态栏
- 连接状态指示
- 版本号显示

---

## 🐛 故障排查

### 问题1: 无法启动
```powershell
# 检查Python版本
python --version  # 需要3.11+

# 检查依赖
pip install -r requirements.txt
```

### 问题2: Ollama连接失败
**这是正常的！** 系统会自动使用Mock适配器。

如需使用Ollama:
```powershell
ollama serve
```

### 问题3: 端口被占用
```powershell
# 查看占用进程
netstat -ano | findstr :8000

# 结束进程
taskkill /PID <进程ID> /F
```

---

## 📚 相关文档

- `docs/PHASE1_SUMMARY.md` - Phase 1完成总结
- `docs/DESKTOP_APP_READY.md` - 桌面应用指南
- `docs/BACKEND_ERRORS_FIXED.md` - 错误修复说明

---

**🎉 选择你喜欢的方式开始使用吧！**