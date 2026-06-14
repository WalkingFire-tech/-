"""
记忆回顾模块 - 周回顾推送、遗忘统计
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict
from loguru import logger


class MemoryReview:
    """记忆回顾管理器"""
    
    def __init__(self, db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
        self.notification_queue = []
    
    def weekly_summary(self) -> Dict:
        """
        统计上周被遗忘的知识数量，生成回顾消息
        
        Returns:
            {
                "forgotten_count": int,
                "fading_count": int,
                "message": str,
                "details": List[Dict]
            }
        """
        one_week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # 查询最近7天内即将遗忘的知识（L3层且salience低）
            cur = conn.execute('''
                SELECT question, answer, source, salience, last_accessed
                FROM knowledge_items
                WHERE memory_layer = 3 
                AND salience < 0.3
                AND last_accessed < ?
                ORDER BY salience ASC
                LIMIT 10
            ''', (one_week_ago,))
            
            forgotten_items = [dict(row) for row in cur.fetchall()]
            forgotten_count = len(forgotten_items)
            
            # 查询正在衰减的知识
            cur = conn.execute('''
                SELECT COUNT(*) as count
                FROM knowledge_items
                WHERE memory_layer = 3
                AND salience BETWEEN 0.3 AND 0.5
                AND last_accessed < ?
            ''', (one_week_ago,))
            
            fading_count = cur.fetchone()['count']
        
        # 生成回顾消息
        message = ""
        if forgotten_count > 0:
            message = f"📖 这一周，我默默遗忘了 {forgotten_count} 件小事。如果你觉得它们重要，可以告诉我\"记住它\"。"
            logger.info(f"周回顾: 遗忘 {forgotten_count} 条知识")
        elif fading_count > 0:
            message = f"💭 这一周，有 {fading_count} 条记忆正在慢慢淡去..."
            logger.info(f"周回顾: {fading_count} 条知识正在衰减")
        else:
            message = "✨ 这一周，所有记忆都保持完好。"
            logger.info("周回顾: 记忆完好")
        
        result = {
            "forgotten_count": forgotten_count,
            "fading_count": fading_count,
            "message": message,
            "details": forgotten_items
        }
        
        # 添加到通知队列
        if forgotten_count > 0 or fading_count > 0:
            self.notification_queue.append(message)
        
        return result
    
    def get_memory_stats(self) -> Dict:
        """获取记忆统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # L1核心记忆
            cur = conn.execute('''
                SELECT COUNT(*) as count
                FROM knowledge_items
                WHERE memory_layer = 1
            ''')
            l1_count = cur.fetchone()['count']
            
            # L2框架记忆
            cur = conn.execute('''
                SELECT COUNT(*) as count
                FROM knowledge_items
                WHERE memory_layer = 2
            ''')
            l2_count = cur.fetchone()['count']
            
            # L3情境碎片
            cur = conn.execute('''
                SELECT COUNT(*) as count
                FROM knowledge_items
                WHERE memory_layer = 3
            ''')
            l3_count = cur.fetchone()['count']
            
            # 即将遗忘
            cur = conn.execute('''
                SELECT COUNT(*) as count
                FROM knowledge_items
                WHERE memory_layer = 3 AND salience < 0.3
            ''')
            fading_count = cur.fetchone()['count']
            
            # 最近访问
            cur = conn.execute('''
                SELECT question, access_count, last_accessed
                FROM knowledge_items
                WHERE access_count > 0
                ORDER BY access_count DESC
                LIMIT 5
            ''')
            hot_memories = [dict(row) for row in cur.fetchall()]
            
            return {
                "l1_core": l1_count,
                "l2_framework": l2_count,
                "l3_context": l3_count,
                "fading": fading_count,
                "hot_memories": hot_memories,
                "total": l1_count + l2_count + l3_count
            }
    
    def pop_notifications(self) -> List[str]:
        """获取并清空通知队列"""
        notifications = self.notification_queue.copy()
        self.notification_queue.clear()
        return notifications


memory_review = MemoryReview()