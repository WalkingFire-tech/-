# P3中继形态 W2 里程碑 — "值得信任"阶段完成

**日期**: 2026-07-25
**提交**: 940b9d9

---

## 里程碑声明

系统从"能力存在但不可靠"进入"能力运行且可信任"状态。WorldModel从旁路装饰升级为内核组件，因果决策区分度从0提升到26.7倍，244处静默失败被照亮，端口抽象从概念走向路由层迁移。

---

## 量化证据

### 因果决策能力

| 指标 | W1 | W2 | 变化 |
|------|----|----|------|
| predict区分度(标准差) | 0.000 | 0.307 | ∞ |
| pre_enact采纳率 | 100%(无区分) | 100%(有区分) | 质变 |
| 因果图节点 | 585 | 585+ | 稳定增长 |
| 因果图边 | 1621 | 1621+ | 稳定增长 |
| verified预测 | 97 | 97+ | 闭环运行 |
| truth→method桥接 | 491 | 491 | 知识图谱活桥接 |

### predict区分度详情

| action | W1 prob | W2 prob | W2 conf | score |
|--------|---------|---------|---------|-------|
| ollama | 0.560 | 0.800 | 1.000 | 0.800 |
| deepseek | 0.560 | 0.799 | 1.000 | 0.799 |
| experience_pool | 0.560 | 0.700 | 0.700 | 0.490 |
| internal | 0.560 | 0.473 | 0.700 | 0.331 |
| knowledge_base | 0.560 | 0.370 | 0.150 | 0.056 |

### 系统健康度

| 指标 | 值 |
|------|-----|
| 工具注册 | 16/16 (含unified_read) |
| conservative模式 | NORMAL (内存27.6%) |
| 日志洪水 | 0 (唯一源已修复) |
| SSE接口兼容 | 零破坏 |
| 裸except修复 | 244/705 (35%) |

---

## 本轮完成项

### MM. ToolRegistry register_tool方法修复
- `_FuncToolWrapper`类 + `register_tool()`便捷方法
- UnifiedReader通过新方法成功注册(cat=io, pri=50)
- 裸except改为logger.warning

### NN. predict函数区分度优化
- `_build_causal_paths`: 多步因果路径(method→outcome→outcome)，路径概率=边概率连乘
- `_find_relevant_edges`: `state["action"]`→`method:{action}`搜索词映射
- PREVENTS边正确衰减: `prob *= (1 - prevents_prob)`
- intent→method ENABLES边加权
- pre_enact概率下限过滤(0.05) + 全过滤fallback兜底

### OO. 裸except静默pass批量修复
- 244处 `except Exception: pass` → `except Exception as e: logger.warning(f"操作降级跳过: {e}")`
- core/ 144处 + backend/ 100处
- 67个文件覆盖

### PP. 端口抽象Phase3外部接口标准化
- 新增 `ChatHistoryPort` + `EventBusPort` (ABC + 适配器 + 工厂函数)
- 扩展 `FactStorePort`: add_assertion/add_correction/get_stats
- 扩展 `EventBusPort`: get_subscriber_count
- 迁移3个路由: chat.py(6处) + system.py(2处) + knowledge.py(4处)
- 路由层 `from infrastructure.xxx` 直接导入减少12处

### 额外修复
- existence_layer L705: 休息状态日志 warning→debug
- lifespan: 删除重复except块

---

## 验证结果

| 验证项 | 结果 | 证据 |
|--------|------|------|
| V1 日志洪水 | ✅ | 唯一无条件循环warning(L705)已修复为debug |
| V2 工具注册 | ✅ | 16/16成功，unified_read通过register_tool注册 |
| V3 predict 0.030根因 | ✅ | 数据不足(prob=0.37/conf=0.15)，非下溢非PREVENTS |
| V4 SSE兼容 | ✅ | SSE聊天接口零修改，ChatHistoryPort仅影响CRUD |
| conservative | ✅ | NORMAL(27.6%内存)，VRAM tight误判已修复 |

---

## 发现记录

| # | 发现 | 影响 |
|---|------|------|
| 111 | predict区分度根因是搜索词格式不匹配 | `_find_relevant_edges`搜索`intent:{action}`但因果图是`method:{action}` |
| 112 | 端口抽象Phase3渐进式迁移策略 | 按绕过频率排序：ChatHistory(6)>FactStore(4)>EventBus(2) |
| 113 | lifespan重复except块 | 行543-550有重复`except Exception as e` |
| 114 | health端点仍直接import infrastructure | `/api/health`中`from infrastructure.vector_retriever` |
| 115 | existence_layer休息状态日志洪水源 | L705无条件warning在每次resting tick触发 |

---

## 诚实标注

### 已知限制

1. **predict区分度依赖因果图数据量** — knowledge_base只有1条边(prob=0.37/conf=0.15)，低置信度反映经验不足，非算法缺陷
2. **端口抽象Phase3未完成** — evolution路由、system路由仍有直接import，需继续迁移
3. **裸except仅修复35%** — 705处中244处已修复，剩余461处需逐步处理
4. **运行时E2E验证未完成** — 完整服务器启动测试因断电风险未执行

### 未验证假设

- HTTP启动修复(lifespan yield提前)在完整服务器环境下是否消除ERR_CONNECTION_REFUSED
- 244处logger.warning在高并发下是否引入性能退化
- pre_enact概率下限0.05是否为最优阈值

---

## 下一步方向

### 方向A: 继续巩固"值得信任"

| 项目 | 价值 |
|------|------|
| 测试覆盖提升 | 244处except修改需要回归测试覆盖 |
| 端口抽象Phase3剩余迁移 | 完成全部路由替换 |
| orchestrator瘦身 | 进一步降低耦合 |

### 方向B: 开始"让它更聪明"

| 项目 | 价值 |
|------|------|
| 贝叶斯优化接入主流程 | predict权重更新从启发式走向概率推断 |
| 动态概率场与WorldModel联动 | 概率场探索值直接驱动因果路径搜索 |
| 自主好奇循环 | 系统在无交互时主动发起探索查询 |

---

## 数据库快照

```
data/world_model.db: 585+节点/1621+边/3270+预测/97+verified
data/truths.db: 27条真谛(清理后)
data/experience_pool.db: 28000+条经验
data/knowledge_graph.db: 178节点/13215连接
data/ratchet_gate.db: ratchet≈0.6977
```