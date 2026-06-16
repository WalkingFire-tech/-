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
        
        try:
            self._run_cognitive_transformation()
        except Exception as e:
            logger.error(f"认知转化失败: {e}")
        
        try:
            self._run_genome_evolution()
        except Exception as e:
            logger.error(f"基因演化失败: {e}")
    
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
    
    def _run_cognitive_transformation(self):
        """运行认知转化（每周一次）"""
        today = datetime.now()
        
        # 每周日执行认知转化
        if today.weekday() == 6:
            try:
                from core.cognitive_transformer import cognitive_transformer
                
                results = cognitive_transformer.transform_all()
                
                total = sum([
                    results.get('situations_to_skills', 0),
                    results.get('skills_to_reflexes', 0),
                    results.get('situations_to_abstractions', 0)
                ])
                
                if total > 0:
                    notification = {
                        "type": "cognitive_transformation",
                        "message": f"🧠 认知转化完成：情景→技能({results['situations_to_skills']}), 技能→反射({results['skills_to_reflexes']}), 情景→抽象({results['situations_to_abstractions']})",
                        "results": results,
                        "timestamp": today.isoformat()
                    }
                    
                    self.pending_notifications.append(notification)
                    logger.info(f"认知转化: {results}")
            except Exception as e:
                logger.error(f"认知转化失败: {e}")
    
    def _run_genome_evolution(self):
        """运行基因演化（每两周一次）"""
        today = datetime.now()
        
        # 每14天执行一次基因演化
        if not hasattr(self, 'last_evolution'):
            self.last_evolution = None
        
        if self.last_evolution is None or (today - self.last_evolution).days >= 14:
            try:
                from core.genome_evolver import genome_evolver
                
                # 计算当前适应度
                stats = self._collect_fitness_stats()
                fitness = genome_evolver.evaluate_fitness(stats)
                
                # 执行进化
                child_ids = genome_evolver.evolve(fitness)
                
                if child_ids:
                    notification = {
                        "type": "genome_evolution",
                        "message": f"🧬 基因演化完成：当前适应度={fitness:.3f}，产生{len(child_ids)}个候选基因组",
                        "fitness": fitness,
                        "child_ids": child_ids,
                        "timestamp": today.isoformat()
                    }
                    
                    self.pending_notifications.append(notification)
                    logger.info(f"基因演化: fitness={fitness:.3f}, children={child_ids}")
                
                self.last_evolution = today
            except Exception as e:
                logger.error(f"基因演化失败: {e}")
    
    def _collect_fitness_stats(self) -> Dict:
        """收集适应度统计"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # 用户点赞率（简化：使用访问次数作为代理）
                cur = conn.execute('''
                    SELECT 
                        AVG(CASE WHEN access_count > 1 THEN 1.0 ELSE 0.5 END) as like_rate
                    FROM knowledge_items
                    WHERE knowledge_type = 'qa'
                ''')
                like_rate = cur.fetchone()['like_rate'] or 0.5
                
                # 知识库命中率
                cur = conn.execute('''
                    SELECT 
                        COUNT(CASE WHEN quality_score >= 60 THEN 1 END) as hits,
                        COUNT(*) as total
                    FROM knowledge_items
                    WHERE knowledge_type = 'qa'
                ''')
                row = cur.fetchone()
                hit_rate = (row['hits'] / row['total']) if row['total'] > 0 else 0.5
                
                # 效率（简化：使用平均质量分数）
                cur = conn.execute('''
                    SELECT AVG(quality_score) as avg_quality
                    FROM knowledge_items
                    WHERE knowledge_type = 'qa'
                ''')
                efficiency = (cur.fetchone()['avg_quality'] or 50) / 100.0
                
                return {
                    "like_rate": like_rate,
                    "hit_rate": hit_rate,
                    "dialog_reduction": 0.1,  # 默认值
                    "external_reduction": 0.05,  # 默认值
                    "efficiency": efficiency
                }
        except Exception as e:
            logger.error(f"收集适应度统计失败: {e}")
            return {
                "like_rate": 0.5,
                "hit_rate": 0.5,
                "dialog_reduction": 0,
                "external_reduction": 0,
                "efficiency": 0.5
            }
    
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