# P4阶段全局调用路径审计报告

**审计时间**: 2026-07-16
**审计范围**: chat_orchestrator → 所有提取模块的import链 + P4新增模块调用链 + 函数签名匹配
**审计原因**: 文件迁移/大规模改动后，调用路径可能断裂导致运行时错误

---

## 一、审计发现汇总

| 类别 | 数量 | 严重度 |
|------|------|--------|
| ❌ 导入断裂（ImportError） | 4 | 严重 |
| ⚠️ 签名不匹配 | 1 | 中等 |
| ⚠️ P4功能未接入主流程 | 1 | 低 |
| ✅ 正常 | 60+ | - |

---

## 二、已修复的导入断裂

### 断裂 #1: `methodology_discoverer.py:32`
- **问题**: `from orchestrator_helpers import discover_methodology` — 函数在 `intent_service.py` 中
- **修复**: 改为 `from backend.services.intent_service import discover_methodology`
- **根因**: 提取模块时错误引用了源模块

### 断裂 #2: `intent_dispatcher.py:6`
- **问题**: `from orchestrator_helpers import get_cognitive_planner` — 函数已重命名为 `get_cognitive_planner_safe`
- **修复**: 改为 `from orchestrator_helpers import get_cognitive_planner_safe as _get_cognitive_planner`
- **根因**: 重构时 `orchestrator_helpers` 中函数加了 `_safe` 后缀，但提取模块未同步更新

### 断裂 #3: `self_verifier.py:8`
- **问题**: `from orchestrator_helpers import get_self_model` — 函数已重命名为 `get_self_model_safe`
- **修复**: 改为 `from orchestrator_helpers import get_self_model_safe as _get_self_model`
- **根因**: 同断裂 #2

### 断裂 #4: `core/metacognition/snapshot.py:117`
- **问题**: `from core.self.model import self_model` — 模块中不存在 `self_model` 变量，只有 `get_self_model` 函数
- **修复**: 改为 `from core.self.model import get_self_model`，调用处改为 `get_self_model().snapshot()`
- **根因**: 混淆了类实例名和工厂函数名

---

## 三、已修复的签名不匹配

### `context_builder.py:20` — `_l1_normalized` 类型标注
- **问题**: 定义中 `_l1_normalized: str`，但调用处传入 `dict`（L1规范化结果对象）
- **修复**: 改为 `_l1_normalized: dict`
- **影响**: Python运行时不报错，但类型标注误导开发者

---

## 四、已修复的运行时Bug（P4集成期发现）

### Bug #1: `methodology` 未初始化
- **问题**: `chat_orchestrator.py` 中 `methodology["spirit_drive"]` 在 `methodology = {}` 之前访问
- **修复**: 在函数开头添加 `methodology = {}`

### Bug #2: `StereoMemoryEntry` 对象传入 `save(Dict)` 方法
- **问题**: `cognitive_planner._save_memory()` 创建 `StereoMemoryEntry` 对象传入 `stereo_store.save()`，但 `save()` 期望 `Dict`
- **修复**: 改为直接传入 dict

---

## 五、P4新增模块调用链完整性

| 模块 | 导出 | 调用者 | 状态 |
|------|------|--------|------|
| `core/presence/inner_time.py` | `inner_time_engine`, `CognitiveEventType` | chat_orchestrator, context_builder, existence_layer, self/model | ✅ |
| `core/self/model.py` | `SelfModel`, `get_self_model` | orchestrator_helpers, intent_dispatcher, curiosity_engine, lifespan, routers | ✅ |
| `core/spirit_core.py` | `spirit_core`, `resonate()` | chat_orchestrator, response_assembler, spirit_validator, auto_fix_service | ✅ |
| `core/debate/arena.py` | `debate_arena` | chat_orchestrator | ✅ |
| `core/debate/personas.py` | `Persona`, `PRAGMATIST`, `IDEALIST`, `SKEPTIC` | arena.py | ✅ |
| `core/debate/arbitrator.py` | `Arbitrator`, `ArbitrationResult` | arena.py | ✅ |
| `core/metacognition/agent.py` | `metacognitive_agent`, `detect_stagnation()` | chat_orchestrator | ✅ |
| `core/presence/curiosity_engine.py` | `perceive_frontier()` | 仅测试代码 | ⚠️ 未接入主流程 |

---

## 六、验证结果

### 单元测试
- 137个P4相关测试全部通过
- 328个全局单元测试全部通过

### 端到端测试
- Greeting查询: ✅ 通过（状态200，无SSE错误）
- 深度查询: ✅ 通过（状态200，无SSE错误，成功返回结果）
- P4特征信号: ✅ 存在层状态(awake/growing)、内在时间tick、精神验证等阶段均正常

---

## 七、根因分析与铁律提炼

### 根因
所有4个导入断裂的根因相同：**大规模重构时，函数重命名（加 `_safe` 后缀）和模块提取未全量传播到所有引用点**。这本质上是"改动-验证"闭环缺失——改了源头但没验证所有下游。

### 提炼的铁律（已写入 `SEED_TRUTHS`）

1. **改动验证闭环铁律（L5级）**: 任何代码改动后必须执行完整验证闭环：沙盒验证→全局调用路径核查→端到端集成验证→真实反馈收集→反思与沉淀。

2. **进化九步闭环（L5级）**: 想法→规划→实施→验证→真实反馈→反思→总结→思考→形成技能或知识铁律。没有经过真实系统运行验证的"改进"不是改进，只是假设。

---

## 八、待办事项

1. ⚠️ `curiosity_engine.perceive_frontier()` 未接入主流程 — 需评估是否应在 `chat_orchestrator` 中调用
2. HuggingFace连接超时是已有问题，非P4引入，但影响深度查询响应时间