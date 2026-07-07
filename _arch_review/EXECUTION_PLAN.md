# 联盟拓荒者 — 可执行改进计划

> **基线**: 架构审核 `ARCHITECTURE_ANALYSIS.md` 中的 P0-P2 问题 & 5 阶段路线图  
> **策略**: P0 与阶段 1（稳基）合并，优先修复系统正确性/安全性问题，不新增功能  
> **估算**: 每个任务标注了预计工时，以"人·天"为单位  
> **最新更新**: 2026-07-07

---

## 总览：阶段划分与并行策略

```
                    时间线 (周)
任务              W1  W2  W3  W4  W5  W6  W7  W8
─────────────────────────────────────────────────
阶段1 稳基 (含P0)  ████
阶段2 拆巨兽       ░░  ████  ████
阶段3 治沉疴       ░░  ░░  ░░  ████
阶段4 筑高台       ░░  ░░  ░░  ░░  ████
阶段5 开新篇       ░░  ░░  ░░  ░░  ░░  ████
─────────────────────────────────────────────────
          并行清理任务（贯穿全程）░░░░░░░░░░░░░
```

**建议**: 阶段 1 必须串行完成；从阶段 2 开始，可与清理任务并行推进。

---

## 阶段 1：稳基（W1-W2，共 8 个任务）

### 总目标

在不改变系统行为的条件下，修复已知正确性/安全性问题，建立核心模块的防护网。

---

### 1.1 SpiritCore 原则常量不可变性加固

| 项目 | 内容 |
|------|------|
| **文件** | `core/spirit_core.py` |
| **问题** | 8 条核心原则和 3 条元宪法是类属性，运行时可通过 `SpiritCore.PRINCIPLE_NEVER_GIVE_UP = "xxx"` 修改，违反"不可违背"的设计承诺 |
| **方案** | 将常量改为 `@property` + 私有属性 + `typing.Final` |
| **预估** | 0.5 人·天 |
| **难度** | ★☆☆☆☆ |

**伪代码**：

```python
from typing import Final

class SpiritCore:
    _PRINCIPLE_NEVER_GIVE_UP: Final[str] = "永不放弃是元能力"
    _PRINCIPLE_MEANINGFUL_RESPONSE: Final[str] = "即使失败也给出有意义的回复"
    _PRINCIPLE_LOGICAL_SELF_CONSISTENT: Final[str] = "所有回答都必须逻辑清晰有理有据且自洽"
    _PRINCIPLE_LEARNING_FROM_FAILURE: Final[str] = "每次失败都是学习机会"
    _PRINCIPLE_STATE_SYNC: Final[str] = "回复是状态同步，不是结束动作"
    _PRINCIPLE_PURSUE_ESSENCE: Final[str] = "追求本质——从第一性原理出发"
    _PRINCIPLE_HONEST_WHEN_LOST: Final[str] = "困惑时坦诚——宁可诚实罗列分歧"
    _PRINCIPLE_MULTI_SOURCE_VERIFY: Final[str] = "多源交叉验证"

    @property
    def PRINCIPLE_NEVER_GIVE_UP(self) -> str:
        return self._PRINCIPLE_NEVER_GIVE_UP

    # ... 其余 7 条同理

    META_LAW_SANDBOX: Final[str] = "未经沙盒验证的真谛，视同毒药"
    META_LAW_GRADUAL: Final[str] = "未经渐进式注入的重组，视同自杀"
    META_LAW_HUMAN_APPROVAL: Final[str] = "未经人类批准的进化，视同背叛"
```

**验证**：
1. `SpiritCore.PRINCIPLE_NEVER_GIVE_UP = "new"` → `AttributeError` 或静默失败（不可修改）
2. 所有现有调用 `sp.enforce_on_output(text)` 行为不变
3. 新增 `test_principles_are_immutable` 测试用例

**注意**: 如果现有代码中有任何对常量的**写操作**（如 `core.alignment_guard.py` 中可能修改原则），需先在 grep 中确认并修复调用方。

---

### 1.2 chat_stream.py 异常处理审计（P0-2）

| 项目 | 内容 |
|------|------|
| **文件** | `backend/chat_stream.py` |
| **问题** | 多处 `try/except` 直接返回 `{"response": "", "error": str(e)}`，静默失败，违反"永不放弃"元原则 |
| **方案** | 逐 handler 审计，区分"可降级路径"和"不可降级路径"；所有不可降级路径失败时确保调用 NeverGiveUpEngine 兜底 |
| **预估** | 1 人·天（含理解代码逻辑的时间） |
| **难度** | ★★★☆☆ |

**审计清单**（需 grep 确认精确行号）：

```python
# [ ] _fetch_experience() — 经验池查询失败 → 可降级（跳过此路）
# [ ] _fetch_knowledge() — 知识库查询失败 → 可降级（跳过此路）
# [ ] _fetch_ollama_all() — 本地模型失败 → 可降级（跳过此路，尝试外部API）
# [ ] _fetch_external_api() — 外部API失败 → 可降级
# [ ] _fetch_external_learning() — 外部搜索失败 → 可降级
# [ ] _identify_intent() — 意图识别失败 → 不可降级！必须给出合理回复
# [ ] essence_reasoner.reason() — 本质推理失败 → 不可降级！需给出不确定性说明
# [ ] spirit_core.enforce_on_output() — 精神验证失败 → 不可降级！需触发反思

# 修复模式：
# 可降级路径：logger.warning → skip → 其他路径补充
# 不可降级路径：logger.error → NeverGiveUpEngine.solve() → 返回"当前最佳答案"
```

**方案细节**：

```python
# 可降级路径统一模式
async def _safe_fetch(fetch_fn, path_name: str, *args, **kwargs):
    """包装所有可降级的并行路径"""
    try:
        return await fetch_fn(*args, **kwargs)
    except asyncio.TimeoutError:
        logger.warning(f"[{path_name}] 超时，跳过此路")
        return None, 0
    except Exception as e:
        logger.warning(f"[{path_name}] 失败: {e}，跳过此路")
        return None, 0

# 不可降级路径 — 对结果验证
if not best_response or not best_response.strip():
    logger.error("所有路径均失败，触发 NeverGiveUpEngine 兜底")
    backup = await never_give_up.solve(query, context={
        "previous_attempts": all_path_results,
        "path_status": path_status,
    })
    best_response = backup.get("response", "抱歉，我当前无法处理这个问题。请换个方式描述？")
    
    # 补充 spirit_core 验证（必须通过）
    validation = await _run_sync(spirit_core.enforce_on_output, best_response)
    if not validation.get("passed", False):
        logger.warning(f"兜底回复未通过精神验证: {validation.get('issues', '')}")
        # 追加不确定性说明而非吞掉
        best_response += "\n\n> ⚠️ 此回复未完全通过系统验证，请谨慎参考。"
```

**验证**：
1. 每个 `_fetch_*` 函数调用都包裹了 `_safe_fetch`
2. `NeverGiveUpEngine.solve()` 在所有路径失败时被调用（而非返回空字符串）
3. `test_all_paths_failure_triggers_never_give_up` 测试通过

---

### 1.3 SQLite 多线程并发写加固（P0-3）

| 项目 | 内容 |
|------|------|
| **涉及文件** | `infrastructure/fact_store.py`, `infrastructure/experience_pool.py`, `core/task_queue.py`, `core/spirit_core.py`, `core/alignment_guard.py` 等 |
| **问题** | 所有 SQLite 操作用 `sqlite3.connect()` 直接连接，多线程环境下有并发写冲突 |
| **方案** | 创建统一的 `DatabaseManager` 类，提供线程安全的读写接口 |
| **预估** | 1.5 人·天（含重构 5-8 个文件的数据库调用） |
| **难度** | ★★★☆☆ |

**设计方案**：

```python
# 新增文件: infrastructure/database_manager.py

import sqlite3
import threading
from pathlib import Path
from typing import Optional, Callable, TypeVar
from loguru import logger

T = TypeVar("T")

class DatabaseManager:
    """线程安全的 SQLite 数据库管理器"""
    
    def __init__(self, db_path: str, timeout: float = 10.0):
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._timeout = timeout
        # 每个线程一个连接（避免跨线程共享连接）
        self._local = threading.local()
    
    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self._path),
                timeout=self._timeout,
                check_same_thread=False,  # 由锁控制并发
            )
            self._local.conn.execute("PRAGMA journal_mode=WAL")        # WAL 模式提升并发读
            self._local.conn.execute("PRAGMA synchronous=NORMAL")      # 平衡安全与性能
        return self._local.conn
    
    def execute(self, sql: str, params=(), commit: bool = False):
        """线程安全的 execute"""
        with self._lock:
            conn = self._get_connection()
            cursor = conn.execute(sql, params)
            if commit:
                conn.commit()
            return cursor
    
    def execute_many(self, sql: str, seq_params, commit: bool = True):
        with self._lock:
            conn = self._get_connection()
            conn.executemany(sql, seq_params)
            if commit:
                conn.commit()
    
    # ... query() / transaction() / close() 等方法

# 初始化（在 lifespan 或模块级别）
db_instances: dict[str, DatabaseManager] = {}

def init_databases(data_dir: str = "data"):
    from pathlib import Path
    data_path = Path(data_dir)
    db_instances["experience"] = DatabaseManager(str(data_path / "experience.db"))
    db_instances["knowledge"] = DatabaseManager(str(data_path / "knowledge.db"))
    db_instances["spirit"] = DatabaseManager(str(data_path / "spirit.db"))
    # ...
```

**迁移策略**：不一次全部替换，按以下优先级逐文件迁移：

1. `fact_store.py` — 读多写少，风险高（并发校验写入）
2. `experience_pool.py` — 写频繁
3. `spirit_core.py` — 教训持久化
4. `alignment_guard.py` — 偏离记录
5. `task_queue.py` — 后台任务队列

**验证**：
1. `test_concurrent_writes_no_corruption` — 10 线程同时写入无数据损坏
2. 现有功能回归测试通过
3. 数据库文件统一位于 `data/` 目录

---

### 1.4 超时路径用户反馈（P0-4）

| 项目 | 内容 |
|------|------|
| **文件** | `backend/chat_stream.py` + `backend/main_fast.py`（SSE 相关） |
| **问题** | 并行路径超时后静默跳过，用户无感知 |
| **方案** | 通过 SSE 推送每条路径的状态（进行中/超时/失败/成功），前端显示加载状态 |
| **预估** | 1 人·天（含前后端配合） |
| **难度** | ★★☆☆☆ |

**前端/SSE 事件格式**：

```json
// SSE event: path_status
{
  "type": "path_status",
  "data": {
    "path": "ollama",
    "status": "timeout",
    "elapsed_seconds": 30.2,
    "message": "本地模型响应超时，已跳过此路"
  }
}

// SSE event: path_status
{
  "type": "path_status",
  "data": {
    "path": "external_api",
    "status": "success",
    "elapsed_seconds": 4.1,
    "contribution": 0.35
  }
}

// SSE event: fallback_notice
{
  "type": "fallback_notice",
  "data": {
    "reason": "所有主路径均失败",
    "activated": "NeverGiveUpEngine",
    "elapsed_seconds": 65.0
  }
}
```

**后端改动**：

```python
# chat_stream.py 中的并行 gather 改为逐条状态推送
async def _fetch_with_progress(session, path_name, fetch_fn, emit_fn, *args, **kwargs):
    start = time.time()
    try:
        await emit_fn("path_status", {"path": path_name, "status": "running"})
        result = await asyncio.wait_for(fetch_fn(*args, **kwargs), timeout=30)
        elapsed = time.time() - start
        await emit_fn("path_status", {
            "path": path_name, "status": "success",
            "elapsed_seconds": round(elapsed, 1),
        })
        return result
    except asyncio.TimeoutError:
        elapsed = time.time() - start
        await emit_fn("path_status", {
            "path": path_name, "status": "timeout",
            "elapsed_seconds": round(elapsed, 1),
            "message": f"{path_name} 响应超时（30s），已跳过",
        })
        return None
    except Exception as e:
        elapsed = time.time() - start
        await emit_fn("path_status", {
            "path": path_name, "status": "failed",
            "elapsed_seconds": round(elapsed, 1),
            "message": str(e)[:100],
        })
        return None
```

**验证**：
1. 前端在每条路径开始/超时/失败时收到 SSE 事件
2. 所有路径超时后，前端显示兜底回复
3. `test_parallel_path_timeout_emits_event` 测试

---

### 1.5 核心模块单元测试（贯穿时段 1）

| 项目 | 内容 |
|------|------|
| **文件** | `tests/unit/test_spirit_core.py`、`tests/unit/test_essence_reasoner.py`、`tests/unit/test_cognitive_dispatcher.py` |
| **问题** | 当前测试以集成/端到端为主，核心模块无单元测试 |
| **方案** | 为 SpiritCore、EssenceReasoner、CognitiveDispatcher 编写 Mock 隔离的单元测试 |
| **预估** | 2 人·天（可按模块分工） |
| **难度** | ★★☆☆☆ |

**Mock 策略**（以 SpiritCore 为例）：

```python
# tests/unit/test_spirit_core.py
import pytest
from core.spirit_core import SpiritCore

@pytest.fixture
def spirit() -> SpiritCore:
    return SpiritCore(db_path=":memory:")  # 使用内存数据库

class TestSpiritCorePrinciples:
    def test_principles_are_immutable(self):
        with pytest.raises((AttributeError, TypeError)):
            SpiritCore.PRINCIPLE_NEVER_GIVE_UP = "changed"  # type: ignore
    
    def test_enforce_on_output_passes_valid(self, spirit):
        text = "这是一个基于多源验证的合理回答。"
        result = spirit.enforce_on_output(text)
        assert result["passed"] is True
    
    def test_enforce_on_output_rejects_empty(self, spirit):
        result = spirit.enforce_on_output("")
        assert result["passed"] is False

# tests/unit/test_essence_reasoner.py
from core.essence_reasoner import EssenceReasoner

def test_reasoner_detects_contradiction():
    reasoner = EssenceReasoner()
    result = reasoner.reason("地球是平的。地球是圆的。")
    assert result.get("contradiction_detected") is True

# tests/unit/test_cognitive_dispatcher.py
@pytest.mark.asyncio
async def test_dispatcher_routes_simple_query():
    dispatcher = CognitiveDispatcher(config={})
    intent = await dispatcher.classify("你好")
    assert intent == "greeting"
```

**验证**：
1. `pytest tests/unit/ -v` 全部通过
2. 不依赖 Ollama、DB 文件、网络
3. 覆盖率 `pytest --cov=core --cov-report=term` > 70%

---

### 1.6 新增模块集成检查清单（流程建立）

| 项目 | 内容 |
|------|------|
| **文件** | `CODEOWNERS` + `.github/PULL_REQUEST_TEMPLATE.md`（新建） |
| **方案** | 建立 PR 模板 + 合并检查清单 |
| **预估** | 0.5 人·天 |
| **难度** | ★☆☆☆☆ |

**PR 模板**：

```markdown
## 变更摘要
<!-- 说明改了什么、为什么改 -->

## 架构对齐
- [ ] 本变更符合 SpiritCore 8 条原则（特别说明：______）
- [ ] 本变更符合元宪法 R1/R2/R3
- [ ] 本变更不绕过闭环学习机制

## 测试覆盖
- [ ] 新增/修改了单元测试
- [ ] 所有测试通过（`pytest -v`）
- [ ] 集成测试标记了 `@pytest.mark.integration`

## 代码规模
- [ ] 单个文件不超过 500 行（是/否，超过请说明）
- [ ] 与现有模块无功能重叠

## 检查项
- [ ] 配置项写入 config.yaml（如适用）
- [ ] 日志按 loguru 规范输出
```

---

### 1.7 阶段 1 交付检查清单

```
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
  阶段 1 — 稳基交付检查
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓

□ 1.1 SpiritCore 常量不可变
    - 8 条原则 + 3 条元宪法全部 Final/不可写
    - 测试通过了原则不可修改断言
    - grep 确认无任何代码试图写这些常量

□ 1.2 chat_stream 异常审计
    - 所有 try/except 区分了可降级/不可降级
    - NeverGiveUpEngine 在所有路径失败时被调用
    - 吞掉的异常平均 < 移除前的 10%

□ 1.3 SQLite 并发写安全
    - DatabaseManager 实现完成
    - 高频写文件（fact_store / experience_pool）迁移完毕
    - 并发测试通过

□ 1.4 超时路径用户反馈
    - SSE path_status 事件推送到前端
    - 所有路径超时后有兜底通知
    - 前端有对应的加载状态展示

□ 1.5 核心单元测试
    - SpiritCore 测试覆盖 > 80%（原则 + enforce + 异常记录）
    - EssenceReasoner 测试覆盖 > 70%
    - CognitiveDispatcher 测试覆盖 > 70%

□ 1.6 流程检查清单
    - PR 模板已建立
    - CODEOWNERS 已配置
```

---

## 阶段 2：拆巨兽（W2-W4）

### 2.1 chat_stream.py → 模块拆分

**当前**: `chat_stream.py` ~4000 行，包含意图识别/并行调度/择优融合/推理验证/反思学习/后台进化

**目标拆分**：

```
backend/
├── chat_stream.py              # 删除或保留为编排入口（~200 行）
├── services/
│   ├── __init__.py
│   ├── intent_service.py       # 意图识别 + 本质闸门
│   ├── parallel_router.py      # 8 路径并行调度 + 超时管理
│   ├── response_aggregator.py  # 对比择优 + 回复融合
│   ├── chat_orchestrator.py    # 编排 1-8 阶段
│   └── path_handlers/
│       ├── __init__.py
│       ├── experience_path.py
│       ├── knowledge_path.py
│       ├── ollama_path.py
│       ├── external_api_path.py
│       ├── rule_path.py
│       ├── fact_path.py
│       └── tool_path.py
```

**原则**: 拆分时只搬移代码不做行为改变，不重构内部逻辑。行为改变留给阶段 2.2。

### 2.2 main_fast.py → routers + lifespan 分离

```
backend/
├── main_fast.py                # 仅 app 创建 + 中间件 + lifespan
├── lifespan.py                 # 启动序列（从 main_fast 抽出）
├── routers/
│   ├── chat.py                 # /chat, /stream
│   ├── knowledge.py            # /knowledge/*
│   ├── system.py               # /health, /stats, /config
│   └── evolution.py            # /evolve, /gene
├── middleware/
│   └── timeout.py              # 连接超时中间件
```

### 2.3 引入端口抽象

```
core/ports/
├── __init__.py
├── llm_port.py                 # ✅ 已存在
├── ui_port.py                  # ✅ 已存在
├── vector_store_port.py        # 向量检索
├── knowledge_port.py           # 知识库
├── fact_store_port.py          # 事实库
├── experience_port.py          # 经验池
├── tool_executor_port.py       # 工具执行
├── event_bus_port.py           # 事件总线
├── config_port.py              # 配置管理
└── task_queue_port.py          # 任务队列
```

每个端口文件原则上不超过 50 行（仅抽象方法）。

---

## 阶段 3：治沉疴（W3-W5）

### 3.1 死代码清理

```
行动                                   价值
───────────────────────────────────────
□ 审查 orchestrator.py + cognitive_loop.py
   → 如果 main_fast.py 绝不使用，移入 archives/   减少 2 个文件
□ 合并 signal_integration.py → gap_growth.py    减少 1 个文件
□ 合并 versioned_fact_store.py → fact_store.py   减少 1 个文件
□ 审查 learning/ 目录下 7 个文件
   → 与已集成功能重叠的归档                       减少 3-5 个文件
□ 审查 layers/ 目录下 6 个文件
   → 实际只有 L0-L4，L5/L6 不存在的文档纠正        更新文档
□ 删除 _archives 中 temp_scripts 的旧测试脚本     减少认知负担
```

### 3.2 配置统一

```
当前分散状态              目标状态
────────────────────────────────
.env (API keys)        ├── .env (仅 secrets)
config.yaml (系统配置)  ├── config.yaml (所有系统配置)
pyproject.toml (工具)   ├── pyproject.toml (仅构建+工具)
                      └── config/default.yaml (默认值模板)
```

### 3.3 数据库统一

```
当前：工程根目录散落 5+ .db 文件
迁移至：data/ 目录
```

---

## 阶段 4：筑高台（W5-W6）

- GitHub Actions CI（push → lint → unit test → integration test）
- ruff + 统一风格配置
- 前端 RPV 循环展示
- 性能基线 + APM 埋点

---

## 阶段 5：开新篇（W7-W8）

- scikit-optimize 贝叶斯优化替代当前简单统计
- 修复 sentence_transformers DLL 问题
- 端口可插拔存储适配器（Redis/PostgreSQL）
- 进化岛沙盒自动定时运行

---

## 协作执行建议

### 分工矩阵

```
任务                  建议认领角色       所需前置条件
────────────────────────────────────────────
1.1 SpiritCore 加固   后端工程师        无
1.2 异常审计          架构师+后端       1.1 完成后
1.3 DatabaseManager   后端工程师        无（独立）
1.4 SSE 超时反馈      全栈工程师        1.2 部分依赖
1.5 单元测试          测试工程师/新人   1.1-1.3 完成后
1.6 PR 模板           任一工程师        无
```

### 任务边界原则

1. **阶段 1 内**：只修改行为边界，不新增模块。
   - ✅ `SpiritCore` 原则加固 → 只改 `spirit_core.py`
   - ✅ 异常审计 → 只改 `chat_stream.py`
   - ❌ 拆分 `chat_stream.py` → 属于阶段 2
2. **一个任务一个 PR**：PR 模板（1.6）应在第一个 PR 之前合并。
3. **凡改动必有测试**：阶段 1 整体要求测试覆盖率从当前 < 10% 提升到 > 60%。
4. **凡删除必有备份**：死代码先移入 `archives/` 目录，观察 2 周无回归再彻底删除。

---

## 附录：快速开始指南

### 对协作者的建议阅读路径

```
1. 先读 README.md（15 分钟）— 理解核心理念
2. 再读 ALIGNMENT_CHARTER.md（10 分钟）— 理解价值观约束
3. 再读 ARCHITECTURE_CURRENT.md（15 分钟）— 理解实际架构
4. 再读 _arch_review/ARCHITECTURE_ANALYSIS.md（20 分钟）— 理解问题全局
5. 再读本执行计划 _arch_review/EXECUTION_PLAN.md（10 分钟）— 认领任务
```

### 环境准备

```powershell
# 1. 克隆并创建虚拟环境
git clone <repo_url>
cd alliance_pioneer
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. 安装依赖
pip install -e ".[dev,all]"

# 3. 运行现有测试确认基线
pytest -v --tb=short

# 4. 运行现有后端确认可用
python -m uvicorn backend.main_fast:app --reload
```

---

> **核心原则回顾**：所有改动必须与精神内核对齐 — 不违反元宪法、不静默吞噬错误、不替用户做决定、始终保持可被质疑。  
> **祝编码愉快 🚀**
