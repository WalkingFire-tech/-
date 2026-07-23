"""元问题求解 mixin — 元问题处理、任务分解"""
from typing import Optional
from loguru import logger
from core.services.intent_parser import Intent


class MetaProblemSolverMixin:
    """元问题求解能力：元问题处理、元价值问题处理、复杂任务分解"""

    def _init_meta_solver(self):
        self._current_depth = 0

    def _handle_meta_value_question(self, user_question: str) -> str:
        """处理价值性问题（进入对话模式）"""
        logger.info("进入对话模式：价值性问题")
        if any(kw in user_question for kw in ["最优", "最好", "最佳"]):
            return """你问的这个问题很有意思——"最优结果"没有一个固定的定义，它取决于你希望满足什么。

让我先分享我的理解，然后听听你的想法：

**从我的角度看，一个"最优结果"可能需要平衡多个维度：**

1. **准确性** - 信息是否正确、是否有误导
2. **相关性** - 是否回答了你真正关心的问题（而非我理解的问题）
3. **可操作性** - 你能否直接使用这个回答
4. **启发价值** - 是否帮你打开了新的思路

但这里有个关键问题：**不同场景下，这些维度的权重不同**。

**所以我想问你**：在你刚才的那个场景中，你更看重哪个维度？
"""
        elif any(kw in user_question for kw in ["标准", "判断"]):
            return """关于"标准"的问题，我觉得没有绝对的标准，但有相对的共识。

**我想先了解**：你是在问什么样的标准？

- 评价回答质量的标准？
- 判断系统是否理解你的标准？
- 还是其他？

不同场景下的"好标准"可能完全不同。

**你能具体说说**：你刚才希望我达到什么样的标准？
"""
        else:
            return f"""这是一个很有深度的问题。"{user_question}"——这其实是在探讨价值的定义。

**我想先理解你的语境**：
- 你是在反思刚才的对话吗？
- 还是在探讨一个更普遍的问题？

如果是关于刚才的对话，**你觉得哪里没有达到你的期望**？
"""

    def _handle_meta_question(self, user_question: str, meta_type: str = "meta") -> str:
        """处理元认知问题"""
        return f"""关于「{user_question}」——这是一个元认知层面的问题。

让我从几个角度来思考：

1. **从系统角度**，我可以...
2. **从对话角度**，我觉得...
3. **从成长角度**，我注意到...

你更希望我从哪个角度展开？
"""

    def _decompose_and_execute(self, intent: Intent) -> Optional[str]:
        """分解复杂任务并执行"""
        try:
            if not hasattr(self, 'task_decomposer') or self.task_decomposer is None:
                logger.warning("任务分解器不可用，使用联邦调度")
                return self._parallel_schedule(intent)
            llm_adapter = self.adapters.get('code_light') or next(iter(self.adapters.values()))
            subtasks = self.task_decomposer.decompose_with_llm(intent.raw_text, llm_adapter=llm_adapter)
            if len(subtasks) <= 1:
                logger.info("任务无法分解，使用联邦调度")
                return self._parallel_schedule(intent)
            logger.info(f"任务已分解为 {len(subtasks)} 个子任务")
            results = []
            for i, subtask in enumerate(subtasks):
                try:
                    result = self._parallel_schedule(subtask)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"子任务{i}执行失败: {e}")
            if not results:
                return None
            if len(results) == 1:
                return results[0]
            combined = "\n\n---\n\n".join(results)
            return combined
        except Exception as e:
            logger.error(f"分解执行异常: {e}")
            return None
