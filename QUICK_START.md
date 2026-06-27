# 联盟拓荒者 - 快速启动指南

## ⚡ 一键启动

```bash
# Windows双击运行
START.bat
```

这会自动：
1. 检查并清理端口占用
2. 启动服务
3. 打开浏览器

## 🔧 其他启动方式

### 方式1: 最小化应用（推荐测试）

```bash
python minimal_app.py
```

### 方式2: 简单HTTP服务器

```bash
python simple_server.py
```

### 方式3: 完整后端

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## 🌐 访问地址

启动成功后访问：

| 页面 | 地址 |
|------|------|
| 主页 | http://localhost:8000/ |
| API文档 | http://localhost:8000/docs |
| 学习仪表盘 | http://localhost:8000/learning |
| 知识面板 | http://localhost:8000/knowledge-panel |

## 🔍 环境检查

```bash
# Windows
check_env.bat

# 或手动检查
python -c "import fastapi, uvicorn; print('✓ 依赖已安装')"
```

## ❓ 常见问题

### 1. 无法打开前端

**检查服务是否启动：**
```bash
netstat -ano | findstr ":8000.*LISTENING"
```

**如果没有输出，说明服务未启动，运行：**
```bash
START.bat
```

### 2. 端口被占用

```bash
# 查找并结束占用进程
netstat -ano | findstr ":8000"
taskkill /F /PID <PID>
```

### 3. 依赖缺失

```bash
pip install fastapi uvicorn loguru requests
```

## 📊 系统状态

```
✅ 前端文件: frontend/index.html
✅ 后端配置: backend/main.py
✅ 静态挂载: 已配置
✅ 根路径: 返回前端页面
```

## 🚀 推荐启动流程

1. 运行 `check_env.bat` 检查环境
2. 运行 `START.bat` 启动服务
3. 浏览器自动打开 http://localhost:8000/

---

**问题反馈：**
如果仍然无法打开，请提供：
1. `check_env.bat` 的输出
2. `START.bat` 的完整日志
3. 浏览器显示的错误信息