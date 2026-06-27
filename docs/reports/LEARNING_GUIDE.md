# 联盟拓荒者 - 学习系统使用指南

## 一、系统概述

联盟拓荒者现在具备**主动学习能力**，能够：

1. **从文件学习**：自动扫描文件夹，提取函数、类、代码片段等知识
2. **从对话学习**：用户点赞时自动保存问答到知识库
3. **外部学习**：不确定时主动向搜索引擎和更强AI请教
4. **元认知学习**：学习如何更好地解析对话、积累经验
5. **主动汇报**：自动通知学习成果
6. **实时监听**：基于watchdog的文件变化监听
7. **智能调度**：优先级队列和学习任务管理

---

## 二、学习子系统架构

```
┌─────────────────┐
│  CLI命令/API    │ ← 用户交互层
└────────┬────────┘
         │
┌────────▼────────┐
│  学习引擎       │ ← 任务队列、优先级调度、模式管理
│  (Engine)       │
└────────┬────────┘
         │
┌────────▼────────┐
│  文件监听器     │ ← watchdog实时监听文件变化
│  (Monitor)      │
└────────┬────────┘
         │
┌────────▼────────┐
│  文件夹学习器   │ ← 批量扫描、状态记录
│  (Folder)       │
└────────┬────────┘
         │
┌────────▼────────┐
│  增强学习器     │ ← 知识提取、规则生成
│  (Enhanced)     │
└────────┬────────┘
         │
┌────────▼────────┐
│  外部学习器     │ ← 搜索引擎、LLM请教
│  (External)     │
└─────────────────┘
```

---

## 三、学习模式

### 3.1 三种学习模式

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `auto` | 自动学习所有文件 | 初次设置、全量学习 |
| `smart` | 智能学习（推荐） | 日常使用、平衡性能 |
| `manual` | 仅学习用户指定的文件 | 精确控制、测试 |

### 3.2 学习优先级

| 优先级 | 文件类型 | 示例 |
|--------|----------|------|
| `HIGH` (1) | 核心业务代码 | main.py, app.py, api.py, core/ |
| `NORMAL` (2) | 普通代码文件 | utils/, helpers/ |
| `LOW` (3) | 文档、配置 | README.md, config.yaml |

### 3.3 排除规则

以下文件/目录自动排除：
- 测试文件：`test_`, `_test.py`, `tests/`
- 缓存目录：`__pycache__`, `.git`, `node_modules`
- 虚拟环境：`venv`, `env`, `.venv`

---

## 四、CLI命令

### 4.1 学习状态

```bash
:learning status
```

显示学习引擎和文件监听器的完整状态。

### 4.2 切换模式

```bash
:learning mode auto    # 自动模式
:learning mode smart   # 智能模式（推荐）
:learning mode manual  # 手动模式
```

### 4.3 添加学习路径

```bash
:learning add /path/to/folder
```

添加文件夹并自动扫描所有文件。

### 4.4 移除学习路径

```bash
:learning remove /path/to/folder
```

### 4.5 强制学习文件

```bash
:learning force /path/to/file.py
```

立即学习指定文件，不受模式限制。

### 4.6 暂停/恢复学习

```bash
:learning pause   # 暂停学习
:learning resume  # 恢复学习
```

### 4.7 查看知识库

```bash
:learning knowledge    # 列出知识条目
:learning tools        # 列出自动生成的工具
:learning tasks        # 列出最近的学习任务
```

---

## 五、API接口

### 5.1 学习系统状态

```http
GET /api/learning/status
```

**响应**：
```json
{
  "success": true,
  "engine": {
    "mode": "smart",
    "is_running": true,
    "total_tasks": 42,
    "completed_tasks": 38,
    "total_knowledge": 156
  },
  "monitor": {
    "is_running": true,
    "total_paths": 2
  }
}
```

### 5.2 设置学习模式

```http
POST /api/learning/mode
Content-Type: application/json

{
  "mode": "smart"
}
```

### 5.3 添加学习路径

```http
POST /api/learning/add
Content-Type: application/json

{
  "path": "/path/to/folder",
  "priority": "high"
}
```

### 5.4 强制学习文件

```http
POST /api/learning/force
Content-Type: application/json

{
  "path": "/path/to/file.py"
}
```

### 5.5 暂停/恢复学习

```http
POST /api/learning/pause
POST /api/learning/resume
```

### 5.6 获取学习任务

```http
GET /api/learning/tasks?limit=20
```

### 5.7 获取知识库

```http
GET /api/learning/knowledge?limit=50
```

### 5.8 获取自动生成的工具

```http
GET /api/learning/tools
```

---

## 六、文件夹学习

### 6.1 设置学习根目录

**API接口**：
```http
POST /api/folder/set_root
Content-Type: application/json

{
  "path": "E:/my_knowledge"
}
```

**对话方式**：
```
用户：设置学习文件夹为 E:/my_knowledge
系统：已设置学习根目录: E:/my_knowledge
```

### 6.2 扫描并学习

**API接口**：
```http
POST /api/folder/scan
Content-Type: application/json

{
  "start_monitor": true,
  "interval": 300
}
```

**支持的文件类型**：
- Python: `.py`
- Markdown: `.md`
- 文本: `.txt`
- 配置: `.json`, `.yaml`, `.yml`, `.toml`, `.ini`
- Web: `.js`, `.ts`, `.html`, `.css`
- 其他: `.csv`, `.rst`, `.xml`, `.sh`, `.bat`

**忽略的目录**：
- `__pycache__`, `node_modules`, `.git`
- `venv`, `env`, `.venv`, `.env`
- `dist`, `build`

### 6.3 查询学习状态

**API接口**：
```http
GET /api/folder/status
```

**对话方式**：
```
用户：学习进度
系统：📚 文件夹学习进度报告：
- 学习根目录: E:/my_knowledge
- 已扫描文件: 42 个
- 成功学习: 38 个
- 学习失败: 4 个
- 提取知识: 156 条
- 最后扫描: 2026-06-15T10:30:00
- 后台监控: 运行中
```

### 6.4 查看失败文件

**API接口**：
```http
GET /api/folder/failed
```

**对话方式**：
```
用户：显示失败的文件
系统：❌ 学习失败的文件：
- large_data.bin: 不支持的文件类型
- notes.doc: 非文本格式
```

### 6.5 重新学习文件

**API接口**：
```http
POST /api/folder/relearn
Content-Type: application/json

{
  "pattern": "test.py"
}
```

**对话方式**：
```
用户：重新学习 test.py
系统：✅ 已重新学习 test.py，提取了3条知识
```

### 6.6 后台监控

**启动监控**：
```http
POST /api/folder/monitor/start
Content-Type: application/json

{
  "interval": 300
}
```

**停止监控**：
```http
POST /api/folder/monitor/stop
```

---

## 七、外部学习

### 7.1 自动触发条件

系统会在以下情况自动触发外部学习：

1. **深度关键词**：深入、详细解释、原理、经验等
2. **低置信度**：回复包含"不确定"、"可能"等
3. **置信度过低**：confidence < 0.5
4. **知识库为空**：没有相关知识
5. **元认知问题**：如何学习、学习机制等
6. **研究关键词**：研究、分析一下等

### 7.2 配置API密钥

编辑 `.env.external` 文件：

```env
# 搜索引擎配置
SEARCH_API_KEY=your_google_api_key
SEARCH_ENGINE_ID=your_search_engine_id

# LLM配置
LLM_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4
LLM_BASE_URL=https://api.openai.com/v1
```

### 7.3 学习内容类型

- `external`：外部搜索结果
- `meta`：元认知知识（对话解析策略、经验教训）

---

## 八、对话学习

### 8.1 自动学习

用户点赞👍时，系统自动保存问答到知识库。

### 8.2 知识检索

对话时自动检索相关知识并应用。

---

## 九、自动好奇心系统

### 9.1 后台定期扫描

自动扫描低质量但频繁访问的知识，尝试改进。

### 9.2 补充未解答问题

检测常见但未解答的问题模式，主动学习补充。

---

## 十、知识库统计

当前知识库：
- 总知识：28条
- 问答知识：8条
- 函数知识：6条
- 外部学习：4条
- 元认知知识：4条

---

## 十一、使用示例

### 示例1：通过CLI使用

```bash
# 查看状态
:learning status

# 添加学习路径
:learning add E:/my_project

# 切换模式
:learning mode smart

# 强制学习
:learning force E:/my_project/main.py

# 查看知识
:learning knowledge
```

### 示例2：通过API使用

```bash
# 添加学习路径
curl -X POST http://localhost:8000/api/learning/add \
  -H "Content-Type: application/json" \
  -d '{"path": "E:/my_project", "priority": "high"}'

# 查看状态
curl http://localhost:8000/api/learning/status

# 获取知识库
curl http://localhost:8000/api/learning/knowledge
```

### 示例3：通过对话使用

```
用户：学习进度
系统：📚 文件夹学习进度报告...

用户：最近学习了哪些文件？
系统：📖 最近学习的文件：
✅ main.py (3条知识)
✅ utils.py (5条知识)

用户：重新学习 utils.py
系统：✅ 已重新学习 utils.py，提取了5条知识
```

---

## 十二、最佳实践

1. **使用智能模式**：平衡性能和学习效果
2. **设置合理的监控间隔**：建议300秒（5分钟）
3. **优先级配置**：核心代码设为高优先级
4. **定期检查失败文件**：修复编码或格式问题
5. **配置真实API密钥**：获得更准确的外部学习结果
6. **主动询问学习成果**：让系统汇报学习进度
7. **点赞有价值的回答**：帮助系统积累高质量知识

---

## 十三、故障排查

### 问题1：学习失败

**原因**：文件编码问题、二进制文件、格式不支持

**解决**：
- 转换为UTF-8编码
- 转换为支持的格式（如.txt, .md）
- 检查文件是否为文本文件

### 问题2：外部学习无结果

**原因**：未配置API密钥

**解决**：编辑 `.env.external` 配置真实API密钥

### 问题3：后台监控不工作

**原因**：未启动或已停止

**解决**：
```http
POST /api/learning/resume
```

### 问题4：任务队列堵塞

**原因**：大量文件待处理

**解决**：
```bash
:learning mode manual  # 切换到手动模式
:learning force <file> # 逐个学习重要文件
```

---

## 十四、API接口汇总

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/learning/status` | GET | 获取学习系统状态 |
| `/api/learning/mode` | POST | 设置学习模式 |
| `/api/learning/add` | POST | 添加学习路径 |
| `/api/learning/remove` | POST | 移除学习路径 |
| `/api/learning/force` | POST | 强制学习文件 |
| `/api/learning/pause` | POST | 暂停学习 |
| `/api/learning/resume` | POST | 恢复学习 |
| `/api/learning/tasks` | GET | 获取学习任务 |
| `/api/learning/knowledge` | GET | 获取知识库 |
| `/api/learning/tools` | GET | 获取工具列表 |
| `/api/folder/set_root` | POST | 设置根目录 |
| `/api/folder/scan` | POST | 扫描学习 |
| `/api/folder/status` | GET | 学习状态 |
| `/api/folder/failed` | GET | 失败文件 |
| `/api/folder/recent` | GET | 最近学习 |
| `/api/folder/relearn` | POST | 重新学习 |
| `/api/folder/monitor/start` | POST | 启动监控 |
| `/api/folder/monitor/stop` | POST | 停止监控 |

---

## 十五、系统优势

### 15.1 透明可控
- 实时查看学习状态
- 清晰的任务队列
- 详细的学习日志

### 15.2 智能调度
- 优先级队列
- 三种学习模式
- 自动排除无关文件

### 15.3 实时监听
- watchdog文件变化监听
- 自动触发学习
- 防抖机制

### 15.4 持续成长
- 知识积累
- 规则生成
- 工具自动生成
- 元认知学习

---

**让AI主动学习，持续成长，与你共同进步！**

### 2.1 设置学习根目录

**API接口**：
```http
POST /api/folder/set_root
Content-Type: application/json

{
  "path": "E:/my_knowledge"
}
```

**对话方式**：
```
用户：设置学习文件夹为 E:/my_knowledge
系统：已设置学习根目录: E:/my_knowledge
```

### 2.2 扫描并学习

**API接口**：
```http
POST /api/folder/scan
Content-Type: application/json

{
  "start_monitor": true,
  "interval": 300
}
```

**支持的文件类型**：
- Python: `.py`
- Markdown: `.md`
- 文本: `.txt`
- 配置: `.json`, `.yaml`, `.yml`, `.toml`, `.ini`
- Web: `.js`, `.ts`, `.html`, `.css`
- 其他: `.csv`, `.rst`, `.xml`, `.sh`, `.bat`

**忽略的目录**：
- `__pycache__`, `node_modules`, `.git`
- `venv`, `env`, `.venv`, `.env`
- `dist`, `build`

### 2.3 查询学习状态

**API接口**：
```http
GET /api/folder/status
```

**对话方式**：
```
用户：学习进度
系统：📚 文件夹学习进度报告：
- 学习根目录: E:/my_knowledge
- 已扫描文件: 42 个
- 成功学习: 38 个
- 学习失败: 4 个
- 提取知识: 156 条
- 最后扫描: 2026-06-15T10:30:00
- 后台监控: 运行中
```

### 2.4 查看失败文件

**API接口**：
```http
GET /api/folder/failed
```

**对话方式**：
```
用户：显示失败的文件
系统：❌ 学习失败的文件：
- large_data.bin: 不支持的文件类型
- notes.doc: 非文本格式
```

### 2.5 重新学习文件

**API接口**：
```http
POST /api/folder/relearn
Content-Type: application/json

{
  "pattern": "test.py"
}
```

**对话方式**：
```
用户：重新学习 test.py
系统：✅ 已重新学习 test.py，提取了3条知识
```

### 2.6 后台监控

**启动监控**：
```http
POST /api/folder/monitor/start
Content-Type: application/json

{
  "interval": 300
}
```

**停止监控**：
```http
POST /api/folder/monitor/stop
```

---

## 三、外部学习

### 3.1 自动触发条件

系统会在以下情况自动触发外部学习：

1. **深度关键词**：深入、详细解释、原理、经验等
2. **低置信度**：回复包含"不确定"、"可能"等
3. **置信度过低**：confidence < 0.5
4. **知识库为空**：没有相关知识
5. **元认知问题**：如何学习、学习机制等
6. **研究关键词**：研究、分析一下等

### 3.2 配置API密钥

编辑 `.env.external` 文件：

```env
# 搜索引擎配置
SEARCH_API_KEY=your_google_api_key
SEARCH_ENGINE_ID=your_search_engine_id

# LLM配置
LLM_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4
LLM_BASE_URL=https://api.openai.com/v1
```

### 3.3 学习内容类型

- `external`：外部搜索结果
- `meta`：元认知知识（对话解析策略、经验教训）

---

## 四、对话学习

### 4.1 自动学习

用户点赞👍时，系统自动保存问答到知识库。

### 4.2 知识检索

对话时自动检索相关知识并应用。

---

## 五、自动好奇心系统

### 5.1 后台定期扫描

自动扫描低质量但频繁访问的知识，尝试改进。

### 5.2 补充未解答问题

检测常见但未解答的问题模式，主动学习补充。

---

## 六、知识库统计

当前知识库：
- 总知识：28条
- 问答知识：8条
- 函数知识：6条
- 外部学习：4条
- 元认知知识：4条

---

## 七、使用示例

### 示例1：设置并开始学习

```bash
# 1. 设置学习根目录
curl -X POST http://localhost:8000/api/folder/set_root \
  -H "Content-Type: application/json" \
  -d '{"path": "E:/my_project"}'

# 2. 扫描并学习
curl -X POST http://localhost:8000/api/folder/scan \
  -H "Content-Type: application/json" \
  -d '{"start_monitor": true, "interval": 300}'

# 3. 查看状态
curl http://localhost:8000/api/folder/status
```

### 示例2：对话查询

```
用户：学习进度
系统：📚 文件夹学习进度报告...

用户：最近学习了哪些文件？
系统：📖 最近学习的文件：
✅ main.py (3条知识)
✅ utils.py (5条知识)
✅ config.yaml (1条知识)

用户：重新学习 utils.py
系统：✅ 已重新学习 utils.py，提取了5条知识
```

---

## 八、最佳实践

1. **设置合理的监控间隔**：建议300秒（5分钟）
2. **定期检查失败文件**：修复编码或格式问题
3. **配置真实API密钥**：获得更准确的外部学习结果
4. **主动询问学习成果**：让系统汇报学习进度
5. **点赞有价值的回答**：帮助系统积累高质量知识

---

## 九、故障排查

### 问题1：学习失败

**原因**：文件编码问题、二进制文件、格式不支持

**解决**：
- 转换为UTF-8编码
- 转换为支持的格式（如.txt, .md）
- 检查文件是否为文本文件

### 问题2：外部学习无结果

**原因**：未配置API密钥

**解决**：编辑 `.env.external` 配置真实API密钥

### 问题3：后台监控不工作

**原因**：未启动或已停止

**解决**：
```http
POST /api/folder/monitor/start
```

---

## 十、API接口汇总

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/folder/set_root` | POST | 设置学习根目录 |
| `/api/folder/scan` | POST | 扫描并学习 |
| `/api/folder/status` | GET | 获取学习状态 |
| `/api/folder/failed` | GET | 获取失败文件 |
| `/api/folder/recent` | GET | 获取最近学习 |
| `/api/folder/relearn` | POST | 重新学习文件 |
| `/api/folder/monitor/start` | POST | 启动后台监控 |
| `/api/folder/monitor/stop` | POST | 停止后台监控 |

---

**让AI主动学习，持续成长！**