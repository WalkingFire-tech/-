# 悬空模块尸检报告

生成日期: 2026-07-20
审计范围: core/, meta/, backend/
总文件数: 329 | 可达: 243 | 悬空: 86 (25.6%)

---

## 一、已归档模块 (7个)

以下模块已 `git mv` 至 `_arch/OLD/`，原因：与可达模块功能重叠，仅被 tests/scripts 引用。

| 原路径 | 归档名 | 重叠对象 | 引用者 |
|--------|--------|---------|--------|
| `core/learning.py` | `core_learning_shadowed.py` | `core/learning/` 包目录 | 无（Python优先导入包目录） |
| `core/closed_loop_module.py` | `core_closed_loop_module.py` | `core/closed_loop_orchestrator.py` | scripts/ |
| `core/cognitive_architecture_complete.py` | `core_cognitive_architecture_complete.py` | `core/cognitive_architecture_v2.py` | tests/ |
| `core/cognitive_loop_base.py` | `core_cognitive_loop_base.py` | `core/loop_mixin.py` | tests/ |
| `core/enhanced_scheduler.py` | `core_enhanced_scheduler.py` | `core/active_scheduler.py` | tests/ |
| `core/learning_engine.py` | `core_learning_engine.py` | `core/learning_loop.py` | 无 |
| `core/state_collector.py` | `core_state_collector.py` | `core/reporting/state_collector.py` | tests/ |

---

## 二、已编码未接线模块 — 高价值待接入

以下模块代码完整、设计意图明确，但尚未接入主运行路径。**不应归档**，应规划接入。

### P1: 反馈信号管道 (core/feedback/)

| 文件 | 主要符号 | 设计意图 | 接入路径 |
|------|---------|---------|---------|
| `signal_capture.py` | `FeedbackSignalCapture` | 捕获用户隐式/显式反馈信号 | chat_orchestrator 响应后调用 |
| `feedback_router.py` | `FeedbackSignalRouter` | 将反馈信号路由到正确的学习器 | signal_capture 的下游 |
| `knowledge_pipeline.py` | `KnowledgePromotionPipeline` | 将临时知识晋升为持久知识 | feedback_router 的下游 |
| `knowledge_validator.py` | (验证器) | 验证晋升知识的质量 | knowledge_pipeline 内部 |

**接入方案**: 在 `chat_orchestrator.py` 的 `post_response` 阶段注入 `signal_capture`，形成 信号捕获→路由→验证→晋升 的完整链路。

### P1: 安全学习层 (core/ethics/)

| 文件 | 主要符号 | 设计意图 | 接入路径 |
|------|---------|---------|---------|
| `safe_learning.py` | `SafeLearningLayer` | 学习前的安全审查（防止学习有害内容） | learning_loop 学习前调用 |
| `value_alignment_checker.py` | `ValueAlignmentChecker` | 检查系统行为与核心价值的一致性 | self_reflector 反思时调用 |

**接入方案**: `safe_learning` 作为 `learning_loop` 的前置门控；`value_alignment_checker` 作为 `self_reflector` 的检查维度。

### P1: 对话认知引擎 (core/dialogue/)

| 文件 | 主要符号 | 设计意图 | 接入路径 |
|------|---------|---------|---------|
| `scene_perceiver.py` | `ScenePerceiver` | 场景感知（识别对话上下文类型） | chat_orchestrator 请求预处理 |
| `dialogue_understander.py` | `DialogueUnderstander` | 深层理解（意图+情感+隐含信息） | scene_perceiver 下游 |
| `dialogue_cognitive_engine.py` | `DialogueCognitiveEngine` | 对话认知编排 | chat_orchestrator 的理解增强层 |
| `self_verifier.py` | `SelfVerifier` | 自验证（检查回答的内部一致性） | 响应生成后、返回前 |

**接入方案**: `DialogueCognitiveEngine` 作为 `chat_orchestrator` 的可选理解增强层，在 CBNR L1 之后、L2 之前插入。

### P2: 符号推理引擎 (core/symbolic/)

| 文件 | 主要符号 | 设计意图 | 接入路径 |
|------|---------|---------|---------|
| `rule.py` | `Rule`, `RuleSet` | 规则定义与求值 | 基础设施 |
| `engine.py` | `SymbolicEngine` | 前向链推理引擎 | 替代硬编码规则逻辑 |
| `hybrid_reasoner.py` | `HybridReasoner` | 符号+神经混合推理 | 认知调度器的推理路径 |

**接入方案**: 长期目标。当规则数量超过阈值时，从硬编码 `if/else` 迁移到 `SymbolicEngine`。

### P2: 内容提取器 (core/content_extractors/)

| 文件 | 主要符号 | 设计意图 | 接入路径 |
|------|---------|---------|---------|
| `base.py` | `ContentExtractor` | 提取器基类 | 基础设施 |
| `code_extractor.py` | `CodeExtractor` | 代码文件提取 | folder_learner 下游 |
| `docx_extractor.py` | `DocxExtractor` | Word文档提取 | folder_learner 下游 |
| `pdf_extractor.py` | `PDFExtractor` | PDF提取 | folder_learner 下游 |
| `text_extractor.py` | `TextExtractor` | 纯文本提取 | folder_learner 下游 |

**注意**: 可能与 `document_parser.py`（可达）功能重叠，需先评估再决定接入或合并。

---

## 三、已编码未接线模块 — 元控制层 (meta/)

| 文件 | 主要符号 | 状态 | 接入路径 |
|------|---------|------|---------|
| `active_learner_v2.py` | `ActiveLearner` | 已集成治理器，未被主路径调用 | planner 的学习决策点 |
| `self_reflector_v2.py` | `SelfReflector` | 已集成治理器，未被主路径调用 | planner 的反思调度点 |
| `evolution_validator.py` | `EvolutionValidator` | 烟雾测试+验证 | 进化岛评估后调用 |
| `hyperparam_optimizer.py` | `HyperparamOptimizer` | 超参数优化 | 与 bayesian_optimizer 合并或替代 |
| `controller.py` | `MetaController` | 旧版元控制器 | 被 bayesian_optimizer 替代，可归档 |
| `learning_safety.py` | `LearningSafetyManager` | 学习安全 | 仅被不可达的 cli_ui 引用 |
| `privacy_manager.py` | `PrivacyManager` | 隐私管理 | 仅被不可达的 cli_ui 引用 |

---

## 四、死亡集群 — 大文件但仅被 tests/scripts/archives 引用

| 文件 | 大小 | 主要符号 | 评估 |
|------|------|---------|------|
| `core/reflective_model_free_evolution.py` | 41KB | `DataDrivenReflectionEngine` | 仅 tests/，与可达模块无重叠，暂保留 |
| `core/cognitive_scheduler.py` | 25KB | `CognitiveScheduler` | 与 active_scheduler 部分重叠 |
| `core/never_give_up.py` | 23KB | `NeverGiveUpEngine` | 仅 archives/，可归档 |
| `core/orchestrator.py` | 23KB | `SystemOrchestrator` | 旧版编排器，与 chat_orchestrator 重叠 |
| `core/cognitive_loop.py` | 20KB | `CognitiveLoop` | 仅被旧版 orchestrator 引用 |
| `core/skill_tree.py` | 20KB | `SkillTree` | 仅 scripts/ |
| `core/long_term_memory.py` | 20KB | `LongTermMemory` | 仅 tests/ |
| `core/evolution_gene.py` | 18KB | `EvolutionGene` | 仅 tests/ |
| `core/self_evolution.py` | 18KB | `SelfEvolutionEngine` | 仅 archives/ |

---

## 五、统计摘要

| 类别 | 数量 | 处置 |
|------|------|------|
| 已归档（重叠死代码） | 7 | git mv → _arch/OLD/ |
| 高价值待接入 | 20+ | 保留，规划接入路径 |
| 元控制层待接线 | 7 | 保留，部分已集成治理器 |
| 死亡集群（大文件） | 9+ | 暂保留，需进一步评估 |
| 工具模块（手动使用） | 2 | 保留（compliance_check, enforcement） |

---

## 六、R5铁律合规声明

本报告遵循 R5 铁律：**禁止删除任何已编码但未接入的模块**。所有归档操作均使用 `git mv`，文件内容完整保留在 `_arch/OLD/` 目录中，可随时恢复。