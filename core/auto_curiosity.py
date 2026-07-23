"""
后台守护任务 - 定期主动学习
"""
from core.ports.adapters import get_storage_port
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List
from loguru import logger


class AutoCuriosity:
    """自动好奇心 - 定期主动学习"""
    
    def __init__(self, db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
        self.running = False
        self.thread = None
        self.scan_interval = 3600
        logger.info("自动好奇心系统已初始化")
    
    def scan_low_quality_knowledge(self, threshold: float = 50.0, 
                                    min_access: int = 3) -> List[Dict]:
        """扫描低质量但频繁访问的知识"""
        
        items = []
        rows = get_storage_port(self.db_path).query('''
            SELECT question, answer, quality_score, access_count, source
            FROM knowledge_items
            WHERE quality_score < ?
            AND access_count >= ?
            AND knowledge_type = 'qa'
            ORDER BY access_count DESC
            LIMIT 10
        ''', (threshold, min_access))
        
        items = [dict(row) for row in rows]
        
        if items:
            logger.info(f"发现 {len(items)} 条低质量但频繁访问的知识")
        
        return items
    
    def scan_unanswered_patterns(self) -> List[str]:
        """扫描常见但未解答的问题模式"""
        
        patterns = []
        rows = get_storage_port(self.db_path).query('''
            SELECT question, COUNT(*) as cnt
            FROM knowledge_items
            WHERE answer IS NULL OR answer = '' OR answer LIKE '%不确定%'
            GROUP BY question
            HAVING cnt >= 2
            ORDER BY cnt DESC
            LIMIT 5
        ''')
        
        patterns = [row[0] for row in rows]
        
        if patterns:
            logger.info(f"发现 {len(patterns)} 个常见未解答问题")
        
        return patterns
    
    def improve_knowledge(self, question: str, old_answer: str) -> Dict:
        """尝试改进现有知识"""
        
        from core.external_learner import external_learner
        
        logger.info(f"尝试改进知识: {question[:50]}...")
        
        items = external_learner.learn_from_external(
            user_input=question,
            context=f"旧答案: {old_answer}",
            trigger_reason="质量改进"
        )
        
        saved_count = external_learner.save_to_knowledge_base(items)
        
        return {
            "question": question,
            "improved": saved_count > 0,
            "new_items": len(items)
        }
    
    def run_scan(self):
        """执行一次扫描并学习"""
        
        logger.info("开始主动学习扫描...")
        
        try:
            low_quality = self.scan_low_quality_knowledge()
            
            improved_count = 0
            for item in low_quality:
                result = self.improve_knowledge(
                    item["question"],
                    item["answer"]
                )
                if result["improved"]:
                    improved_count += 1
                    time.sleep(2)
            
            unanswered = self.scan_unanswered_patterns()
            
            for question in unanswered:
                from core.external_learner import external_learner
                items = external_learner.learn_from_external(
                    user_input=question,
                    context="未解答问题",
                    trigger_reason="补充解答"
                )
                external_learner.save_to_knowledge_base(items)
                time.sleep(2)
            
            logger.info(f"扫描完成: 改进{improved_count}条知识, 补充{len(unanswered)}个解答")
            
        except Exception as e:
            logger.error(f"扫描失败: {e}")
    
    def _run_loop(self):
        """后台循环"""
        while self.running:
            try:
                self.run_scan()
            except Exception as e:
                logger.error(f"后台学习失败: {e}")
            
            for _ in range(self.scan_interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def start(self):
        """启动后台学习"""
        if self.running:
            logger.warning("后台学习已在运行")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("后台主动学习已启动")
    
    def stop(self):
        """停止后台学习"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("后台主动学习已停止")
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "running": self.running,
            "interval": self.scan_interval,
            "thread_alive": self.thread.is_alive() if self.thread else False
        }


auto_curiosity = AutoCuriosity()