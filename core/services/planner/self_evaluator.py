"""
自我评估 mixin — 能力边界、置信度、质量评估
"""
from typing import Optional
from loguru import logger
from core.ports.adapters import get_storage_port
from core.services.intent_parser import Intent


class SelfEvaluatorMixin:
    """自我评估能力：边界报告、置信度计算、质量评估"""

    def _init_evaluator(self):
        self._evaluation_history = []
        self._confidence_threshold = 0.7

    def _report_capability_boundary(self) -> str:
        """报告能力边界"""
        try:
            from infrastructure.health_dashboard import health_dashboard
            from infrastructure.model_capability import model_capability
            aphi = health_dashboard.calculate_aphi()
            cap_stats = model_capability.export_stats()
            models = list(self.adapters.keys())
            report = f"""
╔══════════════════════════════════════════════════════════╗
║              联盟拓荒者能力边界报告                        ║
╚══════════════════════════════════════════════════════════╝

📊 健康状态
- APHI指数: {aphi['aphi']}/100
- 运行模式: {aphi['mode']}
- 任务成功率: {aphi['task_success_rate']}%
- 用户满意度: {aphi['user_satisfaction']}%

🤖 可用模型 ({len(models)}个)
"""
            for model in models:
                report += f"  • {model}\n"
            report += f"""
🧠 能力矩阵
- 已注册模型: {cap_stats.get('total_models', 0)}
- 能力维度: {cap_stats.get('total_dimensions', 0)}
- 平均置信度: {cap_stats.get('avg_confidence', 0):.2f}
"""
            return report
        except Exception as e:
            logger.error(f"能力边界报告生成失败: {e}")
            return "抱歉，我暂时无法获取完整的能力边界信息。请稍后再试。"

    def _report_self_assessment(self) -> str:
        """生成自我评估报告"""
        report = """AI系统自我评估报告\n"""
        try:
            models = list(self.adapters.keys())
            report += f"""
模型状态
- 可用模型: {len(models)}个
- 默认模型: {models[0] if models else '无'}
"""
            return report
        except Exception as e:
            logger.error(f"自我评估报告生成失败: {e}")
            return report

    def _evaluate_recent_dialogs(self) -> str:
        """评估最近对话质量"""
        try:
            conn = get_storage_port()._get_conn('data/experience_pool.db')
            recent = conn.execute(
                "SELECT intent_type, raw_input, quality_score, success, model_name FROM experiences ORDER BY timestamp DESC LIMIT 10"
            ).fetchall()
            if not recent:
                return "暂无对话记录可供评估。"
            report = "📊 最近对话评估\n\n"
            qualities, successes = [], 0
            for r in recent:
                status = "✅" if r[3] else "❌"
                if r[3]:
                    successes += 1
                if r[2] is not None:
                    qualities.append(r[2])
                report += f"{status} [{r[0]}] {str(r[1])[:30]}... 质量:{r[2] or 0:.0f} 模型:{r[4]}\n"
            avg_q = sum(qualities) / len(qualities) if qualities else 0
            rate = successes / len(recent) * 100
            report += f"\n平均质量:{avg_q:.0f} 成功率:{rate:.0f}% 对话数:{len(recent)}\n"
            return report
        except Exception as e:
            logger.error(f"对话评价失败: {e}")
            return "抱歉，无法获取对话评价信息。"

    def _estimate_self_confidence(self, intent: Intent) -> float:
        """评估系统对当前任务的理解置信度 (0~1)"""
        intent_conf = intent.confidence
        try:
            conn = get_storage_port()._get_conn('data/experience_pool.db')
            similar = conn.execute(
                "SELECT success FROM experiences WHERE intent_type = ? ORDER BY timestamp DESC LIMIT 5",
                (intent.type,)
            ).fetchall()
            success_rate = sum(1 for row in similar if row[0]) / max(len(similar), 1)
        except Exception:
            success_rate = 0.5
        complexity = min(1.0, len(intent.raw_text) / 500)
        has_rule = self._match_learning_rule(intent) is not None
        confidence = (0.6 * intent_conf + 0.2 * success_rate + 0.1 * (1 - complexity) + 0.1 * (1.0 if has_rule else 0.0))
        return min(0.95, max(0.05, confidence))

    def _evaluate_quality(self, response: str, task_type: str) -> int:
        """评估响应质量"""
        if not response or len(response) < 10:
            return 20
        score = 50
        if task_type == "code":
            if "def " in response or "class " in response:
                score += 15
            if "```" in response:
                score += 10
            if len(response) > 100:
                score += 10
        elif task_type == "question":
            if len(response) > 50:
                score += 10
            if any(word in response for word in ["因为", "所以", "因此", "由于"]):
                score += 10
            if "?" in response or "？" in response:
                score += 5
        else:
            if len(response) > 30:
                score += 10
            if "。" in response:
                score += 5
        return min(score, 100)
