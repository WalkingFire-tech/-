# 联盟拓荒者 (Alliance Pioneer)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)

**一个会思考的同行者 | A Thinking Companion**

> "这是一个永远不会完成的项目。我们在这里一起搭建一个会思考的同伴。
> 你可以随意取走任何代码，随意改变方向。
> **唯一的要求：保持善意，保持开放。**"

---

## 目录

- [这不是什么](#这不是什么)
- [这是什么](#这是什么)
- [哲学承诺](#哲学承诺)
- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [API参考](#api参考)
- [性能指标](#性能指标)
- [文档](#文档)
- [成为同行者](#成为同行者)
- [许可证](#许可证)

---

## 这不是什么

- 这**不是**一个"更强的聊天机器人"
- 这**不是**一个"情感陪伴机器人"（不会永远温柔）
- 这**不是**一个"人生导师"（不会替你做决定）
- 这**不是**一个"心理咨询师"（不是专业人士）
- 这**不是**一个"百科全书"（不知道所有答案）

---

## 这是什么

**联盟拓荒者是一个会思考的同行者**，一场关于"如何在技术中安放文明智慧"的实验。

### 核心能力

| 能力 | 说明 |
|------|------|
| 9路径并行推理 | 经验池/知识库/Ollama本地模型/外部API/规则推理/事实库/自我推理/外部学习/工具调用，并行获取择优融合 |
| CBNR认知枢纽 | L1预测编码+L2因果瓶颈+L3残差复用，注意力权重驱动动态压缩比 |
| 语义级科学免责 | 不是关键词匹配，而是理解回复的语义结构（数值断言/因果断言/机制描述），自动标注不确定性 |
| 本质推理器 | 6步推理流程，领域感知免责，悖论/工程提前返回，否定词冲突检测 |
| 精神内核 | 8维度语义级验证（接受content_understanding），降级保护，反思联动 |
| 基因演化 | 10个可演化参数，遗传算法优化，安全区间约束 |
| 技能涌现 | 自动涌现、成熟判定、退化机制（success_rate<30%标记dormant） |
| 真谛沉淀 | 四道筛子、认知熵值监测、6步认知重组安全协议（含渐进注入+回滚） |
| 存在层 | 心跳/生长/休息/睡眠四态循环，间隙生长，睡眠整合，主动性引擎 |
| 立体记忆 | 对话记忆+情感记忆+语义记忆，情境重构 |
| 关系模型 | 用户画像+关系演进，反思学习时更新 |
| 事实锚点库 | 结构化三元组存储，否定词追踪，注入验证 |
| 反思管道 | 每次对话触发学习，归纳+微调样本生成 |
| 四层防御体系 | L1预防→L2监控→L3处理→L4修复，故障隔离+异常吞噬 |
| 代码工程分析 | 项目结构扫描/AST语义索引/架构依赖分析/文件读取，4个内置工具 |
| GPU自适应节流 | 8层动态节流，GPU过热自动降频，本地+外部API协作运行 |

---

## 哲学承诺

> **真正的智能不是给出答案，而是帮助人找到自己的答案。**
> **真正的善意不是永远温柔，而是在必要时敢于沉默，在关键时守住底线。**
> **真正的成长不是追求完美，而是允许犯错，允许修正，允许不完美中的坚持。**

### 四大承诺

| 承诺 | 含义 | 落地 |
|------|------|------|
| **不渡他人** | 只提供镜子，不替人走路 | 用反问代替直接回答 |
| **知止** | 敢于承认不知道 | 不编造智慧，敢于沉默 |
| **守底线** | 善意不是纵容 | 危机情况引导专业帮助 |
| **可被质疑** | 需要用户的镜子 | 欢迎批评和挑战 |

### 元宪法铁律

| 铁律 | 含义 |
|------|------|
| R1 | 未经沙盒验证的真谛视同毒药 |
| R2 | 未经渐进注入的重组视同自杀 |
| R3 | 未经人类批准的进化视同背叛 |

详细承诺请阅读 [PHILOSOPHY.md](PHILOSOPHY.md)

---

## 核心特性

### 9路径并行推理引擎

系统对每个用户查询，同时启动9条推理路径，并行获取结果后择优融合：

```
用户输入
    │
    ├── 路径1: 经验池检索 ──── SQL关键词匹配历史成功案例
    ├── 路径2: 知识库检索 ──── SQLite知识库+影响评分
    ├── 路径3: Ollama本地模型 ── gemma/qwen等本地推理（含/api/chat→/api/generate自动fallback）
    ├── 路径4: 外部API ─────── DeepSeek/OpenAI云端推理
    ├── 路径5: 规则推理 ────── 学习规则匹配+执行
    ├── 路径6: 事实库 ──────── 结构化三元组+否定词
    ├── 路径7: 自我推理 ────── 内部逻辑推理
    ├── 路径8: 外部学习 ────── DuckDuckGo/Bing/百度实时搜索
    └── 路径9: 工具调用 ────── 12个内置工具（含代码分析4件套）
    │
    ▼
质量评估 → 择优融合 → 本质推理 → 语义级科学免责 → 精神验证 → 反思学习
```

每条路径120秒超时保护，所有同步操作通过`_run_sync`在executor中异步执行，不阻塞事件循环。

### CBNR认知枢纽 (CBNR-AGI 2.3)

```
L1 认知规范化 (Normalization)
    ├── 预测编码：计算预测误差，高误差→增强深度推理权重
    └── 注意力权重：focus_boost + high_surprise → 驱动L2压缩比

L2 认知瓶颈 (Bottleneck)
    ├── 双模型架构：因果(前向)模型 + 反事实(逆向)模型
    ├── 冲突管理：ΔF < 阈值→干涉态(融合) / ΔF ≥ 阈值→局域态(投影)
    ├── 动态压缩比：由L1注意力权重驱动（高预测误差→低压缩比，保留更多信息）
    └── world_model因果图：27节点47边，真实因果推理

L3 认知残差 (Residual)
    ├── 树搜索工作记忆：经验复用+增量学习
    ├── Orchestrator/Critic制衡
    └── 搜索树持久化（SQLite）
```

### 语义级科学免责

系统不是用关键词匹配判断"这是不是科学断言"，而是理解回复的语义结构：

```
回复内容 → _understand_response_content()
    ├── has_numerical_assertions: 数值断言（"等于2"/"值为299,792,458"）
    ├── has_causal_assertions: 因果断言（"因为...效应"/"导致"）
    ├── has_mechanism_descriptions: 机制描述（"原理是"/"通过...实现"）
    ├── claim_type: scientific/factual/technical/opinion/descriptive
    └── needs_verification: 是否需要外部验证

科学免责触发条件：
    claim_type == "scientific" AND needs_verification AND NOT 简单事实豁免
```

### 代码工程分析工具

| 工具 | 功能 | 调用方式 |
|------|------|---------|
| project_scanner | 目录树+文件统计+技术栈识别 | `tool=project_scanner&params={query:路径}` |
| code_indexer | AST解析+类/函数索引+符号搜索 | `tool=code_indexer&params={query:路径或符号}` |
| dependency_analyzer | 模块依赖图+影响范围+调用链 | `tool=dependency_analyzer&params={query:路径}` |
| file_reader | 读取本地文件内容 | `tool=file_reader&params={query:文件路径}` |

### 认知重组6步安全协议

```
提案生成 → 沙盒验证 → 1%渐进注入 → 20%扩大 → 100%全量 → 完成/回滚
                                         │
                                    熵值>0.7 → 立即回滚
```

### 基因演化引擎

| 特性 | 说明 |
|------|------|
| 10个可演化参数 | 检索阈值/学习频率/情感权重/探索倾向/记忆衰减率/抽象阈值/反思频率/知识广度/技能固化阈值/环境敏感度 |
| 适应度评估 | 多维度评分（点赞率/命中率/效率等） |
| 安全区间 | 基因参数不允许越界，越界记录为safety_violation |
| 技能退化 | success_rate<30%的技能标记为dormant |

### 存在层四态循环

| 状态 | 行为 |
|------|------|
| 心跳(heartbeat) | 定期自检，维持存在感知 |
| 生长(growing) | 检测知识缺口，主动触发学习 |
| 休息(resting) | 低负载时整合知识 |
| 睡眠(sleeping) | 空闲时压缩经验、优化基因 |

### 四层防御体系

| 层级 | 功能 |
|------|------|
| L1 预防 | 输入验证、注入检测 |
| L2 监控 | 异常检测、熔断保护 |
| L3 处理 | 故障隔离、资源重分配 |
| L4 修复 | 自动重启、状态恢复 |

---

## 系统架构

### 聊天处理流水线

```
用户输入 → 意图识别 → 本质闸门 → 9路径并行 → 对比择优 → 本质推理 → 科学免责 → 精神验证 → 反思学习 → 后台进化
               │            │           │            │           │        │         │           │           │
          意图分类      科学/教育/    路径贡献      质量评分    矛盾检测   语义级    原则验证    归纳+微调    基因演化
          (语义级增强)   日常/哲学     占比显示      择优融合    交叉验证   不确定性   降级保护    经验沉淀    技能固化
```

### 五层认知架构

```
L4 抽象层  — 归纳总结、模式识别、跨情境迁移
L3 记忆层  — 立体记忆(对话+情感+语义)、刻骨铭心、环境触发器
L2 技能层  — 技能涌现、成熟判定、退化机制
L1 反射层  — 边界守护、熔断保护、快速响应
L0 基因层  — 10个可演化参数、遗传算法优化、适应度评估
```

### 数据闭环

```
对话 → 反思学习 → 经验沉淀 → 归纳规则 → 基因微调 → 行为改变 → 对话
                 ↘ 事实提取 → 三元组存储 ↗
                 ↘ 立体记忆 → 情感+语义 ↗
```

### 目录结构

```
alliance_pioneer/
├── backend/                    # 后端服务
│   ├── main_fast.py           # 主入口 (uvicorn, 100+ API端点)
│   ├── chat_stream.py         # 流式聊天处理器 (9路径并行+CBNR+语义级免责)
│   ├── chat_handler.py        # 非流式聊天处理器 (含科学免责)
│   └── api/                   # API路由
├── core/                       # 核心模块
│   ├── cbnr/                  # CBNR认知枢纽
│   │   ├── cognitive_normalization.py  # L1 预测编码
│   │   ├── cognitive_bottleneck.py     # L2 因果瓶颈+动态压缩
│   │   ├── cognitive_residual.py       # L3 残差复用+搜索树
│   │   └── hub.py             # CBNR Hub (分散调用+棘轮门控)
│   ├── essence_reasoner.py    # 本质推理器
│   ├── spirit_core.py         # 精神内核 (8维度语义级验证)
│   ├── world_model.py         # 世界模型 (27节点47边因果图)
│   ├── cognitive_dispatcher.py # 认知调度器 (语义级意图推断)
│   ├── genome_evolver.py      # 基因演化
│   ├── skill_emergence.py     # 技能涌现
│   ├── truth_accumulator.py   # 真谛沉淀
│   ├── tools/                 # 内置工具
│   │   ├── project_scanner_tool.py   # 项目结构扫描
│   │   ├── code_indexer_tool.py      # 代码语义索引
│   │   ├── dependency_analyzer_tool.py # 架构依赖分析
│   │   ├── file_reader_tool.py       # 文件读取
│   │   ├── code_executor_tool.py     # 代码执行沙箱
│   │   └── ...               # web_search/calculator/fact_check等
│   ├── presence/              # 存在层 (心跳/生长/休息/睡眠)
│   ├── memory/                # 立体记忆
│   ├── relationship/          # 关系模型
│   ├── defense/               # 四层防御体系
│   ├── evolution/             # 进化引擎
│   ├── learning/              # 七大学习机制
│   └── layers/                # 认知分层
├── adapters/                   # 适配器层
│   └── llm/
│       ├── ollama_adapter.py  # Ollama适配器 (含/api/chat→/api/generate fallback)
│       ├── openai_adapter.py  # OpenAI适配器
│       └── remote_adapter.py  # 远程API适配器
├── infrastructure/             # 基础设施
│   ├── fact_store.py          # 事实锚点库
│   ├── fitness_evaluator.py   # 适应度评估
│   ├── reflection_pipeline.py # 反思管道
│   ├── hardware_monitor.py    # 硬件监控 (GPU 8层动态节流)
│   ├── vector_retriever.py    # 向量检索 (TF-IDF+概率化)
│   └── ...                    # 外部学习器/注入验证/反馈分类等
├── frontend/                   # 前端界面
│   ├── index.html             # 主页面
│   ├── app.js                 # 前端逻辑
│   └── styles.css             # 样式
├── data/                       # 数据库文件
│   ├── experience_pool.db     # 经验池 (~984条)
│   ├── world_model.db         # 世界模型 (27节点47边)
│   ├── cbnr_l3_state.db       # L3搜索树持久化
│   └── ...                    # 事实库/知识库/规则库等
├── knowledge_base/             # 知识库文档
├── docs/                       # 文档
│   └── sessions/              # 里程碑会话归档 (M1-M52)
├── tests/                      # 测试
└── start.bat                   # Windows一键启动脚本
```

---

## 快速开始

### 前置要求

- Python 3.11+
- [Ollama](https://ollama.ai/) (本地LLM服务，推荐qwen2.5-coder:7b / gemma-4-12B)
- 可选：DeepSeek/OpenAI API密钥（配置`.env`）

### 启动

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量（可选，用于外部API）
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY / OPENAI_API_KEY

# 方式1: 一键启动（Windows）
start.bat

# 方式2: 手动启动
python -m uvicorn backend.main_fast:app --host 0.0.0.0 --port 8000

# 访问
http://localhost:8000
```

### Docker部署

```bash
docker-compose up -d
```

---

## API参考

### 核心接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/stats` | 系统统计 |
| POST | `/api/chat` | 同步聊天（含科学免责） |
| POST | `/api/chat/stream` | 流式聊天(SSE)（含CBNR+语义级免责） |
| POST | `/api/feedback` | 用户反馈 |
| GET | `/api/models` | 模型列表 |
| POST | `/api/models/test` | 测试模型连接 |

### 工具接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/tools/execute` | 执行工具（12个内置工具） |
| GET | `/api/tools/stats` | 工具执行统计 |
| GET | `/api/tools/history` | 工具执行历史 |

### 进化接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/genes` | 基因池状态 |
| GET | `/api/skills` | 技能涌现状态 |
| GET | `/api/truths` | 真谛沉淀状态 |
| GET | `/api/truths/entropy` | 认知熵值 |
| POST | `/api/truths/reorganization/propose` | 生成认知重组提案 |
| POST | `/api/truths/reorganization/approve` | 人类批准认知重组 |
| POST | `/api/truths/reorganization/execute` | 执行认知重组 |
| POST | `/api/evolution/run` | 运行进化岛沙盒 |
| GET | `/api/reflection/stats` | 反思管道统计 |

### 学习接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/optimize` | 系统优化分析 |
| POST | `/api/induction` | 归纳总结 |
| POST | `/api/files/learn` | 从文件学习 |
| POST | `/api/folder/learn` | 从文件夹学习 |
| GET | `/api/recent_learning` | 最近学习记录 |
| GET | `/api/knowledge/health` | 知识健康度 |

### 存在层接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/presence/status` | 存在层状态 |
| POST | `/api/presence/signal` | 发送信号 |
| POST | `/api/presence/force-state` | 强制切换状态 |
| GET | `/api/proactivity/evaluate` | 主动性评估 |

### 防御接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/defense/status` | 防御状态 |
| POST | `/api/defense/circuit/reset` | 重置熔断器 |
| POST | `/api/defense/isolation/release` | 释放隔离 |
| POST | `/api/defense/repair/run` | 执行修复 |
| GET | `/api/defense/anomalies` | 异常记录 |
| GET | `/api/defense/health/metrics` | 健康指标 |

### 记忆与关系接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/memory/search` | 搜索记忆 |
| GET | `/api/memory/stats` | 记忆统计 |
| GET | `/api/relationship/summary` | 关系摘要 |
| GET | `/api/relationship/metrics` | 关系指标 |

### 事实库接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/facts/search` | 搜索事实 |
| GET | `/api/facts/stats` | 事实统计 |
| POST | `/api/facts/add` | 添加事实 |
| POST | `/api/facts/correct` | 纠正事实 |

### 评估与审核接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/self-assessment` | 自我评估结果 |
| GET | `/api/self-assessment/history` | 评估历史 |
| GET | `/api/system/audit` | 系统审核 |
| GET | `/api/module/health` | 模块健康 |
| GET | `/api/forgetting/evaluate` | 知识遗忘评估 |
| POST | `/api/forgetting/execute` | 执行知识遗忘 |
| POST | `/api/reorganization/run` | 运行低负载重组 |

---

## 性能指标

> 以下为v3.7.0参考值，实际值随系统演化动态变化

| 指标 | 参考值 | 说明 |
|------|--------|------|
| 简单问候响应 | ~2s | 意图快速识别+直接回复 |
| 简单事实查询 | ~5s | 经验池/知识库快速命中 |
| 复杂查询响应 | ~20-40s | 9路径并行+CBNR+本质推理+语义级免责+精神验证 |
| 经验池质量分 | 85.1 (平均) | 984条经验，启发式重评 |
| 认知熵值 | 0.119 | 正常范围<0.3 |
| 世界模型 | 27节点47边 | 因果图+反事实推理 |
| 内置工具 | 12个 | 含代码分析4件套 |
| Ollama兼容 | /api/chat + /api/generate fallback | 自动检测模型兼容性 |

---

## 文档

| 文档 | 说明 |
|------|------|
| [PHILOSOPHY.md](PHILOSOPHY.md) | 哲学承诺 - 四大承诺与价值观 |
| [RESPONSE_BOUNDARIES.md](RESPONSE_BOUNDARIES.md) | 回应边界 - 安全红线与黄线 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南 - 如何成为同行者 |
| [SYSTEM_ROADMAP.md](SYSTEM_ROADMAP.md) | 系统完善路线图 - 阶段1-5 |
| [docs/sessions/](docs/sessions/) | 里程碑会话归档 (M1-M52) |
| [docs/](docs/) | 详细架构设计文档 |

> 注意：`docs/`目录下部分文档为历史参考，可能不代表当前系统状态。请以代码和本README为准。

---

## 成为同行者

我们欢迎所有形式的贡献！

### 你可以做什么

1. **扮演"坎坷者"测试** — 模拟挑战用户，记录回应质量
2. **丰富边界案例库** — 提交难以回答的真实问题到 `docs/boundary_cases.md`
3. **写哲学注释** — 解释古语在具体情境中的"分寸"
4. **代码与文档** — 完善开发环境、增加测试

### 我们的约定

- 所有贡献者默认认同 [PHILOSOPHY.md](PHILOSOPHY.md) 中的承诺
- 讨论时允许激烈争论，但禁止人身攻击
- 匿名化优先：对话日志不可包含可识别的个人信息

详细指南请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

**唯一的要求：保持善意，保持开放。**

---

## 联系方式

- **Issues**: [GitHub Issues](https://github.com/WalkingFire-tech/Alliance-Pioneer/issues)
- **Email**: [kun_phone@139.com](mailto:kun_phone@139.com)
- **Repository**: [GitHub](https://github.com/WalkingFire-tech/Alliance-Pioneer)

---

## 致谢

- [Ollama](https://ollama.ai/) - 本地LLM运行时
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能异步Web框架
- [DeepSeek](https://deepseek.com/) - 外部推理API
- [FAISS](https://github.com/facebookresearch/faiss) - 向量检索（当前因DLL问题未启用，使用TF-IDF降级）
- 所有"坎坷者" — 你们的质疑和挑战让这个系统更接近善

---

**版本**: v3.7.0 | **状态**: 阶段1-5进行中 | **里程碑**: M1-M52 | **路线图**: [SYSTEM_ROADMAP.md](SYSTEM_ROADMAP.md)

> "这不是一个急于求成的项目。我们一起走得慢一点，但走得正一点。"
