"""
历史对话反思机制 - 从历史中自动发现错误并纠正
"""
from infrastructure.database_manager import DatabaseManager
from typing import List, Dict, Tuple
from loguru import logger

class HistoryReflector:
    """历史对话反思器"""
    
    def __init__(self, db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
    
    def analyze_contradictions(self, history: List[Dict]) -> List[Dict]:
        """分析历史对话中的矛盾"""
        
        contradictions = []
        
        for i in range(len(history) - 1):
            current = history[i]
            next_item = history[i + 1]
            
            # 检测芯片推荐矛盾
            if '推荐' in current.get('user', ''):
                # 提取推荐的芯片
                import re
                chips1 = re.findall(r'(TPS\d+|BQ\d+|SH\d+|RT\d+)', 
                                   current.get('assistant', ''))
                chips2 = re.findall(r'(TPS\d+|BQ\d+|SH\d+|RT\d+)', 
                                   next_item.get('assistant', ''))
                
                # 如果两次推荐不同芯片，检查是否有纠正
                if chips1 and chips2 and chips1[0] != chips2[0]:
                    contradictions.append({
                        'type': '芯片推荐变化',
                        'first_recommendation': chips1[0],
                        'second_recommendation': chips2[0],
                        'context': f"用户: {current.get('user', '')[:50]}",
                        'needs_review': True
                    })
            
            # 检测自我纠正
            if '错误' in next_item.get('user', '') or '不对' in next_item.get('user', ''):
                contradictions.append({
                    'type': '用户指出错误',
                    'error_response': current.get('assistant', '')[:100],
                    'correction_request': next_item.get('user', ''),
                    'needs_correction': True
                })
        
        return contradictions
    
    def reflect_on_history(self, user_query: str = None, 
                          recent_n: int = 10) -> Dict:
        """反思历史对话"""
        
        # 获取历史对话
        history = self._get_recent_history(recent_n)
        
        if not history:
            return {
                'has_issues': False,
                'message': '暂无历史对话'
            }
        
        # 分析矛盾
        contradictions = self.analyze_contradictions(history)
        
        # 检测知识缺失
        knowledge_gaps = self._detect_knowledge_gaps(history)
        
        # 生成反思报告
        reflection = {
            'has_issues': len(contradictions) > 0 or len(knowledge_gaps) > 0,
            'contradictions': contradictions,
            'knowledge_gaps': knowledge_gaps,
            'suggestions': []
        }
        
        # 生成建议
        if contradictions:
            for c in contradictions:
                if c['type'] == '芯片推荐变化':
                    reflection['suggestions'].append(
                        f"⚠️ 发现推荐不一致: {c['first_recommendation']} → {c['second_recommendation']}"
                    )
                elif c['type'] == '用户指出错误':
                    reflection['suggestions'].append(
                        f"❌ 之前的回答可能有误: {c['error_response'][:50]}..."
                    )
        
        if knowledge_gaps:
            for gap in knowledge_gaps:
                reflection['suggestions'].append(
                    f"📚 发现知识盲区: {gap['topic']}"
                )
        
        return reflection
    
    def auto_correct_from_history(self, user_query: str) -> Tuple[bool, str]:
        """从历史中自动纠正"""
        
        reflection = self.reflect_on_history()
        
        if not reflection['has_issues']:
            return False, ""
        
        # 检查是否是回顾历史的问题
        if '回顾' in user_query or '历史' in user_query:
            # 生成反思报告
            report = self._generate_reflection_report(reflection)
            return True, report
        
        # 检查是否是质疑之前回答的问题
        if '之前' in user_query or '刚才' in user_query:
            # 分析之前的回答
            history = self._get_recent_history(3)
            if history:
                last_response = history[-1].get('assistant', '')
                
                # 验证之前的回答
                from core.requirement_validator import requirement_validator
                last_query = history[-1].get('user', '')
                
                req = requirement_validator.extract_core_requirement(last_query)
                is_valid, issues = requirement_validator.validate_response_against_requirement(
                    req, last_response
                )
                
                if not is_valid:
                    correction = f"""
【自动反思纠正】

经过分析，我发现之前的回答存在问题：

**问题**:
{chr(10).join(f'- {issue}' for issue in issues)}

**纠正**:
让我重新回答您的问题...

"""
                    return True, correction
        
        return False, ""
    
    def _get_recent_history(self, n: int = 10) -> List[Dict]:
        """获取最近的对话历史"""
        
        try:
            conn = DatabaseManager.get(self.db_path)._get_conn()
            cursor = conn.execute('''
                SELECT question as user, answer as assistant, created_at
                FROM knowledge_items
                WHERE knowledge_type = 'chat'
                ORDER BY created_at DESC
                LIMIT ?
            ''', (n,))
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    'user': row['user'],
                    'assistant': row['assistant'],
                    'created_at': row['created_at']
                })
            
            return history
        except:
            return []
    
    def _detect_knowledge_gaps(self, history: List[Dict]) -> List[Dict]:
        """检测知识盲区"""
        
        gaps = []
        
        for item in history:
            response = item.get('assistant', '')
            
            # 检测不确定性
            uncertainty_phrases = ['可能', '大概', '不确定', '不太清楚']
            if any(phrase in response for phrase in uncertainty_phrases):
                gaps.append({
                    'topic': item.get('user', '')[:50],
                    'reason': '回答包含不确定性'
                })
        
        return gaps
    
    def _generate_reflection_report(self, reflection: Dict) -> str:
        """生成反思报告"""
        
        report = """
【历史对话反思报告】

"""
        
        if reflection['contradictions']:
            report += "### 发现的矛盾:\n"
            for i, c in enumerate(reflection['contradictions'], 1):
                report += f"{i}. {c['type']}\n"
                if 'first_recommendation' in c:
                    report += f"   - 第一次推荐: {c['first_recommendation']}\n"
                    report += f"   - 第二次推荐: {c['second_recommendation']}\n"
                if 'error_response' in c:
                    report += f"   - 错误回答: {c['error_response'][:50]}...\n"
        
        if reflection['knowledge_gaps']:
            report += "\n### 知识盲区:\n"
            for i, gap in enumerate(reflection['knowledge_gaps'], 1):
                report += f"{i}. {gap['topic']}\n"
                report += f"   - 原因: {gap['reason']}\n"
        
        if reflection['suggestions']:
            report += "\n### 改进建议:\n"
            for suggestion in reflection['suggestions']:
                report += f"- {suggestion}\n"
        
        if not reflection['has_issues']:
            report += "✅ 未发现明显问题，历史对话质量良好。\n"
        
        report += "\n---\n_这是系统的自我反思，我会持续改进！_"
        
        return report

# 全局实例
history_reflector = HistoryReflector()

# 测试
if __name__ == "__main__":
    print("测试历史对话反思机制")
    print("=" * 60)
    
    # 模拟历史对话
    history = [
        {'user': '推荐一款26650的锂电保护板控制芯片', 
         'assistant': '推荐使用TPS61182...'},
        {'user': 'TPS61182这颗芯片是做什么用的？',
         'assistant': 'TPS61182是LED背光驱动芯片...'},
        {'user': '我之前需求是什么？你这个推荐的跟需求一致么？',
         'assistant': '我目前只能记住当前对话中的内容...'},
    ]
    
    # 分析矛盾
    contradictions = history_reflector.analyze_contradictions(history)
    print(f"\n发现矛盾: {len(contradictions)}")
    for c in contradictions:
        print(f"  - {c}")
    
    # 反思
    reflection = history_reflector.reflect_on_history()
    print(f"\n反思结果: {reflection}")