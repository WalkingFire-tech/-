# 后端启动验证清单

## 已修复的问题

### 1. ✅ 配置文件路径问题
**问题**: `配置文件不存在: config\settings.yaml`

**修复**: 
- 修改 `infrastructure/config_manager.py`
- 添加 `_find_config_file()` 方法，支持多路径查找
- 自动从项目根目录查找配置文件

**验证**:
```powershell
python -c "from infrastructure.config_manager import config; print(list(config._config.keys()))"
# 输出: ['models', 'routing', 'intent', 'memory', 'stats', ...]
```

### 2. ✅ 工具生成器路径问题
**问题**: `FileNotFoundError: [WinError 3] 系统找不到指定的路径。: 'tools\\generated'`

**修复**:
- 修改 `tools/generator.py` 第21行
- 使用 `mkdir(parents=True, exist_ok=True)` 创建父目录

**验证**:
```powershell
python -c "from tools.generator import ToolGenerator; ToolGenerator(); print('OK')"
# 输出: OK
```

### 3. ✅ 启动脚本编码问题
**问题**: 中文乱码

**修复**:
- 添加 `chcp 65001 >nul` 设置UTF-8编码
- 添加 `cd /d "%~dp0"` 确保正确路径

## 启动后端服务

### 方式1: 使用启动脚本（推荐）
```powershell
.\scripts\start_backend.bat
```

### 方式2: 直接启动
```powershell
cd backend
python -m uvicorn main:app --reload --port 8000
```

### 方式3: 后台启动
```powershell
Start-Process python -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--port", "8000" -WorkingDirectory "backend"
```

## 验证服务

### 1. 健康检查
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/health"
```

预期输出:
```json
{
  "status": "ok",
  "version": "3.1.1",
  "models": ["mindchat", "code_light", "remote_gpt4", "deepseek-chat"]
}
```

### 2. 访问API文档
浏览器打开: http://localhost:8000/docs

### 3. 测试聊天API
```powershell
$body = @{message = "你好"} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/chat" -Method Post -Body $body -ContentType "application/json"
```

## 常见问题

### Q1: Ollama连接失败
```
ERROR | Ollama unavailable: HTTPConnectionPool(host='localhost', port=11434)
```

**解决方案**:
1. 启动Ollama服务: `ollama serve`
2. 或使用远程模型（配置OPENAI_API_KEY或DEEPSEEK_API_KEY）

### Q2: 模块导入错误
```
ModuleNotFoundError: No module named 'infrastructure'
```

**解决方案**:
确保在项目根目录运行，或使用启动脚本

### Q3: 端口被占用
```
ERROR: [Errno 10048] error while attempting to bind on address
```

**解决方案**:
```powershell
# 查找占用进程
netstat -ano | findstr :8000
# 结束进程
taskkill /PID <进程ID> /F
```

## 下一步

- [ ] 启动后端服务（使用上述任一方式）
- [ ] 验证API端点
- [ ] 创建Tauri+Vue前端
- [ ] 测试完整流程