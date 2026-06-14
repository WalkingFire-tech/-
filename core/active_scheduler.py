"""
主动调度器 - 定期执行学习优化任务
"""
import threading
import time
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List
from loguru import logger


class ActiveScheduler:
    """主动调度器 - 定期执行学习优化任务"""
    
    def __init__(self, interval_seconds: int = 300, 
                 db_path: str = "data/knowledge_store.db"):
        self.interval = interval_seconds
        self.db_path = db_path
        self.running = False
        self.thread = None
        self.task_count = 0
        self.pending_notifications = []
        self.last_sunday = None
        
        logger.info(f"主动调度器已初始化，间隔 {interval_seconds} 秒")
    
    def _background_job(self):
        """后台定期任务"""
        while self.running:
            try:
                self.task_count += 1
                logger.info(f"执行第 {self.task_count} 次后台学习优化任务...")
                
                self._run_optimization_tasks()
                
            except Exception as e:
                logger.error(f"后台任务失败: {e}")
            
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def _run_optimization_tasks(self):
        """运行所有优化任务"""
        
        try:
            from core.learning import enhanced_learner
            
            rules_count = enhanced_learner.detect_and_create_rules()
            if rules_count > 0:
                logger.info(f"生成 {rules_count} 条新规则")
        except Exception as e:
            logger.error(f"规则生成失败: {e}")
        
        try:
            from core.learning import enhanced_learner
            
            tools_count = enhanced_learner.auto_generate_tools()
            if tools_count > 0:
                logger.info(f"生成 {tools_count} 个新工具")
        except Exception as e:
            logger.error(f"工具生成失败: {e}")
        
        try:
            self._decay_quality_scores()
        except Exception as e:
            logger.error(f"质量衰减失败: {e}")
        
        try:
            self._cleanup_old_knowledge()
        except Exception as e:
            logger.error(f"知识清理失败: {e}")
        
        try:
            self._generate_memory_review()
        except Exception as e:
            logger.error(f"记忆回顾失败: {e}")
        
        try:
            self._weekly_memory_review()
        except Exception as e:
            logger.error(f"周回顾失败: {e}")
    
    def _decay_quality_scores(self):
        """知识质量衰减（长期未访问的知识质量下降）"""
        decay_rate = 0.99
        days_threshold = 30
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE knowledge_items
                SET quality_score = quality_score * ?
                WHERE last_accessed < ?
                AND knowledge_type = 'qa'
            ''', (
                decay_rate,
                (datetime.now() - timedelta(days=days_threshold)).isoformat()
            ))
            conn.commit()
    
    def _cleanup_old_knowledge(self):
        """清理低质量知识"""
        min_quality = 10.0
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                DELETE FROM knowledge_items
                WHERE quality_score < ?
                AND knowledge_type = 'qa'
                AND access_count < 2
            ''', (min_quality,))
            
            deleted = cursor.rowcount
            conn.commit()
            
            if deleted > 0:
                logger.info(f"清理了 {deleted} 条低质量知识")
                
                # 记录遗忘通知
                self._add_forget_notification(deleted)
    
    def _generate_memory_review(self):
        """生成记忆回顾报告"""
        try:
            from core.learning import enhanced_learner
            
            review = enhanced_learner.get_memory_review()
            
            if review['l3_fading'] > 0:
                notification = {
                    "type": "memory_review",
                    "message": f"💭 这周我默默忘记了 {review['l3_fading']} 件小事（情境碎片正在淡去）。",
                    "detail": f"核心记忆: {review['l1_core']}条\n框架记忆: {review['l2_framework']}条\n即将遗忘: {review['l3_fading']}条",
                    "timestamp": datetime.now().isoformat()
                }
                
                self.pending_notifications.append(notification)
                logger.info(f"生成记忆回顾通知")
        except Exception as e:
            logger.error(f"记忆回顾失败: {e}")
    
    def _add_forget_notification(self, count: int):
        """添加遗忘通知"""
        notification = {
            "type": "forgotten",
            "message": f"🥀 我刚刚遗忘了 {count} 条不太重要的记忆",
            "timestamp": datetime.now().isoformat()
        }
        
        self.pending_notifications.append(notification)
    
    def _weekly_memory_review(self):
        """周回顾 - 每周日执行"""
        today = datetime.now()
        
        if today.weekday() == 6:  # 周日
            if self.last_sunday is None or (today - self.last_sunday).days >= 7:
                try:
                    from core.memory_review import memory_review
                    
                    summary = memory_review.weekly_summary()
                    
                    if summary['forgotten_count'] > 0 or summary['fading_count'] > 0:
                        notification = {
                            "type": "weekly_review",
                            "message": summary['message'],
                            "forgotten_count": summary['forgotten_count'],
                            "fading_count": summary['fading_count'],
                            "timestamp": today.isoformat()
                        }
                        
                        self.pending_notifications.append(notification)
                        logger.info(f"周回顾: {summary['message']}")
                    
                    self.last_sunday = today
                except Exception as e:
                    logger.error(f"周回顾执行失败: {e}")
    
    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._background_job, daemon=True)
        self.thread.start()
        
        logger.info(f"主动调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=5)
        
        logger.info("主动调度器已停止")
    
    def pop_notifications(self):
        """取出并清空通知"""
        notifs = self.pending_notifications[:]
        self.pending_notifications.clear()
        return notifs
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        return {
            "running": self.running,
            "interval": self.interval,
            "task_count": self.task_count,
            "thread_alive": self.thread.is_alive() if self.thread else False
        }
    
    def run_once(self):
        """手动执行一次优化任务"""
        logger.info("手动执行优化任务...")
        self._run_optimization_tasks()
        logger.info("优化任务完成")


active_scheduler = ActiveScheduler()