# 行动指南 v2026-07-24 — "唤醒沉睡者"计划执行记录

> 生成时间：2026-07-24 03:20
> 基于看板全量数据 + 代码交叉验证 + SelfRepairLoop 扫描
> 策略：不新建任何模块，从现有代码中挖掘价值

---

## 一、今日成果（9 commits）

### 止血（工作区清零，打破9轮冻结）

| commit | 动作 | 效果 |
|--------|------|------|
| `f6e0de4` | 强制提交 389 文件 | 工作区 0 变更，打断 9 轮 0 commit 记录 |
| `e8bb4e7` | 更新 .gitignore | tests/OLD/, tests/scripts/ 不再追踪 |

### 接线（2 条断裂修复）

| commit | 断裂 | 修复方式 | 行数 |
|--------|------|---------|:----:|
| `4672f0e` | 全路径失败后无兜底 | never_give_up.py → chat_orchestrator 阶段R前 | +23 |
| `7618964` | 反思不指导决策（看板#41） | reflection → truth_accumulator._save_truth() | +17 |

### 诊断工具（可重复运行）

| commit | 工具 | 功能 |
|--------|------|------|
| `edaff46` | SelfRepairLoop v1 | 孤立模块检测 + 接入桩生成 |
| `725acfe` | SelfRepairLoop v2 | 启发式修复：完整导入路径匹配（168→2） |

### 清理（减少噪音）

| commit | 清理内容 | 当前最大文件 |
|--------|---------|:------------:|
| `82ac25a` | 删除 143 个误报 hook 文件 | — |
| `6b3759b` | 归档 2 个零引用 ports 模块 | — |
| `a466b97` | planner.py 拆分第一步 | **2894→2744** |

---

## 二、当前状态

### 工作区
```
HEAD:        a466b97 (2026-07-24)
工作区变更:  0
未跟踪文件:  0
今日 commits: 9
```

### 孤立模块清单（SelfRepairLoop v2 确认）
```
真孤立：0 个（core/ 下所有 .py 均被引用）
已归档：compliance_check.py + enforcement.py（零引用，职责已分散）
```

### 最大 5 个源文件

| 文件 | 行数 | 目标 |
|------|:----:|:----:|
| `core/services/planner_main.py` | **2744** | **<150**（7 mixin 提取中） |
| `core/cognitive_architecture_v2.py` | 1653 | 待评估 |
| `core/self/model.py` | 1492 | 逼近1500警戒线 |
| `core/truth_accumulator.py` | 1289 | 超1000 |
| (第5未显示) | — | — |

### 未完成项清单（有效值：9项，看板确认）

| 优先级 | 项目 | 状态 |
|--------|------|------|
| P1 | 端口抽象 Phase3 外部接口标准化 | ⏳ 未开始 |
| P1 | core 裸 except 扩围跟踪集 | ⏳ 未开始 |
| P1 | 因果图真实经验注入 | ⏳ 未开始 |
| P2 | planner.py 拆分（7 mixin） | 🏗️ 1/7 完成 |
| P2 | orchestrator 545→进一步瘦身 | ⏳ 未开始 |
| P2 | 贝叶斯优化接入主流程 | ⏳ 未开始 |
| P2 | 连接池完善 | ⏳ 未开始 |
| P3 | pending_questions 追踪 | ⏳ 未开始 |
| P3 | 置信度衰减机制 | ⏳ 未开始 |

---

## 三、下一步行动：planner.py 拆分计划

### 目标
`core/services/planner_main.py` **2744 → <150 行**（7 个 mixin 提取）

### 7 个 mixin 分配

```
planner_main.py (壳)                  ~150 行   ← DataDrivenPlanner 多继承组装
├── search_engine.py      ✅ 已提取   ~110 行   ← Bing/Wikipedia/DDGS 搜索
├── knowledge_retriever.py  ⏳ 待提取  ~100 行   ← 知识检索
├── self_evaluator.py       ⏳ 待提取  ~200 行   ← 自我评估报告
├── meta_problem_solver.py  ⏳ 待提取  ~200 行   ← 元问题处理
├── model_selector.py       ⏳ 待提取  ~200 行   ← 模型选择
├── tool_executor.py        ⏳ 待提取  ~100 行   ← 工具执行
└── optimizer.py            ⏳ 待提取  ~100 行   ← 贝叶斯/归纳优化
```

### 执行顺序

```
每步：grep 方法行号 → 创建 .py → 写入 mixin class → 删除原方法 → 验证导入 → commit
```

| 步骤 | 文件 | 方法 | 耗时 |
|------|------|------|:----:|
| ✅ 1 | search_engine.py | `_try_search_enhanced_answer`, `_search_bing`, `_search_wikipedia` | 15min |
| 2 | knowledge_retriever.py | `_try_knowledge_retrieval`, `_try_vector_reuse`, `_try_rule_based_routing` | 15min |
| 3 | self_evaluator.py | `_report_capability_boundary`, `_report_self_assessment`, `_evaluate_recent_dialogs`, `_estimate_self_confidence` | 20min |
| 4 | meta_problem_solver.py | `_handle_meta_question`, `_handle_meta_value_question` | 15min |
| 5 | model_selector.py | `_select_model`, `_data_driven_select`, `_skill_to_model`, `_get_user_preference_weights` | 20min |
| 6 | tool_executor.py | `_try_tool_first`, `_check_reflex_level` | 15min |
| 7 | optimizer.py | `run_optimization`, `run_induction`, `_setup_bayesian_optimization` | 20min |

### 验证方法

```bash
# 每提取一个 mixin 后
python -c "from core.services.planner import DataDrivenPlanner; print('import OK')"

# 全部提取完成后
python -c "
from core.services.planner import DataDrivenPlanner, Planner
from core.services.cognitive_planner import get_cognitive_planner
print('引用兼容:', type(get_cognitive_planner()).__name__)
"
```

---

## 四、自修复工具使用说明

```bash
# 运行完整审计
python core/self_repair/loop.py

# 输出：
# - 孤立模块清单 + 大小 + 建议优先级
# - >5KB 的孤立模块自动生成接入桩到 _arch/hooks/
# - 人工审核后将桩移动到合适位置

# 验证接线前后对比
python -c "
from core.self_repair.loop import SelfRepairLoop
print('接线前:', len(SelfRepairLoop().find_dangling_modules()))
# 预期接一个模块少一个
"
```

---

## 五、关键原则

1. **不新建模块** — 只在现有流程中插接入点
2. **每天至少一个 commit** — 哪怕只改了注释（防止冻结）
3. **try/except 降级保护** — 所有接入点失败不阻塞主流程
4. **验证后再接下一个** — 每完成一个 mixin 运行导入测试
5. **归档不删除** — git mv 到 _arch/OLD/，保留完整 git 历史

---

*行动计划由架构巡检系统生成 — 2026-07-24*
*巡检员: Kun*
