# 联盟拓荒者 - 启动指南

## 快速启动

### 方式1: 使用启动脚本（推荐）

```bash
# Windows
start.bat

# 或直接运行Python启动脚本
python start.py
```

### 方式2: 使用uvicorn命令

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 方式3: 直接运行main.py

```bash
python backend/main.py
```

## 访问地址

启动成功后，访问以下地址：

| 页面 | 地址 |
|------|------|
| 主页 | http://localhost:8000/ |
| API文档 | http://localhost:8000/docs |
| 学习仪表盘 | http://localhost:8000/learning |
| 知识面板 | http://localhost:8000/knowledge-panel |
| 八卦知识图谱 | http://localhost:8000/bagua-knowledge |

## 常见问题

### 1. 前端打不开

**原因**: API服务未启动

**解决方案**:
```bash
# 检查服务是否运行
netstat -ano | findstr :8000

# 如果没有输出，说明服务未启动，运行：
python start.py
```

### 2. 端口被占用

**解决方案**:
```bash
# 查找占用8000端口的进程
netstat -ano | findstr :8000

# 结束进程（替换PID为实际进程ID）
taskkill /F /PID <PID>

# 或使用其他端口
uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

### 3. 模块导入错误

**解决方案**:
```bash
# 确保在项目根目录
cd C:\Users\Administrator\alliance_pioneer

# 检查依赖
pip install -r requirements.txt
```

## 系统状态检查

运行验证脚本：
```bash
python scripts/verification/verify_startup.py
```

## 开发模式

启用热重载：
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir backend --reload-dir core
```

## 生产部署

使用gunicorn（Linux）：
```bash
gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```