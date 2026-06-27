# 网页无法打开 - 解决方案

## 问题诊断

您看到的日志只是模块加载，但API服务可能没有真正启动监听。

## 解决方案

### 方案1: 使用最小化应用（推荐测试）

```bash
python minimal_app.py
```

这会跳过复杂的初始化，快速启动服务。

### 方案2: 使用简化启动

```bash
python simple_start.py
```

### 方案3: 直接uvicorn

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 方案4: 运行诊断

```bash
python scripts/diagnose_startup.py
```

## 验证服务是否启动

### Windows:
```bash
netstat -ano | findstr ":8000.*LISTENING"
```

### 或使用Python:
```python
import requests
response = requests.get("http://localhost:8000/")
print(response.status_code)  # 应该返回200
```

## 访问地址

启动成功后访问:
- 主页: http://localhost:8000/
- API文档: http://localhost:8000/docs
- 学习仪表盘: http://localhost:8000/learning

## 常见问题

### 1. 端口被占用
```bash
# 查找占用进程
netstat -ano | findstr :8000

# 结束进程
taskkill /F /PID <PID>
```

### 2. 模块导入错误
```bash
# 确保在项目根目录
cd C:\Users\Administrator\alliance_pioneer

# 安装依赖
pip install fastapi uvicorn loguru
```

### 3. lifespan阻塞
如果`start.bat`启动后没有看到uvicorn的启动日志（如`Uvicorn running on...`），可能是lifespan函数中有阻塞操作。

解决: 使用`minimal_app.py`测试。