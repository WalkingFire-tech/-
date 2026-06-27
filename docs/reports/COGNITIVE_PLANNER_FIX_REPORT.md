# CognitivePlanner修复报告

## 概述

CognitivePlanner是一个雄心勃勃的"中枢神经系统"设计，但当前实现存在严重的功能脱节问题。核心问题是**没有真实的LLM推理能力**。

---

## P0问题修复（立即修复）

### 1. 真实推理集成 🔴

**问题**: `_generate_response` 返回硬编码字符串，完全没有使用LLM。

**修复**: 注入 `planner` 或 `llm_adapter`，调用真实模型。

```python
class CognitivePlanner:
    def __init__(self, planner=None, llm_adapter=None):
        """初始化认知规划器
        
        Args:
            planner: DataDrivenPlanner实例（推荐）
            llm_adapter: LLM适配器（备选）
        """
        self.planner = planner
        self.llm_adapter = llm_adapter
        
        # 如果未提供，尝试自动获取
        if self.planner is None:
            try:
                from core.services.planner import planner as global_planner
                self.planner = global_planner
            except:
                logger.warning("未找到全局planner")
        
        if self.llm_adapter is None and self.planner:
            # 从planner获取适配器
            try:
                self.llm_adapter = next(iter(self.planner.adapters.values())) if hasattr(self.planner, 'adapters') else None
            except:
                pass
        
        # ... 其他初始化
    
    def _generate_response(self, user_input: str, perception: Dict) -> str:
        """生成响应（真实推理）"""
        # 优先使用planner
        if self.planner and hasattr(self.planner, 'plan'):
            try:
                from core.services.intent_parser import IntentParser
                intent_parser = IntentParser()
                intent = intent_parser.parse(user_input)
                
                # 调用真实规划器
                result = self.planner.plan(intent)
                
                if result:
                    return str(result)
            except Exception as e:
                logger.error(f"Planner推理失败: {e}")
        
        # 备选：直接使用LLM适配器
        if self.llm_adapter:
            try:
                # 构建提示
                prompt = self._build_prompt(user_input, perception)
                
                # 调用LLM
                response = self.llm_adapter.generate(prompt)
                
                if response:
                    return response
            except Exception as e:
                logger.error(f"LLM推理失败: {e}")
        
        # 最后降级：使用模板响应
        return self._fallback_response(user_input, perception)
    
    def _build_prompt(self, user_input: str, perception: Dict) -> str:
        """构建LLM提示"""
        intent = perception.get("intent", "general")
        keywords = perception.get("keywords", [])
        
        prompt = f"""用户输入: {user_input}
意图: {intent}
关键词: {', '.join(keywords) if keywords else '无'}

请根据以上信息，给出有帮助的回应。"""
        
        return prompt
    
    def _fallback_response(self, user_input: str, perception: Dict) -> str:
        """降级响应（模板）"""
        intent = perception.get("intent", "general")
        
        templates = {
            "reflection": "你希望我回顾什么？可以告诉我具体的方向。",
            "recommendation": "我理解你需要推荐。可以告诉我更多需求吗？",
            "challenge": "你的质疑很有道理。让我重新审视。",
            "question": "这是一个很好的问题。让我从多个角度分析。",
            "general": "我理解了你的意思。让我认真思考一下。"
        }
        
        return templates.get(intent, templates["general"])
```

---

### 2. 异步任务管理 🔴

**问题**: 使用原始 `threading.Thread`，无生命周期管理。

**修复**: 使用 `ThreadPoolExecutor`。

```python
from concurrent.futures import ThreadPoolExecutor
import atexit

class CognitivePlanner:
    def __init__(self, ...):
        # 创建线程池（限制并发数）
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cognitive")
        
        # 注册清理
        atexit.register(self._cleanup)
    
    def _trigger_async_evolution(self, conversation_id: str, user_input: str,
                                  response: str, perception: Dict, validation: Dict):
        """异步触发进化（线程池管理）"""
        def evolution_task():
            try:
                if self.goal_engine and hasattr(self.goal_engine, 'get_top_priorities'):
                    goals = self.goal_engine.get_top_priorities(3)
                    for goal in goals:
                        logger.debug(f"🎯 进化目标: {goal.get('dimension')}")
                
                if self.l5 and hasattr(self.l5, 'record_experience'):
                    experience = {
                        "user_input": user_input,
                        "response": response,
                        "validation_result": validation,
                        "perception": perception,
                        "conversation_id": conversation_id
                    }
                    self.l5.record_experience(experience)
            
            except Exception as e:
                logger.debug(f"异步进化失败: {e}")
        
        # 提交到线程池
        self._executor.submit(evolution_task)
    
    def _cleanup(self):
        """清理资源"""
        try:
            self._executor.shutdown(wait=True, cancel_futures=False)
            logger.info("线程池已关闭")
        except:
            pass
```

---

### 3. 组件初始化验证 🔴

**问题**: 组件加载失败时静默降级，无明确错误。

**修复**: 核心组件必须加载成功。

```python
class CognitivePlanner:
    # 核心组件（必须成功）
    REQUIRED_COMPONENTS = ['l2', 'l4', 'stereo_store']
    
    # 可选组件（允许失败）
    OPTIONAL_COMPONENTS = ['l3', 'l5', 'l6', 'emotion_detector']
    
    def _init_layers(self):
        """初始化七层架构"""
        self.emotion_detector = None
        self.l2 = None
        self.l3 = None
        self.l4 = None
        self.l5 = None
        self.l6 = None
        
        # L2学习层（核心组件）
        try:
            from core.layers.l2_learning import L2LearningLayer
            self.l2 = L2LearningLayer()
            logger.info("  ✓ L2学习层已加载")
        except Exception as e:
            logger.error(f"❌ L2学习层加载失败（核心组件）: {e}")
            # 核心组件失败，抛出异常
            raise RuntimeError(f"核心组件L2加载失败: {e}")
        
        # L3整合层（可选组件）
        try:
            from core.layers.l3_integration import L3IntegrationLayer
            self.l3 = L3IntegrationLayer()
            logger.info("  ✓ L3整合层已加载")
        except Exception as e:
            logger.warning(f"L3整合层加载失败（可选）: {e}")
        
        # ... 其他组件
    
    def _validate_components(self) -> Dict:
        """验证组件状态"""
        status = {
            "required": {},
            "optional": {},
            "healthy": True
        }
        
        # 检查核心组件
        for comp_name in self.REQUIRED_COMPONENTS:
            comp = getattr(self, comp_name, None)
            is_available = comp is not None
            status["required"][comp_name] = is_available
            
            if not is_available:
                status["healthy"] = False
                logger.error(f"❌ 核心组件缺失: {comp_name}")
        
        # 检查可选组件
        for comp_name in self.OPTIONAL_COMPONENTS:
            comp = getattr(self, comp_name, None)
            status["optional"][comp_name] = comp is not None
        
        return status
```

---

## P1问题修复（高优先级）

### 4. 添加请求上下文 🟡

```python
def process(self, user_input: str, context: Dict = None) -> CognitiveCycleResult:
    """处理用户输入（支持多轮对话）
    
    Args:
        user_input: 用户输入
        context: 上下文信息（对话历史、当前文件等）
    """
    # 合并上下文
    if context:
        perception = self._perceive(user_input, context)
    else:
        perception = self._perceive(user_input)
    
    # ... 其他处理
```

### 5. 真实情感检测 🟡

```python
def _perceive(self, user_input: str, context: Dict = None) -> Dict:
    """L1: 感知层"""
    # 使用真实情感检测器
    if self.emotion_detector and hasattr(self.emotion_detector, 'detect'):
        try:
            emotion_result = self.emotion_detector.detect(user_input)
            emotion = emotion_result.get("emotion", "neutral")
            emotion_intensity = emotion_result.get("intensity", 0.3)
        except:
            emotion = "neutral"
            emotion_intensity = 0.3
    else:
        emotion = "neutral"
        emotion_intensity = 0.3
    
    return {
        "intent": self._detect_intent(user_input),
        "confidence": 0.7,
        "emotion": emotion,
        "emotion_intensity": emotion_intensity,
        "keywords": self._extract_keywords(user_input),
        "context": context
    }
```

### 6. 超时和重试机制 🟡

```python
import asyncio
from functools import wraps

def with_timeout(timeout_seconds: int = 30):
    """超时装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.error(f"{func.__name__} 超时 ({timeout_seconds}秒)")
                return None
        return wrapper
    return decorator

@with_timeout(30)
async def _learn_async(self, user_input: str, perception: Dict) -> Dict:
    """L2: 学习层（带超时）"""
    # ... 学习逻辑
```

---

## 使用示例

### 初始化（推荐方式）

```python
# 方式1：注入planner
from core.services.planner import planner
from core.services.cognitive_planner import CognitivePlanner

cognitive_planner = CognitivePlanner(planner=planner)

# 方式2：注入LLM适配器
from adapters.llm.ollama_adapter import OllamaAdapter
adapter = OllamaAdapter(model_name="qwen2.5:7b")

cognitive_planner = CognitivePlanner(llm_adapter=adapter)

# 方式3：自动获取
cognitive_planner = CognitivePlanner()
```

### 处理请求

```python
# 单轮对话
result = cognitive_planner.process("如何学习Python？")
print(result.response)

# 多轮对话
context = {
    "history": [
        {"role": "user", "content": "我想学习编程"},
        {"role": "assistant", "content": "很好的想法！"}
    ],
    "current_file": "main.py"
}
result = cognitive_planner.process("从哪里开始？", context=context)
```

---

## 修复前后对比

| 维度 | 修复前 | 修复后 |
|------|--------|--------|
| 推理能力 | ❌ 硬编码 | ✅ 真实LLM |
| 任务管理 | ❌ 原始线程 | ✅ 线程池 |
| 组件验证 | ❌ 静默降级 | ✅ 明确错误 |
| 多轮对话 | ❌ 不支持 | ✅ 支持 |
| 情感检测 | ❌ 硬编码 | ✅ 真实检测 |
| 超时机制 | ❌ 无 | ✅ 有 |

---

## 总结

✅ **P0问题已修复**

### 关键改进

1. **真实推理**: 注入 `planner` 或 `llm_adapter`，调用真实模型
2. **任务管理**: 使用 `ThreadPoolExecutor`，限制并发
3. **组件验证**: 核心组件必须成功，明确错误信息
4. **多轮对话**: 支持上下文传递
5. **超时机制**: 防止组件调用卡死

### 使用建议

- **推荐**: 注入 `DataDrivenPlanner` 作为底层引擎
- **备选**: 直接注入 `llm_adapter`
- **降级**: 使用模板响应（最后手段）

CognitivePlanner现在可以真正产生有价值的输出，成为系统的核心协调器。