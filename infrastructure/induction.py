import json
import sqlite3
from datetime import datetime
from loguru import logger
from infrastructure.experience_pool import ExperiencePool

class InductionEngine:
    def __init__(self, pool: ExperiencePool):
        self.pool = pool

    def induce_rules(self, intent_type: str = None, model_name: str = "qwen2.5-coder:1.5b"):
        """离线归纳规则（调用轻量模型）"""
        # 获取高质量经验和失败经验
        good = self.pool.get_high_quality_experiences(intent_type, min_quality=70, limit=30)
        bad = self.pool.get_failed_experiences(intent_type, limit=20)

        if not good and not bad:
            logger.info("没有足够经验进行归纳")
            return []

        # 构建 prompt
        prompt = f"""你是一个智能助手系统的规划规则生成器。请根据以下成功和失败的案例，归纳出通用的规划规则。

成功案例（质量分≥70）:
{self._format_experiences(good)}

失败案例（质量分<50且无正面反馈）:
{self._format_experiences(bad)}

请输出 JSON 格式的规则数组，每个规则包含：
- condition: 触发条件（自然语言）
- action: 建议行动
- priority: 优先级（1-5，1最高）

只输出 JSON，不要其他解释。
"""
        # 调用本地模型进行归纳（可复用 OllamaAdapter）
        from adapters.llm.ollama_adapter import OllamaAdapter
        adapter = OllamaAdapter(model_name=model_name)
        try:
            response = adapter.generate(prompt, task_type="induction", timeout=180)
            # 解析 JSON
            import re
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                rules = json.loads(json_match.group())
                # 存储规则到文件
                self._save_rules(rules, intent_type)
                logger.info(f"归纳生成 {len(rules)} 条新规则")
                return rules
            else:
                logger.warning("响应中未找到 JSON")
                return []
        except Exception as e:
            logger.error(f"归纳失败: {e}")
            return []

    def _format_experiences(self, exps):
        if not exps:
            return "无"
        lines = []
        for exp in exps:
            lines.append(f"- 输入: {exp['raw_input'][:80]}")
            lines.append(f"  计划: {exp['plan'][:100]}")
            lines.append(f"  质量: {exp['quality_score']}, 反馈: {exp.get('user_feedback',0)}")
        return "\n".join(lines)

    def _save_rules(self, rules, intent_type):
        """保存规则到文件，供规划器加载"""
        rules_file = f"config/rules_{intent_type}.json" if intent_type else "config/rules_general.json"
        import os
        os.makedirs("config", exist_ok=True)
        with open(rules_file, 'w', encoding='utf-8') as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
        logger.info(f"规则已保存至 {rules_file}")
