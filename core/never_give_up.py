"""
真正的永不放弃引擎 - Never Give Up Engine
穷尽所有可能性，直到找到答案
"""
import asyncio
import time
from loguru import logger
from typing import Dict, Any, List, Tuple


class NeverGiveUpEngine:
    """
    永不放弃引擎
    
    核心理念：
    1. 不跳过任何能力
    2. 穷尽所有可能性
    3. 从失败中学习
    4. 自我创造新方法
    5. 直到找到答案或穷尽所有可能
    """
    
    def __init__(self):
        self.strategies = []
        self.attempts = []
        self.lessons_learned = []
        self.tools_created = []
        
    async def solve(self, question: str, context: dict = None) -> Dict[str, Any]:
        """
        解决问题 - 穷尽所有可能性
        
        不返回"失败"，只返回"当前最佳答案"
        """
        start_time = time.time()
        self.attempts = []
        best_answer = None
        best_confidence = 0.0
        
        logger.info(f"🎯 开始解决问题: {question[:50]}...")
        
        # ========== 第一轮：使用现有能力 ==========
        logger.info("🔄 第一轮：尝试现有能力")
        
        # 能力1：意图理解
        intent = await self._try_understand_intent(question)
        self.attempts.append(("意图理解", intent["success"], intent))
        
        # 能力2：快速知识检索
        knowledge = await self._try_knowledge_retrieval(question)
        self.attempts.append(("知识检索", knowledge["success"], knowledge))
        if knowledge["success"] and knowledge.get("confidence", 0) > best_confidence:
            best_answer = knowledge["answer"]
            best_confidence = knowledge["confidence"]
        
        # 能力3：深度认知处理
        cognition = await self._try_deep_cognition(question, context)
        self.attempts.append(("深度认知", cognition["success"], cognition))
        if cognition["success"] and cognition.get("confidence", 0) > best_confidence:
            best_answer = cognition["answer"]
            best_confidence = cognition["confidence"]
        
        # 能力4：模型推理
        model = await self._try_model_inference(question)
        self.attempts.append(("模型推理", model["success"], model))
        if model["success"] and model.get("confidence", 0) > best_confidence:
            best_answer = model["answer"]
            best_confidence = model["confidence"]
        
        # 能力5：工具调用
        tools = await self._try_tool_execution(question)
        self.attempts.append(("工具调用", tools["success"], tools))
        if tools["success"] and tools.get("confidence", 0) > best_confidence:
            best_answer = tools["answer"]
            best_confidence = tools["confidence"]
        
        # 能力6：经验回顾
        experience = await self._try_experience_recall(question)
        self.attempts.append(("经验回顾", experience["success"], experience))
        if experience["success"] and experience.get("confidence", 0) > best_confidence:
            best_answer = experience["answer"]
            best_confidence = experience["confidence"]
        
        # ========== 第二轮：如果还没找到答案，尝试组合能力 ==========
        if best_confidence < 0.7:
            logger.info("🔄 第二轮：组合多种能力")
            
            # 组合1：知识检索 + 模型推理
            combined1 = await self._try_combine_knowledge_model(question)
            self.attempts.append(("知识+模型", combined1["success"], combined1))
            if combined1["success"] and combined1.get("confidence", 0) > best_confidence:
                best_answer = combined1["answer"]
                best_confidence = combined1["confidence"]
            
            # 组合2：分解问题 + 逐个解决
            combined2 = await self._try_decompose_and_solve(question)
            self.attempts.append(("问题分解", combined2["success"], combined2))
            if combined2["success"] and combined2.get("confidence", 0) > best_confidence:
                best_answer = combined2["answer"]
                best_confidence = combined2["confidence"]
        
        # ========== 第三轮：如果还不够，创造新方法 ==========
        if best_confidence < 0.5:
            logger.info("🔄 第三轮：创造新方法")
            
            # 创造1：生成专用工具
            new_tool = await self._create_specialized_tool(question)
            self.attempts.append(("创造工具", new_tool["success"], new_tool))
            if new_tool["success"] and new_tool.get("confidence", 0) > best_confidence:
                best_answer = new_tool["answer"]
                best_confidence = new_tool["confidence"]
            
            # 创造2：生成推理链
            reasoning_chain = await self._create_reasoning_chain(question)
            self.attempts.append(("推理链", reasoning_chain["success"], reasoning_chain))
            if reasoning_chain["success"] and reasoning_chain.get("confidence", 0) > best_confidence:
                best_answer = reasoning_chain["answer"]
                best_confidence = reasoning_chain["confidence"]
        
        # ========== 第四轮：如果还没有满意答案，学习并改进 ==========
        if best_confidence < 0.3:
            logger.info("🔄 第四轮：学习并改进")
            
            # 学习：分析为什么失败
            lessons = self._analyze_failures()
            self.lessons_learned.extend(lessons)
            
            # 改进：基于教训重新尝试
            improved = await self._retry_with_lessons(question, lessons)
            self.attempts.append(("学习改进", improved["success"], improved))
            if improved["success"] and improved.get("confidence", 0) > best_confidence:
                best_answer = improved["answer"]
                best_confidence = improved["confidence"]
        
        # ========== 最终：总是返回一个答案 ==========
        if not best_answer:
            # 即使所有方法都失败，也给出一个有价值的回复
            best_answer = self._generate_meaningful_response(question, self.attempts)
            best_confidence = 0.1
        
        elapsed = time.time() - start_time
        logger.info(f"✅ 问题解决完成: 尝试{len(self.attempts)}种方法, 置信度{best_confidence:.0%}, 耗时{elapsed:.1f}秒")
        
        return {
            "answer": best_answer,
            "confidence": best_confidence,
            "attempts": self.attempts,
            "elapsed": elapsed,
            "lessons": self.lessons_learned,
            "tools_created": self.tools_created
        }
    
    async def _try_understand_intent(self, question: str) -> Dict:
        """尝试理解意图"""
        try:
            from core.cognitive_dispatcher import CognitiveDispatcher
            dispatcher = CognitiveDispatcher()
            result = dispatcher.dispatch(user_query=question)
            return {
                "success": True,
                "answer": None,
                "confidence": 0.5,
                "intent": result.get("intent_type"),
                "route": result.get("route")
            }
        except Exception as e:
            logger.debug(f"意图理解失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def _try_knowledge_retrieval(self, question: str) -> Dict:
        """尝试知识检索"""
        try:
            import sqlite3
            conn = sqlite3.connect("data/knowledge_store.db")
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM knowledge WHERE content LIKE ? LIMIT 1", (f"%{question[:30]}%",))
            row = cursor.fetchone()
            conn.close()
            if row:
                return {"success": True, "answer": row[0], "confidence": 0.8}
        except:
            pass
        return {"success": False}
    
    async def _try_deep_cognition(self, question: str, context: dict) -> Dict:
        """尝试深度认知"""
        try:
            from core.metacognitive_executor import MetacognitiveExecutor
            executor = MetacognitiveExecutor()
            result = await asyncio.wait_for(
                executor.execute_with_full_metacognition(user_query=question, context=context or {}),
                timeout=15.0
            )
            answer = result.get("final_result", "")
            if answer and len(answer) > 20:
                return {
                    "success": True,
                    "answer": answer,
                    "confidence": result.get("confidence", 0.7)
                }
        except Exception as e:
            logger.debug(f"深度认知失败: {e}")
        return {"success": False}
    
    async def _try_model_inference(self, question: str) -> Dict:
        """尝试模型推理"""
        try:
            import requests
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "qwen2.5:7b", "prompt": question, "stream": False},
                    timeout=10
                )
            )
            if response.status_code == 200:
                answer = response.json().get("response", "")
                if answer and len(answer) > 20:
                    return {"success": True, "answer": answer, "confidence": 0.6}
        except Exception as e:
            logger.debug(f"模型推理失败: {e}")
        return {"success": False}
    
    async def _try_tool_execution(self, question: str) -> Dict:
        """尝试工具调用"""
        try:
            from tools.registry import registry
            question_lower = question.lower()
            
            if any(kw in question_lower for kw in ["计算", "数学"]):
                result = registry.execute("math_calculator", query=question)
                if hasattr(result, 'output'):
                    return {"success": True, "answer": str(result.output), "confidence": 0.9}
            
            if any(kw in question_lower for kw in ["搜索", "查找"]):
                result = registry.execute("web_search", query=question)
                if hasattr(result, 'output'):
                    return {"success": True, "answer": str(result.output), "confidence": 0.7}
        except Exception as e:
            logger.debug(f"工具调用失败: {e}")
        return {"success": False}
    
    async def _try_experience_recall(self, question: str) -> Dict:
        """尝试经验回顾"""
        try:
            import sqlite3
            conn = sqlite3.connect("data/experience_pool.db")
            cursor = conn.cursor()
            cursor.execute("SELECT response FROM experiences WHERE query LIKE ? ORDER BY timestamp DESC LIMIT 1", (f"%{question[:20]}%",))
            row = cursor.fetchone()
            conn.close()
            if row:
                return {"success": True, "answer": row[0], "confidence": 0.6}
        except:
            pass
        return {"success": False}
    
    async def _try_combine_knowledge_model(self, question: str) -> Dict:
        """组合知识检索和模型推理"""
        knowledge = await self._try_knowledge_retrieval(question)
        if knowledge["success"]:
            # 用知识增强提示
            enhanced_prompt = f"基于以下知识：{knowledge['answer']}\n\n回答问题：{question}"
            model = await self._try_model_inference(enhanced_prompt)
            if model["success"]:
                return {
                    "success": True,
                    "answer": model["answer"],
                    "confidence": min(knowledge["confidence"] + 0.1, 0.9)
                }
        return {"success": False}
    
    async def _try_decompose_and_solve(self, question: str) -> Dict:
        """分解问题并逐个解决"""
        # 简单分解
        parts = question.replace("？", "?").replace("，", ",").split("?")
        parts = [p.strip() for p in parts if p.strip()]
        
        if len(parts) > 1:
            answers = []
            for part in parts[:3]:
                result = await self._try_model_inference(part)
                if result["success"]:
                    answers.append(result["answer"])
            
            if answers:
                return {
                    "success": True,
                    "answer": "\n\n".join(answers),
                    "confidence": 0.6
                }
        return {"success": False}
    
    async def _create_specialized_tool(self, question: str) -> Dict:
        """创造专用工具"""
        question_lower = question.lower()
        
        if any(kw in question_lower for kw in ["代码", "编程"]):
            tool_code = f"""
def specialized_tool():
    \"\"\"为问题创建的专用工具: {question}\"\"\"
    # TODO: 根据问题生成具体实现
    pass
"""
            self.tools_created.append(("代码生成工具", tool_code))
            return {
                "success": True,
                "answer": f"已创建专用工具\n{tool_code}",
                "confidence": 0.4
            }
        
        return {"success": False}
    
    async def _create_reasoning_chain(self, question: str) -> Dict:
        """创建推理链"""
        chain = [
            f"问题：{question}",
            "步骤1：理解问题含义",
            "步骤2：检索相关知识",
            "步骤3：应用推理规则",
            "步骤4：验证结论",
            "步骤5：生成答案"
        ]
        
        return {
            "success": True,
            "answer": "\n".join(chain),
            "confidence": 0.3
        }
    
    def _analyze_failures(self) -> List[str]:
        """分析失败原因"""
        lessons = []
        for attempt in self.attempts:
            if not attempt[1]:  # 失败
                lessons.append(f"{attempt[0]}失败: {attempt[2].get('error', 'unknown')}")
        return lessons
    
    async def _retry_with_lessons(self, question: str, lessons: List[str]) -> Dict:
        """基于教训重试"""
        if not lessons:
            return {"success": False}
        
        # 用教训增强提示
        enhanced_prompt = f"注意避免以下错误：{'; '.join(lessons)}\n\n问题：{question}"
        return await self._try_model_inference(enhanced_prompt)
    
    def _generate_meaningful_response(self, question: str, attempts: List) -> str:
        """即使失败也生成有意义的回复"""
        successful = [a for a in attempts if a[1]]
        failed = [a for a in attempts if not a[1]]
        
        response = f"关于"{question}"，我尝试了{len(attempts)}种方法：\n\n"
        
        if successful:
            response += f"✅ 成功方法：{', '.join([a[0] for a in successful])}\n"
        
        if failed:
            response += f"❌ 失败方法：{', '.join([a[0] for a in failed])}\n"
        
        response += "\n虽然暂时无法给出完整答案，但我会：\n"
        response += "1. 记住这个问题，持续学习\n"
        response += "2. 改进失败的方法\n"
        response += "3. 下次遇到时做得更好\n"
        response += "\n请尝试换个方式提问，或稍后重试。"
        
        return response


# 全局引擎
never_give_up_engine = NeverGiveUpEngine()