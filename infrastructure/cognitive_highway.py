"""
认知主干道（Cognitive Highway）- 系统的脊髓

跨学科理论基础：
- 系统神经学：重建"自主神经系统"，让意识连接肌肉
- 控制论：RPV循环（Plan → Verify → Execute → Reflect）实现负反馈
- 认知科学：双重加工理论（强制唤醒系统2）
- 计算机架构：内存映射I/O（让LLM看到工具）

核心：强制性的、不可跳过的"感知-认知-行动-校验"闭环管道
"""
import asyncio
import json
import logging
import time
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger


class CognitiveHighway:
    """
    认知主干道：让系统从"植物人"变成"自主体"
    
    RPV循环：
    Plan（计划）→ Verify（验证）→ Execute（执行）→ Reflect（反思）
    
    这是连接意识（六层架构）与肌肉（工具/模型）的脊髓
    """
    
    def __init__(self, llm_adapter=None, tool_registry=None, vector_retriever=None, reflection_pipeline=None):
        self.llm = llm_adapter
        self.tools = tool_registry
        self.retriever = vector_retriever
        self.reflection = reflection_pipeline
        self.execution_timeout = 3.0  # 工具硬超时
        
        logger.info("🧬 认知主干道已初始化（系统脊髓）")
    
    async def process(self, user_query: str, history: List[Dict] = None) -> Dict[str, Any]:
        """
        处理用户请求的主入口
        
        RPV循环：Plan → Verify → Execute → Reflect
        """
        start_time = time.time()
        
        logger.info("=" * 60)
        logger.info(f"🧬 认知主干道启动：{user_query[:50]}...")
        logger.info("=" * 60)
        
        # ========== 阶段 1: 计划 (Plan) - 唤醒系统2 ==========
        logger.info("\n[阶段1] 计划生成 - 唤醒系统2（逻辑思考）")
        
        # 1.1 检索"255条闭环数据"中最相似的3个历史策略（情景记忆）
        similar_strategies = await self._retrieve_strategies(user_query)
        
        logger.info(f"  ✓ 检索到{len(similar_strategies)}个历史策略")
        
        # 1.2 获取当前可用工具列表（本体感知）
        available_tools = self._scan_available_tools()
        
        logger.info(f"  ✓ 可用工具: {len(available_tools)}个")
        
        # 1.3 强制LLM生成JSON执行计划（而非直接回答）
        plan = await self._generate_execution_plan(user_query, similar_strategies, available_tools)
        
        logger.info(f"  ✓ 执行计划: {len(plan.get('tasks', []))}个任务")
        logger.info(f"  ✓ 预期置信度: {plan.get('expected_confidence', 0.5):.0%}")
        
        # ========== 阶段 2: 验证 (Verify) - 自检能力边界 ==========
        logger.info("\n[阶段2] 验证评估 - 自检能力边界")
        
        validation = self._validate_plan(plan, available_tools)
        
        if not validation["valid"]:
            logger.warning(f"  ⚠️ 计划验证失败: {validation['issues']}")
            # 修正计划
            plan = self._fix_plan(plan, validation["issues"], available_tools)
            logger.info("  ✓ 计划已修正")
        else:
            logger.info("  ✓ 计划验证通过")
        
        # ========== 阶段 3: 执行 (Execute) - 并行调用 ==========
        logger.info("\n[阶段3] 执行实施 - 并行调用工具/模型")
        
        # 简单问题走捷径
        if plan.get("complexity") == "简单" and len(plan.get("tasks", [])) == 0:
            logger.info("  ⚡ 快路径：直接回答")
            final_answer = await self._direct_answer(user_query)
            confidence = 0.9
            execution_results = []
        else:
            # 完整执行流程
            execution_results = await self._execute_plan(plan, user_query)
            
            # 结果融合
            final_answer = await self._synthesize_results(user_query, execution_results, plan)
            confidence = self._calculate_confidence(execution_results, plan)
            
            logger.info(f"  ✓ 执行完成: {len([r for r in execution_results if r['status']=='success'])}/{len(execution_results)}成功")
        
        # ========== 阶段 4: 反思 (Reflect) - 闭环的命脉 ==========
        logger.info("\n[阶段4] 反思沉淀 - 闭环的命脉")
        
        # 关键：无论成败，强制异步触发反思管道，喂饱归纳器
        execution_context = {
            "query": user_query,
            "plan": plan,
            "tool_calls": [t for t in plan.get("tasks", []) if t.get("type") == "tool"],
            "final_answer": final_answer,
            "confidence": confidence,
            "model_used": "cognitive_highway",
            "duration_ms": int((time.time() - start_time) * 1000),
            "success": confidence > 0.6,
        }
        
        # 异步触发反思，绝不阻塞返回
        if self.reflection:
            asyncio.create_task(self.reflection.process(execution_context))
            logger.info("  ✓ 反思管道已触发（异步）")
        
        elapsed = time.time() - start_time
        
        logger.info(f"\n✅ 认知主干道完成: {elapsed:.2f}秒, 置信度{confidence:.0%}")
        logger.info("=" * 60)
        
        return {
            "answer": final_answer,
            "confidence": confidence,
            "plan_used": plan,
            "execution_results": execution_results,
            "elapsed": elapsed
        }
    
    async def _retrieve_strategies(self, query: str) -> List[Dict]:
        """检索历史策略（从255条闭环数据）"""
        strategies = []
        
        try:
            # 尝试从向量库检索
            if self.retriever:
                results = self.retriever.hybrid_search(
                    query=f"元认知策略: {query}",
                    top_k=3
                )
                
                if results:
                    for r in results[:3]:
                        if r.get('answer'):
                            strategies.append({
                                "question": r.get('question', ''),
                                "answer": r['answer'][:200],
                                "confidence": r.get('final_score', 0.5)
                            })
        except Exception as e:
            logger.debug(f"策略检索失败: {e}")
        
        # 如果没有检索到，返回默认范例
        if not strategies:
            strategies = [
                {
                    "question": "计算问题",
                    "answer": "使用calculator工具进行精确计算",
                    "confidence": 0.8
                },
                {
                    "question": "知识查询",
                    "answer": "先检索知识库，再综合推理",
                    "confidence": 0.7
                }
            ]
        
        return strategies
    
    def _scan_available_tools(self) -> List[str]:
        """扫描可用工具（本体感知）"""
        tools = []
        
        try:
            from tools.registry import ToolRegistry
            registry = ToolRegistry()
            for tool in registry.list_tools():
                tools.append(tool.name)
        except Exception as e:
            logger.debug(f"工具扫描失败: {e}")
        
        # 添加默认工具（即使注册表失败）
        if not tools:
            tools = ["calculator", "search", "knowledge_retrieval"]
        
        return tools
    
    async def _generate_execution_plan(
        self, 
        query: str, 
        strategies: List[Dict], 
        tools: List[str]
    ) -> Dict:
        """强制生成执行计划（唤醒系统2）"""
        
        # 构建规划提示
        plan_prompt = f"""
你是系统架构师。请勿直接回答用户问题。请严格遵循以下步骤输出JSON：

1. 分析用户意图：「{query}」
2. 参考历史成功策略：{json.dumps(strategies, ensure_ascii=False)}
3. 可用工具列表：{tools}
4. 请输出JSON格式的执行计划：
{{
    "intent": "意图分类",
    "complexity": "简单/中等/复杂",
    "tasks": [
        {{"id": 1, "type": "tool|llm|hybrid", "name": "工具名或推理指令", "description": "做什么", "fallback": "备用方案"}}
    ],
    "expected_confidence": 0.0-1.0
}}

【强制要求】
- 如果涉及计算，必须使用calculator工具
- 如果涉及搜索，必须使用search工具
- 不要仅靠推理，优先使用工具
"""

        # 调用LLM生成计划
        try:
            if self.llm:
                plan_raw = await self._call_llm(plan_prompt)
                
                # 解析JSON
                json_match = re.search(r'\{[\s\S]*\}', plan_raw)
                if json_match:
                    plan = json.loads(json_match.group())
                    return plan
        except Exception as e:
            logger.debug(f"计划生成失败: {e}")
        
        # 降级：紧急兜底计划
        return self._emergency_plan(query, tools)
    
    async def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        try:
            if hasattr(self.llm, 'generate'):
                return self.llm.generate(prompt)
            elif hasattr(self.llm, 'chat'):
                return self.llm.chat(prompt)
            else:
                return str(self.llm(prompt))
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return ""
    
    def _validate_plan(self, plan: Dict, available_tools: List[str]) -> Dict:
        """验证计划是否可行"""
        issues = []
        
        # 检查任务列表
        if not plan.get("tasks"):
            issues.append("无执行任务")
        
        # 检查工具是否存在
        for task in plan.get("tasks", []):
            if task.get("type") == "tool":
                tool_name = task.get("name")
                if tool_name and tool_name not in available_tools:
                    issues.append(f"工具不存在: {tool_name}")
        
        # 检查置信度
        if plan.get("expected_confidence", 0) < 0.3:
            issues.append("预期置信度过低")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def _fix_plan(self, plan: Dict, issues: List[str], tools: List[str]) -> Dict:
        """修正计划"""
        # 简单修正：添加默认任务
        if "无执行任务" in issues:
            plan["tasks"] = [
                {"id": 1, "type": "llm", "name": "直接推理", "description": "无可用工具，直接推理"}
            ]
        
        # 修正不存在的工具
        for task in plan.get("tasks", []):
            if task.get("type") == "tool":
                tool_name = task.get("name")
                if tool_name and tool_name not in tools:
                    # 替换为LLM推理
                    task["type"] = "llm"
                    task["name"] = f"推理（原工具{tool_name}不可用）"
        
        return plan
    
    async def _execute_plan(self, plan: Dict, query: str) -> List[Dict]:
        """执行计划"""
        results = []
        
        for task in plan.get("tasks", []):
            task_id = task.get("id", 0)
            task_type = task.get("type", "llm")
            task_name = task.get("name", "")
            
            logger.info(f"  执行任务[{task_id}]: {task_type} - {task_name}")
            
            result = {
                "task_id": task_id,
                "type": task_type,
                "status": "pending",
                "output": None
            }
            
            try:
                if task_type == "tool":
                    # 带超时的工具调用
                    tool_result = await asyncio.wait_for(
                        self._call_tool(task_name, query),
                        timeout=self.execution_timeout
                    )
                    result["output"] = tool_result
                    result["status"] = "success"
                    
                elif task_type == "llm":
                    # LLM推理
                    llm_result = await self._call_llm(task_name or query)
                    result["output"] = llm_result
                    result["status"] = "success"
                    
                else:  # hybrid
                    # 混合模式：先尝试工具，失败则LLM
                    try:
                        tool_result = await asyncio.wait_for(
                            self._call_tool(task_name, query),
                            timeout=self.execution_timeout
                        )
                        result["output"] = tool_result
                        result["status"] = "success"
                    except:
                        llm_result = await self._call_llm(query)
                        result["output"] = llm_result
                        result["status"] = "fallback"
                
            except asyncio.TimeoutError:
                logger.warning(f"    ⏱️ 任务[{task_id}]超时")
                result["status"] = "timeout"
                result["output"] = "执行超时"
                
            except Exception as e:
                logger.error(f"    ❌ 任务[{task_id}]失败: {e}")
                result["status"] = "error"
                result["output"] = str(e)
            
            results.append(result)
        
        return results
    
    async def _call_tool(self, tool_name: str, query: str) -> str:
        """统一工具调用适配器 - 自动适配不同工具接口"""
        try:
            from tools.registry import ToolRegistry
            registry = ToolRegistry()
            
            # 查找工具
            tool = None
            for t in registry.list_tools():
                if t.name == tool_name:
                    tool = t
                    break
            
            if not tool:
                return f"工具 {tool_name} 不存在"
            
            # 检查工具的execute方法签名
            import inspect
            sig = inspect.signature(tool.execute)
            params = list(sig.parameters.keys())
            
            # 智能传递参数
            if "query" in params:
                result = tool.execute(query=query)
            elif "text" in params:
                result = tool.execute(text=query)
            elif "input" in params:
                result = tool.execute(input=query)
            elif "kwargs" in str(sig):
                result = tool.execute(query=query)
            else:
                # 无参数工具，直接调用
                result = tool.execute()
            
            # 处理结果
            if hasattr(result, 'output'):
                return str(result.output)
            elif hasattr(result, 'success') and result.success:
                return str(result.output) if hasattr(result, 'output') else "执行成功"
            else:
                return str(result)
                
        except Exception as e:
            logger.error(f"工具 {tool_name} 执行失败: {e}")
            return f"工具执行错误: {str(e)}"
    
    async def _synthesize_results(self, query: str, results: List[Dict], plan: Dict) -> str:
        """综合结果生成最终答案"""
        # 收集成功的结果
        successful_results = [r for r in results if r["status"] == "success"]
        
        if not successful_results:
            return "抱歉，我暂时无法回答这个问题。"
        
        # 如果只有一个结果，直接返回
        if len(successful_results) == 1:
            return successful_results[0]["output"]
        
        # 多个结果，需要综合
        prompt = f"""
用户问：{query}

执行计划：{json.dumps(plan, ensure_ascii=False)}

执行结果：
{json.dumps(successful_results, ensure_ascii=False, indent=2)}

请综合以上结果，给出最终回答：
"""
        
        try:
            final = await self._call_llm(prompt)
            return final
        except:
            # 降级：拼接所有结果
            return "\n\n".join([r["output"] for r in successful_results if r.get("output")])
    
    def _calculate_confidence(self, results: List[Dict], plan: Dict) -> float:
        """计算置信度"""
        if not results:
            return 0.5
        
        # 成功率
        success_rate = len([r for r in results if r["status"] == "success"]) / len(results)
        
        # 基础置信度
        base_confidence = plan.get("expected_confidence", 0.6)
        
        # 综合置信度
        confidence = base_confidence * success_rate + 0.3 * (1 - success_rate)
        
        return min(1.0, confidence)
    
    async def _direct_answer(self, query: str) -> str:
        """直接回答（快路径）"""
        try:
            return await self._call_llm(query)
        except:
            return "你好！有什么可以帮你的吗？"
    
    def _emergency_plan(self, query: str, tools: List[str]) -> Dict:
        """紧急兜底计划"""
        # 智能推测：如果包含数学关键词，强制调用计算器
        math_keywords = ["计算", "+", "-", "×", "÷", "*", "/", "π", "sin", "cos", "sqrt", "平方", "立方"]
        if any(k in query for k in math_keywords):
            return {
                "intent": "calculation",
                "complexity": "中等",
                "tasks": [
                    {"id": 1, "type": "tool", "name": "calculator", "description": "数学计算", "fallback": "llm"}
                ],
                "expected_confidence": 0.8
            }
        
        # 搜索关键词
        search_keywords = ["搜索", "查找", "找", "查询", "什么是", "介绍"]
        if any(k in query for k in search_keywords):
            return {
                "intent": "search",
                "complexity": "中等",
                "tasks": [
                    {"id": 1, "type": "tool", "name": "search", "description": "搜索信息", "fallback": "llm"}
                ],
                "expected_confidence": 0.7
            }
        
        # 默认：LLM推理
        return {
            "intent": "general",
            "complexity": "中等",
            "tasks": [
                {"id": 1, "type": "llm", "name": query, "description": "直接推理"}
            ],
            "expected_confidence": 0.6
        }


# 全局实例
_highway = None

def get_cognitive_highway(
    llm_adapter=None, 
    tool_registry=None, 
    vector_retriever=None, 
    reflection_pipeline=None
) -> CognitiveHighway:
    """获取认知主干道实例"""
    global _highway
    if _highway is None:
        _highway = CognitiveHighway(llm_adapter, tool_registry, vector_retriever, reflection_pipeline)
    return _highway