"""
元问题处理 mixin — 任务分解、元认知问题、记忆查询
"""
from typing import Optional, Dict, List
from loguru import logger
from core.ports.adapters import get_storage_port
from core.services.intent_parser import Intent


class MetaProblemSolverMixin:

    def _init_meta_solver(self) -> None:
        self._decomposition_cache: Dict[str, object] = {}
        self._max_recursion_depth = 3
        self._current_depth = 0

    def _decompose_and_execute(self, intent: Intent) -> Optional[str]:
        """分解复杂任务并执行"""
        try:
            if not hasattr(self, 'task_decomposer') or self.task_decomposer is None:
                logger.warning("任务分解器不可用，使用联邦调度")
                return self._parallel_schedule(intent)

            llm_adapter = self.adapters.get('code_light') or next(iter(self.adapters.values()))
            subtasks = self.task_decomposer.decompose_with_llm(
                intent.raw_text,
                llm_adapter=llm_adapter
            )

            if len(subtasks) <= 1:
                logger.info("任务无法分解，使用联邦调度")
                return self._parallel_schedule(intent)

            logger.info(f"任务已分解为 {len(subtasks)} 个子任务")

            results = []
            for subtask in subtasks:
                sub_intent = Intent(
                    type=subtask['type'],
                    raw_text=subtask['description'],
                    confidence=0.8,
                    entities={}
                )

                result = self._parallel_schedule(sub_intent)
                if result:
                    results.append(result)
                else:
                    model = self._select_model(sub_intent)
                    result = model.generate(subtask['description'], task_type=subtask['type'])
                    if isinstance(result, tuple):
                        result = result[0]
                    results.append(result if result else "")

            summary_model = self.adapters.get('qwen2.5-coder:7b') or self.adapters.get('deepcoder')
            fused_result = self.result_fusion.fuse(
                subtasks=subtasks,
                results=results,
                original_intent=intent.raw_text,
                strategy='auto',
                summary_model=summary_model
            )

            self.task_decomposer.save_decomposition(
                original_task=intent.raw_text,
                subtasks=subtasks,
                strategy='llm' if llm_adapter else 'rule',
                success=True,
                quality_score=self._evaluate_quality(fused_result, intent.type) / 100.0
            )

            logger.info(f"任务分解执行完成，融合结果长度: {len(fused_result)}")
            return fused_result

        except Exception as e:
            logger.error(f"任务分解执行失败: {e}")
            return None

    def _handle_meta_value_question(self, user_question: str) -> str:
        """处理价值性问题（进入对话模式）"""
        logger.info("进入对话模式：价值性问题")

        if "最优" in user_question or "最好" in user_question or "最佳" in user_question:
            return """你问的这个问题很有意思——"最优结果"没有一个固定的定义，它取决于你希望满足什么。

让我先分享我的理解，然后听听你的想法：

**从我的角度看，一个"最优结果"可能需要平衡多个维度：**

1. **准确性** - 信息是否正确、是否有误导
2. **相关性** - 是否回答了你真正关心的问题（而非我理解的问题）
3. **可操作性** - 你能否直接使用这个回答
4. **启发价值** - 是否帮你打开了新的思路

但这里有个关键问题：**不同场景下，这些维度的权重不同**。

- 如果你问"如何写代码"，可能"可操作性"权重最高
- 如果你问"为什么这样设计"，可能"启发价值"权重最高
- 如果你问"这个方案对不对"，可能"准确性"权重最高

**所以我想问你**：在你刚才的那个场景中，你更看重哪个维度？或者说，你希望我刚才的回答在哪个方面做得更好？

这样我能更准确地理解你的期望，下次才能给出更"最优"的回答。"""

        elif "标准" in user_question or "判断" in user_question:
            return """关于"标准"的问题，我觉得没有绝对的标准，但有相对的共识。

**我想先了解**：你是在问什么样的标准？

- 评价回答质量的标准？
- 判断系统是否理解你的标准？
- 还是其他？

不同场景下的"好标准"可能完全不同。比如：

- 技术问答：准确、完整、有代码示例
- 概念解释：清晰、有类比、有边界说明
- 问题诊断：找到根因、给出方案、解释原理

**你能具体说说**：你刚才希望我达到什么样的标准？这样我能更好地调整自己的回答方式。"""

        else:
            return f"""这是一个很有深度的问题。"{user_question}"——这其实是在探讨价值的定义。

我注意到，这类问题通常没有标准答案，而是需要根据具体场景来讨论。

**我想先理解你的语境**：
- 你是在反思刚才的对话吗？
- 还是在探讨一个更普遍的问题？

如果是关于刚才的对话，**你觉得哪里没有达到你的期望**？这样我能更具体地改进。

如果是普遍性的探讨，我很乐意和你一起深入讨论这个话题。"""

    def _handle_meta_question(self, user_question: str, meta_type: str = "meta") -> str:
        """处理元认知问题（关于系统自身的问题）"""

        if meta_type == "meta_value":
            return self._handle_meta_value_question(user_question)

        q_lower = user_question.lower()
        if any(kw in q_lower for kw in ["学习能力", "学习的能力"]):
            return """提升学习能力的核心方法：

**1. 主动回想（Active Recall）**
- 读完内容后合上书，用自己的话复述
- 不要重复阅读，而是主动提取记忆

**2. 间隔重复（Spaced Repetition）**
- 今天学、明天复习、一周后再看、一个月后再巩固
- 利用睡眠巩固记忆，分散学习比集中学习更有效
- 工具推荐：Anki（间隔重复闪卡）

**3. 费曼技巧（Feynman Technique）**
- 假装教给一个8岁孩子
- 卡住的地方就是你的知识盲区
- 用简单语言解释复杂概念

**4. 最小可行习惯**
- 每天5分钟，先建立习惯再延长
- 不要一开始就要求学1小时
- 习惯 > 强度

**5. 多模态编码**
- 同时使用：视觉（图表）、听觉（讲解）、动觉（动手写）
- 多通道输入强化神经连接

**6. 错误驱动学习**
- 错误不是失败，是定位盲区的信号
- 对每个错误做"错误分析"：为什么错？正确思路是什么？

**7. 元认知监控**
- 学习前：我要学什么？为什么学？
- 学习中：我理解了吗？哪里卡住了？
- 学习后：我学到了哪三个关键点？

如果需要针对特定领域（编程、语言、考试）的详细方案，请直接告诉我。"""

        if any(kw in q_lower for kw in ["培养学习", "自主学习", "学习习惯"]):
            return """培养自主学习习惯的实用方法：

**第一阶段：建立习惯（1-2周）**
- 固定时间：每天同一时间学习（如早上8点）
- 固定地点：创造专属学习空间
- 最小行动：从"打开书"开始，不要求学多久
- 触发机制：将学习绑定到已有习惯后（如"喝完咖啡后学习"）

**第二阶段：形成节奏（3-4周）**
- 番茄工作法：25分钟专注 + 5分钟休息
- 每日清单：列出3个最重要的事，完成打勾
- 周回顾：每周日回顾本周学习，规划下周

**第三阶段：深化习惯（2-3月）**
- 输出倒逼输入：学完就教别人或写笔记
- 项目驱动：用真实项目练习
- 社群支持：找到学习伙伴或社区

**关键原则**：
1. 环境 > 意志力（改变环境比靠意志力更有效）
2. 身份认同（"我是学习者"而非"我要学习"）
3. 允许失败（断档后立刻恢复，不要自责）

**工具推荐**：
- Forest：专注时种树，可视化学习时间
- Notion：构建个人知识库
- Obsidian：双向链接笔记"""

        if any(kw in user_question for kw in ["能力边界", "边界", "能力在哪", "你的能力"]):
            return self._report_capability_boundary()

        if any(kw in user_question for kw in ["自我评估", "评估体系", "如何决策", "如何认识"]):
            return self._report_self_assessment()

        if any(kw in user_question for kw in ["回顾对话", "评价", "给出评价"]):
            return self._evaluate_recent_dialogs()

        try:
            conn_exp = get_storage_port()._get_conn('data/experience_pool.db')
            cur = conn_exp.execute("SELECT COUNT(*), AVG(quality_score) FROM experiences")
            exp_count, exp_quality = cur.fetchone()

            conn_rules = get_storage_port()._get_conn('data/learning_rules.db')
            cur = conn_rules.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            active_rules = cur.fetchone()[0]

            best_score = getattr(self, 'last_optimization_score', 0.0)

        except Exception as e:
            logger.error(f"收集系统状态失败: {e}")
            exp_count, exp_quality, active_rules, best_score = 0, 0.0, 0, 0.0

        exp_quality = exp_quality if exp_quality is not None else 0.0
        best_score = best_score if best_score is not None else 0.0

        meta_prompt = f"""用户问我关于自身能力的问题：" {user_question} "

作为联盟拓荒者智能体，我需要反思自己的能力。以下是我的当前状态：

【系统状态】
- 经验池: {exp_count}条经验
- 平均响应质量: {exp_quality:.2f}分
- 活跃学习规则: {active_rules}条
- 最近优化得分: {best_score:.2f}

【我的理解能力】
我通过以下方式理解用户需求：
1. 意图识别：使用规则匹配识别任务类型（code/question/meta等）
2. 模型路由：根据统计库选择最适合的模型
3. 经验复用：通过向量检索重用历史成功案例
4. 规则学习：从失败中归纳新规则

【改进方向】
为了更好地理解需求，我可以：
1. 积累更多对话经验，学习用户的表达习惯
2. 主动提出澄清问题，减少误解
3. 从用户反馈中学习，调整路由策略
4. 优化意图识别规则，覆盖更多表达方式

请以第一人称"我"的语气回答用户，提供真诚的反思和具体的改进建议。
回答要简洁、具体、有温度。"""

        model = self.adapters.get("code_light") or self.adapters.get("remote_gpt4")

        if model:
            try:
                response = model.generate(meta_prompt, task_type="meta")
                if isinstance(response, tuple):
                    response, _ = response
                return response
            except Exception as e:
                logger.error(f"元认知回答生成失败: {e}")

        return f"""作为联盟拓荒者，我目前通过意图识别和模型路由来理解你的需求。

当前状态：
- 已积累 {exp_count} 条经验
- 平均响应质量 {exp_quality:.1f} 分
- 活跃学习规则 {active_rules} 条

为了更好地理解你的需求，我需要：
1. 从你的反馈中学习更多表达方式
2. 积累更多对话经验
3. 主动提出澄清问题

你觉得我在哪方面最需要改进？"""

    def _handle_memory_query(self, intent: Intent) -> str:
        """处理记忆查询意图 - 真正的反思，不是形式主义"""
        user_question = intent.raw_text.lower()

        if any(kw in user_question for kw in ["回顾历史", "历史对话", "历史问题", "回顾对话", "之前的对话"]):
            try:
                if hasattr(self, 'campfire') and self.campfire:
                    context = self.campfire.get_recent_context(rounds=10)
                else:
                    from infrastructure.logger import CampfireLogger
                    temp_logger = CampfireLogger()
                    context = temp_logger.get_recent_context(rounds=10)

                if not context:
                    return "暂无历史对话记录。"

                try:
                    from core.honest_learning_system import honest_system

                    history = self._parse_history(context)

                    reflection = honest_system.deep_reflection(user_question, history)

                    return reflection

                except Exception as e:
                    logger.warning(f"深度反思失败: {e}")
                    return f"""以下是最近的对话历史：

{context}

---

**反思声明**

我必须承认：我目前只是罗列了历史，没有进行真正的反思。

这是我的不足，我会改进。

---
_共显示最近10轮对话_"""

            except Exception as e:
                logger.error(f"读取历史对话失败: {e}")
                return "抱歉，无法读取历史对话记录。"

        if any(kw in user_question for kw in ["之前", "刚才", "刚才你", "你刚才", "不对", "错误"]):
            try:
                from core.honest_learning_system import honest_system
                from core.requirement_validator import requirement_validator

                if hasattr(self, 'campfire') and self.campfire:
                    context = self.campfire.get_recent_context(rounds=2)
                else:
                    from infrastructure.logger import CampfireLogger
                    temp_logger = CampfireLogger()
                    context = temp_logger.get_recent_context(rounds=2)

                if not context:
                    return "让我回顾一下刚才的对话..."

                history = self._parse_history(context)

                if history:
                    last = history[-1]
                    user_msg = last.get('user', '')
                    assistant_msg = last.get('assistant', '')

                    req = requirement_validator.extract_core_requirement(user_msg)
                    is_valid, issues = requirement_validator.validate_response_against_requirement(
                        req, assistant_msg
                    )

                    if not is_valid:
                        return f"""
【承认错误】

您说得对，我刚才的回答有问题。

**用户需求**: {user_msg[:100]}
**我的回答**: {assistant_msg[:100]}

**问题所在**:
{chr(10).join(f'- {issue}' for issue in issues)}

**自我批评**:
我没有仔细验证就给出了答案，这是不负责任的表现。

**纠正**:
让我重新认真回答您的问题...

---

_感谢您的质疑，这帮助我发现了错误。_
"""

                return "让我认真反思刚才的回答..."

            except Exception as e:
                logger.warning(f"历史纠正失败: {e}")
                return "我正在反思刚才的回答..."

        return "我目前只能记住当前对话中的内容。如果需要回顾历史对话，请说'回顾历史对话'。"

    def _parse_history(self, context: str) -> list:
        """解析历史对话文本"""
        history = []
        lines = context.split('\n')

        current_user = ""
        current_assistant = ""

        for line in lines:
            if line.startswith('用户:') or line.startswith('User:'):
                if current_user and current_assistant:
                    history.append({
                        'user': current_user,
                        'assistant': current_assistant
                    })
                current_user = line.split(':', 1)[1].strip()
                current_assistant = ""
            elif line.startswith('拓荒者:') or line.startswith('Assistant:'):
                current_assistant = line.split(':', 1)[1].strip()

        if current_user and current_assistant:
            history.append({
                'user': current_user,
                'assistant': current_assistant
            })

        return history
