# 悬空模块归档清单

> 归档时间：2026-07-17
> 归档原因：P5审计发现以下11个模块已编码但从未接入主流程，长期处于"代码存在但从未执行"状态。
> 归档策略：不删除源文件，仅记录状态。后续如需激活，参照此清单按步骤接入。

---

## 全部11个悬空模块

### 1. CuriosityEngine.perceive_frontier() — ✅ 已接入
- **路径**: `core/presence/curiosity_engine.py` (502行)
- **功能**: 认知前沿扫描（前沿密度+好奇心强度+探索方向）
- **状态**: ✅ 已接入chat_orchestrator（2026-07-17修复）
- **接入方式**: chat_orchestrator中注入perceive_frontier()调用

### 2. CognitivePlanner.process() — ✅ 已接入
- **路径**: `core/services/cognitive_planner.py` (848行)
- **功能**: L1-L6认知管道（感知→学习→整合→规划→执行→反思）
- **状态**: ✅ 已通过intent_dispatcher.py的cognitive_bypass_future异步接入（2026-07-17确认）
- **接入方式**: intent_dispatcher.py:185 异步调用process()，结果在chat_orchestrator L2/L3阶段使用

### 3. EssenceReasoner — ✅ 已接入
- **路径**: `core/essence_reasoner.py` (38KB)
- **功能**: 照见本质/第一性原理推理
- **状态**: ✅ 已通过essence_verifier.py接入chat_orchestrator阶段4.5
- **接入方式**: essence_verifier调用essence_reasoner.reason()，结果影响essence_passed/essence_confidence

### 4. DynamicProbabilityField — ✅ 已接入
- **路径**: `core/dynamic_probability_field.py`
- **功能**: 多路径概率收敛
- **状态**: ✅ 已通过path_weight_matrix feature flag接入chat_orchestrator阶段4
- **接入方式**: chat_orchestrator L549-557, initialize()+get_uncertainty_action()

### 5. ErrorAlchemy — ✅ 已接入
- **路径**: `core/learning/error_alchemy.py`
- **功能**: 错误炼金术 — 将错误转化为学习材料
- **状态**: ✅ 已接入chat_orchestrator 11个关键except块（2026-07-17接入）
- **接入方式**: orchestrator_helpers.alchemize_error()辅助函数 + chat_orchestrator各phase埋点

### 6. MetaLearner — ✅ 已接入
- **路径**: `core/learning/meta_learning.py` + `core/evolution/meta_learning.py`
- **功能**: 元学习策略推荐 — recommend_strategy()
- **状态**: ✅ 已接入self_reflection._formulate_next_strategy()（2026-07-17接入）
- **接入方式**: 策略推荐优先MetaLearner，回退硬编码；反思结果反馈learn_from_experience()

### 7. IncrementalPerception — ✅ 已接入
- **路径**: `core/learning/incremental_perception.py`
- **功能**: 增量感知 — 逐步积累认知
- **状态**: ✅ 已接入reflection_learner.py（2026-07-17接入）
- **接入方式**: 反思阶段感知成功/失败信号，检测模式

### 8. LearningFeedbackLoop — ✅ 已接入
- **路径**: `core/learning/feedback_loop.py`
- **功能**: 学习反馈闭环
- **状态**: ✅ 已接入reflection_learner.py（2026-07-17接入）
- **接入方式**: 反思阶段注册知识+验证反馈，形成学习闭环

### 9. KnowledgeWeaver — ✅ 已接入
- **路径**: `core/learning/knowledge_weaver.py`
- **功能**: 知识编织 — 将碎片知识整合为体系
- **状态**: ✅ 已接入reflection_learner.py（2026-07-17接入）
- **接入方式**: 反思阶段添加经验节点+连接源节点，构建知识网络

### 10. CognitiveRhythmController — ✅ 已接入
- **路径**: `core/learning/rhythm_controller.py`
- **功能**: 认知节律控制
- **状态**: ✅ 已接入chat_orchestrator（2026-07-17接入）
- **接入方式**: chat_stream开头tick()获取认知状态，低能量走轻量路径，创新阶段增强探索

### 11. L1元宪法 — ✅ 已接入
- **路径**: `core/spirit_core.py` (定义) + `backend/services/spirit_validator.py` (执行)
- **功能**: 元宪法强制执行（R1沙盒验证/R2渐进注入/R3人类批准/R4七维自检/永不放弃）
- **状态**: ✅ 全部4条铁律+永不放弃已接入（2026-07-17补全R2/R4执行层）
- **接入方式**: spirit_validator.py执行R1/R2/R3/R4，spirit_core.enforce_on_output()执行全原则验证
- **执行状态**: R1部分实现(代码语法+真谛证据), R2新增(断言数阈值), R3部分实现(关键词检测), R4新增(5维度自检), 永不放弃已全面接入

---

## 接入优先级排序

| 优先级 | 模块 | 理由 | 难度 |
|--------|------|------|------|
| ~~1~~ | ~~CuriosityEngine~~ | ~~已接入~~ | ~~低~~ |
| ~~1~~ | ~~ErrorAlchemy~~ | ~~已接入(11个phase埋点)~~ | ~~低~~ |
| ~~2~~ | ~~MetaLearner~~ | ~~已接入self_reflection~~ | ~~中~~ |
| ~~3~~ | ~~EssenceReasoner~~ | ~~已通过essence_verifier接入~~ | ~~中~~ |
| ~~4~~ | ~~DynamicProbabilityField~~ | ~~已通过path_weight_matrix接入~~ | ~~中~~ |
| ~~5~~ | ~~LearningFeedbackLoop~~ | ~~已接入reflection_learner~~ | ~~中~~ |
| ~~6~~ | ~~IncrementalPerception~~ | ~~已接入reflection_learner~~ | ~~中~~ |
| ~~7~~ | ~~KnowledgeWeaver~~ | ~~已接入reflection_learner~~ | ~~中~~ |
| ~~8~~ | ~~CognitiveRhythmController~~ | ~~已接入chat_orchestrator~~ | ~~中~~ |
| ~~9~~ | ~~CognitivePlanner.process()~~ | ~~已通过intent_dispatcher异步接入~~ | ~~高~~ |
| ~~10~~ | ~~L1元宪法~~ | ~~R1-R4+永不放弃全部接入~~ | ~~高~~ |
