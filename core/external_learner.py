"""
外部学习模块 - 主动向搜索引擎和更强AI请教
"""
import json
from core.ports.adapters import get_storage_port
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger
from adapters.llm.ollama_adapter import ollama_chat_request


class ExternalLearner:
    """主动向外部资源学习"""
    
    _UNAVAILABLE_COOLDOWN = 300
    _deepseek_unavailable_until = 0.0
    _ollama_unavailable_until = 0.0
    
    def __init__(self, config: Dict = None, db_path: str = "data/knowledge_store.db"):
        self.config = config or {}
        self.db_path = db_path
        self.search_api_key = self.config.get("search_api_key", "")
        self.search_engine_id = self.config.get("search_engine_id", "")

        # 从external_api.json读取API密钥
        try:
            import json
            with open("config/external_api.json", "r", encoding="utf-8") as f:
                ext_config = json.load(f)
                self.llm_api_key = ext_config.get("deepseek_api_key") or ext_config.get("openai_api_key") or ""
                if ext_config.get("deepseek_api_key"):
                    self.llm_model = "deepseek-chat"
                    self.llm_base_url = "https://api.deepseek.com/v1"
                elif ext_config.get("openai_api_key"):
                    self.llm_model = "gpt-4"
                    self.llm_base_url = "https://api.openai.com/v1"
                else:
                    self.llm_api_key = ""
                    self.llm_model = "gpt-4"
                    self.llm_base_url = "https://api.openai.com/v1"
        except Exception as e:
            logger.warning(f"读取external_api.json失败: {e}，使用默认配置")
            self.llm_api_key = self.config.get("llm_api_key", "")
            self.llm_model = self.config.get("llm_model", "gpt-4")
            self.llm_base_url = self.config.get("llm_base_url", "https://api.openai.com/v1")

        Path(db_path).parent.mkdir(exist_ok=True)
        logger.info(f"外部学习器已初始化 (API: {'DeepSeek' if 'deepseek' in self.llm_base_url else 'OpenAI' if self.llm_api_key else 'None'})")
    
    def search_web(self, query: str, num_results: int = 3) -> List[str]:
        """搜索引擎查询 — 优先隐身搜索(TLS指纹伪装)，降级到多源搜索，再降级到本地"""

        try:
            from infrastructure.stealth_search import search_web_stealthy
            stealth_results = search_web_stealthy(query, max_results=num_results)
            if stealth_results:
                return [f"[{r['source']}] {r['title']}: {r['snippet']}" for r in stealth_results]
        except Exception as e:
            logger.error(f"隐身搜索失败: {e}")
        
        try:
            from infrastructure.external_learners import composite_learner
            if composite_learner.is_available():
                results = composite_learner.learn(query, max_results=num_results)
                if results:
                    return [f"[{r.source}] {r.content}" for r in results]
        except Exception as e:
            logger.error(f"composite_learner搜索失败: {e}")
        
        if not self.search_api_key:
            logger.warning("外部搜索不可用，尝试本地知识库降级")
            local_results = self._search_local_knowledge(query)
            if local_results:
                return local_results
            
            logger.warning("本地知识库也无结果，尝试问本地模型")
            llm_answer = self.ask_llm(
                f"请简要回答以下问题，列出关键事实：{query}",
                system_prompt="你是一个知识助手，简洁准确地回答问题。"
            )
            if llm_answer:
                return [f"[本地推理] {llm_answer[:500]}"]
            
            return []
        
        try:
            import requests
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.search_api_key,
                "cx": self.search_engine_id,
                "q": query,
                "num": num_results
            }
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get("items", []):
                    results.append(f"{item.get('title', '')}: {item.get('snippet', '')}")
                return results
            else:
                logger.error(f"搜索API调用失败: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []
    
    def _search_local_knowledge(self, query: str) -> List[str]:
        """从本地知识库和经验池搜索"""
        results = []
        
        try:
            for db_name, label in [("data/knowledge_base.db", "知识库"), ("data/experience_pool.db", "经验池")]:
                try:
                    db = get_storage_port(db_name)
                    tables = [row[0] for row in db.query("SELECT name FROM sqlite_master WHERE type='table'")]
                    
                    if "knowledge_entries" in tables:
                        rows = db.query("SELECT content, source FROM knowledge_entries WHERE content LIKE ? LIMIT 3", (f"%{query[:20]}%",))
                        for row in rows:
                            if row[0] and len(row[0]) > 20:
                                results.append(f"[{label}] {row[0][:300]}")
                    
                    elif "experiences" in tables:
                        rows = db.query("SELECT raw_input, response FROM experiences WHERE raw_input LIKE ? AND success=1 ORDER BY timestamp DESC LIMIT 3", (f"%{query[:20]}%",))
                        for row in rows:
                            if row[1] and len(row[1]) > 20:
                                results.append(f"[{label}] {row[1][:300]}")
                except Exception:
                    logger.warning("操作降级跳过")
        except Exception:
            logger.warning("操作降级跳过")
        
        return results[:5]
    
    def ask_llm(self, prompt: str, system_prompt: str = None) -> str:
        """调用更强大的LLM获取答案或反思 — 优先外部API，降级到本地Ollama"""
        
        _now = __import__('time').time()
        
        if self.llm_api_key and _now > self._deepseek_unavailable_until:
            try:
                import requests
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                logger.info(f"调用外部LLM: {self.llm_base_url}, 模型: {self.llm_model}")
                response = requests.post(
                    f"{self.llm_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.llm_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.llm_model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 2000
                    },
                    timeout=15,
                    verify=False
                )
                logger.info(f"外部LLM响应状态码: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                elif response.status_code in (400, 401, 403):
                    self._deepseek_unavailable_until = _now + self._UNAVAILABLE_COOLDOWN
                    logger.warning(f"外部LLM认证/配置错误({response.status_code})，标记不可用{self._UNAVAILABLE_COOLDOWN}s")
                else:
                    logger.error(f"外部LLM失败({response.status_code})，尝试本地Ollama")
            except Exception as e:
                logger.error(f"外部LLM失败: {e}，尝试本地Ollama")
        elif self.llm_api_key:
            logger.debug(f"外部LLM标记不可用，剩余{self._deepseek_unavailable_until - _now:.0f}s")

        if _now > self._ollama_unavailable_until:
            logger.info(f"降级到本地Ollama")
            result = self._ask_local_ollama(prompt, system_prompt)
            if result:
                return result
            self._ollama_unavailable_until = _now + self._UNAVAILABLE_COOLDOWN
            logger.warning(f"Ollama不可用，标记不可用{self._UNAVAILABLE_COOLDOWN}s")
        
        return json.dumps({
            "intent": "无可用LLM",
            "common_mistakes": ["外部API和本地Ollama均不可用"],
            "parsing_strategies": ["请配置DEEPSEEK_API_KEY或启动Ollama"],
            "experience_notes": "无法获取深度分析"
        }, ensure_ascii=False)
    
    def _ask_local_ollama(self, prompt: str, system_prompt: str = None) -> str:
        """使用本地Ollama模型进行推理"""
        try:
            model = self._get_ollama_model()
            if not model:
                return json.dumps({
                    "intent": "无可用LLM",
                    "common_mistakes": ["未配置外部API且Ollama不可用"],
                    "parsing_strategies": ["请配置DEEPSEEK_API_KEY或启动Ollama"],
                    "experience_notes": "无法获取深度分析"
                }, ensure_ascii=False)
            
            result = ollama_chat_request(
                base_url="http://localhost:11434",
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                timeout=15
            )
            
            content = result.get("content", "")
            if content:
                return content
            else:
                logger.debug("Ollama推理失败: 返回空内容")
        except Exception as e:
            logger.error(f"Ollama推理失败: {e}")
        
        return ""
    
    def _get_ollama_model(self) -> str:
        """获取可用的Ollama模型"""
        try:
            import requests
            tags = requests.get("http://localhost:11434/api/tags", timeout=3)
            available = [m["name"] for m in tags.json().get("models", [])]
            priority = ["gemma-4-12B:latest", "qwen2.5-coder:7b", "qwen2.5:7b", "deepcoder:latest"]
            for m in priority:
                for a in available:
                    if m in a or a.startswith(m.split(":")[0]):
                        return a
            if available:
                return available[0]
        except Exception:
            logger.warning("操作降级跳过")
        return ""
    
    def analyze_conversation_parsing(self, user_input: str, context: str) -> Dict[str, Any]:
        """询问更强AI：这个对话应该如何解析？有什么解析经验？"""
        
        prompt = f"""你是一个对话系统分析专家。以下是用户输入和对话上下文：

用户输入：{user_input}

上下文：{context}

请回答以下问题（用JSON格式输出）：
1. 用户真正的意图是什么？可能隐藏的需求？
2. 解析这个对话时容易犯哪些错误？
3. 针对这类对话，有哪些通用的解析策略或经验？
4. 有什么经验教训可以积累？

输出格式：
{{
  "intent": "用户的真实意图",
  "hidden_needs": ["隐藏需求1", "隐藏需求2"],
  "common_mistakes": ["错误1", "错误2"],
  "parsing_strategies": ["策略1", "策略2"],
  "experience_notes": "经验总结"
}}
"""
        
        system_prompt = "你是一个专业的对话分析专家，擅长理解用户意图并总结经验教训。请用JSON格式输出分析结果。"
        
        response = self.ask_llm(prompt, system_prompt)
        
        try:
            result = json.loads(response)
            return result
        except Exception:
            return {
                "intent": "解析失败",
                "hidden_needs": [],
                "common_mistakes": ["JSON解析失败"],
                "parsing_strategies": ["请检查LLM输出格式"],
                "experience_notes": response
            }
    
    def deep_research(self, question: str) -> Dict[str, Any]:
        """深入研究某个问题"""
        
        prompt = f"""请深入研究以下问题，并提供详细的分析：

问题：{question}

请提供：
1. 问题的核心是什么？
2. 有哪些常见的解决方案？
3. 有哪些陷阱和注意事项？
4. 最佳实践是什么？
5. 有哪些可以学习的经验？

用JSON格式输出。
"""
        
        response = self.ask_llm(prompt)
        
        try:
            return json.loads(response)
        except Exception:
            return {
                "question": question,
                "analysis": response,
                "source": "external_llm"
            }
    
    def learn_from_external(self, user_input: str, context: str, 
                            trigger_reason: str = "unknown") -> List[Dict]:
        """
        主入口：从外部学习并返回新增的知识点列表
        
        策略：
        1. 多源搜索（arXiv/极客公园/知乎/CSDN等）
        2. 问自己/问模型（本地Ollama或外部API）
        3. 综合分析+沉淀见解
        """
        new_items = []
        timestamp = datetime.now().isoformat()
        
        logger.info(f"触发外部学习，原因: {trigger_reason}")
        
        search_results = self.search_web(user_input)
        if search_results:
            search_item = {
                "question": f"关于'{user_input[:50]}'的多源搜索结果",
                "answer": "\n".join(search_results),
                "source": "multi_source_search",
                "knowledge_type": "external",
                "metadata": json.dumps({
                    "method": "multi_source_search",
                    "timestamp": timestamp,
                    "trigger_reason": trigger_reason
                }, ensure_ascii=False)
            }
            new_items.append(search_item)
            logger.info(f"从多源搜索获取 {len(search_results)} 条结果")
        
        try:
            parsing_insight = self.analyze_conversation_parsing(user_input, context)
            if parsing_insight and parsing_insight.get("intent") != "无可用LLM":
                parsing_item = {
                    "question": f"如何解析：{user_input[:50]}",
                    "answer": json.dumps(parsing_insight, ensure_ascii=False),
                    "source": "llm_analysis",
                    "knowledge_type": "meta",
                    "metadata": json.dumps({
                        "method": "llm_analysis",
                        "timestamp": timestamp,
                        "trigger_reason": trigger_reason,
                        "type": "parsing_experience"
                    }, ensure_ascii=False)
                }
                new_items.append(parsing_item)
                logger.info("从LLM获取对话解析经验")
        except Exception as e:
            logger.error(f"LLM分析失败: {e}")
        
        try:
            synthesis = self._synthesize_insights(user_input, search_results)
            if synthesis:
                synthesis_item = {
                    "question": f"综合分析：{user_input[:50]}",
                    "answer": synthesis,
                    "source": "self_synthesis",
                    "knowledge_type": "synthesis",
                    "metadata": json.dumps({
                        "method": "self_synthesis",
                        "timestamp": timestamp,
                        "trigger_reason": trigger_reason,
                        "search_result_count": len(search_results)
                    }, ensure_ascii=False)
                }
                new_items.append(synthesis_item)
                logger.info("完成自主综合分析")
        except Exception as e:
            logger.error(f"综合分析失败: {e}")
        
        return new_items
    
    def _synthesize_insights(self, question: str, search_results: List[str]) -> str:
        """综合搜索结果，添加自己的见解"""
        if not search_results:
            return ""
        
        results_text = "\n".join(search_results[:5])
        prompt = f"""基于以下多源搜索结果，请综合分析问题并给出有价值的见解：

问题：{question}

搜索结果：
{results_text}

请：
1. 提炼核心观点（2-3条）
2. 指出不同来源的共识与分歧
3. 给出你自己的分析和建议
4. 标注哪些观点需要进一步验证

用简洁的中文回答。"""
        
        response = self.ask_llm(prompt)
        if response and len(response) > 50:
            return response[:1000]
        return ""
    
    def learn_and_integrate(self, user_input: str, context: str,
                           trigger_reason: str = "unknown") -> Dict:
        """学习并直接集成到知识库"""
        items = self.learn_from_external(user_input, context, trigger_reason)
        saved_count = self.save_to_knowledge_base(items)
        
        return {
            "items": items,
            "saved_count": saved_count,
            "trigger_reason": trigger_reason
        }
    
    def save_to_knowledge_base(self, items: List[Dict]) -> int:
        """保存外部学习结果到知识库"""
        
        saved_count = 0
        db = get_storage_port(self.db_path)
        for item in items:
            try:
                question_hash = hashlib.md5(item["question"].lower().encode()).hexdigest()
                
                db.execute('''
                    INSERT OR REPLACE INTO knowledge_items 
                    (question_hash, question, answer, source, knowledge_type, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    question_hash,
                    item["question"],
                    item["answer"],
                    item["source"],
                    item.get("knowledge_type", "external"),
                    item.get("metadata", "{}"),
                    datetime.now().isoformat()
                ), commit=True)
                saved_count += 1
            except Exception as e:
                logger.error(f"保存知识失败: {e}")
        

        if saved_count > 0:
            logger.info(f"保存 {saved_count} 条外部学习知识")
        
        return saved_count


def should_trigger_external_learning(user_input: str, response_text: str = None, 
                                      confidence: float = 1.0, 
                                      knowledge_count: int = 0) -> tuple:
    """
    判断是否应该触发外部学习
    返回: (should_trigger, reason)
    """
    
    deep_keywords = [
        "深入", "详细解释", "为什么", "原理", "经验", 
        "怎么解析", "如何成长", "学习机制", "不懂",
        "请教", "研究", "分析一下", "帮我理解"
    ]
    if any(kw in user_input for kw in deep_keywords):
        return True, "用户要求深度解析"
    
    uncertainty_phrases = [
        "可能", "不确定", "我不清楚", "不太确定",
        "也许", "大概", "应该是", "我不太了解"
    ]
    if response_text and any(phrase in response_text for phrase in uncertainty_phrases):
        return True, "系统置信度低"
    
    if confidence < 0.5:
        return True, f"置信度过低({confidence:.2f})"
    
    if knowledge_count == 0:
        return True, "知识库无相关条目"
    
    meta_keywords = [
        "你是如何学习", "你能学习吗", "你的学习机制",
        "你会成长吗", "如何改进", "元认知",
        "学习成长", "自我学习"
    ]
    if any(kw in user_input for kw in meta_keywords):
        return True, "元认知问题"
    
    return False, ""


external_learner = ExternalLearner()