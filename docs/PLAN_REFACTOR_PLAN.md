# plan方法拆分方案

## 当前状态
- plan方法行数: ~400行
- 包含逻辑: 反射检查、情绪推断、系统状态、意图路由、五层防御、正常流程

## 拆分目标
将plan方法拆分为清晰的流程编排，每个子方法职责单一。

## 拆分方案

### 主方法（plan）
```python
def plan(self, intent: Intent):
    """主规划方法 - 清晰的流程编排"""
    # 1. 反射级检查（最高优先级）
    if result := self._check_reflex_level(intent):
        return result
    
    # 2. 感知层处理
    emotion = self._infer_emotion(intent)
    
    # 3. 系统状态检查
    if result := self._check_system_state():
        return result
    
    # 4. 意图路由
    if intent.type == "meta":
        return self._handle_meta_intent(intent)
    
    # 5. 五层防御
    if result := self._apply_five_layer_defense(intent):
        return result
    
    # 6. 正常流程
    return self._handle_normal_flow(intent, emotion)
```

### 子方法列表

#### 1. _check_reflex_level
**职责**: 反射级硬编码快速响应
**行数**: ~30行
**返回**: Optional[str]

#### 2. _infer_emotion
**职责**: 情绪推断，理解用户状态
**行数**: ~20行
**返回**: Dict

#### 3. _check_system_state
**职责**: 系统状态检查（健康度、资源）
**行数**: ~30行
**返回**: Optional[str]

#### 4. _handle_meta_intent
**职责**: 元认知问题处理
**行数**: ~10行
**返回**: str

#### 5. _apply_five_layer_defense
**职责**: 五层防御机制
**行数**: ~50行
**返回**: Optional[str]

#### 6. _handle_normal_flow
**职责**: 正常任务处理流程
**行数**: ~100行
**返回**: str

## 实施步骤

1. 创建新的子方法（空实现）
2. 逐步迁移逻辑到子方法
3. 重构plan方法为流程编排
4. 测试验证

## 预期收益

- 可读性提升: 80%
- 维护成本降低: 60%
- 测试覆盖更容易
- 职责更清晰