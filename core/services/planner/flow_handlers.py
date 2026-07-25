"""流程处理 mixin — 编排各处理流程"""
from typing import Optional, Dict
from loguru import logger
from infrastructure.event_bus import bus
from core.services.intent_parser import Intent


class FlowHandlersMixin:
    """流程处理：正常流、记忆查询、降级流、认知流"""

    def _init_flow_handlers(self):
        self._current_flow = "normal"

    def _handle_normal_flow(self, intent: Intent, emotion: Dict):
        """标准流程：选择模型 → 调用 → 验证 → 记录"""
        model = self._select_model(intent)
        if not model:
            return None
        try:
            response = model.generate(intent.raw_text, task_type=intent.type)
            if isinstance(response, tuple):
                response, _ = response
            return response
        except Exception as e:
            logger.error(f"正常流失败: {e}")
            return None

    def _handle_memory_query(self, intent: Intent) -> str:
        """处理记忆查询"""
        from infrastructure.experience_pool import ExperiencePool
        pool = ExperiencePool()
        results = pool.query(intent.raw_text, top_k=3)
        if results:
            return "\n".join([r.get("response", "") for r in results])
        return "未找到相关记忆。"

    def _parallel_schedule(self, intent: Intent) -> Optional[str]:
        """并行调度多个模型"""
        responses = []
        for name, adapter in list(self.adapters.items())[:3]:
            try:
                resp = adapter.generate(intent.raw_text, task_type=intent.type)
                if isinstance(resp, tuple):
                    resp, _ = resp
                if resp:
                    responses.append(resp)
            except Exception:
                continue
        return max(responses, key=len) if responses else None

    def _try_federation_flow(self, intent: Intent) -> Optional[str]:
        """尝试联邦调度"""
        return self._parallel_schedule(intent)

    def _try_rule_based_routing(self, intent: Intent) -> Optional[str]:
        """基于规则的路由"""
        return None

    def _request_user_help(self, intent: Intent, error: str) -> Optional[str]:
        """请求用户帮助"""
        return f"我需要更多信息来回答你的问题。{error}"

    def _trigger_failure_learning(self, intent: Intent, error: str):
        """触发失败学习"""
        logger.info(f"记录失败案例: {intent.raw_text[:50]} | {error[:50]}")
        bus.publish("failure_learning", {"query": intent.raw_text, "error": error})

    def _should_use_cognitive_mode(self, intent: Intent) -> bool:
        """判断是否使用认知模式"""
        return intent.type in ("complex_query", "meta")

    def _cognitive_mode(self, intent: Intent) -> str:
        """认知模式处理"""
        model = self._select_model(intent)
        if model:
            try:
                result = model.generate(intent.raw_text, task_type="complex")
                return result[0] if isinstance(result, tuple) else result
            except Exception as e:
                logger.warning(f"操作降级跳过: {e}")
        return "让我仔细思考一下你的问题..."

    def _is_complex_task(self, intent: Intent) -> bool:
        """判断是否为复杂任务"""
        return len(intent.raw_text) > 200 or intent.type in ("complex_query", "code")
