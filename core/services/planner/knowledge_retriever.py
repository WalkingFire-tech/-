"""
知识检索 mixin — 内部知识库、向量检索、外脑协作
"""
from typing import Optional
from loguru import logger
from infrastructure.event_bus import bus
from core.ports.adapters import get_storage_port
from core.services.intent_parser import Intent


class KnowledgeRetrieverMixin:
    """知识检索能力：内部知识库、向量检索、专家协作"""

    def _init_knowledge(self):
        self._knowledge_cache = {}
        self._vector_store = None

    def _try_knowledge_retrieval(self, intent: Intent) -> Optional[str]:
        """【第3层防御】知识库检索（经验复用）"""
        try:
            from infrastructure.knowledge_injector import knowledge_injector
            result = knowledge_injector.retrieve_knowledge(
                question=intent.raw_text, intent_type=intent.type, min_quality=70.0
            )
            if result:
                answer, confidence = result
                logger.info(f"【第3层防御】知识库命中 (置信度: {confidence:.2f})")
                if confidence > 0.8:
                    return answer
                else:
                    return f"{answer}\n\n_(基于历史经验，置信度: {confidence:.0%})_"
            return None
        except Exception as e:
            logger.error(f"知识检索失败: {e}")
            return None

    def _expert_collaboration(self, intent: Intent, confidence: float) -> str:
        """调用外部模型进行结构化分析（外脑协作）"""
        expert = None
        if "remote_gpt4" in self.adapters:
            expert = self.adapters["remote_gpt4"]
        elif "deepseek-chat" in self.adapters:
            expert = self.adapters["deepseek-chat"]
        elif "deepcoder" in self.adapters:
            expert = self.adapters["deepcoder"]
        else:
            expert = next(iter(self.adapters.values()))
        logger.info(f"外脑协作专家: {expert.model_name}")
        try:
            response = expert.generate(intent.raw_text, task_type=intent.type)
            if isinstance(response, tuple):
                response, _ = response
            self._store_expert_analysis(intent, response, confidence, expert.model_name)
            return response
        except Exception as e:
            logger.error(f"外脑协作失败: {e}")
            return self._normal_generate(intent)

    def _store_expert_analysis(self, intent: Intent, analysis: str, confidence: float, expert_model: str):
        """存储专家分析（为逆向学习预留）"""
        try:
            conn = get_storage_port()._get_conn('data/experience_pool.db')
            conn.execute(
                "INSERT INTO experiences (intent_type, raw_input, plan, model_name, quality_score, user_feedback, success, response, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (intent.type, intent.raw_text, f"expert_collaboration:{expert_model}", expert_model, 0, False, analysis, time.time())
            )
            conn.commit()
            logger.warning(f"已存储专家分析 (置信度: {confidence:.2f})")
        except Exception as e:
            logger.warning(f"存储专家分析失败: {e}")

    def _try_expert_collaboration(self, intent: Intent) -> Optional[str]:
        """尝试外脑协作（仅当置信度极低时）"""
        confidence = self._estimate_self_confidence(intent)
        if confidence < 0.4:
            logger.info(f"自我置信度低({confidence:.2f})，启用外脑协作模式")
            response = self._expert_collaboration(intent, confidence)
            bus.publish("plan_executed", response)
            return response
        return None

    def _try_vector_reuse(self, intent: Intent) -> Optional[str]:
        """尝试向量检索复用"""
        try:
            from core import VECTOR_AVAILABLE, vector_retriever
        except ImportError:
            return None
        if not VECTOR_AVAILABLE:
            return None
        try:
            similar = vector_retriever.find_similar_plan(intent.raw_text, intent.type)
            if similar and similar.get('plan', {}).get('quality_score', 0) >= 70:
                logger.info(f"✓ 复用相似成功案例(相似度:{similar.get('similarity', 0):.2f})")
                response = similar.get('plan', {}).get('response', '')
                if response:
                    bus.publish("plan_executed", response)
                    return response
        except Exception as e:
            logger.error(f"向量检索异常: {e}")
        return None
