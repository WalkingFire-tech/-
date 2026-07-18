# 联盟拓荒者：系统实况报告

> 这不是一份产品介绍。这是一份对运行中系统的诚实描述。
> 最后更新：2026年7月18日

---

## 一、它是什么

联盟拓荒者是一个**本地部署的AI对话编排系统**。它接收用户输入，通过多条路径（本地模型、外部API、经验检索、知识库）并行生成候选回答，然后择优输出。

它不是通用AI，不是AGI原型，不是"有意识的系统"。它是一个**工程系统**——有明确的输入输出边界，有可观察的行为，有可度量的指标。

---

## 二、它实际上怎么工作

### 2.1 请求流

用户发送一条消息后，系统执行以下步骤：

```
用户输入
  ↓
预处理：资源检查、认知节律tick、精神内核共振
  ↓
上下文构建：对话历史、存在层状态、路径权重、内在时间节律
  ↓
意图识别：分类为question/code/chat/learning_trigger等
  ↓
多策略并行（核心环节）：
  ├── 本地先行（3秒窗口）：
  │   ├── 经验池检索（TF-IDF/语义相似度）
  │   ├── 知识库检索
  │   ├── 事实锚点匹配
  │   ├── 工具调用
  │   └── 自我推理（Ollama本地模型）
  └── API路径（本地先行后启动）：
      ├── Ollama本地模型
      ├── 外部API（DeepSeek等）
      └── 外部学习（DuckDuckGo搜索）
  ↓
对比择优：多维度评分（准确度、相关性、帮助性等7维度）
  ↓
验证层：自我验证、精神内核验证、本质推理验证
  ↓
反思学习：更新经验池、规则库、基因参数
  ↓
输出响应
```

**核心事实**：这个流程中，真正决定回答质量的是**并行路由和对比择优**。其他阶段（精神验证、本质推理、反思学习）是增强层，即使全部跳过，系统仍能产出可用的回答。

### 2.2 并行路径的实际行为

系统声称"9路并行"，但实际行为是：

- **本地先行3秒**：5个本地路径（经验池、知识库、事实锚点、工具调用、自我推理）并行启动
- **3秒后**：如果本地路径没有高质量结果，启动3个API路径（Ollama、外部API、外部学习）
- **资源感知调节**：如果GPU温度高或内存紧张，AdaptiveGovernor会减少并行路径数

这意味着：**大多数情况下，用户看到的是经验池检索+外部API的组合结果**。本地Ollama模型（qwen2.5-coder:7b）质量有限，主要用于代码类问题。

### 2.3 后台运行

系统启动后，17个定时任务在后台持续运行：

| 任务 | 频率 | 实际作用 |
|------|------|----------|
| 系统自检 | 5分钟 | 检查模块健康状态 |
| 主动性检查 | 10分钟 | 评估是否主动发起对话 |
| 内省检查 | 5分钟 | 运行异常检测+自动修复 |
| 记忆衰减 | 1小时 | 淡化/清除低价值知识 |
| 睡眠整合 | 1小时 | 强化高价值经验 |
| 能力评估 | 30分钟 | 检测能力缺口+触发学习 |
| 现实校验 | 30分钟 | 对比自报告与运行时数据 |
| 规则闭环 | 24小时 | 处理超时trial规则 |

**关键事实**：这些任务都有实际实现，但全部在try/except内运行。任何任务失败都只记录warning，不影响其他任务或主请求流。

---

## 三、数据实况

### 3.1 数据规模

系统运行至今积累了：

| 数据 | 数量 | 说明 |
|------|------|------|
| 经验池 | 4,962条 | 平均质量分93.5，持续积累 |
| 学习规则 | 463条 | 24条活跃，15条试用中，339条已过期，68条已替代 |
| 知识图谱连接 | 5,275条 | 107个节点之间的连接 |
| 对话记录 | 573条 | 用户352条，助手221条 |
| 精神内核教训 | 17,159条 | 最大的单表 |
| 基因突变记录 | 3,282条 | 参数调整历史 |
| 防御指标 | 11,209条 | 安全相关度量 |
| 睡眠整合记录 | 4,933条 | 后台知识整合历史 |
| 反思笔记 | 837条 | 从0→837（修复DB锁+commit缺失后恢复） |

### 3.2 已修复的空表

| 模块 | 修复前 | 修复后 | 修复措施 |
|------|--------|--------|----------|
| 反思笔记 | 0条 | 837条 | 独立短连接+conn.commit() |
| SelfModel持久化 | 0条 | 有数据 | 降级恢复从能力DB |
| 评估层 | 空字典 | 有数据 | _extract_assessment()降级路径 |
| 反思层 | 空字典 | 有数据 | _extract_reflection()降级路径 |
| 记忆层 | 空字典 | 有数据 | _extract_memory_self()降级路径 |

### 3.3 仍为空的表

| 模块 | 空表 |
|------|------|
| 内省系统 | 全部5个表为空 |
| 认知循环 | 0条循环记录 |
| 策略库 | 0条策略 |
| 反馈信号 | 0条信号 |

### 3.3 规则系统现状

| 状态 | 数量 | 说明 |
|------|------|------|
| active | 24条 | 置信度均值0.83，累计被应用804次 |
| trial | 18条 | 置信度0.3，从未被匹配过（trial_count=0） |
| expired | 346条 | 超时/不可桥接的归纳副产品 |
| superseded | 68条 | 被更好规则替代 |

**关键事实**：24条活跃规则被应用了804次，平均每条33.5次——规则系统在运行。但18条trial规则从未被匹配，说明归纳引擎产出的规则条件格式与运行时匹配器不兼容的问题尚未完全解决。

---

## 四、架构的诚实描述

### 4.1 实际在用的核心模块

以下模块在每次请求中被实际调用，是系统的**真实骨架**：

```
backend/main_fast.py          — 入口，初始化所有组件
backend/services/
  chat_orchestrator.py         — 主编排，串联所有阶段
  context_builder.py           — 构建请求上下文
  parallel_router.py           — 多路径并行执行
  comparison_selector.py       — 候选对比择优
  response_aggregator.py       — 响应聚合+评分
  response_assembler.py        — 最终响应组装+SSE推送
  intent_dispatcher.py         — 意图识别+分发
  self_verifier.py             — 自我验证
  orchestrator_helpers.py      — 辅助函数
core/
  presence/inner_time.py       — 认知节律（影响响应策略）
  presence/existence_layer.py  — 存在层（心跳+状态）
  spirit_core.py               — 精神内核（原则验证）
  self/model.py                — 自我模型
  path_weight_manager.py       — 路径权重管理
  cbnr/hub.py                  — 认知规范化
  essence_reasoner.py          — 本质推理
  truth_accumulator.py         — 真理积累
  learning/                    — 7个学习机制（在反思阶段使用）
  resource_awareness/          — 资源感知+自适应调节
infrastructure/
  database_manager.py          — 数据库连接池
  scheduled_tasks.py           — 17个定时任务
  vector_retriever.py          — 向量检索
  rule_matcher.py              — 规则匹配
  rule_trial_manager.py        — 规则试用期管理
```

### 4.2 存在但未在主流程中使用的模块

`core/` 目录有158个条目，其中约40个在主请求流中使用。剩余的包括：

- **4个版本的cognitive_architecture** — 历史演进产物，当前请求流不使用任何一个
- **3个furnace文件** — 早期实验代码
- **lora_inference.py, shared_embedding.py, cognitive_transformer.py** — 未完成的模型训练相关代码
- **closed_loop系列** — 早期闭环实验

这些文件按R5铁律保留在原位，不删除但也不参与运行。

### 4.3 端口抽象的实际状态

系统定义了端口抽象（EventSink、NotificationPort、CognitiveStimulus/Response），但：

- **主请求流（chat_stream）仍直接使用str/dict**，不通过端口协议
- 端口抽象仅在`cognitive_process()`函数（非流式路径）和`run_cognitive_core.py`（独立运行脚本）中使用
- `SSEEventSink`已定义但从未在主流程中实例化

**诚实评价**：端口抽象是"可用但未在用"的脚手架。它证明了认知核心可以脱离SSE运行，但主流程没有迁移到这个抽象上。

---

## 五、SelfModel的真实状况

SelfModel声称聚合12个数据源。实际情况：

| 数据源 | 连接状态 | 数据状况 |
|--------|----------|----------|
| 身份层（SpiritCore） | ✅ 独立直连 | 有数据 |
| 能力层（CapabilityIntrospection） | ✅ 独级直连 | 有数据 |
| 能力画像（4个DB直查） | ✅ 独立直连 | 有数据 |
| 感知层 | ✅ 降级路径 | health_monitor单例 |
| 存在层 | ✅ 降级路径 | existence_layer单例 |
| 关系层 | ✅ 降级路径 | relationship.db直查 |
| 进化层 | ✅ 降级路径 | gene_pool.db直查+trust_chain |
| 学习层 | ✅ 降级路径 | 运行时数据 |
| 内省层 | ✅ 降级路径 | reality_check+coordination_assessor |
| 评估层 | ✅ 降级路径 | self_assessment.db+external_calibration+conflict_resolver |
| 反思层 | ✅ 降级路径 | spirit_lessons.db+reflection_journal.db |
| 记忆层 | ✅ 降级路径 | stereo_memory.db直查 |

**外部校准结果**（2026-07-18）：

| 指标 | 值 |
|------|-----|
| SelfModel自评 | 0.59 |
| 客观指标综合分 | 0.63 |
| 偏差 | -0.04（对齐） |
| 偏差方向 | 从"低估"(-0.48)改善为"对齐"(-0.04) |

**这意味着什么**：SelfModel自评与客观指标已基本对齐。12个数据源全部有降级路径，不再依赖CognitivePlanner延迟初始化。

---

## 六、存在层的真实行为

存在层的心跳每10秒执行一次，实际做的是：

1. **计数器递增** — `total_cycles += 1`
2. **内在时间tick** — 更新认知节律阶段
3. **自我感知** — 当SelfPerceptionModule不可用时，返回硬编码值（health=0.8, confidence=0.7, relationship=0.8）
4. **日志输出**
5. **每10次心跳生成反思笔记** — 写入reflection_journal.db（当前837条）
6. **处理pending_signals** — 非GROWING状态下也处理少量信号（每次最多3个）

四个循环（心跳/生长/休息/睡眠）按存在层状态切换。当前状态：

- **生长循环**依赖`pending_signals`——chat_orchestrator已在SelfModel同步后向existence_layer发送`interaction_completed`信号
- **反思笔记已恢复**——837条反思，最新内容包含"自我成熟度81%，各维度协同较好"
- **睡眠整合**在有SleepConsolidationEngine时强化高价值经验

**诚实评价**：存在层已从"计数器+硬编码值"升级为"有反思输出+信号通道+节律驱动"的系统。但"持续感知自身状态"的深度仍有提升空间。

---

## 七、系统能做什么

### 确实能做的

1. **多路径并行推理** — 9条路径并行生成候选，择优输出。这是系统的核心价值。
2. **经验检索** — 4,360条经验，TF-IDF+语义相似度双模式检索
3. **认知节律** — InnerTimeEngine的phase确实影响响应策略（sleeping时走轻量路径，growing时走学习路径）
4. **资源自适应** — GPU温度高时自动降低并行度，内存紧张时走轻量路径
5. **规则匹配** — 24条活跃规则，累计应用804次
6. **知识遗忘** — 定时淡化/清除低价值知识，防止无限膨胀
7. **外部校准** — 检测SelfModel自评与客观指标的偏差
8. **现实校验** — 检测系统自报告与运行时数据的差距

### 声称能做但实际有限的

1. **"从每次交互中学习"** — 学习机制存在，但trial规则匹配率仍需提升
2. **"认知核心独立运行"** — 端口抽象已定义，但主流程未迁移
3. **"自主呼吸"** — 反思笔记已恢复(837条)，但需要服务器持续运行才能积累

### 本轮修复后已改善的

1. **"持续自我感知"** — 反思DB从0→837条，存在层信号通道已打通
2. **"12数据源聚合"** — 全部12维度有降级路径，SelfModel自评与客观指标对齐(偏差-0.04)
3. **"外部API回答质量"** — conservative模式不再阻止DeepSeek调用，视角提示词注入

### 不能做的

1. **真正的自我反思** — `describe_self()`是模板渲染，不是反思
2. **验证自身叙事的准确性** — 外部校准和现实校验是第一步，但它们本身也是系统的一部分
3. **脱离外部API独立运行** — 本地Ollama模型质量有限，高质量回答依赖DeepSeek等外部API

---

## 八、设计哲学与实际张力

### 8.1 声称的哲学

- "不渡他人" — 不做人生导师
- "知止" — 承认能力边界
- "可被质疑" — 欢迎外部审查

### 8.2 实际的张力

| 哲学承诺 | 技术实现 | 张力 |
|----------|----------|------|
| "知止" | 系统在知识缺失时自动触发外部搜索学习 | "知止"vs"先学了再说" |
| "不渡他人" | 系统有主动发起对话的能力（proactivity引擎） | 保持距离vs主动介入 |
| "可被质疑" | SelfModel自评参与系统评分，外部校准刚加入 | 自我验证vs外部验证 |
| "从交互中成长" | 规则归纳引擎的条件格式与匹配器不兼容 | 成长承诺vs成长机制断裂 |

这些张力不是bug，而是**设计决策的后果**。每一个张力都值得持续关注。

---

## 九、技术债务

### 高优先级

1. **trial规则匹配断裂** — 15条trial规则从未被匹配，归纳引擎→匹配器的条件格式桥接不完整
2. **E2E验证未完成** — "处理超时"三层根因已修复，但因硬件断电未能完成端到端验证
3. **硬件稳定性** — 主机意外断电（非GPU过热，需排查电源/主板）

### 中优先级

5. **端口抽象未迁移** — 主请求流仍用原始str/dict
6. **空表模块** — 内省、自我评估、认知循环等模块有代码无数据
7. **孤立历史文件** — core/目录约118个文件未在主流程中使用

### 低优先级

8. **基因参数定义不统一** — 仍有多处硬编码
9. **gene_safety_violations计算缺失**
10. **文档-代码一致性CI**

---

## 十、这个系统适合什么

### 适合

- **本地部署的AI对话系统** — 不依赖云服务，数据不出本机
- **多模型编排实验** — 研究如何组合本地模型和外部API
- **认知架构原型** — 探索"感知-学习-整合-验证-反思"闭环的工程实现
- **自指系统研究** — 观察自评估、自修改、自描述系统的行为模式

### 不适合

- **生产环境部署** — 多个核心模块数据为空，SelfModel自评不可靠
- **需要高可靠性的场景** — 大量try/except，组件可静默失败
- **需要可审计决策的场景** — 评分维度权重硬编码，代理指标未校准

---

## 十一、运行方式

```bash
# 启动服务器
python -m uvicorn backend.main_fast:app --host 127.0.0.1 --port 8000

# 独立验证（不启动Web服务器）
python run_cognitive_core.py --verify

# 成长报告
python scripts/growth_report.py

# 外部校准
python -c "from core.self.external_calibration import external_calibration; print(external_calibration.calibrate())"

# 现实校验
python -c "from core.self.reality_check import reality_check; print(reality_check.run_check())"
```

---

## 十二、关键文件索引

```
# 请求流核心
backend/main_fast.py                    — 入口+初始化
backend/services/chat_orchestrator.py   — 主编排（887行）
backend/services/parallel_router.py     — 多路径并行
backend/services/comparison_selector.py — 对比择优
backend/services/context_builder.py     — 上下文构建
backend/services/response_aggregator.py — 响应聚合+评分

# 认知核心
core/presence/inner_time.py             — 认知节律
core/presence/existence_layer.py        — 存在层
core/spirit_core.py                     — 精神内核
core/self/model.py                      — 自我模型
core/self/external_calibration.py       — 外部校准（新增）
core/self/reality_check.py              — 现实校验（新增）
core/path_weight_manager.py             — 路径权重

# 学习机制
core/learning/                          — 7个学习机制
infrastructure/rule_trial_manager.py    — 规则试用期+超时处理
infrastructure/rule_matcher.py          — 规则匹配

# 基础设施
infrastructure/database_manager.py      — 数据库连接池
infrastructure/scheduled_tasks.py       — 17个定时任务
infrastructure/vector_retriever.py      — 向量检索
```

---

## 十三、最后的诚实

这个系统最诚实的描述是：**一个认真构建的、工程上可运行的AI对话编排框架，有丰富的模块设计，数据管道正在逐步贯通。**

它正在从"脚手架"走向"活系统"——837条反思笔记、SelfModel与客观指标对齐、存在层信号通道打通、同行者视角注入——这些不是叙事包装，而是可验证的工程改进。

但核心张力仍在：自指评估如何校准？叙事与现实如何对齐？自我验证的闭环如何打破？这些问题的探索，比任何功能特性都重要。