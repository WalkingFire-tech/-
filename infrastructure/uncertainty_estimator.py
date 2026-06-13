"""
不确定性评估器 - 认知层核心组件
评估每个环节的不确定性，标注风险和替代方案

核心能力：
- 评估置信度
- 识别风险
- 生成替代方案
"""
from typing import Dict, List
from loguru import logger
from infrastructure.config_manager import config


class UncertaintyEstimator:
    """不确定性评估器 - 认知层第四步"""
    
    def __init__(self):
        self.risk_thresholds = {
            "high": 0.7,
            "medium": 0.5,
            "low": 0.3
        }
        logger.info("不确定性评估器初始化完成")
    
    def estimate(
        self,
        subtasks: List,
        analysis: Dict,
        causal_chain: List[Dict]
    ) -> Dict:
        """
        评估整体不确定性
        
        Args:
            subtasks: 子任务列表
            analysis: 问题分析结果
            causal_chain: 因果链
        
        Returns:
            {
                "overall_confidence": 整体置信度,
                "risks": 风险列表,
                "alternatives": 替代方案,
                "recommendations": 建议
            }
        """
        logger.info("开始不确定性评估...")
        
        # 1. 评估每个子任务的不确定性
        task_uncertainties = [self._estimate_task_uncertainty(task) for task in subtasks]
        
        # 2. 计算整体置信度
        overall_confidence = self._calculate_overall_confidence(task_uncertainties)
        
        # 3. 识别风险
        risks = self._identify_risks(subtasks, analysis, causal_chain)
        
        # 4. 生成替代方案
        alternatives = self._generate_alternatives(subtasks, risks)
        
        # 5. 生成建议
        recommendations = self._generate_recommendations(risks, alternatives)
        
        result = {
            "overall_confidence": overall_confidence,
            "risks": risks,
            "alternatives": alternatives,
            "recommendations": recommendations,
            "task_uncertainties": task_uncertainties
        }
        
        logger.info(f"不确定性评估完成: 整体置信度={overall_confidence:.2f}, "
                   f"风险数={len(risks)}")
        
        return result
    
    def _estimate_task_uncertainty(self, task) -> float:
        """评估单个任务的不确定性"""
        uncertainty = task.uncertainty
        
        # 根据资源类型调整
        if task.required_resource == "human":
            uncertainty += 0.2  # 人工交互不确定性高
        elif task.required_resource == "remote_api":
            uncertainty += 0.15  # 远程API可能失败
        elif task.required_resource == "local_model":
            uncertainty += 0.1  # 本地模型可能质量不足
        
        # 根据优先级调整
        if task.priority >= 4:
            uncertainty *= 1.2  # 高优先级任务失败影响更大
        
        return min(uncertainty, 1.0)
    
    def _calculate_overall_confidence(self, uncertainties: List[float]) -> float:
        """计算整体置信度"""
        if not uncertainties:
            return 1.0
        
        # 使用加权平均
        avg_uncertainty = sum(uncertainties) / len(uncertainties)
        
        # 考虑最坏情况
        max_uncertainty = max(uncertainties)
        
        # 综合置信度
        confidence = 1.0 - (avg_uncertainty * 0.6 + max_uncertainty * 0.4)
        
        return max(0.0, confidence)
    
    def _identify_risks(
        self,
        subtasks: List,
        analysis: Dict,
        causal_chain: List[Dict]
    ) -> List[Dict]:
        """识别风险"""
        risks = []
        
        # 1. 信息缺口风险
        gaps = analysis.get("info_gaps", [])
        for gap in gaps:
            if gap.get("importance") == "high":
                risks.append({
                    "type": "info_gap",
                    "description": f"关键信息缺失：{gap['description']}",
                    "impact": "可能导致结果不符合预期",
                    "severity": "high",
                    "mitigation": f"建议先澄清：{gap['description']}"
                })
        
        # 2. 资源风险
        human_tasks = [t for t in subtasks if t.required_resource == "human"]
        if len(human_tasks) > 2:
            risks.append({
                "type": "resource",
                "description": "需要多次人工交互",
                "impact": "可能影响用户体验",
                "severity": "medium",
                "mitigation": "考虑提供默认值或跳过非必要交互"
            })
        
        # 3. 依赖风险
        high_priority_tasks = [t for t in subtasks if t.priority >= 4]
        for task in high_priority_tasks:
            if task.dependencies:
                risks.append({
                    "type": "dependency",
                    "description": f"高优先级任务'{task.description}'有依赖",
                    "impact": "依赖失败会导致任务无法执行",
                    "severity": "medium",
                    "mitigation": "准备降级方案"
                })
        
        # 4. 因果链风险
        for causal in causal_chain:
            if causal.get("confidence", 0) < 0.7:
                risks.append({
                    "type": "causal",
                    "description": f"因果推断不确定：{causal['cause']}",
                    "impact": f"可能影响：{causal['effect']}",
                    "severity": "low",
                    "mitigation": "需要更多信息验证"
                })
        
        return risks
    
    def _generate_alternatives(
        self,
        subtasks: List,
        risks: List[Dict]
    ) -> List[Dict]:
        """生成替代方案"""
        alternatives = []
        
        # 1. 为高风险任务生成替代方案
        for risk in risks:
            if risk["severity"] == "high":
                if risk["type"] == "info_gap":
                    alternatives.append({
                        "description": "使用默认假设继续",
                        "applicable_to": risk["description"],
                        "trade_off": "可能需要后续修正"
                    })
        
        # 2. 为人工任务生成自动化替代
        human_tasks = [t for t in subtasks if t.required_resource == "human"]
        for task in human_tasks:
            alternatives.append({
                "description": f"使用本地模型替代人工决策：{task.description}",
                "applicable_to": f"任务{task.id}",
                "trade_off": "决策质量可能降低"
            })
        
        # 3. 为远程API任务生成本地替代
        remote_tasks = [t for t in subtasks if t.required_resource == "remote_api"]
        for task in remote_tasks:
            alternatives.append({
                "description": f"使用本地模型替代远程API：{task.description}",
                "applicable_to": f"任务{task.id}",
                "trade_off": "结果质量可能降低，但响应更快"
            })
        
        return alternatives
    
    def _generate_recommendations(
        self,
        risks: List[Dict],
        alternatives: List[Dict]
    ) -> List[str]:
        """生成建议"""
        recommendations = []
        
        # 基于风险的建议
        high_risks = [r for r in risks if r["severity"] == "high"]
        if high_risks:
            recommendations.append("建议先解决高风险问题再继续执行")
        
        for risk in high_risks:
            if risk.get("mitigation"):
                recommendations.append(risk["mitigation"])
        
        # 基于替代方案的建议
        if alternatives:
            recommendations.append("如果资源受限，可考虑使用替代方案")
        
        # 通用建议
        if len(risks) > 3:
            recommendations.append("风险较多，建议分阶段执行并验证每个阶段结果")
        
        return recommendations


# 全局实例
uncertainty_estimator = UncertaintyEstimator()