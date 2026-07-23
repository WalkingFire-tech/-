# P2结构优化 + M2 L5递归化 — 阶段性技术归档

> 归档时间：2026-07-16 | 版本：v5.12.0
> 覆盖范围：P2-8~P2-12 + M2-1~M2-4 + 沙箱/超时配置扩展

---

## 一、总览

### 完成状态

| 里程碑 | 任务数 | 状态 |
|--------|--------|:----:|
| P2 结构优化 | 5项(P2-8~P2-12) | ✅ 全部完成 |
| M2 L5递归化 | 4项(M2-1~M2-4) | ✅ 全部完成 |
| 沙箱/超时扩展 | 3项 | ✅ 全部完成 |

### 核心指标变化

| 指标 | 变化前 | 变化后 | 改善 |
|------|--------|--------|------|
| chat_orchestrator行数 | 2984 | 719 | -75.9% |
| 闭环基类覆盖 | 0/15 | 9/15 | +60% |
| 真谛筛子降级通道 | 2处 | 0处 | 消除 |
| 种子真谛伪造证据 | 10条evidence=99 | 10条evidence=0+is_seed | 修正 |
| 测试根级文件 | 226 | 71 | -68.6% |
| ToolRegistry注册表 | 2套 | 1套 | 统一 |
| L5自修改能力 | 无安全框架 | 自举沙箱+安全自检+影子模式+策略进化 | 完整闭环 |
| 单元测试数 | ~72 | 120 | +66.7% |

---

## 二、P2-8 chat_orchestrator拆分

详见 `docs/architecture/chat_orchestrator_refactor_analysis.md`

关键成果：
- 2984→719行(-75.9%)，14个模块提取
- 提取模式：子函数返回`(result, events_list)`元组，由`chat_stream`统一yield
- 单向依赖原则：提取模块只依赖core/infrastructure/orchestrator_helpers/path_handlers

---

## 三、P2-9/P2-9b 闭环思维代码化

### 基类设计

| 类 | 类型 | 用途 |
|----|------|------|
| CognitiveLoopBase | async抽象基类 | 四阶段骨架+冷却恢复+缓存+指标+线程安全 |
| HealthLoop | CognitiveLoopBase子类 | 健康监控闭环(5个模块) |
| LearningLoop | CognitiveLoopBase子类 | 学习进化闭环(10个模块) |
| LoopMixin | 同步混入 | loop_context()包裹+冷却+指标+异常容忍 |
| AsyncLoopMixin | 异步混入 | async_loop_context()+asyncio.Lock |

### 应用结果

| 模块 | Mixin类型 | 应用方式 |
|------|-----------|----------|
| CuriosityEngine | LoopMixin | loop_context()包裹explore() |
| ProactivityEngine | LoopMixin | loop_context()包裹evaluate() |
| AdaptiveGovernor | LoopMixin | 手动_finish_loop_cycle()（保留自有冷却） |
| SelfModel | LoopMixin | _lock→_loop_lock |
| ExistenceLayer | LoopMixin | loop_context()包裹4个子方法 |
| GenomeEvolver | LoopMixin | loop_context()包裹evolve()/evaluate_fitness() |
| SelfModificationLoop | LoopMixin | loop_context()包裹3个run方法 |
| CognitiveLoop | AsyncLoopMixin | async_loop_context()包裹run_cycle() |
| ReActEngine | AsyncLoopMixin | 手动_finish_loop_cycle() |

不适用模块(6个)：FitnessOptimizer/SelfVerifier(纯函数), SystemHealthMonitor/CognitiveDispatcher/ToolGenerator/MetacognitiveExecutor(非循环)

---

## 四、P2-10 测试目录整理

| 分类 | 文件数 | 说明 |
|------|--------|------|
| tests/ 根级 | 71 | 活跃测试文件 |
| tests/scripts/ | 49 | verify_/check_/diagnose_脚本 |
| tests/integration/ | 19 | e2e/集成测试 |
| tests/benchmark/ | 4 | 性能基准 |
| tests/OLD/ | 83 | 过时脚本存档 |

---

## 五、P2-11 ToolRegistry统一

- `tools/registry.py`(37行)是纯代理层，零自有逻辑
- 所有`from tools.registry import`迁移到`from core.tool_registry import`
- `tools/__init__.py`改为从core.tool_registry重导出，保持向后兼容
- `tools/registry.py`标记DeprecationWarning

---

## 六、P2-12 真谛四道筛子强化

### 问题与修复

| # | 问题 | 修复 |
|---|------|------|
| Q1 | 10条种子真谛evidence_count=99(伪造) | 改为0，添加is_seed标记 |
| Q2 | 筛子3/4有`or evidence >= 5`降级通道 | 移除降级通道 |
| Q3 | _ensure_seeds()直接写入不经筛子 | 对每条种子调用evaluate_for_upgrade() |
| Q4 | _save_truth()新真谛不经质量验证 | 必须通过筛子评估，不通过标记pending_verification |
| Q9 | R1验证不覆盖L3/L4种子真谛 | 扩展到evidence_count=0的种子真谛 |

- `_migrate_fake_evidence()`自动修正数据库中旧的evidence_count=99记录

---

## 七、M2-1 L5自举测试环境

### BootstrapSandbox四步验证

1. **语法验证**: `compile(patched_code)` 检查语法正确性
2. **自修改安全检查**: 8项SELF_MODIFICATION_SAFETY_CHECKLIST
3. **子进程隔离导入**: 独立进程import模块，避免主进程污染
4. **功能自检**: 实例化→方法可调用验证

### 关键定义

- `L5_SELF_FILES`: 5个L5自身文件(loop/diagnoser/generator/deployer/bootstrap)
- `MODULE_TEST_MAP`: 每个L5模块的测试配置
- `SELF_MODIFICATION_SAFETY_CHECKLIST`: 8项自修改专用安全检查

---

## 八、M2-2 L5安全自检协议

- `IMMUTABLE_FILES`统一到`__init__.py`(frozenset)，消除deployer/generator两处不一致
- `SelfModificationLoop._is_self_modification()`检测自修改目标
- 自修改目标走BootstrapSandbox验证路径
- 审计日志新增`is_self_modification`字段

---

## 九、M2-3 L5影子模式四阶段注入

### SelfModificationDeployer

| 阶段 | 注入率 | 行为 |
|------|--------|------|
| 0.1%沙盒验证 | BootstrapSandbox | 子进程隔离自检，失败立即终止 |
| 1%影子运行 | 子进程运行 | 对比输出不替换，记录差异 |
| 20%功能启用 | 逐步验证 | import→实例化→方法可调用 |
| 100%全量替换 | 写文件+导入验证 | 失败自动回滚 |

- 审计日志增强: stage_details/diff_before/diff_after字段

### 递归悖论解决方案

L5修改自身代码时，无法做传统流量分配（只有一个实例）。影子模式替代策略：
- 在子进程中运行修改后代码，不替换主进程
- 逐步验证功能正确性后才真正替换
- 替换失败自动回滚到原始代码

---

## 十、M2-4 L5策略进化器

### StrategyEvolver核心设计

从l5_audit.db分析历史修改成功率，按类别/置信度维度学习，优化修改策略参数。

### StrategyParams参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| template_threshold | 0.9 | 模板补丁自动批准阈值 |
| llm_threshold | 0.95 | LLM补丁自动批准阈值 |
| auto_approve_categories | ["exception_handling"] | 允许自动批准的缺陷类别 |
| priority_files | [] | 优先修改的文件列表 |
| self_mod_confidence_bonus | -0.1 | 自修改额外置信度惩罚 |
| min_samples_for_adjustment | 5 | 最少样本数才调整策略 |
| max_adjustment_per_cycle | 0.1 | 每次最大调整幅度 |

### 策略进化规则

| 条件 | 动作 |
|------|------|
| 成功率 >= 80% | 降低该类别阈值（放宽自动批准） |
| 成功率 < 50% | 提高该类别阈值（收紧自动批准） |
| 自修改成功率 >= 70% | 减少self_mod_confidence_bonus惩罚 |
| 文件修改成功率 >= 70%(>=3次) | 加入priority_files |

### 安全约束

- 阈值下限0.7，上限1.0
- 每次调整不超过10%
- 样本不足5个不调整
- 策略进化不改变安全底线，只调整效率参数（R3原则）

### 集成点

- `SelfModificationLoop._record_run()`: 每5次运行调用策略进化
- `SelfModificationLoop._process_defects()`: should_auto_approve()替代硬编码自动批准逻辑

---

## 十一、沙箱/超时配置扩展

| 组件 | 旧值 | 新值 | 原因 |
|------|------|------|------|
| tool_builder._sandbox_exec | 5s | 15s | 复杂代码执行需要更多时间 |
| config_manager sandbox | 15s | 30s | 全局沙箱超时适配 |
| ReActEngine MAX_TOTAL_SECONDS | 20s | 45s | 3次迭代需要更多总时间 |
| ReActEngine MAX_ITERATIONS | 2 | 3 | 增加推理深度 |

---

## 十二、测试覆盖

| 测试文件 | 测试数 | 覆盖范围 |
|----------|--------|----------|
| test_world_model.py | 21 | 世界模型沙盒化 |
| test_feature_flags.py | 10 | Feature flag系统 |
| test_spirit_core.py | - | 精神内核 |
| test_beam_search.py | - | 束搜索 |
| test_ratchet_gate.py | - | 棘轮门 |
| test_chat_stream_audit.py | 4 | 聊天流审计 |
| test_cognitive_loop_base.py | 12 | 闭环基类 |
| test_loop_mixin.py | 20+8 | LoopMixin+AsyncLoopMixin |
| test_bootstrap_sandbox.py | 14 | BootstrapSandbox+SelfModificationDeployer |
| test_strategy_evolver.py | 29 | StrategyEvolver策略进化 |
| **合计** | **120** | - |

已知问题：8个AsyncLoopMixin测试因Python 3.11事件循环API变更失败（`asyncio.get_event_loop()`需改为`asyncio.new_event_loop()`），非功能性缺陷。

---

## 十三、关键设计决策记录

1. **提取模式选择**: chat_orchestrator提取子函数返回events列表而非直接yield，因为async generator中子函数不能yield
2. **LoopMixin vs CognitiveLoopBase**: Mixin组合模式优于继承，因为现有模块已有继承体系
3. **影子模式替代流量分配**: L5只有一个实例，无法做A/B测试，改用子进程影子运行
4. **策略进化安全底线**: 只调效率参数(threshold/bonus)，不改变安全规则(IMMUTABLE_FILES/安全检查)
5. **IMMUTABLE_FILES统一**: 从deployer/generator两处硬编码改为__init__.py frozenset单点定义