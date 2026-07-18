import asyncio
from typing import Optional
from loguru import logger
from backend.services.path_handlers._shared import _slow_executor, _fast_executor, _save_to_experience_pool
from backend.services.path_handlers.experience_path import get_experience_context


async def fetch_external_api(query: str, conversation_context: str = "", truth_insights: str = "") -> dict:
    """外部API获取（DeepSeek/OpenAI）— Ollama失败后的第二道防线"""
    try:
        import json as _json
        from pathlib import Path as _Path
        config_file = _Path("config/external_api.json")
        if not config_file.exists():
            return None
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = _json.load(f)
        
        exp_context = get_experience_context(query)
        messages = []
        
        if conversation_context:
            history_lines = conversation_context.split("\n")
            for line in history_lines:
                if line.startswith("用户："):
                    messages.append({"role": "user", "content": line[3:]})
                elif line.startswith("助手："):
                    messages.append({"role": "assistant", "content": line[3:]})
        
        if exp_context:
            messages.append({"role": "system", "content": f"以下是之前对类似问题的回答，请参考并纠正错误：\n{exp_context}"})

        is_factual_query = any(kw in query for kw in [
            "为什么", "是什么", "原理", "原因", "机制", "本质", "如何", "怎么",
            "科学", "物理", "化学", "生物", "天文", "数学", "医学",
            "是真的吗", "对吗", "正确吗", "你确定"
        ])
        if is_factual_query:
            messages.append({"role": "system", "content": "请用第一性原理逐步推理：1.从基本事实出发 2.逐步推导不跳步 3.标注确定性(确定/很可能/可能/推测) 4.考虑反面观点 5.区分事实与推论 6.跨学科检查一致性"})

        if truth_insights:
            messages.append({"role": "system", "content": truth_insights})

        try:
            from core.self.model import get_self_model
            _sm = get_self_model()
            directive = _sm.get_behavioral_directive()
            pm = directive.get("perspective_mode", "companion")
            rs = directive.get("relationship_style", "balanced")
            perspective_hints = {
                "thinking_partner": "你是思考伙伴，不是答案机器。提供多角度分析，指出思维盲点，鼓励用户自己判断。避免直接给结论，而是展示推理过程和不同可能性。",
                "companion": "你是同行者，与用户一起探索。提供有深度的分析，同时尊重用户的思考空间。在给出观点时也提及其他可能的视角。",
                "guide": "你是引导者，用户对你还不够熟悉。提供清晰、有条理的解释，同时温和地引导用户思考更深层的角度。",
            }
            hint = perspective_hints.get(pm, perspective_hints["companion"])
            messages.append({"role": "system", "content": hint})
        except Exception:
            pass

        messages.append({"role": "user", "content": query})
        
        deepseek_key = config.get("deepseek_api_key", "")
        if deepseek_key and not deepseek_key.startswith("●"):
            import requests
            loop = asyncio.get_running_loop()
            try:
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        _slow_executor,
                        lambda: requests.post(
                            "https://api.deepseek.com/v1/chat/completions",
                            headers={"Authorization": f"Bearer {deepseek_key}", "Content-Type": "application/json"},
                            json={
                                "model": "deepseek-chat",
                                "messages": messages,
                                "max_tokens": 4096
                            },
                            timeout=30
                        )
                    ),
                    timeout=45
                )
            except asyncio.TimeoutError:
                logger.warning("DeepSeek run_in_executor超时(45秒)，释放线程池")
                response = None
            if response and response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = result.get("usage", {})
                token_info = {}
                if usage:
                    token_info = {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    }
                if content and len(content) > 20:
                    return {"source": "DeepSeek", "response": content, "quality": 90, "tokens": token_info}
        
        openai_key = config.get("openai_api_key", "")
        if openai_key and not openai_key.startswith("●"):
            import requests
            loop = asyncio.get_running_loop()
            base_url = config.get("openai_base_url", "https://api.openai.com/v1")
            try:
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        _slow_executor,
                        lambda: requests.post(
                            f"{base_url}/chat/completions",
                            headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                            json={
                                "model": config.get("openai_model", "gpt-3.5-turbo"),
                                "messages": messages,
                                "max_tokens": 4096
                            },
                            timeout=30
                        )
                    ),
                    timeout=45
                )
            except asyncio.TimeoutError:
                logger.warning("OpenAI run_in_executor超时(45秒)，释放线程池")
                response = None
            if response and response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = result.get("usage", {})
                token_info = {}
                if usage:
                    token_info = {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    }
                if content and len(content) > 20:
                    return {"source": "OpenAI", "response": content, "quality": 90, "tokens": token_info}
    except Exception as e:
        logger.error(f"外部API调用失败: {e}")
    return None


async def fetch_external_learning(query: str, conversation_context: str = "") -> Optional[dict]:
    """路径F：外部学习器（DuckDuckGo/Wikipedia）"""
    try:
        from infrastructure.external_learners import composite_learner
        if not composite_learner.is_available():
            return None
        results = await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(
                _slow_executor, lambda: composite_learner.learn(query, conversation_context, max_results=4)
            ),
            timeout=25
        )
        if results:
            parts = []
            sources = set()
            for item in results:
                if item.content and len(item.content) > 30:
                    parts.append(item.content)
                    sources.add(item.source)
            if parts:
                source_label = f"外部学习({'+'.join(sorted(sources))})"
                return {"source": source_label, "response": "\n\n".join(parts), "quality": 70}
    except Exception as e:
        logger.error(f"外部学习器异常: {e}")
    return None