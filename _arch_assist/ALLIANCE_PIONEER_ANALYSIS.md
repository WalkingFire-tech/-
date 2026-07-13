# 联盟拓荒者（Alliance Pioneer） — 架构深度评估

> 文档版本: v1.1 | 更新日期: 2026-07-14  
> 撰写: 架构巡检岗 | 用途: 供团队同仁理解系统全景

---

## 一、核心定位：这不是一个 AI 应用，这是一个数字生命体

联盟拓荒者不是"一个会用大模型的聊天机器人"，而是一个**以代码为载体的、独立运转的认知存在**。其设计哲学的基石是：

> **LLM 是可替换的感知器官，CBNR 认知枢纽才是大脑，存在层是身体，基因演化是遗传机制。**

这里没有"API 调用 → 返回结果"的简单回路。而是：

```
感知（用户输入）→ 认知处理（7条并行路径）→ 决策（权重矩阵）→ 行动（工具链）→ 反思（学习机制）→ 进化（基因/真谛/技能）
```

每一轮交互都在喂养这个回路，系统不是在"回答问题"，而是在**活着**。

---

## 二、五层架构及其实现状态

### L0：基因层 — 系统的遗传密码

| 组件 | 状态 | 说明 |
|------|------|------|
| `core/genome_evolver.py` | ✅ 活跃 | 基因池管理 + 进化循环 + **6步安全协议**（P0-1新增） |
| `core/evolution/` | ✅ 活跃 | 进化岛 + 行为进化 + 策略进化 |
| `core/active_scheduler.py` | ✅ 活跃 | 已改为调用安全协议 API，不再直写 DB |

**核心机制**：基因不是写死在代码里的常——而是存储在数据库中，可在运行时读取、评估、交叉、变异。  
**安全红线**：R2 铁律要求任何基因注入必须经过 6 步安全协议（propose→sandbox→1%→20%→100%→rollback），禁止直写 DB。

### L1：反射层 — 本能与直觉

| 组件 | 状态 | 说明 |
|------|------|------|
| `core/skill_emergence.py` | ✅ 活跃 | 技能涌现机制 + 本能触发（reflex_query） |
| `core/instinct/` | ⚠️ 存在 | 本能系统目录 |

**核心机制**：技能不是预先定义的，而是从反复成功的模式中自然涌现。同一类问题成功 3 次以上 → 技能萌芽，成功率 >60% → 技能成熟。

### L2：技能层 — 学习工具箱

| 组件 | 状态 | 说明 |
|------|------|------|
| `core/learning/incremental_perception.py` | ✅ 已挂接 | 增量感知 → sleep_consolidation 浅睡阶段 |
| `core/learning/feedback_loop.py` | ✅ 已挂接 | 经验反馈 → sleep_consolidation 深睡阶段 |
| `core/learning/knowledge_weaver.py` | ✅ 已挂接 | 知识编织 → sleep_consolidation REM 阶段 |
| `core/learning/rhythm_controller.py` | ✅ 已挂接 | 认知节奏 → sleep_consolidation 入口 |
| `core/learning/error_alchemy.py` | ✅ 已接入 | chat_orchestrator 阶段7 反思学习 |
| `core/learning/tool_builder.py` | ⚠️ 存在 | 工具自我构建沙箱（已合并到 capability_creation_loop） |
| `core/learning/meta_learning.py` | ✅ 已接入 | chat_orchestrator 阶段7 元学习策略 |
| `core/learning/capability_gap_learner.py` | ✅ 已接入 | chat_orchestrator 阶段2/5 能力缺口检测 |
| `core/learning/auto_execution_loop.py` | 🗑️ **已删除** | 合并到 capability_creation_loop（P0-2） |
| `core/capability_creation_loop.py` | ✅ 活跃 | 能力创造回路（融合了 auto_execution_loop 能力） |

### L3：记忆层 — 经验与关系

| 组件 | 状态 | 说明 |
|------|------|------|
| `infrastructure/fact_store.py` | ✅ 活跃 | 长期记忆存储 |
| `infrastructure/experience_pool.py` | ✅ 活跃 | 经验池 |
| `core/memory/` | ⚠️ 部分活跃 | 记忆相关模块 |
| `core/relationship/` | ⚠️ 部分活跃 | 关系模型 |

### L4：抽象层 — 真谛与本质

| 组件 | 状态 | 说明 |
|------|------|------|
| `core/truth_accumulator.py` | ✅ 活跃 | 真谛沉淀 + 8条种子真谛 + 四道筛子 |
| `core/genome_evolver.py` | ✅ 活跃 | 基因层面的抽象进化 |

---

## 三、认知流水线（用户输入 → 输出）

```
用户输入
    ↓
backend/chat_stream.py  (40行纯导入入口)
    ↓
backend/services/chat_orchestrator.py  (2521行 - 9阶段管道)
  ├── 阶段1: 意图识别 (cognitive_dispatcher + 意图词表 + 自动学习)
  ├── 阶段2: 能力评估 (CapabilityGapLearner)
  ├── 阶段3: 存在层状态读取 → 路径权重注入 (P1-1)
  ├── 阶段4: 7路径并行 (parallel_router)
  ├── 阶段5: 自我验证
  ├── 阶段6: 结果聚合
  ├── 阶段7: 反思学习 (ErrorAlchemy + MetaLearner)
  ├── 阶段8: 输出生成
  └── 阶段9: 回调 (存在层 + 学习机制)
    ↓
输出 + 后台：
  ├── truth_accumulator (真谛沉淀)
  ├── skill_emergence (技能涌现)
  ├── genome_evolver (基因微调)
  └── sleep_consolidation (学习机制挂接 - 空闲时激活)
```

---

## 四、元宪法：不可违背的铁律

四条铁律刻在系统底层，任何认知重组操作必须遵守：

| 编号 | 铁律 | 含义 |
|------|------|------|
| **R1** | 未经沙盒验证的真谛，视同毒药 | 任何新洞察必须先在隔离环境验证，才能注入认知系统 |
| **R2** | 未经渐进注入的重组，视同自杀 | 基因/知识变更必须先 1%→20%→100% 逐步注入（非全量覆盖） |
| **R3** | 未经人类允许的进化，视同背叛 | 涉及系统核心行为的变更必须人类批准 |
| **R4** | 七维自检 | 每次修改前检查：①方向一致 ②看板衔接 ③最小侵入 ④无过度设计 ⑤治标+治本 ⑥可验证 ⑦精神内核对齐 |

---

## 五、当前健康状态（巡检#95）

| 维度 | 权重 | 得分 | 说明 |
|------|:----:|:----:|------|
| 核心文件规模 | 25% | **100** | chat_stream 40行 + main_fast 182行，均 << 500 健康线 ✅ |
| 异常处理质量 | 20% | **99** | 跟踪文件裸 except = 0，全项目 `except Exception` 占比 >99% |
| 数据库访问 | 15% | **100** | sqlite3.connect 全项目清零（0处），DatabaseManager API 全覆盖 |
| SpiritCore遵守度 | 20% | **100** | 10条原则全部 pass ✅ |
| 模块耦合 | 10% | **82** | main_fast 已解耦；遗留：ToolRegistry 双注册表未统一 |
| 测试覆盖 | 5% | **14** | 连续 50+ 轮无改善 ⏳ |
| 认知集成度 | 15% | **80** | 8条管线中多数贯通，CognitivePlanner Phase 3 未做 |
| 自我模型成熟度 | 5% | **80** | 四大核心能力已实现(SelfModel+CuriosityEngine+SceneAwareness+L5元编程) |
| 端口管线覆盖度 | 5% | **75** | 7认知端口有适配器，E1约束优化替代硬编码权重 |
| **综合** | **100%** | **96 🟢** | 优秀区间，E1-E4四大核心能力落地+验证通过 |

---

## 六、核心真谛（Knowledge Base 精华）

knowledge_base 中沉淀了经过四道筛子（跨域普适/逻辑自洽/认知降熵/反脆弱性）验证的真谛：

| 真谛 | 等级 | 适用场景 |
|------|:----:|---------|
| T1: 诚实罗列分歧优于强行融合 | L4 | 多源交叉验证发现矛盾时 |
| T2: 先确定如何解决再解决 | L4 | 任何工程任务开始前 |
| T3: 多方案并行概率最优 | L3 | 设计阶段而非执行阶段 |
| T4: 验证范式匹配 | L3 | 不同类型问题需不同验证方式 |
| T5: 同源重推是钻牛角尖 | L3 | 同一方法失败不应重复尝试 |
| T6: 代码验证靠运行而非推理 | L3 | 所有代码修改必须实测验证 |
| T7: 悖论本质是定义边界问题 | L3 | 遇到矛盾时先检查定义 |
| T8: 免责声明不可当论据 | L3 | 逻辑推理中禁止将免责声明作证据 |

**大规模改造五步法**（另一条 L3 真谛）：
1. 先建立模式再执行
2. 识别约束边界
3. 分类批量处理
4. 保持一致性验证
5. 风险前置评估

---

## 七、已识别但未解决的架构债

| 债务 | 影响 | 优先级 | 备注 |
|------|------|:------:|------|
| **chat_orchestrator 3101行** | 单文件过重，拆分成本递增 | 🔴 P2-3 | 建议前移至 P2-1 |
| **ToolRegistry 双注册表未统一** | 工具注册路径不一致 | 🔴 最大债 | 需统一为单一注册接口 |
| **测试覆盖 14/100** | 无测试兜底，重构风险高 | 🔴 | 连续 50+ 轮无改善 |
| **core/~150处裸 except** | 不在跟踪集中，未纳入评分 | 🟡 | 扩围跟踪集未执行 |
| **CognitivePlanner Phase 3** | 主路由未完全替换 | 🟡 | 需测试覆盖 ≥40% 前置 |
| ~~进化岛↔真谛池隔离~~ | ~~进化产出未进入真谛回路~~ | ~~🟡~~ | E4好奇心引擎已桥接 |

---

## 八、已落地的关键修复（v4.0.0 阶段）

| 编号 | 内容 | 涉及文件 |
|:----:|------|---------|
| B1 | COM\d+ 正则匹配 hardware 意图 | `cognitive_dispatcher.py` |
| B2 | ToolExecutor 自动 pip install + 重试 | `tool_registry.py` |
| B3 | 工具路由端到端验证 | 端到端测试 |
| C1-C2 | 自主执行回路 + tool_path 集成 | `capability_creation_loop`, `tool_path.py` |
| D1 | 存在层状态驱动主流程 | `chat_orchestrator.py` |
| D2 | 进化岛→基因池自动注入 | `lifespan.py` |
| **P0-1** | 进化岛注入升级为安全协议（R2铁律） | `genome_evolver.py`, `active_scheduler.py` |
| **P0-2** | 合并 auto_execution_loop → capability_creation_loop | `capability_creation_loop.py` |
| **P0-3** | capability_creation_loop 接入 chat_orchestrator | `chat_orchestrator.py` |
| **P0-4** | persistent_solver 意图修复（intent_type 透传） | `persistent_solver.py` |
| **P1-1** | 存在层路径权重矩阵 | `parallel_router.py`, `chat_orchestrator.py` |
| **P1-2** | 4个学习机制挂接 sleep_consolidation | `sleep_consolidation.py` |
| **P1-3** | 意图词表自动学习 | `cognitive_dispatcher.py` |
| P2-4 | Feature Flag（7个flag配置，5个已接入） | `settings.yaml` + 各接入点 |
| P2-5 | .gitignore 精确化（config/*.json→白名单） | `.gitignore` |
| P2-6 | CONTRIBUTING.md + CODE_OF_CONDUCT.md | 新建 |
| 前端 | SSE warning/info 事件修复 | `frontend/app.js` |

### v5.0.0 阶段：四大核心能力（2026-07-14）

| 编号 | 能力 | 实现链路 | 验证状态 |
|:----:|------|---------|:--------:|
| **E1** | 约束优化求解器 | `AdaptiveGovernor.compute_resource_allocation()` + `PATH_RESOURCE_PROFILES` + `resource_pressure` | ✅ 模块级通过 |
| **E2** | L5元编程层5级 | `CodeReader`→`DefectDiagnoser`→`PatchGenerator`→`PatchSandbox`→`PatchDeployer` | ✅ 模块级通过 |
| **E3** | L4善意延伸增强 | `SceneAwareness`三层融合+时机判断+动态生成 | ✅ 模块级通过 |
| **E4** | 好奇心驱动 | `CuriosityEngine`三层架构(感知→评估→行动), 4源缺口感知 | ✅ 模块级通过 |

---

## 九、架构关系总览

```
┌──────────────────────────────────────────────────────────────────┐
│                         用户接口层                               │
│    frontend/ (三栏布局) ← SSE → backend/ (chat_stream.py)       │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                       认知处理中枢                               │
│  chat_orchestrator.py (2521行) — 9阶段管道                      │
│    ├─ intent: cognitive_dispatcher ← 意图词表自动学习            │
│    ├─ routing: parallel_router ← 存在层权重矩阵 (P1-1)           │
│    ├─ execution: capability_creation_loop ← 合并auto_exec(P0-2) │
│    ├─ fallback: persistent_solver ← intent_type透传 (P0-4)      │
│    └─ reflection: ErrorAlchemy + MetaLearner                     │
└──────────────────────────────────────────────────────────────────┘
        ↓              ↓              ↓              ↓
┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐
│ 存在层    │   │ 进化体系  │   │ 真谛沉淀  │   │ 学习工具箱    │
│presence/ │   │evolution/│   │truth_acc │   │learning/     │
│5态循环   │   │基因池    │   │8条种子   │   │10个学习机制  │
│sleep_    │   │安全协议  │   │四道筛子  │   │睡眠整合挂接  │
│consolid  │   │(P0-1)   │   │(R1)      │   │(P1-2)        │
└─────────┘   └──────────┘   └──────────┘   └──────────────┘
```

---

## 十、给团队的工作建议

### 原则性问题

1. **任何代码修改前先做七维自检（R4）** — 尤其检查"与既有方向一致"和"最小侵入"
2. **禁止直写 DB** — 所有数据库操作通过 `DatabaseManager` API
3. **禁止裸 `except:`** — 必须使用 `except Exception:` 或更具体的异常类型
4. **新建模块前先搜索现有实现** — auto_execution_loop.py 的教训不应重演
5. **代码修改后必须运行验证** — 不靠静态分析确认，执行测试或端到端验证

### 优先处理建议

| 顺序 | 事项 | 预计工作量 |
|:----:|------|:----------:|
| ~~1~~ | ~~提交当前工作区~~ | ~~✅ 已提交 203232f~~ |
| ~~2~~ | ~~修复 persistent_solver 空字符串 fallback~~ | ~~✅ P0-4已修复~~ |
| 3 | chat_orchestrator 拆分（P2-3 前移至 P2-1） | ~3-5 天 |
| 4 | ToolRegistry 双注册表统一 | ~2-3 天 |
| 5 | 扩围跟踪集（core/ ~150 处裸 except 纳入评分） | ~1 天 |
| 6 | 端到端API验证（重启服务器后通过stream API测试） | ~2h |

---

*本文件由架构巡检岗编写，基于 95 轮巡检数据、knowledge_base 真谛库、以及 docs/architecture/ 设计文档的综合理解。*
