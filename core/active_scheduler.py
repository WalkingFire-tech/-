"""
主动调度器 - 定期执行学习优化任务
"""
import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List
from loguru import logger
from infrastructure.database_manager import DatabaseManager


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
            from meta.induction import induction_scheduler
            result = induction_scheduler.run_induction()
            rules_count = result.get('rules_generated', 0) if isinstance(result, dict) else result
            if rules_count > 0:
                logger.info(f"生成 {rules_count} 条新规则")
        except Exception as e:
            logger.error(f"规则生成失败: {e}")
        
        try:
            from tools.generator import ToolGenerator
            from adapters.llm.ollama_adapter import OllamaAdapter
            primary_model = OllamaAdapter(model_name="qwen2.5-coder:7b")
            tool_gen = ToolGenerator(llm_adapter=primary_model)
            tools_count = tool_gen.scan_and_generate() if hasattr(tool_gen, 'scan_and_generate') else 0
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
        
        # 暂时禁用自动学习触发，避免内存问题
        # try:
        #     self._run_auto_learning()
        # except Exception as e:
        #     logger.error(f"自动学习触发失败: {e}")
    
    def _decay_quality_scores(self):
        """知识质量衰减（长期未访问的知识质量下降）"""
        decay_rate = 0.99
        days_threshold = 30
        
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            UPDATE knowledge_items
            SET quality_score = quality_score * ?
            WHERE last_accessed < ?
            AND knowledge_type = 'qa'
        ''', (
            decay_rate,
            (datetime.now() - timedelta(days=days_threshold)).isoformat()
        ), commit=True)
    
    def _cleanup_old_knowledge(self):
        """清理低质量知识"""
        min_quality = 10.0
        
        db = DatabaseManager.get(self.db_path)
        cursor = db.execute('''
            DELETE FROM knowledge_items
            WHERE quality_score < ?
            AND knowledge_type = 'qa'
            AND access_count < 2
        ''', (min_quality,), commit=True)
        
        deleted = cursor.rowcount
        
        if deleted > 0:
            logger.info(f"清理了 {deleted} 条低质量知识")
            
            self._add_forget_notification(deleted)
    
    def _generate_memory_review(self):
        """生成记忆回顾报告"""
        try:
            from core.memory.stereo_memory import get_stereo_memory
            
            store = get_stereo_memory()
            stats = store.get_stats()
            
            review = {
                'l1_core': stats.get('by_type', {}).get('knowledge', 0),
                'l2_framework': stats.get('by_type', {}).get('conversation', 0),
                'l3_fading': stats.get('total_memories', 0) - stats.get('by_type', {}).get('knowledge', 0) - stats.get('by_type', {}).get('conversation', 0)
            }
            
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
            db = DatabaseManager.get(self.db_path)
            
            like_rate_row = db.query_one('''
                SELECT 
                    AVG(CASE WHEN access_count > 1 THEN 1.0 ELSE 0.5 END) as like_rate
                FROM knowledge_items
                WHERE knowledge_type = 'qa'
            ''')
            like_rate = like_rate_row['like_rate'] if like_rate_row and like_rate_row['like_rate'] is not None else 0.5
            
            hit_row = db.query_one('''
                SELECT 
                    COUNT(CASE WHEN quality_score >= 60 THEN 1 END) as hits,
                    COUNT(*) as total
                FROM knowledge_items
                WHERE knowledge_type = 'qa'
            ''')
            hits = hit_row['hits'] if hit_row else 0
            total = hit_row['total'] if hit_row else 0
            hit_rate = (hits / total) if total > 0 else 0.5
            
            eff_row = db.query_one('''
                SELECT AVG(quality_score) as avg_quality
                FROM knowledge_items
                WHERE knowledge_type = 'qa'
            ''')
            efficiency = ((eff_row['avg_quality'] if eff_row and eff_row['avg_quality'] is not None else 50) or 50) / 100.0
            
            return {
                "like_rate": like_rate,
                "hit_rate": hit_rate,
                "dialog_reduction": 0.1,
                "external_reduction": 0.05,
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
    
    def _run_auto_learning(self):
        """运行自动学习触发"""
        try:
            from core.auto_learning_trigger import auto_learning_trigger
            
            # 获取学习状态
            status = auto_learning_trigger.get_learning_status()
            
            if status.get('pending_count', 0) > 0:
                logger.info(f"自动学习: {status['pending_count']}个目标待学习")
                
                # 检查并触发学习
                auto_learning_trigger._check_and_trigger_learning()
                
                notification = {
                    "type": "auto_learning",
                    "message": f"📚 自动学习触发：{status['pending_count']}个目标待学习",
                    "status": status,
                    "timestamp": datetime.now().isoformat()
                }
                
                self.pending_notifications.append(notification)
            else:
                logger.info("所有学习目标已完成")
                
        except Exception as e:
            logger.error(f"自动学习触发失败: {e}")
    
    def run_evolution_sandbox(self, num_agents: int = 8, generations: int = 20) -> Dict:
        """
        运行进化沙盒
        
        Args:
            num_agents: 智能体数量
            generations: 进化代数
        
        Returns:
            进化结果
        """
        try:
            from core.evolution.evolution_island import EvolutionIsland
            
            logger.info(f"启动进化沙盒: {num_agents}个智能体, {generations}代")
            
            island = EvolutionIsland(
                main_db_path=self.db_path,
                num_agents=num_agents,
                generations=generations,
                tasks_per_gen=30
            )
            
            result = island.run()
            
            # 更新主系统基因
            if result.get('best_genome'):
                self._apply_evolved_genome(result['best_genome'])
            
            # 导入新技能
            if result.get('best_skills'):
                self._import_evolved_skills(result['best_skills'])
            
            # 添加通知
            notification = {
                "type": "evolution_sandbox",
                "message": f"🏝️ 进化沙盒完成：最优适应度={result['stats']['final_best_fitness']:.3f}",
                "stats": result['stats'],
                "timestamp": datetime.now().isoformat()
            }
            
            self.pending_notifications.append(notification)
            
            logger.info(f"进化沙盒完成: {result['stats']}")
            
            return result
            
        except Exception as e:
            logger.error(f"进化沙盒失败: {e}")
            return {"error": str(e)}
    
    def _apply_evolved_genome(self, genome: Dict):
        """应用进化后的基因组"""
        try:
            from core.genome_evolver import genome_evolver
            
            # 更新基因值
            db = DatabaseManager.get(genome_evolver.db_path)
            cur = db.query_one("SELECT gene_values FROM genomes WHERE id = ?", 
                             (genome_evolver.active_genome_id,))
            
            if cur:
                current_values = json.loads(cur['gene_values'])
                
                if 'retrieval_threshold' in genome:
                    current_values['G002'] = str(genome['retrieval_threshold'])
                if 'external_threshold' in genome:
                    current_values['G007'] = str(genome['external_threshold'])
                if 'memory_decay' in genome:
                    current_values['G008'] = str(genome['memory_decay'])
                if 'exploration' in genome:
                    current_values['G010'] = str(genome['exploration'])
                if 'social' in genome:
                    current_values['G009'] = str(genome['social'])
                if 'answer_style' in genome:
                    current_values['G006'] = str(genome['answer_style'])
                
                db.execute("UPDATE genomes SET gene_values = ? WHERE id = ?",
                           (json.dumps(current_values), genome_evolver.active_genome_id), commit=True)
                
                logger.info(f"已应用进化基因组: {genome}")
        except Exception as e:
            logger.error(f"应用进化基因组失败: {e}")
    
    def _import_evolved_skills(self, skills: List[Dict]):
        """导入进化后的技能"""
        try:
            db = DatabaseManager.get(self.db_path)
            for skill in skills:
                name = skill.get('name', f"evolved_skill_{hash(str(skill)) % 10000}")
                code = skill.get('code', '')
                trigger = skill.get('trigger', '')
                
                existing = db.query_one("SELECT 1 FROM tools WHERE name = ?", (name,))
                if existing:
                    continue
                
                db.execute('''
                    INSERT INTO tools (name, code, description, triggers, usage_count, created_at)
                    VALUES (?, ?, ?, ?, 0, ?)
                ''', (
                    name,
                    code,
                    f"进化产生的技能",
                    json.dumps([trigger]),
                    datetime.now().isoformat()
                ), commit=True)
            
            logger.info(f"已导入{len(skills)}个进化技能")
        except Exception as e:
            logger.error(f"导入进化技能失败: {e}")
    
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