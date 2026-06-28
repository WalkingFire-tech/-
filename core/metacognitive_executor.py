"""
元认知执行引擎 (Metacognitive Executor Engine)
基于认知科学、控制论、系统论的完整重构

核心范式转变：
- 从"提示-回复"转变为"感知→规划→执行→验证→沉淀"
- 从System 1（快思考）升级为System 2（慢思考）
- 从开环控制升级为闭环控制
"""
import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from loguru import logger

class MetacognitiveExecutor:
    """
    元认知执行引擎 - 强制闭环的神经反射弧
    
    跨学科理论基础：
    - 认知科学：双重加工理论（System 1 vs System 2）
    - 控制论：闭环控制（传感器→比较器→执行器→反馈）
    - 计算机架构：冯·诺依曼瓶颈（程序与数据的分离）
    - 生物学：本体感觉（Proprioception）
    """
    
    def __init__(self):
        self.capability_cache = None
        self.metacognitive_templates = None
        self.execution_history = []
        
    async def execute_with_full_metacognition(
        self,
        user_query: str,
        context: Dict = None
    ) -> Dict[str, Any]:
        """
        完整的元认知执行流程
        
        阶段0：本体感知（让系统知道自己有什么）
        阶段1：规划生成（强制CoT + 任务分解）
        阶段2：正交执行（工具仲裁 + 并行/串行执行）
        阶段3：验证评估（结果比较器 + 置信度评分）
        阶段4：反思沉淀（数据序列化 → 向量存储 → 归纳触发）
        """
        
        start_time = time.time()
        execution_trace = {
            "query": user_query,
            "phases": {},
            "final_result": None,
            "confidence": 0.0,
            "elapsed": 0.0
        }
        
        # ========== 阶段0：本体感知（快速） ==========
        logger.info("🧠 [阶段0] 本体感知 - 扫描系统能力")
        
        try:
            capability_context = await asyncio.wait_for(
                self._phase0_capability_introspection(),
                timeout=3.0  # 最多3秒
            )
        except asyncio.TimeoutError:
            logger.warning("⚠️ 阶段0超时，使用默认能力")
            capability_context = {
                "tools": [],
                "models": [],
                "knowledge_bases": [],
                "capability_prompt": "系统能力扫描超时",
                "timestamp": datetime.now().isoformat()
            }
        
        execution_trace["phases"]["capability_introspection"] = capability_context
        
        logger.info(f"✓ 能力清单: {len(capability_context['tools'])}个工具, {len(capability_context['models'])}个模型")
        
        # ========== 阶段1：规划生成（快速） ==========
        logger.info("🎯 [阶段1] 规划生成 - 强制CoT + 任务分解")
        
        try:
            plan = await asyncio.wait_for(
                self._phase1_generate_execution_plan(
                    user_query, 
                    capability_context,
                    context
                ),
                timeout=5.0  # 最多5秒
            )
        except asyncio.TimeoutError:
            logger.warning("⚠️ 阶段1超时，使用默认计划")
            plan = self._create_default_plan(user_query)
        
        execution_trace["phases"]["planning"] = plan
        
        logger.info(f"✓ 执行计划: {len(plan['tasks'])}个子任务")
        for i, task in enumerate(plan['tasks'], 1):
            logger.info(f"  [{i}] {task['type']}: {task['description']}")
        
        # ========== 阶段2：正交执行（快速） ==========
        logger.info("⚡ [阶段2] 正交执行 - 工具仲裁 + 并行执行")
        
        try:
            execution_results = await asyncio.wait_for(
                self._phase2_execute_with_arbitration(
                    plan['tasks'],
                    capability_context,
                    user_query
                ),
                timeout=8.0  # 最多8秒
            )
        except asyncio.TimeoutError:
            logger.warning("⚠️ 阶段2超时，返回空结果")
            execution_results = {
                "results": [],
                "success_count": 0,
                "total_count": len(plan['tasks'])
            }
        
        execution_trace["phases"]["execution"] = execution_results
        
        logger.info(f"✓ 执行完成: {execution_results['success_count']}/{execution_results['total_count']}成功")
        
        # ========== 阶段3：验证评估（快速） ==========
        logger.info("✓ [阶段3] 验证评估 - 结果比较器 + 置信度评分")
        
        try:
            validation = await asyncio.wait_for(
                self._phase3_validate_and_score(
                    user_query,
                    execution_results,
                    capability_context
                ),
                timeout=2.0  # 最多2秒
            )
        except asyncio.TimeoutError:
            logger.warning("⚠️ 阶段3超时，使用默认验证")
            validation = {
                "confidence": 0.5,
                "is_valid": True,
                "reason": "验证超时"
            }
        
        execution_trace["phases"]["validation"] = validation
        
        logger.info(f"✓ 置信度: {validation['confidence']:.0%}, 质量: {validation['quality_score']}")
        
        # ========== 阶段4：反思沉淀（强制闭环） ==========
        logger.info("🔄 [阶段4] 反思沉淀 - 数据序列化 → 归纳触发")
        
        # 异步执行但不阻塞返回
        asyncio.create_task(
            self._phase4_force_reflection(
                user_query,
                plan,
                execution_results,
                validation,
                execution_trace
            )
        )
        
        # ========== 综合最终结果 ==========
        final_answer = self._synthesize_final_answer(execution_results, validation)
        
        execution_trace["final_result"] = final_answer
        execution_trace["confidence"] = validation["confidence"]
        execution_trace["elapsed"] = time.time() - start_time
        
        logger.info(f"✅ 元认知执行完成: {execution_trace['elapsed']:.1f}秒, 置信度{validation['confidence']:.0%}")
        
        return execution_trace
    
    async def _phase0_capability_introspection(self) -> Dict:
        """
        阶段0：本体感知
        让系统知道自己有什么能力（动态扫描）
        """
        
        tools = []
        # 注意：工具扫描可能导致卡住，暂时跳过
        # TODO: 修复工具扫描后重新启用
        logger.debug("跳过工具扫描（可能导致卡住）")
        
        # 2. 扫描模型适配器（异步，快速失败）
        models = []
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            import requests
            # 减少超时时间，快速失败
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: requests.get("http://localhost:11434/api/tags", timeout=1)
                ),
                timeout=1.5  # 总超时1.5秒
            )
            if response.status_code == 200:
                for model in response.json().get("models", []):
                    models.append({
                        "name": model["name"],
                        "available": True
                    })
        except asyncio.TimeoutError:
            logger.debug("模型扫描超时，跳过")
        except Exception as e:
            logger.debug(f"模型扫描失败: {e}")
        
        # 3. 扫描知识库
        knowledge_bases = []
        from pathlib import Path
        if Path("data/knowledge_store.db").exists():
            knowledge_bases.append({"name": "主知识库", "available": True})
        if Path("data/experience_pool.db").exists():
            knowledge_bases.append({"name": "经验池", "available": True})
        
        # 4. 构建能力上下文（注入到LLM）
        capability_prompt = self._build_capability_prompt(tools, models, knowledge_bases)
        
        return {
            "tools": tools,
            "models": models,
            "knowledge_bases": knowledge_bases,
            "capability_prompt": capability_prompt,
            "timestamp": datetime.now().isoformat()
        }
    
    def _build_capability_prompt(self, tools: List, models: List, knowledge_bases: List) -> str:
        """构建能力注入提示（动态System Prompt前缀）"""
        
        prompt = "【当前能力清单 - 实时扫描结果】\n\n"
        
        # 工具列表
        if tools:
            prompt += "可调用的工具：\n"
            for tool in tools[:10]:  # 限制长度
                prompt += f"- {tool['name']} ({tool['type']})\n"
            prompt += "\n"
        
        # 模型列表
        if models:
            prompt += "可调用的模型：\n"
            for model in models:
                prompt += f"- {model['name']}\n"
            prompt += "\n"
        
        # 知识库
        if knowledge_bases:
            prompt += "可检索的知识库：\n"
            for kb in knowledge_bases:
                prompt += f"- {kb['name']}\n"
            prompt += "\n"
        
        # 执行原则
        prompt += """【执行原则】
1. 你必须先输出"元认知计划（JSON格式）"，再执行计划
2. 置信度低于70%必须承认无知并触发外部学习
3. 优先使用工具而非纯推理
4. 每个步骤都要输出置信度评估
"""
        
        return prompt
    
    async def _phase1_generate_execution_plan(
        self,
        user_query: str,
        capability_context: Dict,
        context: Dict
    ) -> Dict:
        """
        阶段1：规划生成
        快速生成执行计划，不依赖远程API
        """
        
        # 1. 基于问题类型智能生成计划（不调用远程API）
        plan = self._smart_generate_plan(user_query, capability_context)
        
        return plan
    
    def _smart_generate_plan(self, query: str, capability_context: Dict) -> Dict:
        """基于问题类型智能生成执行计划（不依赖远程API）"""
        
        query_lower = query.lower()
        
        tasks = []
        analysis = f"分析问题: {query}"
        
        # 根据问题类型决定执行策略
        if any(kw in query_lower for kw in ["计算", "数学", "等于", "+", "-", "*", "/"]):
            tasks.append({"type": "tool", "name": "calculator", "description": f"计算: {query}", "timeout": 3})
            analysis += " -> 数学计算问题"
            
        elif any(kw in query_lower for kw in ["搜索", "查找", "最新", "新闻"]):
            tasks.append({"type": "knowledge_retrieval", "description": f"搜索: {query}"})
            analysis += " -> 信息搜索问题"
            
        elif any(kw in query_lower for kw in ["代码", "编程", "函数", "实现", "写"]):
            tasks.append({"type": "llm_reasoning", "description": f"生成代码: {query}"})
            analysis += " -> 代码生成问题"
            
        elif any(kw in query_lower for kw in ["什么是", "是什么", "概念", "定义", "介绍"]):
            tasks.append({"type": "knowledge_retrieval", "description": f"检索知识: {query}"})
            tasks.append({"type": "llm_reasoning", "description": f"综合解释: {query}"})
            analysis += " -> 知识解释问题"
            
        elif any(kw in query_lower for kw in ["为什么", "原因", "如何", "怎么", "怎样"]):
            tasks.append({"type": "knowledge_retrieval", "description": f"检索相关知识: {query}"})
            tasks.append({"type": "llm_reasoning", "description": f"分析推理: {query}"})
            analysis += " -> 分析推理问题"
            
        else:
            tasks.append({"type": "knowledge_retrieval", "description": f"检索: {query}"})
            tasks.append({"type": "llm_reasoning", "description": f"推理: {query}"})
            analysis += " -> 综合问题"
        
        return {
            "analysis": analysis,
            "tasks": tasks,
            "expected_confidence": 0.7
        }
    
    async def _retrieve_metacognitive_examples(self, query: str) -> str:
        """从255条闭环数据中检索相关范例"""
        
        try:
            # 尝试从向量库检索
            from core.vector_retriever import vector_retriever
            results = vector_retriever.hybrid_search(
                query=f"元认知: {query}",
                top_k=3
            )
            
            if results:
                examples = []
                for r in results[:3]:
                    if r.get('answer'):
                        examples.append(r['answer'][:200])
                return "\n\n".join(examples)
        except:
            pass
        
        # 降级：返回默认范例
        return """
范例1：
问题："计算圆的面积"
计划：{"tasks": [{"type": "tool", "name": "calculator"}, {"type": "llm_reasoning"}]}

范例2：
问题："什么是机器学习？"
计划：{"tasks": [{"type": "knowledge_retrieval"}, {"type": "llm_reasoning"}]}
"""
    
    def _create_default_plan(self, query: str) -> Dict:
        """创建默认执行计划"""
        return {
            "analysis": f"分析问题: {query}",
            "tasks": [
                {"type": "knowledge_retrieval", "description": f"检索关于'{query}'的知识"},
                {"type": "llm_reasoning", "description": "综合推理生成答案"}
            ],
            "expected_confidence": 0.7
        }
    
    async def _phase2_execute_with_arbitration(
        self,
        tasks: List[Dict],
        capability_context: Dict,
        user_query: str
    ) -> Dict:
        """
        阶段2：正交执行
        工具仲裁 + 并行探测 + 串行精修
        """
        
        results = []
        success_count = 0
        
        for i, task in enumerate(tasks, 1):
            task_type = task.get("type")
            task_desc = task.get("description", "")
            
            logger.info(f"  执行任务[{i}]: {task_type} - {task_desc}")
            
            result = {
                "task": task,
                "success": False,
                "output": None,
                "confidence": 0.0,
                "elapsed": 0.0
            }
            
            start = time.time()
            
            try:
                if task_type == "tool":
                    # 工具调用（硬超时3秒）
                    tool_name = task.get("name")
                    output = await asyncio.wait_for(
                        self._execute_tool(tool_name, user_query),
                        timeout=task.get("timeout", 3.0)
                    )
                    result["success"] = bool(output)
                    result["output"] = output
                    result["confidence"] = 0.8 if output else 0.0
                    
                elif task_type == "knowledge_retrieval":
                    # 知识检索
                    output = await self._retrieve_knowledge(task_desc)
                    result["success"] = bool(output)
                    result["output"] = output
                    result["confidence"] = output.get("confidence", 0.5) if output else 0.0
                    
                elif task_type == "llm_reasoning":
                    # LLM推理
                    output = await self._llm_reasoning(user_query, results)
                    result["success"] = bool(output)
                    result["output"] = output
                    result["confidence"] = 0.7
                    
            except asyncio.TimeoutError:
                logger.warning(f"  ⏱️ 任务[{i}]超时")
                result["error"] = "timeout"
            except Exception as e:
                logger.error(f"  ❌ 任务[{i}]失败: {e}")
                result["error"] = str(e)
            
            result["elapsed"] = time.time() - start
            results.append(result)
            
            if result["success"]:
                success_count += 1
        
        return {
            "results": results,
            "success_count": success_count,
            "total_count": len(tasks)
        }
    
    async def _execute_tool(self, tool_name: str, query: str) -> Any:
        """执行工具"""
        try:
            from tools.registry import registry
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: registry.execute(tool_name, query=query)
            )
            if hasattr(result, 'output'):
                return result.output
            return result
        except Exception as e:
            logger.debug(f"工具执行失败: {e}")
            return None
    
    async def _retrieve_knowledge(self, query: str) -> Any:
        """检索知识（快速，不依赖向量检索器）"""
        try:
            import sqlite3
            conn = sqlite3.connect("data/knowledge_store.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT content FROM knowledge WHERE content LIKE ? LIMIT 3",
                (f"%{query[:30]}%",)
            )
            rows = cursor.fetchall()
            conn.close()
            if rows:
                results = [row[0] for row in rows]
                return {
                    "answer": "\n".join(results),
                    "confidence": 0.7
                }
        except Exception as e:
            logger.debug(f"知识检索失败: {e}")
        return None
    
    async def _llm_reasoning(self, query: str, previous_results: List) -> str:
        """LLM推理（优先Ollama本地模型，快速失败）"""
        # 1. 尝试Ollama本地模型（自动选择可用模型）
        try:
            import requests
            loop = asyncio.get_event_loop()
            
            # 1a. 先获取可用模型列表
            try:
                tags_response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: requests.get("http://localhost:11434/api/tags", timeout=2)
                    ),
                    timeout=3.0
                )
                available_models = [m["name"] for m in tags_response.json().get("models", [])]
            except Exception:
                available_models = []
            
            # 1b. 按优先级选择模型
            model_priority = [
                "qwen2.5:7b", "qwen2.5-coder:7b", "gemma-4-12B:latest",
                "deepcoder:latest", "gemma-4-12B", "deepcoder"
            ]
            selected_model = None
            for model in model_priority:
                for available in available_models:
                    if model in available or available.startswith(model.split(":")[0]):
                        selected_model = available
                        break
                if selected_model:
                    break
            
            if not selected_model and available_models:
                selected_model = available_models[0]
            
            if selected_model:
                logger.info(f"  🤖 使用模型: {selected_model}")
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: requests.post(
                            "http://localhost:11434/api/generate",
                            json={"model": selected_model, "prompt": query, "stream": False},
                            timeout=15
                        )
                    ),
                    timeout=18.0
                )
                if response.status_code == 200:
                    answer = response.json().get("response", "")
                    if answer and len(answer) > 10:
                        logger.info(f"  ✅ 模型推理完成: {len(answer)}字")
                        return answer
        except asyncio.TimeoutError:
            logger.warning("  ⏱️ Ollama推理超时")
        except Exception as e:
            logger.debug(f"Ollama推理失败: {e}")
        
        # 2. 尝试DeepSeek远程API
        try:
            from adapters.llm.remote_adapter import RemoteAdapter
            adapter = RemoteAdapter(
                model="deepseek-chat",
                base_url="https://api.deepseek.com/v1"
            )
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: adapter.generate(query)),
                timeout=8.0
            )
            if result and len(result) > 10:
                return result
        except asyncio.TimeoutError:
            logger.debug("远程API推理超时")
        except Exception as e:
            logger.debug(f"远程API推理失败: {e}")
        
        return None
    
    async def _phase3_validate_and_score(
        self,
        user_query: str,
        execution_results: Dict,
        capability_context: Dict
    ) -> Dict:
        """
        阶段3：验证评估
        结果比较器 + 置信度评分
        """
        
        # 计算平均置信度
        confidences = [
            r["confidence"] 
            for r in execution_results["results"] 
            if r["success"]
        ]
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        # 质量评分
        quality_score = self._calculate_quality_score(
            user_query,
            execution_results,
            avg_confidence
        )
        
        # 检查是否需要外部学习
        need_external_learning = avg_confidence < 0.7
        
        return {
            "confidence": avg_confidence,
            "quality_score": quality_score,
            "need_external_learning": need_external_learning,
            "success_rate": execution_results["success_count"] / execution_results["total_count"]
        }
    
    def _calculate_quality_score(self, query: str, results: Dict, confidence: float) -> float:
        """计算质量分数"""
        score = confidence * 100
        
        # 成功率加成
        success_rate = results["success_count"] / results["total_count"]
        score += success_rate * 20
        
        return min(100, score)
    
    async def _phase4_force_reflection(
        self,
        user_query: str,
        plan: Dict,
        execution_results: Dict,
        validation: Dict,
        execution_trace: Dict
    ):
        """
        阶段4：反思沉淀（强制闭环，异步不阻塞）
        数据序列化 → 经验存储 → 训练数据生成
        """
        
        logger.info("🔄 [后台] 强制反思沉淀...")
        
        try:
            experience = {
                "query": user_query,
                "plan": plan,
                "results": execution_results,
                "validation": validation,
                "timestamp": datetime.now().isoformat()
            }
            
            # 1. 存储到经验池（SQLite，快速）
            try:
                import sqlite3
                conn = sqlite3.connect("data/experience_pool.db")
                cursor = conn.cursor()
                answer = self._extract_best_answer(execution_results)
                cursor.execute(
                    "INSERT INTO experiences (query, response, timestamp, intent_type, quality_score) VALUES (?, ?, ?, ?, ?)",
                    (user_query, answer, datetime.now().isoformat(), "metacognitive", int(validation.get("quality_score", 50)))
                )
                conn.commit()
                conn.close()
                logger.debug("✓ 经验已存储")
            except Exception as e:
                logger.debug(f"经验存储失败: {e}")
            
            # 2. 生成训练数据（JSONL，快速）
            try:
                if validation.get("confidence", 0) > 0.6:
                    sample = {
                        "question": user_query,
                        "answer": self._extract_best_answer(execution_results),
                        "source": "metacognitive_execution"
                    }
                    with open("data/pending_training.jsonl", "a", encoding="utf-8") as f:
                        f.write(json.dumps(sample, ensure_ascii=False) + "\n")
                    logger.debug("✓ 训练数据已生成")
            except Exception as e:
                logger.debug(f"训练数据生成失败: {e}")
            
            logger.info("✓ 反思沉淀完成")
            
        except Exception as e:
            logger.error(f"反思沉淀失败: {e}")
    
    async def _store_experience(self, experience: Dict):
        """存储经验"""
        try:
            from infrastructure.experience_pool import ExperiencePool
            pool = ExperiencePool()
            
            success = experience["validation"].get("confidence", 0.5) > 0.6
            quality_score = int(experience["validation"].get("quality_score", 50))
            
            pool.add_experience(
                intent_type="metacognitive",
                raw_input=experience["query"],
                plan=json.dumps(experience["plan"], ensure_ascii=False),
                model_name="metacognitive_executor",
                quality_score=quality_score,
                user_feedback=None,
                success=success,
                duration=experience.get("elapsed", 0),
                response=self._extract_best_answer(experience["results"])
            )
        except Exception as e:
            logger.debug(f"经验存储失败: {e}")
    
    async def _trigger_meta_induction(self, experience: Dict):
        """触发元归纳"""
        try:
            from meta.induction import induction_scheduler
            induction_scheduler.run_induction(days=7)
            logger.info("✓ 元归纳已触发")
        except Exception as e:
            logger.debug(f"元归纳触发失败: {e}")
    
    async def _convert_to_training_data(self, experience: Dict):
        """转化为训练数据"""
        try:
            # 构建训练样本
            if experience["validation"]["confidence"] > 0.6:
                sample = {
                    "question": experience["query"],
                    "answer": self._extract_best_answer(experience["results"]),
                    "source": "metacognitive_execution"
                }
                
                # 存储为JSONL
                with open("data/pending_training.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps(sample, ensure_ascii=False) + "\n")
                
                logger.info("✓ 训练数据已生成")
        except Exception as e:
            logger.debug(f"训练数据生成失败: {e}")
    
    def _extract_best_answer(self, results: Dict) -> str:
        """提取最佳答案"""
        for result in results.get("results", []):
            if result["success"] and result.get("output"):
                output = result["output"]
                if isinstance(output, str):
                    return output
                elif isinstance(output, dict) and "answer" in output:
                    return output["answer"]
        return ""
    
    def _synthesize_final_answer(self, results: Dict, validation: Dict) -> str:
        """综合最终答案（符合精神内核：即使失败也给出有意义的回复）"""
        answer = self._extract_best_answer(results)
        
        if not answer or len(answer) < 10:
            # 即使失败，也给出有意义的回复
            from core.spirit_core import spirit_core
            attempts = []
            for r in results.get("results", []):
                task = r.get("task", {})
                attempts.append({
                    "method": f"{task.get('type', '未知')}: {task.get('description', '')}",
                    "success": r.get("success", False),
                    "error": r.get("error", "")
                })
            answer = spirit_core.ensure_meaningful_response("", attempts)
        elif validation["confidence"] < 0.7:
            answer = f"⚠️ 置信度较低({validation['confidence']:.0%})\n\n{answer}"
        
        return answer


# 全局实例
_executor = None

def get_metacognitive_executor() -> MetacognitiveExecutor:
    """获取元认知执行器"""
    global _executor
    if _executor is None:
        _executor = MetacognitiveExecutor()
    return _executor