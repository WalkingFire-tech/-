# Planner高危问题修复报告

## 执行时间
2026-06-19

## 发现的高危问题

### P1: _data_driven_select 方法重复定义 🔴
同一个方法被定义了两次，第二次覆盖了第一次，导致情绪感知逻辑丢失。

**验证**: 检查源代码，确认只有1个定义。

### P2: self.db_path 未定义 🔴
在 `_request_user_help` 和 `_trigger_failure_learning` 中使用 `self.db_path`，但未在 `__init__` 中定义。

**修复**:
```python
def __init__(self, adapters: dict, adapters_lock=None):
    # ...
    self.db_path = "data/experience_pool.db"
    # ...
```

### P3: secondary_emotions 不存在 🔴
`EmotionalState` 数据类中没有 `secondary_emotions` 属性，导致运行时 `AttributeError`。

**修复**:
```python
result = {
    "emotion": emotion_result.primary_emotion,
    "intensity": emotion_result.intensity,
    "confidence": emotion_result.confidence,
    "patience": 1.0 - emotion_result.intensity * 0.3,
    # 移除: "secondary_emotions": emotion_result.secondary_emotions,
    "should_simplify": emotion_result.intensity > 0.7
}
```

### P4: self.task_decomposer 可能为 None 🟡
如果导入失败，`self.task_decomposer` 为 `None`，直接调用会导致 `AttributeError`。

**修复**:
```python
def _decompose_and_execute(self, intent: Intent):
    try:
        # 检查任务分解器是否可用
        if not hasattr(self, 'task_decomposer') or self.task_decomposer is None:
            logger.warning("任务分解器不可用，使用联邦调度")
            return self._parallel_schedule(intent)
        
        # 1. 分解任务
        # ...
```

### P6: self.induction_summarizer 未定义 🟡
在 `_trigger_failure_learning` 中使用 `self.induction_summarizer`，但未定义。

**修复**:
```python
# 3. 触发归纳总结
try:
    if INDUCTION_AVAILABLE:
        from meta.induction import induction_scheduler
        induction_scheduler.run_induction()
        logger.info("失败后触发归纳总结")
except Exception as induction_error:
    logger.debug(f"归纳总结触发失败: {induction_error}")
```

### P10: current_model 可能为 None 🟢
在 `_try_fallback_models` 中，`current_model` 可能为 `None`，直接使用 `in` 比较可能导致问题。

**修复**:
```python
current_model = self.last_call_info.get("model")
if current_model and current_model in fallback_order:
    fallback_order = [m for m in fallback_order if m != current_model]
```

---

## 验证结果

### ✅ Planner高危问题修复验证

| 问题 | 修复状态 |
|------|---------|
| P1: _data_driven_select 重复定义 | ✅ 已验证只有1个定义 |
| P2: self.db_path 未定义 | ✅ 已在__init__中添加 |
| P3: secondary_emotions 不存在 | ✅ 已移除该字段 |
| P4: self.task_decomposer 为None | ✅ 已添加None检查 |
| P6: self.induction_summarizer 未定义 | ✅ 已改用induction_scheduler |
| P10: current_model 可能为None | ✅ 已添加None检查 |

---

## 修复总结

| 问题类型 | 数量 | 严重程度 | 状态 |
|---------|------|---------|------|
| 重复定义 | 1 | 🔴 高危 | ✅ 已验证 |
| 未定义变量 | 2 | 🔴 高危 | ✅ 已修复 |
| 属性不存在 | 1 | 🔴 高危 | ✅ 已修复 |
| None检查缺失 | 2 | 🟡 中等 | ✅ 已修复 |

---

## 文件变更

**修改文件**: `core/services/planner.py`

**备份文件**: `core/services/planner.py.backup2`

**测试文件**: `test_planner_fix.py`

---

## 总结

🎉 **所有高危问题已修复！**

### 修复成果
- ✅ P1: _data_driven_select - 只有1个定义
- ✅ P2: self.db_path - 已初始化
- ✅ P3: secondary_emotions - 已移除
- ✅ P4: task_decomposer - 已添加None检查
- ✅ P6: induction_summarizer - 已改用induction_scheduler
- ✅ P10: current_model - 已添加None检查

### 代码质量提升
- **健壮性**: 添加了多处None检查，防止运行时错误
- **一致性**: 修复了未定义变量问题
- **可维护性**: 移除了不存在的属性引用

**Planner代码质量显著提升！**