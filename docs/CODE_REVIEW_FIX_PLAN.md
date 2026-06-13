# 代码审查问题修复计划

## 审查时间
2026-06-13

## 问题分级

### P0（严重 - 导致功能异常）
1. ✅ intent_parser: meta规则缺失 - **已修复**
2. ⏳ planner: 拆分plan方法 - **进行中**
3. ✅ parallel_scheduler: 模型黑名单 - **已实现model_health_checker**

### P1（中等 - 影响效率）
4. ⏳ model_capability: 学习率、衰减逻辑优化
5. ⏳ charter_executor: 规则动作格式修正
6. ⏳ health_dashboard: 指标算法精确化
7. ⏳ parallel_scheduler: 异常分类重试

### P2（轻微 - 潜在风险）
8. ⏳ math_calculator: π值动态计算
9. ⏳ 工程: 单元测试覆盖
10. ⏳ 工程: 配置类型化

---

## P0-1: meta规则缺失 ✅

**状态**: 已修复

**修复位置**: `core/services/intent_parser.py:30-35`

**修复内容**:
```python
"meta": re.compile(
    r"你.*如何.*理解|你怎么.*知道|你觉得自己|你.*改进|你.*学习|"
    r"你.*自我.*进化|你的.*能力|如何.*让你.*更.*好|"
    r"你.*理解.*需求|你.*思考|你的.*理解|你.*优化|"
    r"系统.*如何|系统.*改进|如何.*提升.*理解|"
    r"你.*处理.*不了|你明白我.*意思|我讲的是你|你.*反思|"
    r"你.*分析.*意图|你.*进化|你.*自我|你.*成长|"
    r"你.*懂|你.*明白|你.*认为|如何.*让.*你.*更|"
    r"你.*能力.*边界|能力边界.*在哪|你的.*边界|"
    r"自我.*评估|评估.*体系|你.*决策|你.*如何.*认识|"
    r"你.*最优|你.*贴切|完善.*你|回顾.*对话|给出.*评价",
    re.IGNORECASE
)
```

---

## P0-2: 拆分plan方法 ⏳

**当前状态**: plan方法超过400行

**修复方案**: 拆分为以下私有方法

```python
def plan(self, intent: Intent):
    """主规划方法 - 清晰的流程编排"""
    # 1. 反射级检查
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
    elif intent.type == "calculation":
        return self._handle_calculation_intent(intent)
    
    # 5. 五层防御
    if result := self._apply_five_layer_defense(intent):
        return result
    
    # 6. 正常流程
    return self._handle_normal_flow(intent, emotion)
```

**预计时间**: 2小时

---

## P0-3: 模型黑名单 ✅

**状态**: 已实现

**实现文件**: `infrastructure/model_health_checker.py`

**功能**:
- ✅ 自动管理黑名单
- ✅ 连续失败检测
- ✅ 冷却机制
- ✅ 集成到planner

---

## P1-4: model_capability优化

### 问题4.1: 学习率优化

**当前问题**: `lr = min(0.1, 1.0 / (sample_count + 1))` 初期变化剧烈

**修复方案**:
```python
def _calculate_learning_rate(self, sample_count: int) -> float:
    """自适应学习率 - 指数衰减"""
    # 初期稳定，后期缓慢衰减
    base_lr = 0.05
    decay_rate = 0.95
    return base_lr * (decay_rate ** min(sample_count, 20))
```

### 问题4.2: 衰减逻辑优化

**当前问题**: 对所有维度统一衰减，不考虑更新时间

**修复方案**:
```python
def apply_decay(self, days_threshold: int = 7):
    """智能衰减 - 只对旧数据衰减"""
    now = datetime.now()
    
    for model in self.models:
        for dim in model.dimensions:
            last_update = dim.last_updated
            days_since_update = (now - last_update).days
            
            if days_since_update >= days_threshold:
                # 只对超过阈值的数据衰减
                decay_factor = 0.95 ** (days_since_update / 7)
                dim.score *= decay_factor
```

### 问题4.3: 维度自动发现

**修复方案**:
```python
def add_dimension(self, dimension_name: str, default_score: float = 0.5):
    """动态添加新维度"""
    if dimension_name not in self.DEFAULT_DIMENSIONS:
        self.DEFAULT_DIMENSIONS[dimension_name] = default_score
        logger.info(f"新增能力维度: {dimension_name}")
```

---

## P1-5: charter_executor规则动作修正

**当前问题**: `avoid_model: {model_name}` 格式不被planner识别

**修复方案**:
```python
def review_failures(self) -> List[Dict]:
    """回顾失败案例"""
    ...
    for intent_type, cases in failure_groups.items():
        if len(cases) >= 3:
            # 找到替代模型
            failed_models = set(c['model_name'] for c in cases)
            alternative = self._find_alternative_model(intent_type, failed_models)
            
            learning_tasks.append({
                'type': 'failure_pattern',
                'intent_type': intent_type,
                'condition': f"intent_type == '{intent_type}'",
                'action': f"reroute:{alternative}",  # 修正格式
                'priority': 'high',
            })
```

---

## P1-6: health_dashboard指标精确化

### 问题6.1: 能力覆盖率加权

**修复方案**:
```python
def _measure_capability_coverage(self) -> float:
    """加权能力覆盖率"""
    from infrastructure.model_capability import model_capability
    
    # 维度权重（根据任务重要性）
    dimension_weights = {
        'reasoning': 0.25,
        'coding': 0.25,
        'math': 0.15,
        'creative': 0.10,
        'knowledge': 0.15,
        'speed': 0.10,
    }
    
    weighted_sum = 0
    for dim, weight in dimension_weights.items():
        dim_score = model_capability.get_dimension_average(dim)
        weighted_sum += dim_score * weight
    
    return weighted_sum * 100
```

### 问题6.2: 按意图类型分类成功率

**修复方案**:
```python
def _measure_task_success_rate(self) -> Dict:
    """分类成功率"""
    from infrastructure.model_stats import ModelStats
    stats = ModelStats()
    
    by_intent = {}
    for intent_type in ['code', 'question', 'calculation', 'document']:
        rate = stats.get_success_rate_for_intent(intent_type)
        by_intent[intent_type] = rate
    
    overall = sum(by_intent.values()) / len(by_intent)
    
    return {
        'overall': overall,
        'by_intent': by_intent
    }
```

### 问题6.3: 隐式满意度指标

**修复方案**:
```python
def _measure_user_satisfaction(self) -> float:
    """综合满意度（显式+隐式）"""
    # 显式反馈
    explicit_score = self._get_explicit_feedback_score()
    
    # 隐式指标
    emotion_score = self._get_emotion_score()  # 情绪分析
    engagement_score = self._get_engagement_score()  # 停留时间
    
    # 加权综合
    satisfaction = (
        0.5 * explicit_score +
        0.3 * emotion_score +
        0.2 * engagement_score
    )
    
    return satisfaction
```

---

## P1-7: parallel_scheduler异常分类重试

**当前问题**: 所有异常都重试，包括永久性错误

**修复方案**:
```python
RETRYABLE_ERRORS = [
    TimeoutError,
    ConnectionError,
    ConnectionResetError,
]

PERMANENT_ERRORS = [
    FileNotFoundError,  # 模型不存在
    PermissionError,    # 认证失败
]

def _safe_call(self, model, prompt, retry_count):
    """智能重试 - 区分异常类型"""
    for attempt in range(retry_count):
        try:
            return model.generate(prompt)
        
        except tuple(RETRYABLE_ERRORS) as e:
            # 可重试错误
            logger.warning(f"可重试错误 ({attempt+1}/{retry_count}): {e}")
            if attempt < retry_count - 1:
                time.sleep(2 ** attempt)  # 指数退避
                continue
            raise
        
        except tuple(PERMANENT_ERRORS) as e:
            # 永久性错误，不重试
            logger.error(f"永久性错误，不重试: {e}")
            raise
        
        except Exception as e:
            # 未知错误，记录并重试一次
            logger.error(f"未知错误: {e}")
            if attempt == 0:
                continue
            raise
```

---

## P2-8: math_calculator动态计算

**修复方案**:
```python
def _compute_pi(self, digits: int) -> str:
    """动态计算π值"""
    predefined_max = 100
    
    if digits <= predefined_max:
        # 使用预定义值（快速）
        return self.PREDEFINED_PI[:digits + 2]
    
    # 动态计算（高精度）
    try:
        from mpmath import mp
        mp.dps = digits + 10
        pi_str = str(mp.pi)
        logger.info(f"动态计算π的前{digits}位")
        return pi_str[:digits + 2]
    
    except ImportError:
        logger.warning("mpmath未安装，无法计算高精度π")
        return f"{self.PREDEFINED_PI}\n\n⚠️ 仅显示前{predefined_max}位，安装mpmath可获取更高精度"
```

---

## 实施进度

| 优先级 | 问题 | 状态 | 预计时间 |
|--------|------|------|----------|
| P0-1 | meta规则缺失 | ✅ 完成 | - |
| P0-2 | 拆分plan方法 | ⏳ 进行中 | 2小时 |
| P0-3 | 模型黑名单 | ✅ 完成 | - |
| P1-4 | model_capability优化 | ⏳ 待开始 | 3小时 |
| P1-5 | charter_executor修正 | ⏳ 待开始 | 1小时 |
| P1-6 | health_dashboard精确化 | ⏳ 待开始 | 2小时 |
| P1-7 | 异常分类重试 | ⏳ 待开始 | 1小时 |
| P2-8 | math_calculator动态 | ⏳ 待开始 | 0.5小时 |

**总预计时间**: 9.5小时

---

## 下一步

立即实施 P1-4: model_capability优化