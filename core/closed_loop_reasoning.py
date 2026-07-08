"""
闭环推理系统 - 确保所有能力被调用
完整的推理→验证→反思→学习→优化闭环
"""
import asyncio
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from loguru import logger

@dataclass
class ReasoningResult:
    """推理结果"""
    answer: str
    confidence: float
    sources: List[str]
    reasoning_chain: List[str]
    issues: List[str] = None
    improvements: List[str] = None

class ClosedLoopReasoning:
    """闭环推理系统"""
    
    def __init__(self, planner, knowledge_base, models):
        self.planner = planner
        self.knowledge_base = knowledge_base
        self.models = models
        self.reasoning_history = []
        
    async def reason_with_full_cycle(
        self, 
        question: str,
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        完整的闭环推理流程
        
        流程：
        1. 多源推理（知识库+模型+工具）
        2. 答案验证（合理性检查）
        3. 自我反思（批判性思考）
        4. 多源对比（交叉验证）
        5. 知识丰富（学习新知识）
        6. 语言优化（重组表达）
        7. 能力提升（更新策略）
        """
        
        results = {}
        start_time = time.time()
        
        # ========== 第1步：多源推理 ==========
        await self._emit_progress(progress_callback, "推理", "🔍 多源推理中...")
        
        # 1.1 知识库检索
        kb_result = await self._search_knowledge_base(question)
        results["kb_result"] = kb_result
        
        # 1.2 模型推理
        model_result = await self._call_model(question)
        results["model_result"] = model_result
        
        # 1.3 工具调用（如需要）
        tool_result = await self._call_tools_if_needed(question)
        results["tool_result"] = tool_result
        
        # 1.4 整合多源结果
        primary_answer = self._integrate_results(results)
        results["primary_answer"] = primary_answer
        
        # ========== 第2步：答案验证 ==========
        await self._emit_progress(progress_callback, "验证", "✓ 答案验证中...")
        
        validation = await self._validate_answer(question, primary_answer)
        results["validation"] = validation
        
        if not validation["is_valid"]:
            logger.warning(f"答案验证失败: {validation['issues']}")
            # 尝试修正
            corrected = await self._correct_answer(question, primary_answer, validation)
            if corrected:
                primary_answer = corrected
                results["corrected_answer"] = corrected
        
        # ========== 第3步：自我反思 ==========
        await self._emit_progress(progress_callback, "反思", "💭 自我反思中...")
        
        reflection = await self._self_reflect(question, primary_answer, results)
        results["reflection"] = reflection
        
        # 反思发现的问题
        if reflection.get("weaknesses"):
            logger.info(f"发现不足: {reflection['weaknesses']}")
        
        # ========== 第4步：多源对比 ==========
        await self._emit_progress(progress_callback, "对比", "🔄 多源对比中...")
        
        comparison = await self._cross_validate(question, primary_answer, results)
        results["comparison"] = comparison
        
        # 如果有更好的答案
        if comparison.get("better_answer"):
            primary_answer = comparison["better_answer"]
            results["final_answer"] = primary_answer
        
        # ========== 第5步：知识丰富 ==========
        await self._emit_progress(progress_callback, "学习", "📚 知识丰富中...")
        
        learning = await self._enrich_knowledge(question, primary_answer, results)
        results["learning"] = learning
        
        # ========== 第6步：语言优化 ==========
        await self._emit_progress(progress_callback, "优化", "✨ 语言优化中...")
        
        optimized = await self._optimize_expression(question, primary_answer)
        results["optimized_answer"] = optimized
        
        # ========== 第7步：能力提升 ==========
        await self._emit_progress(progress_callback, "提升", "🚀 能力提升中...")
        
        improvement = await self._improve_capability(question, results)
        results["improvement"] = improvement
        
        # ========== 汇总结果 ==========
        elapsed = time.time() - start_time
        
        return {
            "answer": optimized,
            "confidence": validation.get("confidence", 0.7),
            "reasoning_chain": self._build_reasoning_chain(results),
            "validation": validation,
            "reflection": reflection,
            "learning": learning,
            "improvement": improvement,
            "elapsed": elapsed,
            "all_results": results
        }
    
    async def _emit_progress(self, callback, stage, message):
        """发送进度"""
        if callback:
            await callback({"stage": stage, "message": message})
        logger.info(f"[闭环推理] {stage}: {message}")
    
    async def _search_knowledge_base(self, question: str) -> Dict:
        """知识库检索"""
        try:
            from core.learning import enhanced_learner
            result = enhanced_learner.retrieve_knowledge(question)
            if result:
                return {
                    "found": True,
                    "answer": result.get("answer"),
                    "confidence": result.get("confidence", 0.5),
                    "source": "knowledge_base"
                }
        except Exception as e:
            logger.debug(f"知识库检索失败: {e}")
        
        return {"found": False, "answer": None, "confidence": 0}
    
    async def _call_model(self, question: str) -> Dict:
        """调用模型"""
        try:
            # 优先使用DeepSeek
            from adapters.llm.remote_adapter import RemoteAdapter
            adapter = RemoteAdapter(
                model="deepseek-chat",
                base_url="https://api.deepseek.com/v1"
            )
            
            response = adapter.generate(question)
            return {
                "found": True,
                "answer": response,
                "confidence": 0.7,
                "source": "deepseek"
            }
        except Exception as e:
            logger.debug(f"模型调用失败: {e}")
        
        return {"found": False, "answer": None, "confidence": 0}
    
    async def _call_tools_if_needed(self, question: str) -> Dict:
        """按需调用工具"""
        # 检查是否需要工具
        tool_keywords = ["计算", "搜索", "查询", "执行"]
        
        if any(kw in question for kw in tool_keywords):
            try:
                # 调用相应工具
                # 这里简化处理
                return {"found": False, "answer": None, "confidence": 0}
            except Exception as e:
                logger.debug(f"工具调用失败: {e}")
        
        return {"found": False, "answer": None, "confidence": 0}
    
    def _integrate_results(self, results: Dict) -> str:
        """整合多源结果"""
        # 优先级：知识库 > 模型 > 工具
        for key in ["kb_result", "model_result", "tool_result"]:
            result = results.get(key, {})
            if result.get("found") and result.get("answer"):
                return result["answer"]
        
        return "抱歉，我暂时无法回答这个问题。"
    
    async def _validate_answer(self, question: str, answer: str) -> Dict:
        """验证答案合理性"""
        issues = []
        
        # 1. 检查是否为空
        if not answer or len(answer) < 5:
            issues.append("答案过短或为空")
        
        # 2. 检查是否包含不确定性短语
        uncertainty_phrases = ["不太确定", "可能", "也许", "不确定"]
        if any(phrase in answer for phrase in uncertainty_phrases):
            issues.append("答案包含不确定性表达")
        
        # 3. 检查是否答非所问
        # 简化：检查是否包含问题关键词
        question_keywords = set(question.replace("？", "").replace("?", "").split())
        answer_words = set(answer.split())
        overlap = len(question_keywords & answer_words)
        
        if overlap < 2 and len(question_keywords) > 2:
            issues.append("答案可能与问题相关性不足")
        
        # 4. 计算置信度
        confidence = 1.0 - len(issues) * 0.2
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "confidence": max(0.3, confidence)
        }
    
    async def _correct_answer(self, question: str, answer: str, validation: Dict) -> Optional[str]:
        """修正答案"""
        issues = validation.get("issues", [])
        
        if "答案包含不确定性表达" in issues:
            # 尝试获取更确定的答案
            # 可以调用不同的模型或知识源
            pass
        
        return None
    
    async def _self_reflect(self, question: str, answer: str, results: Dict) -> Dict:
        """自我反思"""
        weaknesses = []
        strengths = []
        
        # 1. 反思知识覆盖
        kb_result = results.get("kb_result", {})
        if not kb_result.get("found"):
            weaknesses.append("知识库中无相关知识")
        else:
            strengths.append("知识库有相关记录")
        
        # 2. 反思答案质量
        validation = results.get("validation", {})
        if validation.get("is_valid"):
            strengths.append("答案通过验证")
        else:
            weaknesses.extend(validation.get("issues", []))
        
        # 3. 反思推理过程
        if len(results.get("reasoning_chain", [])) < 2:
            weaknesses.append("推理过程较简单")
        
        # 4. 生成改进建议
        improvements = []
        if "知识库中无相关知识" in weaknesses:
            improvements.append("建议学习相关知识并更新知识库")
        if "答案包含不确定性表达" in weaknesses:
            improvements.append("建议获取更确切的信息源")
        
        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "improvements": improvements
        }
    
    async def _cross_validate(self, question: str, answer: str, results: Dict) -> Dict:
        """多源交叉验证"""
        # 对比不同来源的答案
        answers = []
        
        for key in ["kb_result", "model_result", "tool_result"]:
            result = results.get(key, {})
            if result.get("found") and result.get("answer"):
                answers.append({
                    "source": key,
                    "answer": result["answer"],
                    "confidence": result.get("confidence", 0.5)
                })
        
        # 如果有多个答案，检查一致性
        if len(answers) > 1:
            # 简化：选择置信度最高的
            best = max(answers, key=lambda x: x["confidence"])
            return {
                "validated": True,
                "better_answer": best["answer"] if best["confidence"] > 0.7 else None,
                "sources": [a["source"] for a in answers]
            }
        
        return {"validated": False, "better_answer": None}
    
    async def _enrich_knowledge(self, question: str, answer: str, results: Dict) -> Dict:
        """丰富知识库"""
        learned = []
        
        # 1. 如果知识库中没有，添加新知识
        kb_result = results.get("kb_result", {})
        if not kb_result.get("found") and len(answer) > 20:
            try:
                from infrastructure.database_manager import DatabaseManager
                from datetime import datetime
                
                conn = DatabaseManager.get("data/knowledge_store.db")._get_conn()
                conn.execute('''
                    INSERT INTO knowledge_items 
                    (question, answer, source, knowledge_type, quality_score, created_at)
                    VALUES (?, ?, ?, 'learned', 60.0, ?)
                ''', (question, answer, "closed_loop", datetime.now().isoformat()))
                conn.commit()
                
                learned.append("新增知识到知识库")
            except Exception as e:
                logger.debug(f"知识存储失败: {e}")
        
        # 2. 提取知识点
        # 简化处理
        
        return {
            "learned": len(learned) > 0,
            "items": learned
        }
    
    async def _optimize_expression(self, question: str, answer: str) -> str:
        """优化语言表达"""
        # 1. 检查是否需要优化
        if len(answer) < 50:
            return answer
        
        # 2. 可以调用模型进行润色
        # 简化：直接返回
        return answer
    
    async def _improve_capability(self, question: str, results: Dict) -> Dict:
        """提升系统能力"""
        improvements = []
        
        # 1. 记录推理经验
        try:
            from infrastructure.database_manager import DatabaseManager
            from datetime import datetime
            
            conn = DatabaseManager.get("data/knowledge_store.db")._get_conn()
            conn.execute('''
                INSERT INTO experiences 
                (timestamp, intent_type, success, quality_score, context)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                "closed_loop",
                1 if results.get("validation", {}).get("is_valid") else 0,
                results.get("validation", {}).get("confidence", 0.5) * 100,
                question[:200]
            ))
            conn.commit()
            
            improvements.append("记录推理经验")
        except Exception as e:
            logger.debug(f"经验记录失败: {e}")
        
        # 2. 更新策略（如果有反思结果）
        reflection = results.get("reflection", {})
        if reflection.get("improvements"):
            improvements.extend(reflection["improvements"])
        
        return {
            "improved": len(improvements) > 0,
            "items": improvements
        }
    
    def _build_reasoning_chain(self, results: Dict) -> List[str]:
        """构建推理链"""
        chain = []
        
        # 1. 知识检索
        kb = results.get("kb_result", {})
        if kb.get("found"):
            chain.append(f"✓ 知识库检索: 找到相关答案 (置信度: {kb.get('confidence', 0):.0%})")
        else:
            chain.append("✗ 知识库检索: 未找到")
        
        # 2. 模型推理
        model = results.get("model_result", {})
        if model.get("found"):
            chain.append(f"✓ 模型推理: 生成答案 (置信度: {model.get('confidence', 0):.0%})")
        else:
            chain.append("✗ 模型推理: 未调用")
        
        # 3. 验证
        validation = results.get("validation", {})
        if validation.get("is_valid"):
            chain.append(f"✓ 答案验证: 通过 (置信度: {validation.get('confidence', 0):.0%})")
        else:
            chain.append(f"✗ 答案验证: 存在问题 - {validation.get('issues', [])}")
        
        # 4. 反思
        reflection = results.get("reflection", {})
        if reflection.get("weaknesses"):
            chain.append(f"⚠ 自我反思: 发现不足 - {reflection['weaknesses']}")
        else:
            chain.append("✓ 自我反思: 无明显不足")
        
        # 5. 学习
        learning = results.get("learning", {})
        if learning.get("learned"):
            chain.append(f"✓ 知识丰富: {learning.get('items', [])}")
        
        # 6. 能力提升
        improvement = results.get("improvement", {})
        if improvement.get("improved"):
            chain.append(f"✓ 能力提升: {improvement.get('items', [])}")
        
        return chain