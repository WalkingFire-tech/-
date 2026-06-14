"""
外部学习模块 - 主动向搜索引擎和更强AI请教
"""
import json
import sqlite3
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger


class ExternalLearner:
    """主动向外部资源学习"""
    
    def __init__(self, config: Dict = None, db_path: str = "data/knowledge_store.db"):
        self.config = config or {}
        self.db_path = db_path
        self.search_api_key = self.config.get("search_api_key", "")
        self.search_engine_id = self.config.get("search_engine_id", "")
        self.llm_api_key = self.config.get("llm_api_key", "")
        self.llm_model = self.config.get("llm_model", "gpt-4")
        self.llm_base_url = self.config.get("llm_base_url", "https://api.openai.com/v1")
        
        Path(db_path).parent.mkdir(exist_ok=True)
        logger.info("外部学习器已初始化")
    
    def search_web(self, query: str, num_results: int = 3) -> List[str]:
        """搜索引擎查询（模拟或真实调用）"""
        
        if not self.search_api_key:
            logger.warning("未配置搜索引擎API，返回模拟结果")
            return [
                f"[模拟搜索] 关于 '{query}' 的背景资料：",
                f"1. 这是一个技术概念，需要更深入的研究",
                f"2. 建议配置真实搜索引擎API以获取准确信息",
                f"提示：在环境变量中设置 SEARCH_API_KEY 和 SEARCH_ENGINE_ID"
            ]
        
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
    
    def ask_llm(self, prompt: str, system_prompt: str = None) -> str:
        """调用更强大的LLM获取答案或反思"""
        
        if not self.llm_api_key:
            logger.warning("未配置LLM API，返回模拟结果")
            return json.dumps({
                "intent": "需要配置真实LLM API",
                "common_mistakes": ["未配置API密钥"],
                "parsing_strategies": ["请在环境变量中设置 LLM_API_KEY"],
                "experience_notes": "当前为模拟模式，无法获得真实的深度分析"
            }, ensure_ascii=False)
        
        try:
            import requests
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
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
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"LLM API调用失败: {response.status_code}")
                return ""
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
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
        except:
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
        except:
            return {
                "question": question,
                "analysis": response,
                "source": "external_llm"
            }
    
    def learn_from_external(self, user_input: str, context: str, 
                            trigger_reason: str = "unknown") -> List[Dict]:
        """
        主入口：从外部学习并返回新增的知识点列表
        """
        new_items = []
        timestamp = datetime.now().isoformat()
        
        logger.info(f"触发外部学习，原因: {trigger_reason}")
        
        try:
            search_results = self.search_web(user_input)
            if search_results:
                search_item = {
                    "question": f"关于'{user_input[:50]}'的搜索结果",
                    "answer": "\n".join(search_results),
                    "source": "external_search",
                    "knowledge_type": "external",
                    "metadata": json.dumps({
                        "method": "web_search",
                        "timestamp": timestamp,
                        "trigger_reason": trigger_reason
                    }, ensure_ascii=False)
                }
                new_items.append(search_item)
                logger.info(f"从搜索引擎获取 {len(search_results)} 条结果")
        except Exception as e:
            logger.error(f"搜索学习失败: {e}")
        
        try:
            parsing_insight = self.analyze_conversation_parsing(user_input, context)
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
        
        return new_items
    
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
        with sqlite3.connect(self.db_path) as conn:
            for item in items:
                try:
                    question_hash = hashlib.md5(item["question"].lower().encode()).hexdigest()
                    
                    conn.execute('''
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
                    ))
                    saved_count += 1
                except Exception as e:
                    logger.error(f"保存知识失败: {e}")
            
            conn.commit()
        
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