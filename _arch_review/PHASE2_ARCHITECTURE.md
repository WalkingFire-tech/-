# 阶段2 拆巨兽 — 架构设计方案

> **状态**: 进行中（chat_stream.py 已拆分 36%，main_fast.py 未开始）  
> **⚠️ 当前警示**: 健康评分 40/100（DB 反弹：sqlite3.connect 从 4 处反弹回 28 处）  
> **策略**: "借道还债" — 每次改动带走一个函数/路由，同时修复该函数中的遗留问题  
> **质量门槛**: 拆分前必须同时完成该函数的 DB 迁移和异常清理  
> **本文档**: 只给设计，不给实现代码。协作者阅读后自行决策如何落地。

---

## 1. 最终目标架构

### 1.1 backend/ 目录最终结构

```
backend/
├── main_fast.py              # ~100行：仅 app 创建 + lifespan 注册
│
├── lifespan.py                # ~100行：从 main_fast 抽出
│
├── routers/                   # 按领域拆分路由
│   ├── __init__.py
│   ├── chat.py                # 聊天路由（/chat/stream, /chat/send）
│   ├── health.py              # 健康检查（/health）
│   ├── knowledge.py           # 知识管理（/knowledge/*）
│   ├── system.py              # 系统管理（/system/stats, /system/config）
│   ├── evolution.py           # 进化管理（/evolve, /gene）
│   └── proactivity.py         # 主动性 SSE 流（/proactivity/stream）
│
├── services/                  # 业务逻辑层（已有雏形）
│   ├── __init__.py
│   ├── chat_orchestrator.py   # chat_stream() 主编排逻辑（~300行）
│   ├── intent_service.py      # ✅ 已有
│   ├── response_aggregator.py # ✅ 已有
│   ├── methodology_service.py # ← 待从 chat_stream 抽出
│   ├── code_verifier.py       # ← 待从 chat_stream 抽出
│   └── path_handlers/         # ✅ 已有（8个子模块）
│
├── middleware/
│   └── timeout.py             # 连接超时中间件
│
├── chat_stream.py             # 保持向后兼容的编排入口（~100行，委托给 services/*）
└── chat_handler.py            # 非流式聊天（暂保持）
```

### 1.2 chat_stream.py 剩余函数分配方案

当前 2378 行中，除了已抽出的 path_handlers 和 intent_service/response_aggregator，还有以下函数需要安置：

| 函数 | 行数 | 目标模块 | 优先级 |
|------|------|----------|--------|
| `chat_stream()` 主函数 | ~1000 | `services/chat_orchestrator.py` | P0 |
| `_discover_methodology()` | ~50 | `services/methodology_service.py` | P1 |
| `_verify_code_response()` | ~120 | `services/code_verifier.py` | P1 |
| `_has_science_domain_signatures()` | ~15 | → 合并到 intent_service.py | P2 |
| `_understand_response_content()` | ~80 | → 合并到 intent_service.py | P2 |
| `_infer_domain_from_content()` | ~30 | → 合并到 intent_service.py | P2 |
| SSE emit 事件枚举 | ~50 | `services/event_definitions.py` | P3 |

> **"借道还债"排序**: 下一次有人改 chat_stream.py → 优先创建 `chat_orchestrator.py`，把 chat_stream() 主体搬过去。这是单体文件的核心，必须先拆分。

---

## 2. chat_stream() 主编排逻辑 — 架构设计

### 2.1 当前问题

`chat_stream()` 是一个约 1000 行的 `async generator`，内部以**阶段注释**（`# 阶段1：意图识别`、`# 阶段3：多策略并行`）分隔 9 个阶段。每个阶段内部都有独立的异常处理、SSE 事件推送、日志记录——但它们共享同一个函数作用域。

这意味着：
- 修改阶段 3 的逻辑可能会影响阶段 5 的变量
- 无法单独测试阶段 4（对比择优）而不运行完整流程
- 新成员理解这个函数需要同时理解所有 9 个阶段的细节

### 2.2 目标设计

```python
# services/chat_orchestrator.py

async def chat_stream(user_input: str, context: dict):
    """主编排器：只负责"什么时候做什么"，不负责"怎么做" """
    
    # 阶段 1：意图识别 → 委托给 intent_service
    intent, confidence, route = await intent_service.identify(user_input, context)
    
    # 阶段 1.5：规则匹配 → 委托给 rule_path
    rule_actions = rule_path.evaluate_rules(user_input, intent)
    
    # 阶段 2：简单意图直接返回 → intent_service 的快速路径
    quick_reply = intent_service.try_fast_path(intent, user_input)
    if quick_reply:
        return quick_reply
    
    # 阶段 2.5：本质闸门 → 委托给 essence_reasoner（外部 core 模块）
    essence_gate = await call_essence_gate(user_input)
    
    # 阶段 3：多策略并行 → 委托给 parallel_router
    candidates = await parallel_router.execute(
        user_input, intent, essence_gate, context
    )
    
    # 阶段 4：对比择优 → 委托给 response_aggregator
    best, comparison = response_aggregator.select_best(candidates)
    
    # 阶段 4.5-8：本质推理、精神验证、反思学习、后台进化
    # ...逐步委托给对应服务...
    
    return final_response
```

**核心设计原则**: 每个阶段：
1. **只调用一个外部函数**（委托给 services/ 或 core/）
2. **不自己实现逻辑**（不包含 sqlite3.connect、不包含 try/except 业务逻辑）
3. **结果是一个简单 dict**（状态 + 数据，不包含中间变量）

### 2.3 迁移策略（"借道还债"顺序）

```
PR #1: 创建 services/chat_orchestrator.py
       从 chat_stream.py 复制 chat_stream() 函数体（完整复制，不改一行）
       chat_stream.py import 并调用 orchestrator.chat_stream()
       验证回归：原有测试 + API 请求
       ✅ 效果：chat_stream.py -1000行（从不复制时 2378 → 1378 行）

PR #2: 将阶段 1/1.5/2 提取为 orchestrator 内部方法
       然后将这些方法拆入 intent_service 和 rule_path
       ✅ 效果：orchestrator.py -150行，chat_stream.py -50行

PR #3: 将阶段 3 提取为 parallel_router 的调用
       ✅ 效果：orchestrator.py -200行

PR #4-N: 逐阶段提取...
```

### 2.4 ⚠️ 质量门槛（拆分的前置条件）

> **原则**: "借道还债"不只是搬代码，更重要的是在搬的过程中修复遗留问题。

**硬性条件** — 不满足不拆分：

```
拆分 chat_stream() 的任一函数时，该函数必须同时满足：

□ 如果函数里有 sqlite3.connect() → 必须迁移到 DatabaseManager
   chat_stream() 主函数中有 8 处 experience_pool.db 连接（2026-07-07 巡检数据）
   这 8 处必须在拆分 PR #1 前或同时修掉

□ 如果函数里有 except: → 必须改为 except Exception:
   chat_stream.py 当前零裸 except（✅ 阶段1已修复），保持清零

□ 如果函数里有 asyncio.Semaphore() → 必须用 _get_ollama_semaphore() 替代
   所有 path_handlers 已经修复，不要在 orchestrator 中重新引入
```

**为什么要有这个门槛**（来自巡检#11的警示）：

```
健康评分 58→40 暴跌的主因：
  sqlite3.connect 从 4 处反弹回 28 处（DB 访问未统一）

如果 chat_orchestrator.py 带着 8 处裸 connect 被创建：
  → 等于把问题扩散到了新模块
  → 以后查"28处connect"时会变成"28+8=36处"
  → 违背"追求本质"原则——不是在改善，只是在搬家
```

**例外**: 如果某函数本来就无 DB 操作、无裸 except（如 `_discover_methodology`、`_verify_code_response`），可以直接拆分，不受此限制。

---

## 3. main_fast.py 路由拆分 — 架构设计

### 3.1 当前结构

`main_fast.py` 约 2350 行，包含：

```
┌─────────────────────────────────────────────┐
│ lifespan()          ~120行  启动序列          │
│ _periodic_*          ~80行  后台周期任务       │
│ _on_* events        ~60行  事件回调            │
│ middleware            ~20行  超时中间件         │
│ GET /                ~10行  根路由             │
│ GET /api/health      ~20行  健康检查            │
│ GET /api/stats       ~30行  系统状态            │
│ POST /api/chat       ~10行  非流式聊天          │
│ GET /api/chat/stream ~30行  流式聊天 SSE        │
│ POST /api/evolve     ~30行  触发进化             │
│ GET /api/gene        ~20行  查看基因             │
│ POST /api/learn      ~20行  触发学习             │
│ … 还有 15+ 个路由      ~300行  知识/文件/系统    │
│ _on_idle_period      ~80行  空闲周期             │
│ _assessment_driven…  ~100行 评估驱动修复          │
│ proactivity_stream   ~60行  主动性 SSE           │
│ … 后台任务 + 初始化    ~800行  各种服务初始化      │
└─────────────────────────────────────────────┘
```

### 3.2 目标设计

```python
# main_fast.py — 约 80 行
# 职责仅：创建 app、注册 lifespan、注册路由、注册中间件

@asynccontextmanager
async def lifespan(app):
    await lifespan_manager.start()
    yield
    await lifespan_manager.stop()

app = FastAPI(lifespan=lifespan, title="联盟拓荒者 API")
app.add_middleware(CORSMiddleware, ...)
app.include_router(health_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(system_router, prefix="/api")
app.include_router(evolution_router, prefix="/api")
app.include_router(proactivity_router, prefix="/api")
```

```python
# lifespan.py — 约 150 行
# 职责仅：启动序列的编排

class LifespanManager:
    async def start(self):
        await self._init_ollama()
        await self._init_vector_store()
        await self._start_existence_layer()
        await self._start_cognitive_metabolism()
        self._start_background_tasks()
    
    async def stop(self):
        # 反向顺序关闭
        self._stop_background_tasks()
        await self._stop_existence_layer()
```

```python
# routers/health.py — 约 30 行
"""健康检查路由"""
router = APIRouter()

@router.get("/health")
async def health():
    return {"status": "ok", "version": "3.7.0", ...}
```

```python
# routers/chat.py — 约 50 行
"""聊天路由 — 只做请求/响应转换，业务逻辑委托给 services/"""
router = APIRouter()

@router.post("/chat/stream")
async def chat_stream_endpoint(request: Request):
    user_input = await request.json()
    return StreamingResponse(chat_stream(user_input), media_type="text/event-stream")
```

### 3.3 迁移策略

**分工建议**（可并行）：

| 谁 | 做什么 | 预估 |
|----|--------|------|
| 一人 | 创建 `lifespan.py`，把 lifespan 和所有后台任务从 `main_fast.py` 搬过去 | 1 天 |
| 另一人 | 创建 `routers/health.py` + `routers/system.py`，搬走健康检查和系统路由 | 0.5 天 |
| 第三个人 | 创建 `routers/chat.py`，搬走聊天路由 | 0.5 天 |
| 同上人 | 创建 `routers/knowledge.py`，搬走知识管理路由 | 0.5 天 |
| 同上人 | 创建 `routers/evolution.py` + `routers/proactivity.py` | 0.5 天 |

**迁移后 `main_fast.py` 行数变化**：
```
2350 行
 - 120 lifespan
 - 80  periodic tasks
 - 60  event callbacks
 - 300 all route handlers
 - 800 initialization + background tasks
───────
~990 行（仍需要进一步拆分初始化和后台任务，但已可接受）
```

---

## 4. 端口抽象层（core/ports/）— 架构设计

### 4.1 当前状态

```
core/ports/
├── llm_port.py  ← URL：17 行，定义了 generate() + model_name
└── ui_port.py   ← URL：极简
```

缺少 6-8 个端口，导致 infrastructure/ 层的所有模块直接暴露给 core/，无法隔离、无法替换、难以测试。

### 4.2 目标端口体系

```
core/ports/
├── __init__.py               # 统一导出
├── llm_port.py               # ✅ 已存在 — LLM 生成
├── ui_port.py                # ✅ 已存在 — UI 交互
│
├── vector_store_port.py      # 向量检索
│   └── search(query, k, threshold) → list[dict]
│   └── is_available() → bool
│
├── knowledge_port.py         # 知识库
│   └── search(query) → list[dict]
│   └── store(content, metadata) → str
│
├── fact_store_port.py        # 事实锚点
│   └── search_by_keywords(text, limit) → list[dict]
│   └── extract_and_store(text) → int
│
├── experience_port.py        # 经验池
│   └── search(query) → list[dict]
│   └── save(input, response, metadata) → str
│
├── config_port.py            # 配置管理
│   └── get(key, default) → Any
│   └── get_section(name) → dict
│
├── event_bus_port.py         # 事件总线
│   └── publish(event_type, data)
│   └── subscribe(event_type, handler)
│
└── task_queue_port.py        # 任务队列
    └── enqueue(task_type, payload)
    └── dequeue() → Task | None
```

### 4.3 每个端口的接口契约

```python
# core/ports/vector_store_port.py
from abc import ABC, abstractmethod
from typing import Optional

class VectorStorePort(ABC):
    """向量检索端口 — 任何向量数据库实现必须遵循此接口"""
    
    @abstractmethod
    async def search(self, query: str, k: int = 3, threshold: float = 0.3) -> list[dict]:
        """搜索相似内容，返回 [{"text": str, "probability": float, ...}]"""
        ...
    
    @abstractmethod
    def is_available(self) -> bool:
        """向量检索是否可用（如果不可用，调用方自动降级到 SQLite LIKE）"""
        ...
```

**关键设计决策**: 端口接口中统一使用 `async`，即使当前实现是同步的。这确保了未来切换到异步实现时不需要改调用方。同步实现可以用 `_run_sync()` 包装。

### 4.4 迁移策略

**不需要一次实现所有端口**。按以下优先级：

```
P0: fact_store_port.py → 替换 chat_stream.py 中的直接 fact_store 调用
P1: vector_store_port.py + config_port.py
P2: knowledge_port.py + experience_port.py
P3: event_bus_port.py + task_queue_port.py
```

**每个端口的迁移步骤**：

```
1. 在 core/ports/ 下创建接口文件（ABC + 抽象方法）    — 30 分钟
2. 在 infrastructure/ 中让现有类继承接口              — 10 分钟  
3. 在 chat_stream / services 中将 from xxx import yyy 改为依赖接口注入 — 30 分钟
4. 写单元测试：Mock 端口接口 → 测试调用方             — 30 分钟
```

---

## 5. 阶段2整体迁移路线图

### 5.1 依赖关系

```
chat_stream.py 拆分 → 依赖于创建 services/ 新模块
    ↑
    └── 需要有 chat_orchestrator.py 作为编排器
    
main_fast.py 拆分 → 依赖于 routers/ 新目录
    ↑
    └── 只需要移动代码，不依赖 chat_stream 拆分
    
端口抽象 → 依赖于确定端口接口
    ↑
    └── 可在 chat_stream 拆分过程中并行推进
```

### 5.2 建议的并行计划

```
团队 3 人并行：

人 A: chat_stream 拆分（串行）
  PR1: 创建 chat_orchestrator.py，搬走主函数 → chat_stream 减 1000 行
  PR2: 创建 methodology_service.py + code_verifier.py → 再减 200 行
  PR3: 将辅助函数合并到 intent_service → 再减 150 行
  → chat_stream.py 目标: ~1000行（可接受）

人 B: main_fast 拆分（串行）
  PR1: 创建 lifespan.py + routers/health.py → main_fast 减 200 行
  PR2: 创建 routers/chat.py + routers/system.py → 再减 300 行
  PR3: 创建 routers/knowledge/evolution/proactivity → 再减 400 行
  PR4: 剩余初始化和后台任务提取到 services/ → 再减 800 行
  → main_fast.py 目标: ~500行

人 C: 端口抽象（可与 A/B 并行）
  PR1: fact_store_port.py + 适配器实现 → 0.5 天
  PR2: vector_store_port.py + 适配器实现 → 0.5 天
  PR3: config_port.py + 适配器实现 → 0.5 天
  PR4-P6: 其余端口 → 按需
```

### 5.3 每个 PR 的验收标准

```
□ 旧文件减少了行数（chat_stream / main_fast）
□ 新文件有完整的模块 docstring + 函数 docstring
□ 迁移后的函数行为不变（原有 API 测试通过）
□ 没有引入新的 裸 except:
□ 没有引入新的 sqlite3.connect() 硬编码（使用 DatabaseManager）
□ server 能正常启动，/api/health 返回 200
□ commit message 末尾加了对应的标签（[chat_stream] / [main_fast] / [ports]）
```

---

## 6. 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| 拆分后 import 循环依赖 | 中 | 高 | 使用 TYPE_CHECKING + 延迟导入 |
| 拆分后 chat_stream() 行为不一致 | 中 | 高 | 每个 PR 后运行 e2e 测试 + curl 验证 |
| 路由拆分后前端请求路径不匹配 | 低 | 高 | 保持旧路由作为重定向或统一 prefix |
| 端口抽象增加开发负担 | 高 | 低 | 只按 P0-P3 优先级逐步引入，不要求一步到位 |
| 团队不习惯 commit 标签 | 中 | 低 | 巡检系统自动检测，不强制，但标签能让报告更精准 |

---

> **设计哲学**: 这个拆分方案遵循"永不放弃"和"追求本质"原则。  
> "永不放弃"体现在：不要求一次性完美，允许"借道还债"式的渐进改进。  
> "追求本质"体现在：每个模块的职责定义清晰，不把"先搬过去再说"当作最终状态。  
> **下一轮巡检时，我会在留言板中根据团队的实际进展提供调整建议。**
