"""
知识健康度评估 - 多维度评估系统知识水平
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List
from collections import Counter
from loguru import logger

from infrastructure.database_manager import DatabaseManager


class KnowledgeHealthChecker:
    """知识健康度检查器"""
    
    def __init__(self, db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
    
    def check(self) -> Dict:
        """
        执行全面健康检查
        
        Returns:
            {
                "summary": {...},
                "knowledge": {...},
                "memory": {...},
                "skills": {...},
                "rules": {...},
                "quality": {...},
                "topics": {...},
                "trend": {...},
                "score": {...},
                "report": str
            }
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "knowledge": self._check_knowledge(),
            "memory": self._check_memory_layers(),
            "skills": self._check_skills(),
            "rules": self._check_rules(),
            "quality": self._check_quality(),
            "topics": self._check_topics(),
            "trend": self._check_trend(),
            "score": {},
            "report": ""
        }
        
        # 计算综合评分
        result["score"] = self._calculate_score(result)
        # 生成报告文本
        result["report"] = self._generate_report(result)
        
        return result
    
    def _check_knowledge(self) -> Dict:
        """检查知识总量"""
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        
        # 总数
        cur = conn.execute("SELECT COUNT(*) FROM knowledge_items")
        total = cur.fetchone()[0]
        
        # 按类型统计
        cur = conn.execute('''
            SELECT knowledge_type, COUNT(*) as cnt
            FROM knowledge_items
            GROUP BY knowledge_type
        ''')
        by_type = {row['knowledge_type']: row['cnt'] for row in cur.fetchall()}
        
        # 按来源统计
        cur = conn.execute('''
            SELECT source, COUNT(*) as cnt
            FROM knowledge_items
            GROUP BY source
            ORDER BY cnt DESC
            LIMIT 5
        ''')
        top_sources = [{"source": row['source'], "count": row['cnt']} for row in cur.fetchall()]
        
        return {
            "total": total,
            "by_type": by_type,
            "top_sources": top_sources,
            "has_data": total > 0
        }
    
    def _check_memory_layers(self) -> Dict:
        """检查记忆层级"""
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        
        cur = conn.execute('''
            SELECT memory_layer, COUNT(*) as cnt
            FROM knowledge_items
            WHERE memory_layer IS NOT NULL
            GROUP BY memory_layer
        ''')
        
        layers = {row['memory_layer']: row['cnt'] for row in cur.fetchall()}
        
        total = sum(layers.values()) if layers else 0
        
        return {
            "layers": {
                "L1_核心记忆": layers.get(1, 0),
                "L2_框架记忆": layers.get(2, 0),
                "L3_情境碎片": layers.get(3, 0)
            },
            "total": total,
            "layer1_ratio": layers.get(1, 0) / total if total > 0 else 0
        }
    
    def _check_skills(self) -> Dict:
        """检查技能库"""
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        
        cur = conn.execute("SELECT COUNT(*) FROM tools")
        total = cur.fetchone()[0]
        
        cur = conn.execute("""
            SELECT name, usage_count, created_at
            FROM tools
            ORDER BY usage_count DESC
            LIMIT 5
        """)
        top_tools = [dict(row) for row in cur.fetchall()]
        
        cur = conn.execute("SELECT AVG(usage_count) FROM tools")
        avg_usage = cur.fetchone()[0] or 0
        
        return {
            "total": total,
            "top_tools": top_tools,
            "avg_usage": avg_usage,
            "has_skills": total > 0
        }
    
    def _check_rules(self) -> Dict:
        """检查规则库"""
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        
        cur = conn.execute("SELECT COUNT(*) FROM learning_rules")
        total = cur.fetchone()[0]
        
        cur = conn.execute("""
            SELECT status, COUNT(*) as cnt
            FROM learning_rules
            GROUP BY status
        """)
        by_status = {row['status']: row['cnt'] for row in cur.fetchall()}
        
        cur = conn.execute("""
            SELECT AVG(confidence) as avg_confidence
            FROM learning_rules
        """)
        avg_confidence = cur.fetchone()['avg_confidence'] or 0
        
        return {
            "total": total,
            "by_status": by_status,
            "active": by_status.get('active', 0),
            "avg_confidence": avg_confidence
        }
    
    def _check_quality(self) -> Dict:
        """检查知识质量"""
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        
        cur = conn.execute("""
            SELECT 
                AVG(quality_score) as avg_quality,
                AVG(salience) as avg_salience,
                AVG(access_count) as avg_access
            FROM knowledge_items
        """)
        row = cur.fetchone()
        
        cur = conn.execute("""
            SELECT COUNT(*) as cnt
            FROM knowledge_items
            WHERE quality_score >= 80
        """)
        high_quality = cur.fetchone()['cnt']
        
        cur = conn.execute("""
            SELECT COUNT(*) as cnt
            FROM knowledge_items
            WHERE quality_score < 30
        """)
        low_quality = cur.fetchone()['cnt']
        
        total = self._check_knowledge()['total']
        
        return {
            "avg_quality": row['avg_quality'] or 0,
            "avg_salience": row['avg_salience'] or 0,
            "avg_access": row['avg_access'] or 0,
            "high_quality_count": high_quality,
            "high_quality_ratio": high_quality / total if total > 0 else 0,
            "low_quality_count": low_quality,
            "low_quality_ratio": low_quality / total if total > 0 else 0
        }
    
    def _check_topics(self) -> Dict:
        """检查知识覆盖领域"""
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        
        cur = conn.execute("""
            SELECT question FROM knowledge_items
            WHERE question IS NOT NULL
            LIMIT 100
        """)
        
        questions = [row['question'] for row in cur.fetchall()]
        
        # 简单关键词提取
        import re
        keywords = []
        for q in questions:
            words = re.findall(r'\w+', q.lower())
            keywords.extend([w for w in words if len(w) > 3])
        
        keyword_counts = Counter(keywords).most_common(10)
        
        return {
            "total_keywords": len(keywords),
            "unique_keywords": len(set(keywords)),
            "top_keywords": [{"word": w, "count": c} for w, c in keyword_counts[:10]]
        }
    
    def _check_trend(self) -> Dict:
        """检查学习趋势"""
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        
        # 最近7天的知识增长
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        cur = conn.execute("""
            SELECT COUNT(*) as cnt
            FROM knowledge_items
            WHERE created_at >= ?
        """, (week_ago,))
        week_growth = cur.fetchone()['cnt']
        
        # 最近30天的知识增长
        month_ago = (datetime.now() - timedelta(days=30)).isoformat()
        cur = conn.execute("""
            SELECT COUNT(*) as cnt
            FROM knowledge_items
            WHERE created_at >= ?
        """, (month_ago,))
        month_growth = cur.fetchone()['cnt']
        
        # 总遗忘数
        cur = conn.execute("""
            SELECT COUNT(*) as cnt
            FROM knowledge_items
            WHERE salience < 0.2 AND memory_layer = 3
        """)
        fading = cur.fetchone()['cnt']
        
        return {
            "week_growth": week_growth,
            "month_growth": month_growth,
            "fading_count": fading,
            "growth_rate": month_growth / 30 if month_growth > 0 else 0
        }
    
    def _calculate_score(self, data: Dict) -> Dict:
        """计算综合评分 (0-100)"""
        scores = {}
        
        # 1. 知识覆盖度 (20分)
        total = data['knowledge']['total']
        if total >= 100:
            scores['coverage'] = 20
        elif total >= 50:
            scores['coverage'] = 15
        elif total >= 20:
            scores['coverage'] = 10
        elif total >= 5:
            scores['coverage'] = 5
        else:
            scores['coverage'] = 0
        
        # 2. 质量分 (20分)
        avg_quality = data['quality']['avg_quality']
        scores['quality'] = min(20, avg_quality / 100 * 20)
        
        # 3. 记忆结构 (15分)
        l1_ratio = data['memory']['layer1_ratio']
        if l1_ratio >= 0.2:
            scores['memory'] = 15
        elif l1_ratio >= 0.1:
            scores['memory'] = 10
        elif l1_ratio >= 0.05:
            scores['memory'] = 5
        else:
            scores['memory'] = 0
        
        # 4. 技能数量 (15分)
        skills = data['skills']['total']
        if skills >= 10:
            scores['skills'] = 15
        elif skills >= 5:
            scores['skills'] = 10
        elif skills >= 1:
            scores['skills'] = 5
        else:
            scores['skills'] = 0
        
        # 5. 规则数量 (15分)
        rules = data['rules']['active']
        if rules >= 10:
            scores['rules'] = 15
        elif rules >= 5:
            scores['rules'] = 10
        elif rules >= 1:
            scores['rules'] = 5
        else:
            scores['rules'] = 0
        
        # 6. 学习活力 (15分)
        week_growth = data['trend']['week_growth']
        if week_growth >= 20:
            scores['activity'] = 15
        elif week_growth >= 10:
            scores['activity'] = 10
        elif week_growth >= 1:
            scores['activity'] = 5
        else:
            scores['activity'] = 0
        
        scores['total'] = sum(scores.values())
        
        return scores
    
    def _generate_report(self, data: Dict) -> str:
        """生成可读报告"""
        score = data['score']['total']
        total = data['knowledge']['total']
        layers = data['memory']['layers']
        
        # 等级评定
        if score >= 80:
            level = "🌟 优秀"
            assessment = "系统知识体系完善，记忆结构健康，持续学习活跃。"
        elif score >= 60:
            level = "👍 良好"
            assessment = "系统具备基本知识体系，建议继续扩展领域覆盖。"
        elif score >= 40:
            level = "📈 发展中"
            assessment = "系统正在积累知识，建议增加学习材料。"
        elif score >= 20:
            level = "🌱 起步"
            assessment = "系统已开始学习，建议导入更多文档。"
        else:
            level = "⬜ 未初始化"
            assessment = "系统尚未学习任何知识，请开始学习。"
        
        report = f"""
╔══════════════════════════════════════════════════════════╗
║                    📊 知识健康度报告                      ║
╠══════════════════════════════════════════════════════════╣
║  综合评分: {score:.0f}/100  │  等级: {level}              ║
╠══════════════════════════════════════════════════════════╣
║  📚 知识总量                                           ║
║    总知识: {total} 条                                                 ║
║    核心记忆(L1): {layers['L1_核心记忆']} 条                           ║
║    框架记忆(L2): {layers['L2_框架记忆']} 条                           ║
║    情境碎片(L3): {layers['L3_情境碎片']} 条                           ║
╠══════════════════════════════════════════════════════════╣
║  🛠️ 技能与规则                                         ║
║    工具函数: {data['skills']['total']} 个                              ║
║    活跃规则: {data['rules']['active']} 条                              ║
║    平均工具使用: {data['skills']['avg_usage']:.1f} 次                  ║
╠══════════════════════════════════════════════════════════╣
║  📈 学习趋势                                            ║
║    最近7天增长: {data['trend']['week_growth']} 条                     ║
║    最近30天增长: {data['trend']['month_growth']} 条                    ║
║    遗忘中记忆: {data['trend']['fading_count']} 条                     ║
╠══════════════════════════════════════════════════════════╣
║  💡 评估结论                                            ║
║    {assessment}                                           ║
╚══════════════════════════════════════════════════════════╝
        """
        return report


# 全局实例
knowledge_health = KnowledgeHealthChecker()
