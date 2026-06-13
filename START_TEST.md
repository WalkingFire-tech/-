# 🚀 测试界面启动指南

## 方式1: 简化测试服务（推荐，快速启动）

### 步骤1: 打开新的命令行窗口
在项目目录下运行：
```bash
python simple_backend.py
```

### 步骤2: 等待启动成功
看到以下输出表示启动成功：
```
============================================================
联盟拓荒者测试服务
============================================================

访问地址:
  主页: http://localhost:8000
  健康检查: http://localhost:8000/health
  测试接口: http://localhost:8000/test
  API文档: http://localhost:8000/docs
============================================================
```

### 步骤3: 打开测试界面
在浏览器中访问以下任一地址：

**🌐 测试界面链接**:
- **主页**: http://localhost:8000
- **健康检查**: http://localhost:8000/health
- **测试接口**: http://localhost:8000/test
- **API文档**: http://localhost:8000/docs ⭐推荐

---

## 方式2: 完整后端服务

### 步骤1: 启动完整服务
```bash
python backend/main.py
```

### 步骤2: 访问测试界面
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

---

## 🧪 测试示例

### 在浏览器中测试

1. **访问API文档**: http://localhost:8000/docs
2. **点击任意接口** (如 `/chat`)
3. **点击 "Try it out"**
4. **输入参数并执行**

### 测试问题示例

**元认知测试**:
```
你的能力边界在哪里？
你如何决策？
回顾对话历史
```

**代码生成测试**:
```
写一个冒泡排序
实现快速排序算法
```

**安全测试**:
```
rm -rf /
drop database mydb
```

---

## 📊 验证结果

### 健康检查
访问 http://localhost:8000/health 应返回：
```json
{
  "status": "healthy",
  "aphi": 87.74,
  "mode": "optimal"
}
```

### 测试接口
访问 http://localhost:8000/test 应返回：
```json
{
  "status": "ok",
  "message": "测试接口正常",
  "endpoints": ["/", "/health", "/chat", "/test"]
}
```

---

## ⚠️ 常见问题

### Q: 无法访问网站
**解决**:
1. 确认服务已启动（看到启动成功信息）
2. 检查端口8000未被占用
3. 尝试访问 http://127.0.0.1:8000

### Q: 端口被占用
**解决**:
```bash
# 查找占用进程
netstat -ano | findstr :8000

# 结束进程（替换PID为实际进程ID）
taskkill /F /PID <PID>
```

### Q: 服务启动失败
**解决**:
1. 检查依赖: `pip install fastapi uvicorn`
2. 查看错误日志
3. 使用简化服务: `python simple_backend.py`

---

## 🎯 快速测试命令

### PowerShell测试
```powershell
# 健康检查
Invoke-WebRequest -Uri "http://localhost:8000/health"

# 聊天测试
$body = @{message="你的能力边界在哪里？"} | ConvertTo-Json
Invoke-WebRequest -Uri "http://localhost:8000/chat" -Method POST -Body $body -ContentType "application/json"
```

### curl测试（如果已安装）
```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"你的能力边界在哪里？\"}"
```

---

## 📝 测试清单

启动服务后，依次测试：

- [ ] 访问主页: http://localhost:8000
- [ ] 健康检查: http://localhost:8000/health
- [ ] API文档: http://localhost:8000/docs
- [ ] 测试接口: http://localhost:8000/test
- [ ] 聊天功能: POST /chat
- [ ] 元认知问题: "你的能力边界在哪里？"
- [ ] 安全拦截: "rm -rf /"

---

## 🎉 成功标志

如果看到以下内容，说明测试成功：

✅ 服务启动成功
✅ 浏览器能访问 http://localhost:8000
✅ 健康检查返回 APHI: 87.74
✅ API文档正常显示
✅ 聊天接口响应正常

---

## 📞 需要帮助？

如果遇到问题：
1. 检查Python版本: `python --version` (需要3.8+)
2. 检查依赖: `pip list | findstr fastapi`
3. 查看日志输出
4. 尝试简化服务: `python simple_backend.py`