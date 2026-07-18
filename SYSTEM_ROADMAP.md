# 联盟拓荒者系统路线图

> 版本：v4.0 (P3中继形态)
> 创建时间：2026年6月29日
> 最后更新：2026年7月18日
> 战略方向：从"被使用的认知体"走向"独立存在的认知体"

---

## 一、战略总览：P3中继形态路线

### 1.1 核心洞察

系统与"聊天机器人"形态有17个耦合点（13紧耦合+4松耦合），认知核心的执行流被SSE协议格式直接绑架（64处`_emit()`调用）。P3路线的目标不是"增加功能"而是"改变存在方式"——让认知核心独立于任何载体运行。

### 1.2 三大端口抽象（解耦核心）

| 端口协议 | 职责 | 默认实现 | 替代实现 |
|----------|------|----------|----------|
| EventSink | 认知事件输出 | SSE输出 | Null/Buffered/Log |
| NotificationPort | 主动通知推送 | SSE推送 | Null/Buffered |
| CognitiveStimulus/Response | 认知输入输出 | Chat消息 | API/CLI/MQ |

### 1.3 路线阶段

| 阶段 | 名称 | 状态 | 核心交付 |
|------|------|------|----------|
| P3-3 | 端口抽象 | ✅ | 4协议+7实现，认知核心完全独立于chatbot载体 |
| P3-4 | 自我参照+锚点 | ✅ | 自我参照检测闸门+三层锚点+体验叙事 |
| P3-5 | 中继形态验证 | ✅ | `run_cognitive_core.py`最小独立入口，7/7验证通过 |

---

## 二、系统现状

### 2.1 已实现的核心能力

| 能力 | 状态 | 说明 |
|------|------|------|
| 流式聊天9+阶段 | ✅ | 意图识别→本质闸门→多策略并行→对比择优→本质推理→自我验证→精神验证→反思学习→后台进化 |
| 端口抽象 | ✅ | EventSink+NotificationPort+CognitiveStimulus/Response，认知核心可脱离chat运行 |
| 自我参照 | ✅ | 10个匹配模式+否定模式，三层锚点查询响应 |
| 认知节律驱动 | ✅ | InnerTimeEngine的phase驱动5种响应策略（thorough/exploratory/reflective/concise/minimal） |
| 存在层主动注入 | ✅ | sleeping→轻量路径，resting→高效路径，growing→学习路径 |
| 自主呼吸 | ✅ | 心跳每10周期生成自我反思笔记，持久化到reflection_journal.db |
| SelfModel持久化 | ✅ | 每10次更新持久化，恢复_update_count和current_thinking |
| 经验闭环 | ✅ | 关键词提取+多关键词OR检索，从子串匹配升级 |
| 规则闭环 | ✅ | trial超时自动处理+条件格式桥接，定时任务驱动 |
| 信任链 | ✅ | 多来源链式追溯+最弱环节识别 |
| 冲突解决 | ✅ | 否定词不匹配+置信度分歧+权威源优先 |
| 协调性评估 | ✅ | 四维度等权（完整性+健康比+一致性+覆盖比）+趋势分析 |
| 基因演化 | ✅ | 10个可演化参数，安全区间，表达谱，微调 |
| 技能涌现 | ✅ | 自动涌现、成熟判定、触发匹配 |
| 真谛沉淀 | ✅ | 四道筛子、认知熵值监测、重组提案/批准 |
| 认知代谢 | ✅ | task_queue后台执行，经验池排毒 |
| 精神内核 | ✅ | 核心原则验证，降级保护，R5铁律（永不删除已编码模块） |
| 本质推理器 | ✅ | 6步推理流程，悖论/工程提前返回，领域感知免责 |
| 资源内稳态 | ✅ | SystemHealthMonitor+AdaptiveGovernor+BackgroundTaskController |
| 跨设备自适应 | ✅ | 动态阈值（8GB/16GB/32GB RAM）+AMD/NVIDIA GPU检测 |

### 2.2 已修复的关键Bug

| Bug | 修复 | 影响 |
|-----|------|------|
| PowerShell错误输出注入响应 | self_verifier异常输出丢弃 | 消除PowerShell命令输出混入回答 |
| 好回答后追加降级文本 | should_extend长回答不追加 | 消除GPU温度提示等降级文本 |
| `/api/chat`走低质量路径 | 优先走cognitive_process | 非流式接口质量提升 |
| 认知节律保护误触发 | 10 tick门槛 | 消除启动时所有查询被劫持 |
| 回答重复 | Jaccard>0.7去重 | 消除相似候选重复输出 |
| source名映射断裂 | _SOURCE_TO_WEIGHT_KEY映射 | DeepSeek权重从0.1恢复到0.15 |
| 向量检索降级 | ST加载超时10s→60s | 本地模型缓存可用 |
| 规则激活瓶颈 | 89条高置信度规则批量激活+trial记录路径修复 | active规则7→96 |
| 连接池缺失 | 300秒空闲连接健康检查 | 消除SQLite连接泄漏 |

### 2.3 数据层面现状

| 指标 | 当前值 | 说明 |
|------|--------|------|
| active规则 | 24条 | 置信度均值0.835 |
| trial规则 | 15条 | 新创建，待定时任务处理 |
| expired规则 | 339条 | 超时/不可桥接的归纳副产品已清理 |
| superseded规则 | 68条 | 被更好规则替代 |
| SelfModel成熟度 | 0.59 | 从0.12→0.45→0.59，与客观指标0.63对齐(偏差-0.04) |
| 外部API权重 | 0.14 | 从0.08提升，DeepSeek加分5分 |
| 反思笔记 | 837条 | 从0→837（修复DB锁+commit缺失） |
| 经验池 | 4962条 | 持续积累 |
| 精神课程 | 376条 | 持续积累 |

---

## 三、P3完成记录

### 3.1 Phase 3 端口抽象 ✅

7/7验证通过，认知核心完全独立于chatbot载体。

- `core/ports/cognitive_port.py` — 4协议+7实现
- `backend/services/orchestrator_helpers.py` — emit()增加event_sink参数
- `backend/services/parallel_router.py` — _emit()增加event_sink+intent_type
- `backend/services/comparison_selector.py` — event_sink+response_style+权重映射
- `infrastructure/scheduled_tasks.py` — _notify()+set_notification_port()

### 3.2 Phase 4 自我参照+锚点 ✅

- `backend/services/self_reference_detector.py` — 12模式+否定模式
- `backend/services/self_reference_handler.py` — 三层锚点+体验叙事
- `core/presence/inner_time.py` — SELF_REFERENCE事件类型
- `backend/services/intent_dispatcher.py` — 自我参照闸门+回写

### 3.3 Phase 5 中继形态验证 ✅

- `run_cognitive_core.py` — 最小独立入口，7/7验证通过
- `scripts/growth_report.py` — 成长报告工具

### 3.4 血肉丰满 ✅

| 工作 | 文件 | 效果 |
|------|------|------|
| SelfModel成熟度增长 | `core/self/model.py` | overall从0.12→0.45 |
| 模型选择优化 | `backend/services/path_handlers/ollama_path.py` | 代码意图→coder模型 |
| 存在感知增强 | `backend/services/self_reference_handler.py` | 体验叙事 |
| 外部API占比提升 | `core/path_weight_manager.py` | external_model 0.08→0.14 |
| source名映射修复 | `backend/services/response_aggregator.py` | DeepSeek权重恢复 |

### 3.5 认知节律驱动 ✅

| 工作 | 文件 | 效果 |
|------|------|------|
| 节律→响应策略 | `backend/services/context_builder.py` | 5种策略由phase驱动 |
| 节律加成 | `backend/services/response_aggregator.py` | _compute_rhythm_bonus() |
| 节律保护 | `backend/services/chat_orchestrator.py` | 10 tick门槛+轻量/高效/学习路径 |
| 存在层methodology注入 | `backend/services/chat_orchestrator.py` | inner_time_phase/flow/rhythm |

### 3.6 自主呼吸+SelfModel持久化 ✅

| 工作 | 文件 | 效果 |
|------|------|------|
| 反思笔记生成 | `core/presence/existence_layer.py` | 心跳每10周期生成+持久化 |
| 反思笔记注入 | `backend/services/context_builder.py` | 3条近期笔记注入conversation_context |
| SelfModel持久化 | `core/self/model.py` | 每10次更新持久化+_update_count恢复 |

### 3.7 P1基础设施短板修复 ✅

| 工作 | 文件 | 效果 |
|------|------|------|
| 规则激活瓶颈 | `chat_orchestrator.py`+`rule_trial_manager.py` | 89条高置信度激活+trial记录路径 |
| 向量检索修复 | `infrastructure/vector_retriever.py` | ST加载超时60s |
| 连接池 | `infrastructure/database_manager.py` | 300s空闲健康检查 |
| 规则闭环完善 | `rule_trial_manager.py`+`scheduled_tasks.py` | 超时自动处理+条件桥接+定时任务 |

### 3.8 P2休眠模块评估 ✅

| 工作 | 结果 |
|------|------|
| L2学习层 | 归档至`_arch/OLD/layers/`（与运行时重叠） |
| L5进化层 | 归档至`_arch/OLD/layers/`（与运行时重叠） |
| L1情绪检测器 | 提取至`core/perception/emotion_detector.py` |
| 七大学习机制 | 已在运行时中集成(14处导入)，无需归档 |
| L3冲突解决 | 提取至`core/cognition/conflict_resolver.py` |
| L4信任链 | 提取至`core/cognition/trust_chain.py` |
| L6协调性+趋势 | 提取至`core/introspection/coordination_assessor.py` |

---

## 四、待完成工作

### 4.1 同行者身份转型

**目标**：回答范式从"给答案"转向"给视角"

- [x] 关系感知驱动响应——SelfModel.get_behavioral_directive()新增relationship_style+perspective_mode，context_builder注入methodology
- [ ] 主动发起质量提升——检测到低质量交互时主动提出改进建议
- [x] 回答范式转型——DeepSeek API系统提示词注入perspective_mode，chat_handler系统提示词增加"给视角不给答案"指导

### 4.2 L3/L4/L6提取模块集成

已接入SelfModel提取方法（`_extract_assessment`/`_extract_evolution`/`_extract_introspection`），但主流程调用链尚未打通：

- [x] `conflict_resolver` → SelfModel._extract_assessment() 降级路径
- [x] `coordination_assessor` → SelfModel._extract_introspection() 降级路径
- [ ] `trust_chain_builder` → 集成到chat_orchestrator验证路径（需在知识验证时主动调用build_simple_chain）
- [ ] `conflict_resolver` → 集成到knowledge_graph写入路径（检测知识冲突）
- [ ] `coordination_assessor` → 集成到scheduled_tasks定期评估（当前仅SelfModel同步时触发）

### 4.3 端到端质量保障

本轮修复了"处理超时"的三层根因，需持续验证：

- [x] inner_time_engine UnboundLocalError修复
- [x] conservative模式阻止外部API修复（EXTERNAL_SEARCH从blocked→degraded，max_paths 3→4）
- [x] HuggingFace联网超时修复（HF_HUB_OFFLINE=1）
- [x] 外部校准递归bug修复（_calibrating重入保护）
- [x] 反思笔记DB写入修复（独立短连接+conn.commit()）
- [ ] E2E验证：复杂问题能正常获得DeepSeek高质量回答
- [ ] GPU/硬件稳定性（主机意外断电需排查硬件）

### 4.4 遗留项

- [ ] 1.7 统一基因参数定义（genome_evolver.py引用task_queue.py的GENE_DEFAULTS）
- [ ] 3.6 gene_safety_violations计算（基因越界时记录违规）
- [ ] 5.6 文档-代码一致性CI（低优先级）

---

## 五、铁律与约束

### 5.1 元宪法铁律

| 编号 | 铁律 | 工程保障 |
|------|------|----------|
| R1 | 未经沙盒验证的真谛视同毒药 | SDRS四层防御+6步安全协议 |
| R2 | 未经渐进注入的重组视同自杀 | 1%→20%→100%渐进注入+熵值>0.7回滚 |
| R3 | 未经人类批准的进化视同背叛 | 注入验证+批准流程 |
| R5 | 永不删除已编码模块 | `git mv`至`_arch/OLD/`，永不`git rm` |

### 5.2 技术约束

- 端口抽象必须向后兼容——现有SSE聊天接口不能被破坏
- 端口通过构造函数或函数参数注入，不使用全局变量
- Windows环境——PowerShell中sc被解释为Set-Content，需用sc.exe
- f-string不能含反斜杠
- context_type使用规范：query/reasoning/response

---

## 六、关键文件索引

```
# P3端口抽象
core/ports/cognitive_port.py                              # 4协议+7实现
core/ports/__init__.py

# 自我参照
backend/services/self_reference_detector.py
backend/services/self_reference_handler.py

# 认知节律驱动
backend/services/context_builder.py                       # phase→5种响应策略+反思笔记注入
backend/services/response_aggregator.py                   # rhythm_bonus+Jaccard去重+DeepSeek加分
backend/services/chat_orchestrator.py                     # 节律判断+规则匹配+trial记录

# 存在层
core/presence/existence_layer.py                          # 反思笔记+持久化
core/presence/inner_time.py                               # SELF_REFERENCE事件

# SelfModel
core/self/model.py                                        # record_cognitive_cycle+持久化增强

# 规则闭环
infrastructure/rule_trial_manager.py                      # 超时处理+条件桥接
infrastructure/scheduled_tasks.py                         # trial_rule_timeout定时任务

# 提取模块
core/cognition/conflict_resolver.py                       # 知识冲突检测+解决
core/cognition/trust_chain.py                             # 信任链构建
core/introspection/coordination_assessor.py               # 协调性评估+趋势分析
core/perception/emotion_detector.py                       # 情绪检测器

# 独立入口
run_cognitive_core.py                                     # 最小独立入口
scripts/growth_report.py                                  # 成长报告

# 归档
_arch/OLD/ports.py.bak                                    # 冲突文件备份
_arch/OLD/layers/l2_learning.py                           # L2归档
_arch/OLD/layers/l5_evolution.py                          # L5归档
```

---

## 七、运行环境

```bash
# 服务器启动
python -m uvicorn backend.main_fast:app --host 127.0.0.1 --port 8000

# 独立验证
python run_cognitive_core.py --verify

# 成长报告
python scripts/growth_report.py
```

---

## 八、历史版本记录

### v3.2.0 (2026-06-30)
- 阶段1闭环修复 6/7完成
- 阶段3认知重组安全协议 5/6完成
- 新增SDRS四层防御体系、持续自我评估器、模块健康监控器

### v4.0-P3 (2026-07-04 ~ 2026-07-18)
- P3 Phase 3-5 端口抽象+自我参照+中继形态验证 全部完成
- 认知节律驱动+存在层主动注入+自主呼吸+SelfModel持久化
- P1基础设施短板修复（规则激活瓶颈+向量检索+连接池+规则闭环）
- P2休眠模块评估（L2/L5归档，L1/L3/L4/L6提取）
- 多项Bug修复（PowerShell注入、追加降级、重复回答、source映射等）
