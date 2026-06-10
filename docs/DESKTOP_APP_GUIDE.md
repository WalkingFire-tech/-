# 桌面应用开发指南

## Phase 1: FastAPI后端 + Tauri/Vue前端

---

## 一、项目结构

```
alliance_pioneer/
├── backend/               # FastAPI 后端服务
│   ├── __init__.py
│   ├── main.py           # FastAPI 应用入口
│   └── api/
│       └── __init__.py
├── frontend/              # Tauri + Vue 前端（需初始化）
│   ├── src/
│   ├── src-tauri/
│   └── package.json
├── scripts/               # 启动脚本
│   ├── start_backend.bat
│   ├── start_frontend.bat
│   └── start_all.bat
└── ... (原有 core/, adapters/, infrastructure/ 等)
```

---

## 二、后端 FastAPI 服务

### 已实现的端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/models` | GET | 获取可用模型列表 |
| `/api/chat` | POST | 聊天对话 |
| `/api/optimize` | POST | 运行贝叶斯优化 |
| `/api/induction` | POST | 运行归纳总结 |
| `/api/stats` | GET | 获取统计信息 |

### 启动后端

**方式1：使用启动脚本**
```bash
scripts\start_backend.bat
```

**方式2：手动启动**
```bash
# 激活虚拟环境
.\venv\Scripts\activate

# 启动服务
cd backend
uvicorn main:app --reload --port 8000
```

**访问地址**：
- 后端服务: http://localhost:8000
- API文档: http://localhost:8000/docs
- ReDoc文档: http://localhost:8000/redoc

---

## 三、前端 Tauri + Vue

### 初始化前端项目（首次使用）

```bash
# 1. 安装Tauri CLI
npm install -g @tauri-apps/cli

# 2. 创建Tauri项目
npm create tauri-app@latest frontend
# 选择: Vue + TypeScript + npm

# 3. 安装依赖
cd frontend
npm install

# 4. 安装marked（Markdown渲染）
npm install marked
```

### 替换前端代码

将提供的 `App.vue` 代码复制到 `frontend/src/App.vue`

### 配置Tauri

编辑 `frontend/src-tauri/tauri.conf.json`：

```json
{
  "tauri": {
    "allowlist": {
      "http": {
        "all": true,
        "scope": ["http://localhost:8000/**"]
      }
    }
  }
}
```

### 启动前端

**方式1：使用启动脚本**
```bash
scripts\start_frontend.bat
```

**方式2：手动启动**
```bash
cd frontend
npm run tauri dev
```

---

## 四、测试API

### 使用curl测试

```bash
# 健康检查
curl http://localhost:8000/api/health

# 聊天
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"写一个快速排序\"}"

# 获取统计
curl http://localhost:8000/api/stats
```

### 使用Python测试

```python
import requests

# 聊天
response = requests.post(
    "http://localhost:8000/api/chat",
    json={"message": "写一个快速排序"}
)
print(response.json())

# 获取统计
stats = requests.get("http://localhost:8000/api/stats")
print(stats.json())
```

---

## 五、完整启动流程

### 方式1：一键启动

```bash
scripts\start_all.bat
```

这会同时启动后端和前端服务。

### 方式2：分步启动

**终端1 - 后端**：
```bash
scripts\start_backend.bat
```

**终端2 - 前端**：
```bash
scripts\start_frontend.bat
```

---

## 六、后续扩展（Phase 2-4）

### Phase 2: 文件上传
- 添加 `/api/upload` 端点
- 前端集成文件选择器

### Phase 3: 模型管理
- 添加 `/api/models/switch` 端点
- 前端侧边栏模型切换

### Phase 4: 规则管理
- 添加 `/api/rules` 端点
- 前端规则列表和编辑界面

---

## 七、打包发布

### 打包桌面应用

```bash
cd frontend
npm run tauri build
```

生成的安装包位于 `frontend/src-tauri/target/release/bundle/`

---

## 八、常见问题

### Q1: 后端启动失败
**A**: 检查依赖是否安装：
```bash
pip install fastapi uvicorn sse-starlette
```

### Q2: 前端无法连接后端
**A**: 
1. 确认后端已启动（访问 http://localhost:8000/api/health）
2. 检查CORS配置
3. 检查Tauri allowlist配置

### Q3: 模型加载失败
**A**: 
1. 确认Ollama服务已启动
2. 确认模型已下载：`ollama pull mindchat`

---

## 九、开发建议

1. **后端开发**：修改 `backend/main.py` 后自动重载
2. **前端开发**：修改 `frontend/src/` 后自动热更新
3. **调试工具**：使用浏览器开发者工具和FastAPI文档

---

**当前状态**: Phase 1 后端已完成，前端需初始化Tauri项目