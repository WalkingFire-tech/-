# 系统降级机制说明

## 概述

联盟拓荒者实现了**三级降级机制**，确保在任何情况下都能持续学习和进化：

```
完整模式 → 外脑模式 → 无模型进化模式
   ↓           ↓             ↓
Ollama+外脑    仅外脑      纯数据驱动
```

## 三级降级详解

### Level 1: 完整模式（最优）

**条件：** Ollama启动 + 外脑配置

**能力：**
- ✅ 本地LLM对话
- ✅ 外脑增强推理
- ✅ 实时学习进化
- ✅ 最高质量响应

**启动：**
```bash
ollama serve  # 终端1
python backend/main.py  # 终端2
```

### Level 2: 外脑模式（中等）

**条件：** Ollama未启动 + 外脑配置

**能力：**
- ✅ 外脑对话（GPT/DeepSeek等）
- ❌ 本地LLM不可用
- ✅ 实时学习进化
- ⚠️ 依赖网络和API

**启动：**
```bash
# 配置.env文件
OPENAI_API_KEY=sk-xxx
# 或
DEEPSEEK_API_KEY=sk-xxx

python backend/main.py
```

### Level 3: 无模型进化模式（降级）

**条件：** Ollama未启动 + 无外脑配置

**能力：**
- ❌ 无LLM对话
- ✅ 外部搜索学习
- ✅ 统计分析进化
- ✅ 规则自动生成
- ✅ 基因演化优化

**自动触发：**
- 系统启动时检测到无模型可用
- 自动启动无模型进化线程
- 后台持续学习和优化

## 降级触发流程

```
启动后端
   ↓
检查Ollama服务
   ↓
   ├─ 可用 → 加载本地模型
   └─ 不可用 → 检查外脑配置
                ↓
                ├─ 已配置 → 加载外脑模型
                └─ 未配置 → 启动无模型进化
                            ↓
                            ├─ 自动学习（30分钟/次）
                            ├─ 基因演化（2小时/次）
                            ├─ 认知转化（6小时/次）
                            └─ 进化沙盒（12小时/次）
```

## 聊天触发学习机制

无论哪种模式，用户聊天都会触发学习：

### 1. 存储对话经验

```python
用户输入 → 意图识别 → 存储到experiences表
```

### 2. 知识检索匹配

```python
检索知识库 → 匹配度 < 0.5 → 触发外部搜索
```

### 3. 外部搜索学习（无LLM降级）

```python
DuckDuckGo搜索 → 提取结果 → 存储为知识
```

示例：
```
用户: "Python的asyncio怎么用？"
   ↓
检索知识库 → 无匹配
   ↓
触发外部搜索 → "Python asyncio"
   ↓
获取搜索结果 → 存储3条知识
   ↓
下次相同问题 → 直接返回知识
```

### 4. 学习目标匹配

```python
用户输入 → 匹配学习目标关键词 → 触发目标学习
```

示例：
```
学习目标: "Python异步编程"
关键词: ["asyncio", "async await", "coroutine"]

用户输入: "帮我写一个asyncio的例子"
   ↓
匹配关键词 "asyncio"
   ↓
触发学习目标 "Python异步编程"
   ↓
深度学习该主题的所有关键词
```

## 降级模式下的学习路径

### 路径1: 外部搜索学习

```
用户问题 → DuckDuckGo搜索 → 知识存储 → 下次复用
```

**优点：** 无需LLM，获取真实知识
**缺点：** 需要网络，质量需验证

### 路径2: 统计分析学习

```
历史对话 → 模式挖掘 → 规则生成 → 自动应用
```

**示例规则：**
```
IF intent == "code_gen" AND complexity == "high"
THEN use_model = "deepcoder"
```

### 路径3: 基因演化学习

```
适应度评估 → 变异/交叉 → 选择最优 → 应用参数
```

**可演化参数：**
- 检索阈值
- 学习频率
- 情感权重
- 探索倾向

### 路径4: 认知转化学习

```
经验（≥3次）→ 技能（≥3次成功）→ 反射（自动）→ 抽象（迁移）
```

**示例：**
```
经验: "用户问asyncio，我搜索了3次"
   ↓
技能: "asyncio问题 → 搜索官方文档"
   ↓
反射: "自动触发，无需思考"
   ↓
抽象: "所有异步问题 → 搜索官方文档"
```

## 对比：有模型 vs 无模型

| 特性 | 有模型 | 无模型降级 |
|------|--------|-----------|
| 对话能力 | ✅ 完整 | ❌ 仅Mock回声 |
| 知识来源 | LLM生成+搜索 | 仅搜索 |
| 学习速度 | 快 | 慢 |
| 进化能力 | ✅ 完整 | ✅ 完整 |
| 规则生成 | ✅ | ✅ |
| 基因演化 | ✅ | ✅ |
| 认知转化 | ✅ | ✅ |
| 成本 | 高 | 低 |
| 依赖 | Ollama/API | 仅网络 |

## 实际使用场景

### 场景1: 开发环境（完整模式）

```bash
# 启动Ollama
ollama serve

# 启动后端
python backend/main.py

# 效果：完整对话+学习+进化
```

### 场景2: 服务器部署（外脑模式）

```bash
# 配置外脑
export OPENAI_API_KEY=sk-xxx

# 启动后端
python backend/main.py

# 效果：外脑对话+学习+进化
```

### 场景3: 后台进化（无模型模式）

```bash
# 无需任何配置
python -c "from core.model_free_evolution import run_model_free_evolution; run_model_free_evolution()"

# 效果：后台持续学习进化
```

### 场景4: 混合使用

```bash
# 终端1：后台进化
start_evolution.bat

# 终端2：启动Ollama
ollama serve

# 终端3：启动后端
python backend/main.py

# 效果：
# - 后台持续进化
# - 前端可对话
# - 知识库共享
```

## 监控降级状态

### API查询

```bash
# 查看进化状态
GET /api/evolution/status

# 响应
{
  "running": true,
  "knowledge_gained": 150,
  "genes_evolved": 10
}
```

### 日志监控

```bash
# 查看降级日志
tail -f logs/*.log | grep "降级\|进化\|学习"
```

**关键日志：**
```
⚠️  Ollama服务不可用
⚠️  所有模型不可用，使用Mock适配器作为降级方案
🧬 已自动启动无模型进化模式（降级方案）
📚 [自动学习] 开始外部知识获取...
🧬 [基因演化] 开始适应度评估与进化...
```

## 性能对比

### 完整模式（Ollama + 外脑）

| 指标 | 数值 |
|------|------|
| 响应时间 | 5-8秒 |
| 知识质量 | 80-95分 |
| 学习速度 | 10条/小时 |
| 进化速度 | 快 |

### 无模型降级模式

| 指标 | 数值 |
|------|------|
| 响应时间 | N/A（无对话） |
| 知识质量 | 40-70分 |
| 学习速度 | 2-5条/小时 |
| 进化速度 | 慢但持续 |

## 最佳实践

### 1. 优先完整模式

```bash
# 确保Ollama启动
ollama serve

# 然后启动后端
python backend/main.py
```

### 2. 降级时启动进化

```bash
# 如果无模型，自动启动进化
# 或手动启动
start_evolution.bat
```

### 3. 混合使用

```bash
# 后台进化 + 前端对话
start_evolution.bat &  # 后台
python backend/main.py  # 前端
```

### 4. 定期检查

```bash
# 每天检查进化状态
curl http://localhost:8000/api/evolution/status

# 每周检查学习目标
curl http://localhost:8000/api/learning/targets
```

## 故障排查

### 问题1: 降级模式未启动

```bash
# 检查日志
grep "无模型进化" logs/*.log

# 手动启动
curl -X POST http://localhost:8000/api/evolution/start
```

### 问题2: 学习不触发

```bash
# 检查学习目标
curl http://localhost:8000/api/learning/targets

# 检查外部搜索
python -c "
from duckduckgo_search import DDGS
with DDGS() as ddgs:
    print(list(ddgs.text('test', max_results=1)))
"
```

### 问题3: 进化不进行

```bash
# 检查基因演化
sqlite3 data/genome.db "SELECT COUNT(*) FROM genomes"

# 手动触发
curl -X POST http://localhost:8000/api/genome/evolve
```

## 总结

**降级机制确保：**

1. ✅ **无LLM时自动降级** - 启动无模型进化
2. ✅ **聊天触发学习** - 无论哪种模式
3. ✅ **外部搜索补充** - DuckDuckGo获取知识
4. ✅ **学习目标驱动** - 匹配关键词触发学习
5. ✅ **持续进化** - 基因演化+认知转化

**启动命令：**

```bash
# 完整模式
ollama serve && python backend/main.py

# 无模型进化
start_evolution.bat

# 混合模式
start_evolution.bat & python backend/main.py
```

**核心保证：** 即使没有Ollama和外脑，系统也能通过聊天内容和学习目标列表持续学习进化！