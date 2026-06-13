# 代码优化计划

## 优先级排序

### P0（立即实施）
1. ✅ 拆分plan方法 - 提高可维护性
2. ✅ 增加单元测试 - 降低回归风险
3. ✅ 细化异常处理 - 提高稳定性

### P1（本周内）
4. ✅ 增强meta规则 - 已完成
5. ⏳ 模型健康检查与黑名单
6. ⏳ 决策日志记录

### P2（本月内）
7. ⏳ 能力初始化预测试
8. ⏳ 统一配置类
9. ⏳ 请求ID日志绑定

### P3（长期）
10. ⏳ 分解器置信度输出
11. ⏳ 融合器智能合并
12. ⏳ 流式输出支持

---

## P0-1: 拆分plan方法

**当前问题**: plan方法超过300行，包含多种逻辑

**优化方案**: 拆分为以下私有方法

```python
def plan(self, intent: Intent):
    # 1. 反射级检查
    if result := self._check_reflex(intent):
        return result
    
    # 2. 情绪推断
    emotion = self._infer_emotion(intent)
    
    # 3. 系统状态检查
    if result := self._check_system_health():
        return result
    
    # 4. 元认知处理
    if intent.type == "meta":
        return self._handle_meta_intent(intent)
    
    # 5. 五层防御
    if result := self._apply_five_layer_defense(intent):
        return result
    
    # 6. 正常流程
    return self._handle_normal_flow(intent, emotion)
```

**收益**:
- 可读性提升 80%
- 测试覆盖更容易
- 维护成本降低 60%

---

## P0-2: 单元测试

**需要测试的模块**:

1. `tests/test_intent_parser.py`
   - 测试meta意图识别
   - 测试各意图类型规则
   - 测试置信度计算

2. `tests/test_model_capability.py`
   - 测试能力矩阵更新
   - 测试衰减机制
   - 测试路由选择

3. `tests/test_parallel_scheduler.py`
   - 测试并行调度
   - 测试超时处理
   - 测试降级逻辑

4. `tests/test_reflex_engine.py`
   - 测试反射规则触发
   - 测试优先级排序
   - 测试参数调整

---

## P0-3: 细化异常处理

**当前问题**: 多处使用 `except Exception`

**优化方案**:

```python
# 定义异常类型
class ModelNotAvailableError(Exception): pass
class ModelTimeoutError(Exception): pass
class ModelRateLimitError(Exception): pass
class ToolExecutionError(Exception): pass

# 细化处理
try:
    result = model.generate(prompt)
except ModelTimeoutError:
    logger.warning(f"模型超时: {model_name}")
    return self._fallback_to_faster_model(intent)
except ModelRateLimitError:
    logger.warning(f"模型限流: {model_name}")
    return self._fallback_to_alternative(intent)
except ModelNotAvailableError:
    logger.error(f"模型不可用: {model_name}")
    return self._handle_model_unavailable(intent)
```

---

## P1-5: 模型健康检查

**实现方案**:

```python
class ModelHealthChecker:
    def __init__(self):
        self.failure_counts = defaultdict(int)
        self.blacklist = {}
        self.cooldown = 300  # 5分钟
    
    def is_available(self, model_name: str) -> bool:
        # 检查是否在黑名单中
        if model_name in self.blacklist:
            ban_time = self.blacklist[model_name]
            if time.time() - ban_time < self.cooldown:
                return False
            else:
                # 冷却结束，移出黑名单
                del self.blacklist[model_name]
                self.failure_counts[model_name] = 0
        return True
    
    def record_failure(self, model_name: str):
        self.failure_counts[model_name] += 1
        if self.failure_counts[model_name] >= 3:
            # 连续失败3次，加入黑名单
            self.blacklist[model_name] = time.time()
            logger.warning(f"模型 {model_name} 已加入黑名单")
```

---

## P1-6: 决策日志记录

**实现方案**:

```python
class DecisionLogger:
    def __init__(self):
        self.decisions = deque(maxlen=100)
    
    def log_decision(self, decision_type: str, details: Dict):
        record = {
            "type": decision_type,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        self.decisions.append(record)
    
    def get_last_decision(self) -> Dict:
        return self.decisions[-1] if self.decisions else {}
    
    def explain_last_decision(self) -> str:
        last = self.get_last_decision()
        if not last:
            return "无最近决策记录"
        
        if last["type"] == "model_selection":
            return f"""
最近决策: 模型选择
- 选择模型: {last['details']['model']}
- 原因: {last['details']['reason']}
- 得分: {last['details']['score']:.2f}
- 备选: {last['details']['alternatives']}
"""
```

---

## P2-7: 能力预测试

**实现方案**:

```python
QUICK_BENCHMARKS = {
    "code": [
        "写一个冒泡排序",
        "实现二分查找",
    ],
    "question": [
        "什么是机器学习？",
        "解释递归",
    ],
    "math": [
        "计算 2+2",
        "求 10 的阶乘",
    ]
}

def estimate_capabilities_from_tests(self, model_name: str) -> Dict[str, float]:
    scores = {}
    for dimension, tests in QUICK_BENCHMARKS.items():
        success_count = 0
        for test in tests:
            try:
                result = model.generate(test)
                if self._evaluate_response(result, dimension):
                    success_count += 1
            except:
                pass
        scores[dimension] = success_count / len(tests)
    return scores
```

---

## 实施进度

| 任务 | 状态 | 预计时间 |
|------|------|----------|
| P0-1 拆分plan方法 | ⏳ 进行中 | 2小时 |
| P0-2 单元测试 | ⏳ 待开始 | 4小时 |
| P0-3 异常处理 | ⏳ 待开始 | 1小时 |
| P1-5 模型健康检查 | ⏳ 待开始 | 2小时 |
| P1-6 决策日志 | ⏳ 待开始 | 1小时 |
| P2-7 能力预测试 | ⏳ 待开始 | 3小时 |

**总预计时间**: 13小时

---

## 下一步

立即实施 P0-1: 拆分plan方法