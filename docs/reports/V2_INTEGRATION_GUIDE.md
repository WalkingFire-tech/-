# v2.0认知架构集成指南

## 架构对比

### 现有架构（infrastructure/cognitive_layer.py）
```
问题分析器 → 因果推理器 → 规划生成器 → 不确定性评估器
```
**特点**：四组件并行处理，侧重任务分解

### v2.0架构（core/cognitive_architecture_v2.py）
```
存在层 → 感知层 → 学习层 → 整合层 → 校验层 → 进化层
```
**特点**：六层串行处理，侧重认知进化和反思

---

## 集成方案

### 方案A：双轨并行（推荐）

**原理**：保留现有架构，v2.0作为增强层

```
用户输入
  ↓
[现有cognitive_layer] → 任务分解
  ↓
[v2.0认知架构] → 反思校验
  ↓
输出
```

**实现**：
```python
# 在 planner.py 中
from infrastructure.cognitive_layer import cognitive_layer
from core.cognitive_architecture_v2 import cognitive_architecture as v2_architecture

# 1. 现有流程
result = cognitive_layer.analyze(text, intent_type)

# 2. v2.0增强（可选）
if enable_evolution:
    v2_result = v2_architecture.process(text)
    result['evolution'] = v2_result
```

**优点**：
- 不破坏现有功能
- 渐进式引入v2.0
- 可对比两种架构效果

---

### 方案B：完全替换

**原理**：用v2.0替换现有cognitive_layer

```python
# 在 infrastructure/cognitive_layer.py 中
from core.cognitive_architecture_v2 import cognitive_architecture

class CognitiveLayer:
    def analyze(self, text, intent_type=None, context=""):
        # 调用v2.0架构
        result = cognitive_architecture.process(text)
        
        # 转换为现有格式
        return {
            "analysis": {"core_need": text},
            "subtasks": [],
            "uncertainty": {"overall_confidence": 1.0},
            "evolution": result
        }
```

**优点**：
- 统一架构
- 功能完整

**缺点**：
- 需要全面测试
- 可能影响现有功能

---

### 方案C：场景分流

**原理**：根据问题类型选择架构

```python
def analyze(self, text, intent_type=None, context=""):
    # 判断问题类型
    if self._needs_evolution(text):
        # 需要深度反思的问题 → v2.0
        return v2_architecture.process(text)
    else:
        # 普通问题 → 现有架构
        return cognitive_layer.analyze(text, intent_type)

def _needs_evolution(self, text):
    """判断是否需要进化架构"""
    keywords = ['推荐', '选型', '芯片', '反思', '历史']
    return any(kw in text for kw in keywords)
```

**优点**：
- 针对性优化
- 资源高效

---

## 推荐集成步骤

### 步骤1：创建适配器
```python
# infrastructure/cognitive_evolution_adapter.py
from core.cognitive_architecture_v2 import cognitive_architecture

class CognitiveEvolutionAdapter:
    """v2.0架构适配器"""
    
    def enhance(self, text: str, existing_result: dict) -> dict:
        """用v2.0增强现有结果"""
        
        v2_result = cognitive_architecture.process(text)
        
        # 合并结果
        enhanced = existing_result.copy()
        enhanced['evolution'] = {
            'is_valid': v2_result['is_valid'],
            'thinking_chain': v2_result['thinking_chain'],
            'user_friendly': v2_result['user_friendly_output'],
            'diagnosis': v2_result['meta']
        }
        
        return enhanced
```

### 步骤2：在planner中集成
```python
# core/services/planner.py

try:
    from infrastructure.cognitive_evolution_adapter import CognitiveEvolutionAdapter
    EVOLUTION_AVAILABLE = True
except:
    EVOLUTION_AVAILABLE = False

class DataDrivenPlanner:
    def __init__(self, ...):
        ...
        if EVOLUTION_AVAILABLE:
            self.evolution_adapter = CognitiveEvolutionAdapter()
    
    def plan(self, intent):
        ...
        # 现有流程
        result = cognitive_layer.analyze(...)
        
        # v2.0增强
        if hasattr(self, 'evolution_adapter'):
            result = self.evolution_adapter.enhance(
                intent.original_text,
                result
            )
        
        return result
```

### 步骤3：前端展示
```javascript
// frontend/app.js
function displayResponse(response) {
    // 现有输出
    displayNormalResponse(response);
    
    // 进化信息（如果有）
    if (response.evolution) {
        displayEvolutionInfo(response.evolution);
    }
}
```

---

## 配置选项

```yaml
# config.yaml
cognitive:
  # 启用v2.0进化架构
  evolution_enabled: true
  
  # 集成模式：parallel/replace/conditional
  integration_mode: parallel
  
  # 条件模式下的触发关键词
  evolution_keywords:
    - 推荐
    - 选型
    - 芯片
    - 反思
    - 历史
```

---

## 测试验证

### 单元测试
```python
def test_evolution_adapter():
    adapter = CognitiveEvolutionAdapter()
    
    existing = {"analysis": {"core_need": "测试"}}
    enhanced = adapter.enhance("推荐芯片", existing)
    
    assert 'evolution' in enhanced
    assert enhanced['evolution']['is_valid'] is not None
```

### 集成测试
```python
def test_planner_with_evolution():
    planner = DataDrivenPlanner(adapters)
    
    intent = Intent(original_text="推荐26650电池保护芯片")
    result = planner.plan(intent)
    
    assert 'evolution' in result
```

---

## 监控指标

```python
# 添加到元认知层监控
metrics = {
    'evolution_calls': 0,
    'evolution_success': 0,
    'avg_evolution_time': 0,
    'thinking_chain_length': 0
}
```

---

## 下一步

1. **立即执行**：创建适配器并集成到planner
2. **测试验证**：运行端到端测试
3. **监控观察**：收集运行数据
4. **优化调整**：根据反馈优化参数

---

**推荐方案**：方案A（双轨并行）+ 适配器模式

这样既能保留现有功能，又能引入v2.0的进化能力。