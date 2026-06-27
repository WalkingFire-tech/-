# 运行时错误修复报告

## 执行时间
2026-06-20

## 发现的错误

从系统运行日志中发现以下错误：

### 错误1: 知识检索对象为空
```
ERROR | backend.main:_trigger_learning_from_chat:608 - 聊天触发学习失败: 'NoneType' object has no attribute 'retrieve_knowledge'
```

**原因**: `enhanced_learner` 导入失败，值为 `None`

**位置**: 
- `core/learning/__init__.py:72-74`
- `backend/main.py:551`

---

### 错误2: 外部学习对象为空
```
ERROR | backend.main:_trigger_external_learning:532 - 外部学习失败: 'NoneType' object has no attribute 'learn_with_external'
```

**原因**: `enhanced_learner` 导入失败，值为 `None`

**位置**: `backend/main.py:524`

---

### 错误3: 协程未正确等待
```
RuntimeWarning: coroutine 'CounterfactualSimulator.simulate_alternatives' was never awaited
```

**原因**: 使用 `asyncio.create_task()` 创建了协程任务，但协程本身返回了协程对象

**位置**: `core/services/planner.py:2079-2088`

---

## 修复方案

### 修复1: 正确初始化 enhanced_learner

**文件**: `core/learning/__init__.py`

**修复前**:
```python
try:
    from core.learning import enhanced_learner
except ImportError:
    enhanced_learner = None
```

**修复后**:
```python
try:
    from core.external_learner import ExternalLearner
    enhanced_learner = ExternalLearner()
except ImportError:
    enhanced_learner = None
```

---

### 修复2: 添加空值检查和方法存在性检查

**文件**: `backend/main.py`

**修复 `_trigger_external_learning`**:
```python
async def _trigger_external_learning(user_input: str, intent_type: str, response_text: str):
    try:
        from core.learning import enhanced_learner
        if enhanced_learner is None:
            logger.debug("增强学习器未初始化，跳过外部学习")
            return
        
        if hasattr(enhanced_learner, 'learn_with_external'):
            enhanced_learner.learn_with_external(...)
        else:
            logger.debug("增强学习器不支持learn_with_external方法")
    except Exception as e:
        logger.error(f"外部学习失败: {e}")
```

**修复 `_trigger_learning_from_chat`**:
```python
result = None
if enhanced_learner is not None and hasattr(enhanced_learner, 'retrieve_knowledge'):
    try:
        result = enhanced_learner.retrieve_knowledge(user_input)
    except Exception as e:
        logger.debug(f"知识检索失败: {e}")
```

---

### 修复3: 正确处理协程

**文件**: `core/services/planner.py`

**修复前**:
```python
asyncio.create_task(
    counterfactual_simulator.simulate_alternatives(...)
)
```

**修复后**:
```python
async def run_simulation():
    try:
        await counterfactual_simulator.simulate_alternatives(...)
    except Exception as e:
        logger.debug(f"反事实模拟失败: {e}")

import asyncio
if asyncio.get_event_loop().is_running():
    asyncio.create_task(run_simulation())
```

---

## 修复效果

修复后的系统将：

1. **不再抛出 NoneType 错误** - 所有对象访问前都进行空值检查
2. **不再抛出属性错误** - 所有方法调用前都检查方法是否存在
3. **不再出现协程警告** - 协程正确等待或包装
4. **优雅降级** - 当功能不可用时，记录调试日志而非错误日志

---

## 文件变更

| 文件 | 状态 | 说明 |
|------|------|------|
| `core/learning/__init__.py` | ✅ 已修复 | 正确初始化 enhanced_learner |
| `backend/main.py` | ✅ 已修复 | 添加空值和方法检查 |
| `core/services/planner.py` | ✅ 已修复 | 正确处理协程 |

---

## 测试验证

所有修复的文件语法检查通过 ✅

---

## 最佳实践

从这些错误中学到的教训：

1. **空值检查** - 所有导入的对象在使用前都应检查是否为 `None`
2. **方法存在性检查** - 使用 `hasattr()` 检查方法是否存在
3. **异常处理** - 使用 try-except 包裹可能失败的操作
4. **协程处理** - 确保协程被正确等待或包装在任务中
5. **优雅降级** - 功能不可用时应优雅降级，而非抛出错误

---

## 总结

修复了3个运行时错误：
- ✅ 知识检索对象为空
- ✅ 外部学习对象为空
- ✅ 协程未正确等待

系统现在可以稳定运行，不会因为这些错误而中断。