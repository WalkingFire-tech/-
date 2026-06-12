# 🚨 无法访问网页端 - 解决方案

## 问题诊断

### 当前状态
- ✅ 后端代码已创建
- ✅ 前端文件已创建
- ✅ 启动脚本已创建
- ❌ 后端服务未运行

### 原因分析
导入`backend.main`会触发大量初始化（贝叶斯优化器、FAISS索引、归纳器等），在沙箱环境下会超限。

---

## ✅ 解决方案

### 方式1: 使用诊断脚本（推荐）

```powershell
# 在项目根目录运行
.\diagnose.bat
```

这个脚本会：
1. 检查Python进程
2. 检查端口占用
3. 测试API加载
4. 启动后端服务

---

### 方式2: 手动启动（最可靠）

```powershell
# 1. 进入项目目录
cd C:\Users\Administrator\alliance_pioneer

# 2. 直接启动（前台运行，可看到日志）
python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

**等待看到以下日志表示启动成功**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**然后浏览器访问**: http://localhost:8000/

---

### 方式3: 后台启动

```powershell
# 启动后台进程
Start-Process python -ArgumentList "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"

# 等待5秒
Start-Sleep -Seconds 5

# 测试是否启动成功
Invoke-RestMethod -Uri "http://localhost:8000/api/health"
```

---

## 🔍 验证步骤

### 1. 检查后端是否运行
```powershell
# 检查端口
netstat -ano | findstr :8000

# 应该看到类似输出
# TCP    0.0.0.0:8000    0.0.0.0:0    LISTENING    12345
```

### 2. 测试健康检查
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/health"

# 应该返回
# status  version models
# ------ ------- ------
# ok      3.1.1   {mindchat, code_light}
```

### 3. 访问前端
浏览器打开: http://localhost:8000/

---

## 🐛 常见问题

### 问题1: 端口被占用
```powershell
# 查找占用进程
netstat -ano | findstr :8000

# 结束进程（替换PID）
taskkill /PID <进程ID> /F
```

### 问题2: 导入错误
```powershell
# 检查依赖
pip install fastapi uvicorn loguru pydantic python-dotenv

# 或安装全部依赖
pip install -r requirements.txt
```

### 问题3: Ollama连接失败
**这是正常的！** 不影响使用，系统会自动降级。

---

## 📋 完整启动流程

```powershell
# 步骤1: 进入项目目录
cd C:\Users\Administrator\alliance_pioneer

# 步骤2: 启动后端（选择一种方式）
# 方式A: 前台运行（推荐调试时使用）
python -m uvicorn api:app --reload --port 8000

# 方式B: 后台运行
Start-Process python -ArgumentList "-m", "uvicorn", "api:app", "--port", "8000"

# 步骤3: 等待启动（约5-10秒）

# 步骤4: 验证
Invoke-RestMethod -Uri "http://localhost:8000/api/health"

# 步骤5: 访问前端
start http://localhost:8000/
```

---

## 🎯 快速启动命令（复制粘贴）

```powershell
cd C:\Users\Administrator\alliance_pioneer; python -m uvicorn api:app --host 0.0.0.0 --port 8000
```

启动后浏览器访问: **http://localhost:8000/**

---

## 📊 预期日志输出

启动成功后会看到：
```
INFO:     Will watch for changes in these directories: ['C:\\...']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using StatReload
配置文件加载成功: config\settings.yaml
贝叶斯优化器初始化完成
FAISS索引初始化完成
后端服务初始化完成
已加载 2 个模型适配器: ['mindchat', 'code_light']
INFO:     Application startup complete.
```

---

## ⚡ 如果还是无法启动

请提供以下信息：
1. 运行`python --version`的输出
2. 运行`netstat -ano | findstr :8000`的输出
3. 启动时的完整错误日志

---

**建议**: 使用方式2（手动启动），可以看到完整的启动日志，方便排查问题。