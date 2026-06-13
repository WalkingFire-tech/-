"""
认知层集成器 - 统一协调四个核心组件
提供逻辑导向模式的核心入口

核心能力：
- 统一认知流程
- 生成分析报告
- 支持动态降级
"""
from typing import Dict, Optional
from loguru import logger
from infrastructure.problem_analyzer import problem_analyzer
from infrastructure.causal_reasoner import causal_reasoner
from infrastructure.plan_generator import plan_generator
from infrastructure.uncertainty_estimator import uncertainty_estimator


class CognitiveLayer:
    """认知层 - 系统核心中枢"""
    
    def __init__(self):
        logger.info("认知层初始化完成")
    
    def analyze(
        self,
        text: str,
        intent_type: str = None,
        context: str = ""
    ) -> Dict:
        """
        认知分析主入口
        
        Args:
            text: 用户输入
            intent_type: 意图类型
            context: 上下文
        
        Returns:
            完整的认知分析结果
        """
        logger.info(f"认知层开始分析: {text[:50]}...")
        
        # 1. 问题分析
        analysis = problem_analyzer.analyze(text, intent_type)
        
        # 2. 因果推理
        causal_chain = causal_reasoner.reason(
            analysis["core_need"],
            analysis,
            context
        )
        
        # 3. 规划生成
        subtasks = plan_generator.generate(analysis, causal_chain)
        
        # 4. 不确定性评估
        uncertainty = uncertainty_estimator.estimate(
            subtasks,
            analysis,
            causal_chain
        )
        
        # 5. 组装结果
        result = {
            "analysis": analysis,
            "causal_chain": causal_chain,
            "subtasks": subtasks,
            "uncertainty": uncertainty,
            "summary": self._generate_summary(analysis, subtasks, uncertainty)
        }
        
        logger.info(f"认知层分析完成: {len(subtasks)}个子任务, "
                   f"置信度={uncertainty['overall_confidence']:.2f}")
        
        return result
    
    def generate_report(self, result: Dict) -> str:
        """
        生成人类可读的分析报告
        
        Args:
            result: 认知分析结果
        
        Returns:
            Markdown格式的报告
        """
        report = []
        
        # 标题
        report.append("# 问题分析报告")
        report.append("")
        
        # 问题分析
        report.append("## 问题分析")
        report.append("")
        analysis = result["analysis"]
        report.append(f"**核心需求**：{analysis['core_need']}")
        report.append("")
        
        # 已知信息
        known_info = analysis.get("known_info", [])
        if known_info:
            report.append("**已知信息**：")
            for info in known_info:
                report.append(f"- {info['description']}")
            report.append("")
        
        # 信息缺口
        gaps = analysis.get("info_gaps", [])
        if gaps:
            report.append("**信息缺口**：")
            for gap in gaps:
                importance = "⚠️" if gap.get("importance") == "high" else "ℹ️"
                report.append(f"- {importance} {gap['description']}")
            report.append("")
        
        # 因果链
        causal_chain = result.get("causal_chain", [])
        if causal_chain:
            report.append("## 因果链")
            report.append("")
            for causal in causal_chain[:5]:  # 最多显示5条
                conf = causal.get("confidence", 0)
                conf_str = f"(置信度: {conf:.0%})"
                report.append(f"- **{causal['cause']}** → {causal['effect']} {conf_str}")
            report.append("")
        
        # 执行计划
        subtasks = result.get("subtasks", [])
        if subtasks:
            report.append("## 执行计划")
            report.append("")
            for task in subtasks:
                resource_icon = {
                    "human": "👤",
                    "local_model": "🤖",
                    "remote_api": "🌐",
                    "none": "⚙️"
                }.get(task.required_resource, "❓")
                
                deps = f"(依赖: {task.dependencies})" if task.dependencies else ""
                report.append(f"{task.id}. {resource_icon} **{task.description}** {deps}")
                report.append(f"   - 资源: {task.required_resource} | 预期: {task.expected_output_type}")
                report.append(f"   - 优先级: {task.priority} | 预计耗时: {task.estimated_duration}s")
            report.append("")
        
        # 风险与不确定性
        uncertainty = result.get("uncertainty", {})
        risks = uncertainty.get("risks", [])
        if risks:
            report.append("## 风险与不确定性")
            report.append("")
            report.append(f"**整体置信度**：{uncertainty.get('overall_confidence', 0):.0%}")
            report.append("")
            
            for risk in risks:
                severity_icon = {
                    "high": "🔴",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(risk["severity"], "⚪")
                
                report.append(f"{severity_icon} **{risk['description']}**")
                report.append(f"   - 影响: {risk['impact']}")
                if risk.get("mitigation"):
                    report.append(f"   - 缓解: {risk['mitigation']}")
            report.append("")
        
        # 替代方案
        alternatives = uncertainty.get("alternatives", [])
        if alternatives:
            report.append("## 替代方案")
            report.append("")
            for alt in alternatives[:3]:  # 最多显示3个
                report.append(f"- **{alt['description']}**")
                report.append(f"  - 适用: {alt['applicable_to']}")
                report.append(f"  - 代价: {alt['trade_off']}")
            report.append("")
        
        # 建议
        recommendations = uncertainty.get("recommendations", [])
        if recommendations:
            report.append("## 协作建议")
            report.append("")
            for rec in recommendations:
                report.append(f"- {rec}")
            report.append("")
        
        # 摘要
        summary = result.get("summary", "")
        if summary:
            report.append("---")
            report.append("")
            report.append(f"_摘要: {summary}_")
        
        return "\n".join(report)
    
    def _generate_summary(
        self,
        analysis: Dict,
        subtasks: list,
        uncertainty: Dict
    ) -> str:
        """生成摘要"""
        core = analysis.get("core_need", "")[:50]
        n_tasks = len(subtasks)
        conf = uncertainty.get("overall_confidence", 0)
        
        return f"问题'{core}'已分解为{n_tasks}个子任务，整体置信度{conf:.0%}"


# 全局实例
cognitive_layer = CognitiveLayer()