"""
搜索能力 mixin — Bing/Wikipedia/DDGS 多源搜索
"""
from typing import Optional, List, Dict
from loguru import logger
from infrastructure.event_bus import bus
from core.services.intent_parser import Intent


class SearchEngineMixin:
    """搜索能力：Bing/Wikipedia/DDGS 多源搜索"""

    def _init_search(self):
        self._search_cache = {}
        self._search_timeout = self.config.get("search_timeout", 5.0)

    def _try_search_enhanced_answer(self, intent: Intent) -> Optional[str]:
        search_results = None
        search_source = None
        try:
            search_results = self._search_bing(intent.raw_text, max_results=5)
            if search_results:
                search_source = "Bing"
                logger.info(f"✅ Bing搜索成功: {len(search_results)}条")
        except Exception as e:
            logger.error(f"Bing搜索失败: {e}")
        if not search_results:
            try:
                from ddgs import DDGS
                import threading
                def search_task():
                    try:
                        with DDGS() as ddgs:
                            search_results = list(ddgs.text(intent.raw_text, max_results=5))
                    except Exception:
                        logger.warning("操作降级跳过")
                thread = threading.Thread(target=search_task, daemon=True)
                thread.start()
                thread.join(timeout=15)
                if not thread.is_alive() and search_results:
                    search_source = "DDGS"
                    logger.info(f"✅ DDGS搜索成功: {len(search_results)}条")
            except Exception as e:
                logger.error(f"DDGS搜索失败: {e}")
        if not search_results:
            try:
                search_results = self._search_wikipedia(intent.raw_text, max_results=5)
                if search_results:
                    search_source = "Wikipedia"
                    logger.info(f"✅ Wikipedia搜索成功: {len(search_results)}条")
            except Exception as e:
                logger.error(f"Wikipedia搜索失败: {e}")
        if not search_results:
            logger.warning("⚠️ 所有搜索源均失败")
            return None
        try:
            context = f"=== 外部知识（来源：{search_source}） ===\n"
            for i, sr in enumerate(search_results, 1):
                context += f"{i}. {sr.get('title', '')}\n   {sr.get('body', '')[:200]}\n"
            context += "===\n\n"
            history = self._get_recent_context()
            if intent.type == "verification":
                base_prompt = self._build_prompt(intent)
                full_prompt = f"{history}\n{context}{base_prompt}" if history else f"{context}{base_prompt}"
            else:
                full_prompt = f"{history}\n{context}请基于以上外部知识，回答用户的问题：{intent.raw_text}" if history else f"{context}请基于以上外部知识，回答用户的问题：{intent.raw_text}"
            model = self._select_model(intent)
            response = model.generate(full_prompt, task_type=intent.type)
            if isinstance(response, tuple):
                response, _ = response
            logger.info(f"✅ 搜索增强回答: {search_source} + 模型")
            bus.publish("plan_executed", response)
            return response
        except Exception as e:
            logger.error(f"模型组织失败: {e}")
            if search_results:
                response = f"📚 根据{search_source}搜索结果，关于「{intent.raw_text}」：\n\n"
                for i, sr in enumerate(search_results, 1):
                    response += f"**{i}. {sr.get('title', '')}**\n{sr.get('body', '')[:300]}\n\n"
                logger.info(f"✅ 纯搜索模式回答: {search_source} {len(search_results)}条")
                bus.publish("plan_executed", response)
                return response
            return None

    def _search_bing(self, query: str, max_results: int = 5) -> Optional[List[Dict]]:
        import requests, re
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                   "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}
        url = f"https://www.bing.com/search?q={requests.utils.quote(query)}"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return None
            results = []
            pattern = r'<li class="b_algo"[^>]*>.*?<h2><a href="([^"]*)"[^>]*>(.*?)</a></h2>.*?<div class="b_caption".*?<p>(.*?)</p>'
            for href, title, body in re.findall(pattern, resp.text, re.DOTALL)[:max_results]:
                results.append({"title": re.sub(r'<[^>]+>', '', title).strip(),
                                "href": href,
                                "body": re.sub(r'<[^>]+>', '', body).strip()[:300]})
            return results if results else None
        except Exception as e:
            logger.error(f"Bing搜索异常: {e}")
            return None

    def _search_wikipedia(self, query: str, max_results: int = 5) -> Optional[List[Dict]]:
        logger.debug("Wikipedia搜索已禁用（网络不可用）")
        return None
