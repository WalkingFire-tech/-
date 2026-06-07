# 联盟拓荒者 - 数据驱动架构重构

**重构日期**: 2026-06-07  
**核心理念**: 完全数据驱动,配置仅提供静态参数和用户偏好

---

## 🎯 核心矛盾

### 原设计的问题

```yaml
# ❌ 错误:配置文件硬编码路由映射
routing:
  task_model_mapping:
    code:
      preferred: ["code_light", "deepcoder"]  # 硬编码!
      fallback: "mindchat"
```

**问题**:
- 路由决策写死在配置文件
- 无法根据实际表现动态调整
- 违背"自我进化的中枢"理念
- 统计库数据被忽略

---

## ✅ 正确的架构

### 配置文件的定位

| 内容类型 | 配置文件 | 运行时动态 | 原因 |
|:---|:---:|:---:|:---|
| 模型连接参数 | ✅ | ❌ | 基础设施,不变 |
| 模型启用状态 | ✅ | ❌ | 管理员控制 |
| 用户偏好 | ✅ | ❌ | 用户设定 |
| **路由映射** | ❌ | ✅ | **统计库决定** |
| 意图规则 | ⚠️ | ✅ | 初始值,可扩展 |
| 质量阈值 | ⚠️ | ✅ | 初始值,可调优 |

---

## 📊 新架构设计

### 1. 配置文件(仅静态)

```yaml
# 用户偏好(影响路由权重)
user_preferences:
  mode: "balanced"  # quality, speed, cost, balanced
  weights:
    quality: 0.5
    speed: 0.3
    cost: 0.2

# 降级后备(仅在统计库无记录时使用)
fallback:
  task_model_order:
    code: ["code_light", "deepcoder", "mindchat"]
    chat: ["mindchat", "deepseek-chat"]
```

### 2. 运行时决策(完全数据驱动)

```python
def _select_model(self, intent_type):
    # 1. 获取用户偏好权重
    w_quality, w_speed, w_cost = self._get_user_preference_weights()
    
    # 2. 统计库推荐(核心决策)
    best = self.stats.get_best_model_for_task(
        task_type=intent_type,
        quality_weight=w_quality,
        speed_weight=w_speed,
        cost_weight=w_cost
    )
    
    if best:
        return best  # ✅ 完全由数据决定
    
    # 3. 降级:使用fallback
    return fallback_model
```

---

## 🔥 核心优势

### 1. 真正的自我进化

**改进前**:
```
配置文件: code → code_light (硬编码)
系统行为: 永远使用code_light,不管实际表现
```

**改进后**:
```
统计库: code任务历史数据
  - code_light: 成功率85%, 质量82
  - deepcoder: 成功率90%, 质量88
  - mindchat: 成功率60%, 质量65

系统决策: code → deepcoder (数据驱动)
```

### 2. 用户偏好尊重

```yaml
# 用户选择质量优先
user_preferences:
  mode: "quality"

# 系统行为:
- 质量85%,速度慢的模型 → 优先选择
- 质量70%,速度快的模型 → 不选择
```

### 3. 自动适应变化

```
时间线:
Day 1: code_light表现好 → 系统选择code_light
Day 7: deepcoder表现提升 → 系统自动切换deepcoder
Day 30: 新模型加入 → 系统自动探索并评估
```

---

## 📈 决策流程

```
用户输入
    ↓
意图识别
    ↓
获取用户偏好权重
    ↓
统计库查询历史表现
    ├─ 有足够数据?
    │   ├─ 是 → 计算综合得分 → 选择最佳模型 ✅
    │   └─ 否 → 使用fallback配置
    ↓
执行任务
    ↓
记录结果到统计库
    ↓
下次决策更准确
```

---

## 🚀 使用示例

### 用户偏好设置

```yaml
# 质量优先模式
user_preferences:
  mode: "quality"

# 速度优先模式
user_preferences:
  mode: "speed"

# 成本优先模式
user_preferences:
  mode: "cost"

# 平衡模式(自定义权重)
user_preferences:
  mode: "balanced"
  weights:
    quality: 0.6  # 提高质量权重
    speed: 0.3
    cost: 0.1
```

### 运行时行为

```python
# 系统自动根据偏好和统计数据决策
planner = DataDrivenPlanner(adapters)

# 用户偏好: quality优先
# 统计数据: deepcoder质量88, code_light质量82
# 决策结果: 选择deepcoder ✅

# 用户偏好: speed优先  
# 统计数据: code_light耗时2s, deepcoder耗时8s
# 决策结果: 选择code_light ✅
```

---

## 🎯 与自我进化的结合

### 1. 统计库持续学习

```python
# 每次调用记录
stats.record_call(
    model_name="deepcoder",
    task_type="code",
    quality_score=88,
    duration=5.2,
    user_feedback=1
)

# 下次决策自动考虑这些数据
```

### 2. 元控制层自动调优

```python
# 超参数优化器定期调整
optimizer.optimize()

# 可能调整的参数:
- quality_weights
- speed_weights
- cost_weights
```

### 3. 配置文件可进化

```python
# 系统学习到的新规则
generated_rules = {
    "intent": {
        "custom_rules": {
            "code": ["新增关键词", "..."]
        }
    }
}

# 写入config/generated_rules.yaml
# 与用户配置分离,优先加载
```

---

## 📝 重构文件清单

1. ✅ `config/settings.yaml` - 移除硬编码路由
2. ✅ `core/services/planner.py` - 完全数据驱动
3. ✅ `DATA_DRIVEN_ARCHITECTURE.md` - 本文档

---

## 🔥🔥🔥 总结

### 核心改进

1. **配置文件** - 仅静态参数+用户偏好 ✅
2. **统计库** - 路由决策的核心 ✅
3. **用户偏好** - 尊重用户选择 ✅
4. **降级机制** - 仅在无数据时使用 ✅

### 理念匹配

**改进前**: 配置硬编码路由 → 违背自我进化 ❌  
**改进后**: 统计库动态决策 → 符合自我进化 ✅

### 效果

- 系统根据实际表现自动调整 ✅
- 用户偏好得到尊重 ✅
- 新模型自动探索评估 ✅
- 决策完全透明可解释 ✅

**这才是真正的"自我进化的中枢"!** 🔥🔥🔥