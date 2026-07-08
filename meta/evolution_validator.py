"""
自我进化验证系统
用于观察、度量和验证系统的自我进化能力
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from loguru import logger
from infrastructure.database_manager import DatabaseManager


class EvolutionValidator:
    """自我进化验证器"""
    
    def __init__(self):
        self.experience_db = "experience_pool.db"
        self.rules_db = "learning_rules.db"
        self.stats_db = "model_stats.db"
        
    def get_evolution_metrics(self) -> Dict[str, Any]:
        """
        获取自我进化的元指标
        
        Returns:
            包含所有进化指标的字典
        """
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "experience_metrics": self._get_experience_metrics(),
            "rule_metrics": self._get_rule_metrics(),
            "quality_metrics": self._get_quality_metrics(),
            "evolution_score": 0.0
        }
        
        # 计算综合进化分数
        metrics["evolution_score"] = self._calculate_evolution_score(metrics)
        
        return metrics
    
    def _get_experience_metrics(self) -> Dict:
        """经验池指标"""
        try:
            conn = DatabaseManager.get(self.experience_db)._get_conn()
            cursor = conn.cursor()
            
            # 总经验数
            cursor.execute("SELECT COUNT(*) FROM experiences")
            total = cursor.fetchone()[0]
            
            # 高质量经验数（质量分 >= 0.7）
            cursor.execute("SELECT COUNT(*) FROM experiences WHERE quality_score >= 0.7")
            high_quality = cursor.fetchone()[0]
            
            # 最近7天新增
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute("SELECT COUNT(*) FROM experiences WHERE timestamp >= ?", (week_ago,))
            recent = cursor.fetchone()[0]
            
            # 平均质量分
            cursor.execute("SELECT AVG(quality_score) FROM experiences")
            avg_quality = cursor.fetchone()[0] or 0.0
            
            # 按意图类型分布
            cursor.execute("""
                SELECT intent_type, COUNT(*), AVG(quality_score)
                FROM experiences
                GROUP BY intent_type
            """)
            by_intent = {row[0]: {"count": row[1], "avg_quality": row[2]} for row in cursor.fetchall()}
            
            return {
                "total": total,
                "high_quality": high_quality,
                "recent_week": recent,
                "avg_quality": round(avg_quality, 3),
                "by_intent": by_intent,
                "quality_rate": round(high_quality / total, 3) if total > 0 else 0.0
            }
            
        except Exception as e:
            logger.error(f"获取经验指标失败: {e}")
            return {"error": str(e)}
    
    def _get_rule_metrics(self) -> Dict:
        """规则指标"""
        try:
            conn = DatabaseManager.get(self.rules_db)._get_conn()
            cursor = conn.cursor()
            
            # 检查表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # 使用正确的表名
            table_name = "learning_rules" if "learning_rules" in tables else "rules"
            
            # 总规则数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total = cursor.fetchone()[0]
            
            # 按状态统计
            cursor.execute(f"""
                SELECT status, COUNT(*)
                FROM {table_name}
                GROUP BY status
            """)
            by_status = dict(cursor.fetchall())
            
            # 活跃规则数
            active = by_status.get("active", 0)
            
            # 待激活规则数
            pending = by_status.get("pending", 0)
            
            # 平均置信度
            cursor.execute(f"SELECT AVG(confidence) FROM {table_name} WHERE status='active'")
            avg_confidence = cursor.fetchone()[0] or 0.0
            
            # 最近激活的规则
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute(f"""
                SELECT COUNT(*) FROM {table_name}
                WHERE status='active' AND activated_at >= ?
            """, (week_ago,))
            recent_activated = cursor.fetchone()[0]
            
            # 规则应用次数（如果有trigger_count字段）
            try:
                cursor.execute(f"SELECT SUM(trigger_count) FROM {table_name}")
                total_triggers = cursor.fetchone()[0] or 0
            except:
                total_triggers = 0
            
            return {
                "total": total,
                "active": active,
                "pending": pending,
                "by_status": by_status,
                "avg_confidence": round(avg_confidence, 3),
                "recent_activated": recent_activated,
                "total_triggers": total_triggers,
                "activation_rate": round(active / total, 3) if total > 0 else 0.0
            }
            
        except Exception as e:
            logger.error(f"获取规则指标失败: {e}")
            return {"error": str(e)}
    
    def _get_quality_metrics(self) -> Dict:
        """质量指标"""
        try:
            conn = DatabaseManager.get(self.stats_db)._get_conn()
            cursor = conn.cursor()
            
            # 检查表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # 使用正确的表名
            table_name = "model_performance" if "model_performance" in tables else "model_stats"
            
            # 总调用次数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_calls = cursor.fetchone()[0]
            
            # 平均质量分
            cursor.execute(f"SELECT AVG(quality_score) FROM {table_name}")
            avg_quality = cursor.fetchone()[0] or 0.0
            
            # 按模型统计
            cursor.execute(f"""
                SELECT model_name, COUNT(*), AVG(quality_score), AVG(response_time)
                FROM {table_name}
                GROUP BY model_name
            """)
            by_model = {}
            for row in cursor.fetchall():
                by_model[row[0]] = {
                    "calls": row[1],
                    "avg_quality": round(row[2], 3) if row[2] else 0.0,
                    "avg_time": round(row[3], 2) if row[3] else 0.0
                }
            
            # 最近7天质量趋势
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute(f"""
                SELECT AVG(quality_score)
                FROM {table_name}
                WHERE timestamp >= ?
            """, (week_ago,))
            recent_quality = cursor.fetchone()[0] or 0.0
            
            # 用户干预次数（feedback）
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE feedback < 0")
                negative_feedback = cursor.fetchone()[0]
                
                cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE feedback > 0")
                positive_feedback = cursor.fetchone()[0]
            except:
                negative_feedback = 0
                positive_feedback = 0
            
            return {
                "total_calls": total_calls,
                "avg_quality": round(avg_quality, 3),
                "by_model": by_model,
                "recent_quality": round(recent_quality, 3),
                "positive_feedback": positive_feedback,
                "negative_feedback": negative_feedback,
                "feedback_rate": round((positive_feedback + negative_feedback) / total_calls, 3) if total_calls > 0 else 0.0
            }
            
        except Exception as e:
            logger.error(f"获取质量指标失败: {e}")
            return {"error": str(e)}
    
    def _calculate_evolution_score(self, metrics: Dict) -> float:
        """
        计算综合进化分数 (0-100)
        
        评分维度：
        - 经验积累 (30分)
        - 规则有效性 (30分)
        - 质量提升 (25分)
        - 反馈闭环 (15分)
        """
        score = 0.0
        
        # 1. 经验积累 (30分)
        exp_metrics = metrics.get("experience_metrics", {})
        exp_total = exp_metrics.get("total", 0)
        exp_quality = exp_metrics.get("avg_quality", 0)
        
        if exp_total >= 100:
            score += 15
        elif exp_total >= 50:
            score += 10
        elif exp_total >= 20:
            score += 5
        
        if exp_quality >= 0.7:
            score += 15
        elif exp_quality >= 0.5:
            score += 10
        elif exp_quality >= 0.3:
            score += 5
        
        # 2. 规则有效性 (30分)
        rule_metrics = metrics.get("rule_metrics", {})
        active_rules = rule_metrics.get("active", 0)
        rule_confidence = rule_metrics.get("avg_confidence", 0)
        
        if active_rules >= 10:
            score += 15
        elif active_rules >= 5:
            score += 10
        elif active_rules >= 2:
            score += 5
        
        if rule_confidence >= 0.8:
            score += 15
        elif rule_confidence >= 0.6:
            score += 10
        elif rule_confidence >= 0.4:
            score += 5
        
        # 3. 质量提升 (25分)
        quality_metrics = metrics.get("quality_metrics", {})
        avg_quality = quality_metrics.get("avg_quality", 0)
        recent_quality = quality_metrics.get("recent_quality", 0)
        
        if avg_quality >= 0.8:
            score += 15
        elif avg_quality >= 0.6:
            score += 10
        elif avg_quality >= 0.4:
            score += 5
        
        # 质量趋势（最近是否提升）
        if recent_quality > avg_quality:
            score += 10
        elif recent_quality >= avg_quality * 0.9:
            score += 5
        
        # 4. 反馈闭环 (15分)
        feedback_rate = quality_metrics.get("feedback_rate", 0)
        
        if feedback_rate >= 0.3:
            score += 15
        elif feedback_rate >= 0.1:
            score += 10
        elif feedback_rate > 0:
            score += 5
        
        return round(score, 1)
    
    def generate_report(self) -> str:
        """生成进化报告"""
        metrics = self.get_evolution_metrics()
        
        report = [
            "=" * 70,
            "🔥 联盟拓荒者 - 自我进化验证报告",
            "=" * 70,
            f"\n生成时间: {metrics['timestamp']}",
            f"\n【综合进化分数】 {metrics['evolution_score']}/100",
            "\n" + "-" * 70,
        ]
        
        # 经验指标
        exp = metrics["experience_metrics"]
        report.extend([
            "\n【经验池状态】",
            f"  总经验数: {exp.get('total', 0)}",
            f"  高质量经验: {exp.get('high_quality', 0)} ({exp.get('quality_rate', 0):.1%})",
            f"  最近7天新增: {exp.get('recent_week', 0)}",
            f"  平均质量分: {exp.get('avg_quality', 0):.3f}",
        ])
        
        # 规则指标
        rule = metrics["rule_metrics"]
        report.extend([
            "\n【学习规则状态】",
            f"  总规则数: {rule.get('total', 0)}",
            f"  活跃规则: {rule.get('active', 0)} ({rule.get('activation_rate', 0):.1%})",
            f"  待激活规则: {rule.get('pending', 0)}",
            f"  平均置信度: {rule.get('avg_confidence', 0):.3f}",
            f"  最近激活: {rule.get('recent_activated', 0)}",
        ])
        
        # 质量指标
        quality = metrics["quality_metrics"]
        report.extend([
            "\n【质量评估状态】",
            f"  总调用次数: {quality.get('total_calls', 0)}",
            f"  平均质量分: {quality.get('avg_quality', 0):.3f}",
            f"  最近7天质量: {quality.get('recent_quality', 0):.3f}",
            f"  正面反馈: {quality.get('positive_feedback', 0)}",
            f"  负面反馈: {quality.get('negative_feedback', 0)}",
        ])
        
        # 评估建议
        report.extend([
            "\n" + "-" * 70,
            "\n【进化评估】",
        ])
        
        score = metrics['evolution_score']
        if score >= 80:
            report.append("  ✅ 自我进化能力优秀，系统正在持续改进")
        elif score >= 60:
            report.append("  ⚠️  自我进化能力良好，但仍有提升空间")
        elif score >= 40:
            report.append("  ⚠️  自我进化能力一般，需要更多数据和反馈")
        else:
            report.append("  ❌ 自我进化能力不足，需要积累经验和规则")
        
        # 具体建议
        if exp.get('total', 0) < 30:
            report.append("  💡 建议: 积累更多经验（至少30条）以触发归纳")
        
        if rule.get('active', 0) < 5:
            report.append("  💡 建议: 手动运行归纳总结生成更多规则")
        
        if quality.get('feedback_rate', 0) < 0.1:
            report.append("  💡 建议: 鼓励用户提供反馈以形成学习闭环")
        
        report.append("\n" + "=" * 70)
        
        return "\n".join(report)


def run_smoke_test():
    """
    烟雾测试 - 验证自我进化的基本功能
    """
    print("=" * 70)
    print("🔥 自我进化烟雾测试")
    print("=" * 70)
    
    validator = EvolutionValidator()
    
    # 测试1: 经验积累
    print("\n[测试1] 经验积累检查")
    metrics = validator.get_evolution_metrics()
    exp_total = metrics["experience_metrics"].get("total", 0)
    print(f"  经验总数: {exp_total}")
    if exp_total >= 20:
        print("  ✓ 经验积累充足")
    else:
        print("  ✗ 经验不足，建议积累更多数据")
    
    # 测试2: 规则生成
    print("\n[测试2] 规则生成检查")
    active_rules = metrics["rule_metrics"].get("active", 0)
    print(f"  活跃规则: {active_rules}")
    if active_rules >= 2:
        print("  ✓ 规则生成有效")
    else:
        print("  ✗ 规则不足，建议运行归纳")
    
    # 测试3: 质量评估
    print("\n[测试3] 质量评估检查")
    avg_quality = metrics["quality_metrics"].get("avg_quality", 0)
    print(f"  平均质量: {avg_quality:.3f}")
    if avg_quality >= 0.5:
        print("  ✓ 质量评估正常")
    else:
        print("  ✗ 质量偏低，需要优化")
    
    # 测试4: 进化分数
    print("\n[测试4] 综合进化分数")
    score = metrics["evolution_score"]
    print(f"  进化分数: {score}/100")
    if score >= 60:
        print("  ✓ 自我进化能力验证通过")
    else:
        print("  ✗ 自我进化能力需要改进")
    
    print("\n" + "=" * 70)
    print("烟雾测试完成")
    print("=" * 70)
    
    return metrics


if __name__ == "__main__":
    # 生成完整报告
    validator = EvolutionValidator()
    print(validator.generate_report())
    
    print("\n")
    
    # 运行烟雾测试
    run_smoke_test()
