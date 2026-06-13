"""
自我反思报告生成器 - 定期生成系统进化报告
分析能力矩阵变化、调度成功率、规则激活情况
"""
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from loguru import logger


class SelfReflectionReport:
    """自我反思报告生成器"""
    
    def __init__(self, report_dir: str = "reports"):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True)
        logger.info("自我反思报告生成器已初始化")
    
    def generate_weekly_report(self) -> Dict:
        """生成周报
        
        Returns:
            报告数据
        """
        now = datetime.now()
        week_start = now - timedelta(days=7)
        
        report = {
            'period': {
                'start': week_start.isoformat(),
                'end': now.isoformat(),
                'type': 'weekly'
            },
            'generated_at': now.isoformat(),
            'summary': {},
            'details': {}
        }
        
        # 1. 能力矩阵变化
        report['details']['capability_changes'] = self._analyze_capability_changes(week_start)
        
        # 2. 调度成功率
        report['details']['scheduling_stats'] = self._analyze_scheduling_stats(week_start)
        
        # 3. 规则激活情况
        report['details']['rule_activation'] = self._analyze_rule_activation(week_start)
        
        # 4. 任务分解效果
        report['details']['decomposition_stats'] = self._analyze_decomposition_stats(week_start)
        
        # 5. 结果融合效果
        report['details']['fusion_stats'] = self._analyze_fusion_stats(week_start)
        
        # 6. 生成总结
        report['summary'] = self._generate_summary(report['details'])
        
        # 7. 保存报告
        self._save_report(report)
        
        return report
    
    def _analyze_capability_changes(self, since: datetime) -> Dict:
        """分析能力矩阵变化"""
        try:
            from infrastructure.model_capability import model_capability
            
            matrix = model_capability.get_capability_matrix()
            stats = model_capability.export_stats()
            
            return {
                'registered_models': stats['registered_models'],
                'dimensions': stats['dimensions'],
                'matrix': matrix,
                'insights': [
                    f"已注册 {stats['registered_models']} 个模型",
                    f"能力维度: {stats['dimensions']} 个",
                    f"任务类型: {stats['task_types']} 种"
                ]
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_scheduling_stats(self, since: datetime) -> Dict:
        """分析调度统计"""
        try:
            from infrastructure.parallel_scheduler import parallel_scheduler
            
            stats = parallel_scheduler.get_stats(days=7)
            
            insights = []
            if stats['success_rate'] > 0.9:
                insights.append("✓ 调度成功率优秀 (>90%)")
            elif stats['success_rate'] > 0.7:
                insights.append("⚠ 调度成功率良好 (70-90%)")
            else:
                insights.append("✗ 调度成功率需要改进 (<70%)")
            
            if stats['avg_duration'] < 3:
                insights.append("✓ 平均响应速度快 (<3s)")
            elif stats['avg_duration'] < 10:
                insights.append("⚠ 平均响应速度中等 (3-10s)")
            else:
                insights.append("✗ 平均响应速度慢 (>10s)")
            
            return {
                'total_calls': stats['total_calls'],
                'success_rate': stats['success_rate'],
                'avg_duration': stats['avg_duration'],
                'unique_tasks': stats['unique_tasks'],
                'insights': insights
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_rule_activation(self, since: datetime) -> Dict:
        """分析规则激活情况"""
        try:
            conn = sqlite3.connect('learning_rules.db')
            
            # 活跃规则数
            cursor = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            active_rules = cursor.fetchone()[0]
            
            # Pending规则数
            cursor = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status='pending'")
            pending_rules = cursor.fetchone()[0]
            
            # 最近激活的规则
            cursor = conn.execute('''
                SELECT id, condition, action, confidence
                FROM learning_rules
                WHERE status='active'
                ORDER BY last_applied DESC
                LIMIT 5
            ''')
            recent_rules = cursor.fetchall()
            
            conn.close()
            
            insights = []
            if active_rules > 20:
                insights.append(f"✓ 活跃规则充足 ({active_rules}条)")
            else:
                insights.append(f"⚠ 活跃规则较少 ({active_rules}条)")
            
            if pending_rules > 10:
                insights.append(f"⚠ 有 {pending_rules} 条规则待激活")
            
            return {
                'active_rules': active_rules,
                'pending_rules': pending_rules,
                'recent_rules': [
                    {'id': r[0], 'condition': r[1], 'action': r[2], 'confidence': r[3]}
                    for r in recent_rules
                ],
                'insights': insights
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_decomposition_stats(self, since: datetime) -> Dict:
        """分析任务分解效果"""
        try:
            from infrastructure.task_decomposer import task_decomposer
            
            stats = task_decomposer.get_decomposition_stats()
            
            return {
                'total_decompositions': stats['total_decompositions'],
                'avg_quality': stats['avg_quality'],
                'insights': [
                    f"总分解次数: {stats['total_decompositions']}",
                    f"平均质量: {stats['avg_quality']:.2f}"
                ]
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_fusion_stats(self, since: datetime) -> Dict:
        """分析结果融合效果"""
        try:
            from infrastructure.result_fusion import result_fusion
            
            stats = result_fusion.get_fusion_stats()
            
            return {
                'total_fusions': stats['total_fusions'],
                'strategies': stats['strategies'],
                'insights': [
                    f"总融合次数: {stats['total_fusions']}",
                    f"策略分布: {stats['strategies']}"
                ]
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _generate_summary(self, details: Dict) -> Dict:
        """生成总结"""
        all_insights = []
        
        for category, data in details.items():
            if isinstance(data, dict) and 'insights' in data:
                all_insights.extend(data['insights'])
        
        # 评估系统健康度
        health_score = 0.0
        
        # 调度成功率贡献
        if 'scheduling_stats' in details:
            success_rate = details['scheduling_stats'].get('success_rate', 0)
            health_score += success_rate * 40
        
        # 活跃规则贡献
        if 'rule_activation' in details:
            active_rules = details['rule_activation'].get('active_rules', 0)
            health_score += min(30, active_rules)
        
        # 能力矩阵贡献
        if 'capability_changes' in details:
            models = details['capability_changes'].get('registered_models', 0)
            health_score += min(30, models * 5)
        
        return {
            'health_score': health_score,
            'total_insights': len(all_insights),
            'insights': all_insights,
            'recommendations': self._generate_recommendations(details)
        }
    
    def _generate_recommendations(self, details: Dict) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于调度成功率
        if 'scheduling_stats' in details:
            success_rate = details['scheduling_stats'].get('success_rate', 0)
            if success_rate < 0.7:
                recommendations.append("建议检查模型可用性，提高调度成功率")
        
        # 基于规则激活
        if 'rule_activation' in details:
            pending = details['rule_activation'].get('pending_rules', 0)
            if pending > 10:
                recommendations.append(f"建议激活 {pending} 条待处理规则")
        
        # 基于能力矩阵
        if 'capability_changes' in details:
            models = details['capability_changes'].get('registered_models', 0)
            if models < 3:
                recommendations.append("建议注册更多模型，提升调度灵活性")
        
        if not recommendations:
            recommendations.append("系统运行良好，继续保持")
        
        return recommendations
    
    def _save_report(self, report: Dict):
        """保存报告"""
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.report_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"报告已保存: {filepath}")
    
    def print_report(self, report: Dict):
        """打印报告"""
        print("\n" + "=" * 70)
        print("自我反思周报")
        print("=" * 70)
        
        print(f"\n生成时间: {report['generated_at']}")
        print(f"统计周期: {report['period']['start']} 至 {report['period']['end']}")
        
        print("\n" + "-" * 70)
        print("系统健康度")
        print("-" * 70)
        print(f"健康得分: {report['summary']['health_score']:.1f}/100")
        
        print("\n" + "-" * 70)
        print("关键洞察")
        print("-" * 70)
        for insight in report['summary']['insights']:
            print(f"  {insight}")
        
        print("\n" + "-" * 70)
        print("改进建议")
        print("-" * 70)
        for i, rec in enumerate(report['summary']['recommendations'], 1):
            print(f"  {i}. {rec}")


self_reflection = SelfReflectionReport()


def generate_weekly_report():
    """生成并打印周报"""
    report = self_reflection.generate_weekly_report()
    self_reflection.print_report(report)
    return report


if __name__ == "__main__":
    generate_weekly_report()