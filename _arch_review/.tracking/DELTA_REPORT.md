# 🚨 架构 Delta 报告

> **触发条件**: P0 文件变更 + 新模块加入 core/ + 架构级重构
> **巡检#2** | 2026-07-07 02:24 | HEAD: a041f49 (工作区)

---

## 1. P0 目标文件变更分析

### chat_stream.py: 重大重构 ✅

| 维度 | 变化 | 评估 |
|------|------|------|
| 规模 | 3024 → 2133 行 (-891, -29.5%) | 🟢 方向正确 |
| 裸 except | 多处 → **0处** | 🟢 异常处理大幅改善 |
| 耦合 | 内联函数 → 提取到 path_handlers/ | 🟢 解耦 |
| SpiritCore | 修复了"失败有方向"违反 | 🟢 原则遵守度提升 |

**建议**: 继续保持此节奏，目标下一阶段将 chat_stream 降至 < 1500 行。

### main_fast.py: 规模反增 ⚠️

| 维度 | 变化 | 评估 |
|------|------|------|
| 规模 | 1818 → 2160 行 (+342) | 🟡 需要关注 |
| 裸 except | 新增 33 处 | 🔴 违反 SpiritCore |
| 路由组织 | 新路由使用 `except Exception` 模式 ✅ | 🟡 新旧不统一 |

**建议**: 下一轮优先清理 main_fast.py 中的裸 except，然后启动路由拆分。

---

## 2. 新模块架构对齐评估

### core/cbnr/ — 认知瓶颈路由器 (1351行)

| 原则 | 对齐 | 说明 |
|------|------|------|
| 永不放弃 | ✅ | 三层认知管道提供递进式处理 |
| SpiritCore | ✅ | 认知归一化+瓶颈压缩+残差连接 |
| 动态可塑性 | ✅ | 压缩比动态调整 |
| 同行者 | ✅ | 清晰的接口与 hub 门控 |
| 闭环学习 | ✅ | stats 可监控 |

**评估**: 🟢 架构对齐，接口清晰，建议推进集成。

### core/alignment_guard.py — 思想对齐守卫 (286行)

| 原则 | 对齐 | 说明 |
|------|------|------|
| 永不放弃 | ✅ | 偏离检测+修正建议 |
| SpiritCore | ✅ | 5种偏离类型映射SpiritCore |
| 原则不可变 | ✅ | 运行时门控，直接强化此原则 |

**评估**: 🟢 这是 SpiritCore 原则的物化实现，优先级高。

### core/world_model.py — 世界模型 (471行)

**评估**: 🟡 模块独立，但与外部的集成接口尚不清晰。建议在 main_fast 中暴露的 API 端点已就位。

### infrastructure/database_manager.py — 数据库管理器 (73行)

**评估**: 🟡 基座已建但迁移未开始。建议每轮巡检迁移 2-3 个 sqlite3.connect 到 DatabaseManager。

---

## 3. 休眠模块清理进度

| 已删除 | 待清理(估计) |
|--------|------------|
| ✅ `core/vector_retriever.py` | ~15 个休眠模块仍需清理 |
| ✅ `infrastructure/fact_store_v2.py` | 参见 SYSTEM_ROADMAP.md |
| ✅ `infrastructure/versioned_fact_store.py` | |

---

## 4. 架构风险雷达

| 风险 | 等级 | 说明 |
|------|------|------|
| main_fast.py 裸 except 新增 | 🔴 高 | 33处裸except吞噬异常，违反"失败有方向" |
| DB 迁移未启动 | 🟡 中 | database_manager.py 已建但未使用 |
| 新模块未测试覆盖 | 🟡 中 | cbnr/world_model/introspector 等新模块尚缺测试 |
| main_fast.py 规模增长 | 🟡 中 | 拆分未开始，反增342行 |
| chat_stream 仍 > 2000行 | 🟡 低 | 虽已大幅缩减，距500目标仍远 |

---

## 5. 下轮优先行动

1. **🔴 main_fast.py 裸 except 修复** (高优先级) — 33处 `except:` → `except Exception:`
2. **🟢 chat_stream 继续拆分** — 目标下一轮 < 1500 行
3. **🟡 DB 迁移启动** — 迁移 2 个文件到 DatabaseManager
4. **🟡 新模块测试** — 为 alignment_guard/cbnr 添加单元测试
5. **📋 commit 规范** — 再次提醒团队使用标记 `[chat_stream]` `[main_fast]` `[db_migration]` `[dead_code]`
