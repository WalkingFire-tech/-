"""模型选择 mixin — 模型选择、能力追踪、降级"""
from typing import Optional, Dict, Any
from loguru import logger
from infrastructure.event_bus import bus
from core.services.intent_parser import Intent


class ModelSelectorMixin:
    """模型选择能力：根据任务特征选择最优模型"""

    def _init_model_selector(self):
        self._model_performance = {}
        self._default_model = "qwen2.5-coder:1.5b"

    def _auto_load_models(self):
        """自动加载适配器中的模型"""
        for name, adapter in self.adapters.items():
            try:
                logger.info(f"已加载模型: {name}")
            except Exception:
                continue

    def _update_capability_from_result(self, model_name: str, task_type: str, quality: int, duration: float):
        """更新模型能力评分"""
        key = f"{model_name}:{task_type}"
        if key not in self._model_performance:
            self._model_performance[key] = []
        self._model_performance[key].append({"quality": quality, "duration": duration})
        if len(self._model_performance[key]) > 20:
            self._model_performance[key] = self._model_performance[key][-20:]

    def _select_model(self, intent: Intent):
        """根据意图选择最优模型"""
        if not self.adapters:
            logger.error("无可用模型适配器")
            return None

        task_type = intent.type
        skill_name = self._skill_to_model(task_type, intent.type) if hasattr(self, '_skill_to_model') else None
        if skill_name and skill_name in self.adapters:
            return self.adapters[skill_name]

        model_keys = list(self.adapters.keys())
        preferred_order = ["deepcoder", "code_light", "qwen2.5-coder", "qwen2.5", "deepseek"]
        for pref in preferred_order:
            for key in model_keys:
                if pref in key:
                    return self.adapters[key]
        return self.adapters[model_keys[0]]

    def _skill_to_model(self, skill_name: str, intent_type: str) -> Optional[str]:
        """技能到模型的映射"""
        mapping = {
            "code": ["deepcoder", "code_light", "qwen2.5-coder"],
            "question": ["qwen2.5", "deepseek"],
            "calculation": ["code_light", "deepcoder"],
            "meta": ["qwen2.5"],
        }
        candidates = mapping.get(intent_type, [])
        for c in candidates:
            if c in self.adapters:
                return c
        return None

    def _post_process_success(self, intent: Intent, model, response: str, quality: int, duration: float, full_prompt: str):
        """处理模型调用成功后的记录"""
        model_name = getattr(model, 'model_name', 'unknown')
        self._update_capability_from_result(model_name, intent.type, quality, duration)
        try:
            from infrastructure.experience_pool import ExperiencePool
            ExperiencePool().add_experience(
                intent_type=intent.type,
                raw_input=intent.raw_text,
                response=response,
                model_name=model_name,
                quality_score=quality,
                duration=duration,
                success=True,
            )
        except Exception as e:
            logger.warning(f"经验记录失败: {e}")
        bus.publish("task_completed", {"intent": intent.raw_text, "model": model_name, "quality": quality})

    def _single_model_fallback(self, intent: Intent):
        """单模型降级模式"""
        best_model = None
        best_score = -1
        for name, adapter in self.adapters.items():
            key = f"{name}:{intent.type}"
            history = self._model_performance.get(key, [])
            score = sum(h["quality"] for h in history) / max(len(history), 1) if history else 50
            if score > best_score:
                best_score = score
                best_model = adapter
        if not best_model and self.adapters:
            best_model = next(iter(self.adapters.values()))
        if best_model:
            try:
                response = best_model.generate(intent.raw_text, task_type=intent.type)
                if isinstance(response, tuple):
                    response, _ = response
                return response
            except Exception as e:
                logger.error(f"单模型降级失败: {e}")
        return None

    def _try_fallback_models(self, intent: Intent, full_prompt: str) -> Optional[str]:
        """尝试降级模型"""
        model_keys = list(self.adapters.keys())
        fallback_order = [k for k in model_keys if k != "code_light"]
        for key in fallback_order:
            try:
                response = self.adapters[key].generate(full_prompt, task_type=intent.type)
                if response:
                    logger.info(f"降级模型 {key} 成功")
                    return response if not isinstance(response, tuple) else response[0]
            except Exception:
                continue
        return None
