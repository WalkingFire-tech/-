# 联盟拓荒者 当前架构文档

> 版本：v3.2.0 | 更新时间：2026-06-30
> 本文档反映系统**当前实际架构**，而非设计目标。与README互补，提供更深层技术细节。

---

## 1. 运行时入口

| 入口 | 状态 | 说明 |
|------|------|------|
| `backend/main_fast.py` | **唯一运行入口** | FastAPI + uvicorn，包含所有API路由和lifespan管理 |
| `main.py` | 已归档 | 旧CLI入口，不再使用 |

启动命令：`python -m uvicorn backend.main_fast:app --host 0.0.0.0 --port 8000`

### lifespan 启动序列

```
1. 初始化 ThreadPoolExecutor(max_workers=32)
2. 加载 Ollama 模型列表
3. 启动存在层 existence_layer（心跳/生长/休息/睡眠循环）
4. 启动认知代谢后台任务
5. 启动守护者巡逻（SystemGuardian）
```

---

## 2. 聊天处理流水线（chat_stream.py）

`chat_stream()` 是核心函数，处理每个用户查询的完整生命周期。

### 2.1 处理阶段

```
1. 意图识别     → _identify_intent() 分类查询类型
2. 本质闸门     → 判断是否需要深度推理
3. 8路径并行    → asyncio.gather() 并行获取，120秒超时
4. 对比择优     → 质量评估，选择最优回复
5. 本质推理     → essence_reasoner.reason() 矛盾检测+交叉验证
6. 精神验证     → spirit_core.enforce_on_output() 原则验证
7. 反思学习     → _reflect_and_learn() 归纳+微调样本生成
8. 后台进化     → 基因微调+经验沉淀+事实提取
```

### 2.2 8路径并行架构

| 路径 | 函数 | 数据源 | 异步方式 |
|------|------|--------|----------|
| 经验池 | `_fetch_experience()` | experience_pool.db (SQL LIKE) | `_run_sync` |
| 知识库 | `_fetch_knowledge()` | knowledge SQLite + 影响评分 | `_run_sync` |
| Ollama | `_fetch_ollama_all()` | 本地LLM (gemma/qwen等) | `asyncio.wait_for` |
| 外部API | `_fetch_external_api()` | DeepSeek/OpenAI | `aiohttp` |
| 规则推理 | `_fetch_rules()` | learning_rules.db | `_run_sync` |
| 事实库 | `_fetch_fact_assertions()` | fact_store (三元组) | `_run_sync` |
| 自我推理 | `_self_reason()` | 内部逻辑推理 | `_run_sync` |
| 外部学习 | `_fetch_external_learning()` | DuckDuckGo搜索 | `_run_sync` |

### 2.3 异步安全机制

**核心问题**：uvicorn运行在asyncio事件循环中，同步阻塞操作会导致整个服务卡死。

**解决方案**：`_run_sync(func, *args, timeout=30, **kwargs)`
- 在 `ThreadPoolExecutor` 中运行同步函数
- `asyncio.wait_for` 超时保护
- 所有重量级同步操作统一包装

**已修复的关键问题**：
- `asyncio.get_event_loop()` → `asyncio.get_running_loop()`（17处，避免死锁）
- `sentence_transformers` DLL加载失败 → 向量检索禁用
- `_diagnose_ollama_status()` 同步阻塞 → 改为async
- 所有 `essence_reasoner/fact_store/spirit_core/fitness_evaluator` 调用 → `_run_sync` 包装

### 2.4 路径贡献占比

每次回复附带各路径的有效信息占比，前端以彩色圆点展示：
```
经验池: 15% | 知识库: 10% | Ollama: 40% | 外部API: 25% | 规则: 5% | 事实: 5%
```

### 2.5 外部API Token追踪

从DeepSeek/OpenAI响应中提取`usage`字段，统计token消耗并在前端显示。

---

## 3. 核心模块

### 3.1 本质推理器（core/essence_reasoner.py）

6步推理流程：
1. 领域检测（物理/化学/生物/天文/医学/工程/教育/日常/哲学）
2. 悖论提前返回（"如果...那么..."类问题）
3. 否定词冲突检测（排除修辞句式"不是...而是..."）
4. 交叉验证建议
5. 领域感知免责声明
6. 去重检查

领域优先级：物理 > 天文（"量子涨落"等词归入物理而非天文）

### 3.2 精神内核（core/spirit_core.py）

- 核心原则验证：每条输出经过原则检查
- 降级保护：验证失败时降级为安全回复
- 反思联动：`get_lessons_for_reflection()` 提供精神教训
- 教训存储：`spirit_lessons.db`

### 3.3 基因演化（core/genome_evolver.py）

10个可演化参数（定义在 `core/task_queue.py` GENE_DEFAULTS）：
- retrieval_threshold, learning_frequency, emotion_weight, exploration_tendency
- memory_decay_rate, abstraction_threshold, reflection_frequency, knowledge_breadth
- skill_solidification_threshold, environmental_sensitivity

安全机制：
- 参数不允许越界（越界记录为safety_violation）
- 认知熵值从GenePool真实读取gene_safety_violations
- 失败交互时反向微调（增加谨慎、减少激进）

### 3.4 技能涌现（core/skill_emergence.py）

- 自动涌现：经验池中重复出现的模式自动提取为技能
- 成熟判定：成功调用≥3次标记为mature
- 退化机制：success_rate<30%标记为dormant

### 3.5 真谛沉淀（core/truth_accumulator.py）

四道筛子：重复性→一致性→实用性→安全性

6步认知重组安全协议：
1. 提案生成（自动或手动）
2. 沙盒验证（独立环境，不影响主数据库）
3. 1%渐进注入（观察效果）
4. 20%扩大注入
5. 100%全量注入
6. 完成/回滚（熵值>0.7立即回滚）

### 3.6 认知调度器（core/cognitive_dispatcher.py）

- 模块级单例，缓存跨请求生效（300秒内相同问题返回缓存结果）
- 三条路径：fast（简单查询）/ slow（复杂推理）/ learning（知识缺失）

---

## 4. 存在层（core/presence/）

| 模块 | 文件 | 功能 |
|------|------|------|
| 存在层 | existence_layer.py | 四态循环管理（心跳/生长/休息/睡眠） |
| 自我感知 | self_perception.py | 定期自检能力状态 |
| 间隙生长 | gap_growth.py | 检测知识缺口，触发学习 |
| 睡眠整合 | sleep_consolidation.py | 空闲时知识整合+经验压缩 |
| 自我评估 | self_assessment.py | 5维度评估（闭环完整性/知识活力/学习效率/行为偏差/适应速度） |
| 主动性引擎 | proactivity.py | 主动发起对话/学习 |
| 信号集成 | signal_integration.py | 内外部信号统一处理 |

### 存在层状态机

```
heartbeat ──→ growing ──→ resting ──→ sleeping ──→ heartbeat
   │              │           │            │
   │              ↓           ↓            ↓
   │         间隙生长    低负载重组    睡眠整合
   │         知识缺口     知识重组      经验压缩
   │         触发学习     规则激活      基因优化
   │
   └── 定期自检 → 自我感知报告
```

---

## 5. 防御体系（core/defense/）

| 层级 | 模块 | 功能 |
|------|------|------|
| L1 预防 | 输入验证、注入检测 | 阻止恶意输入 |
| L2 监控 | 异常检测、熔断保护 | 连续失败>5次/分钟触发熔断 |
| L3 处理 | 故障隔离、资源重分配 | 标记不健康→隔离→降级运行 |
| L4 修复 | 自动重启、状态恢复 | 自动重启→验证→重新上线 |

SystemGuardian 统一整合四层防御，定期巡逻。

---

## 6. 基础设施层（infrastructure/）

| 模块 | 文件 | 功能 | 集成状态 |
|------|------|------|----------|
| 事实锚点库 | fact_store.py | 结构化三元组+否定词+注入验证 | ✅ 已集成 |
| 适应度评估 | fitness_evaluator.py | 多维度基因适应度评估 | ✅ 已集成 |
| 反思管道 | reflection_pipeline.py | 归纳+微调样本生成 | ✅ 已集成 |
| 注入验证 | injection_verifier.py | 知识注入安全验证 | ✅ 已集成 |
| 外部学习器 | external_learners.py | DuckDuckGo搜索 | ✅ 已集成 |
| 向量检索 | vector_retriever.py | FAISS向量相似度 | ❌ 已禁用（DLL问题） |
| 反馈分类 | feedback_classifier.py | 用户反馈分类 | ✅ 已集成 |
| 版本化事实库 | versioned_fact_store.py | 事实版本控制 | ⚠️ 代码存在，未在主流程使用 |

---

## 7. 数据库

| 数据库 | 位置 | 说明 |
|--------|------|------|
| experience_pool.db | backend/ | 经验池，~2900条交互记录 |
| learning_rules.db | backend/ | 学习规则，~240条（50条活跃，195条待激活） |
| spirit_lessons.db | backend/ | 精神教训 |
| model_stats.db | backend/ | 模型统计 |
| tool_stats.db | backend/ | 工具统计 |
| health_history.db | 根目录 | 健康历史 |
| counterfactual_history.db | 根目录 | 反事实模拟历史 |

---

## 8. 前端（frontend/）

| 文件 | 功能 |
|------|------|
| index.html | 主聊天界面 |
| app.js | 前端逻辑（SSE流式接收、思考过程折叠、路径贡献占比、token消耗显示） |
| styles.css | 样式 |
| knowledge_panel.html | 知识图谱弹窗 |
| learning_dashboard.html | 学习仪表盘 |
| folder_browser.html | 文件浏览器 |

---

## 9. 已知限制

| 限制 | 原因 | 影响 |
|------|------|------|
| 向量检索不可用 | sentence_transformers的torch DLL加载失败 | 经验池使用SQL LIKE替代，检索精度较低 |
| 贝叶斯优化未实现 | /api/optimize只做简单统计 | 超参数调优能力有限 |
| 连接池未实现 | 所有DB操作用sqlite3.connect()直接连接 | 高并发下可能有性能瓶颈 |
| L5/L6认知层不存在 | 代码只实现L0-L4 | 文档中提到的6层架构不准确 |
| 规则激活瓶颈 | 195条待激活 vs 50条活跃 | 归纳→激活通道不畅 |
| 前端RPV循环未显示 | 前端只有简单计时器 | 无法看到Plan/Verify/Execute/Reflect过程 |

---

## 10. 配置

### 环境变量（.env）

```
DEEPSEEK_API_KEY=     # DeepSeek API密钥（可选）
OPENAI_API_KEY=       # OpenAI API密钥（可选）
OLLAMA_BASE_URL=      # Ollama服务地址（默认http://localhost:11434）
```

### 模型配置

系统自动检测Ollama可用模型，按意图类型路由：
- 代码类 → qwen2.5-coder
- 通用类 → gemma
- 复杂推理 → 可配置外部API

---

## 11. 健康阈值体系

| 指标 | 正常 | 警告 | 危险 | 触发动作 |
|------|------|------|------|----------|
| 认知熵值 | <0.3 | 0.3-0.5 | >0.5 | >0.7回滚 |
| 模块错误率 | <5% | 5-20% | >20% | >50%隔离 |
| 响应时间 | <10s | 10-30s | >30s | >60s降级 |
| success率 | >80% | 60-80% | <60% | <30%触发反思 |
| 规则置信度 | >0.6 | 0.4-0.6 | <0.4 | <0.3降级为pending |