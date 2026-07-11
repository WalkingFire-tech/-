"""
无模型进化模式 - 不依赖LLM的自我优化系统
基于统计分析、规则引擎、外部搜索进行自主进化
"""
import sys
import time
import threading
import schedule
from pathlib import Path
from datetime import datetime
from loguru import logger
from infrastructure.database_manager import DatabaseManager

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


class ModelFreeEvolution:
    """无模型进化系统 - 纯统计分析驱动"""
    
    def __init__(self):
        self.running = False
        self.evolution_thread = None
        self.stats = {
            'cycles': 0,
            'knowledge_gained': 0,
            'rules_generated': 0,
            'genes_evolved': 0,
            'skills_formed': 0
        }
        
        logger.info("🧬 无模型进化系统已初始化")
    
    def start(self):
        """启动无模型进化"""
        if self.running:
            logger.warning("进化系统已在运行")
            return
        
        self.running = True
        
        # 启动进化线程
        self.evolution_thread = threading.Thread(target=self._evolution_loop, daemon=True)
        self.evolution_thread.start()
        
        logger.info("🚀 无模型进化系统已启动")
        logger.info("   - 基因演化: 每2小时")
        logger.info("   - 认知转化: 每6小时")
        logger.info("   - 外部学习: 每30分钟")
        logger.info("   - 进化沙盒: 每12小时")
        logger.info("   - 知识清理: 每4小时")
    
    def stop(self):
        """停止进化"""
        self.running = False
        if self.evolution_thread:
            self.evolution_thread.join(timeout=5)
        logger.info("进化系统已停止")
    
    def _evolution_loop(self):
        """进化主循环"""
        # 设置定时任务
        schedule.every(30).minutes.do(self._auto_learning_cycle)
        schedule.every(2).hours.do(self._genome_evolution_cycle)
        schedule.every(6).hours.do(self._cognitive_transformation_cycle)
        schedule.every(4).hours.do(self._knowledge_cleanup_cycle)
        schedule.every(12).hours.do(self._evolution_sandbox_cycle)
        schedule.every(1).hours.do(self._rule_generation_cycle)
        
        logger.info("进化任务调度已设置")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                logger.error(f"进化循环错误: {e}")
                time.sleep(60)
    
    def _auto_learning_cycle(self):
        """自动学习周期 - 通过外部搜索获取知识"""
        logger.info("📚 [自动学习] 开始外部知识获取...")
        
        try:
            from core.auto_learning_trigger import auto_learning_trigger
            
            # 获取待学习目标
            pending = auto_learning_trigger._get_pending_targets()
            
            if not pending:
                logger.info("所有学习目标已完成")
                return
            
            # 按优先级学习
            pending.sort(key=lambda x: x.get('priority', 0), reverse=True)
            
            for target in pending[:3]:  # 每次最多学习3个目标
                self._learn_from_external_search(target)
                
        except Exception as e:
            logger.error(f"自动学习失败: {e}")
    
    def _learn_from_external_search(self, target: dict):
        """通过外部搜索学习（无需LLM）"""

        import json
        
        target_name = target['name']
        keywords = target.get('keywords', [])
        
        logger.info(f"  学习目标: {target_name}")
        
        knowledge_gained = 0
        
        for keyword in keywords:
            try:
                # 使用DuckDuckGo搜索（无需API密钥）
                from ddgs import DDGS
                
                with DDGS() as ddgs:
                    results = list(ddgs.text(f"{target_name} {keyword}", max_results=3))
                
                if results:
                    db = DatabaseManager.get("data/knowledge_store.db")
                    for result in results:
                        question = f"{target_name}: {keyword}"
                        answer = f"{result.get('title', '')}\n\n{result.get('body', '')}"
                        source = result.get('href', 'external_search')
                        
                        existing = db.query_one(
                            "SELECT id FROM knowledge_items WHERE question = ?",
                            (question,)
                        )
                        
                        if not existing:
                            db.execute('''
                                INSERT INTO knowledge_items 
                                (question, answer, source, knowledge_type, quality_score, created_at)
                                VALUES (?, ?, ?, 'external', 50.0, ?)
                            ''', (question, answer, source, datetime.now().isoformat()), commit=True)
                            
                            knowledge_gained += 1
                
                logger.info(f"    - {keyword}: 获得{len(results)}条知识")
                
            except Exception as e:
                logger.warning(f"    - {keyword}: 搜索失败 - {e}")
        
        self.stats['knowledge_gained'] += knowledge_gained
        logger.info(f"  ✅ {target_name}: 新增{knowledge_gained}条知识")
    
    def _genome_evolution_cycle(self):
        """基因演化周期 - 基于统计优化参数"""
        logger.info("🧬 [基因演化] 开始适应度评估与进化...")
        
        try:
            from core.genome_evolver import genome_evolver
            
            # 收集适应度统计（无需LLM）
            stats = self._collect_fitness_stats()
            
            # 评估适应度
            fitness = genome_evolver.evaluate_fitness(stats)
            
            # 执行进化
            child_ids = genome_evolver.evolve(fitness)
            
            self.stats['genes_evolved'] += len(child_ids)
            
            logger.info(f"  ✅ 适应度: {fitness:.3f}, 新基因组: {len(child_ids)}个")
            
            # 应用最优基因
            self._apply_best_genome(genome_evolver)
            
        except Exception as e:
            logger.error(f"基因演化失败: {e}")
    
    def _collect_fitness_stats(self) -> dict:
        """收集适应度统计（纯数据分析）"""
        try:
            db = DatabaseManager.get("data/knowledge_store.db")
            
            row = db.query_one('''
                SELECT 
                    COUNT(CASE WHEN quality_score >= 60 THEN 1 END) as hits,
                    COUNT(*) as total
                FROM knowledge_items
            ''')
            hit_rate = (row['hits'] / row['total']) if row['total'] > 0 else 0.5
            
            avg_quality = db.query_one("SELECT AVG(quality_score) as avg FROM knowledge_items")['avg'] or 50.0
            
            avg_access = db.query_one('''
                SELECT AVG(access_count) as avg_access 
                FROM knowledge_items 
                WHERE access_count > 0
            ''')['avg_access'] or 1.0
            
            diversity = db.query_one('''
                SELECT COUNT(DISTINCT knowledge_type) as types
                FROM knowledge_items
            ''')['types'] / 10.0
            
            return {
                'like_rate': min(avg_access / 5.0, 1.0),
                'hit_rate': hit_rate,
                'dialog_reduction': 0.1,
                'external_reduction': 0.05,
                'efficiency': avg_quality / 100.0,
                'diversity': diversity
            }
        except Exception as e:
            logger.error(f"收集统计失败: {e}")
            return {
                'like_rate': 0.5,
                'hit_rate': 0.5,
                'dialog_reduction': 0.1,
                'external_reduction': 0.05,
                'efficiency': 0.5
            }
    
    def _apply_best_genome(self, genome_evolver):
        """应用最优基因组参数"""
        try:
            genes = genome_evolver.get_all_gene_values()
            
            # 应用到系统配置
            # 例如：调整检索阈值、学习频率等
            logger.info(f"  应用基因组: 检索阈值={genes.get('retrieval_threshold', 0.5):.2f}")
            
        except Exception as e:
            logger.error(f"应用基因组失败: {e}")
    
    def _cognitive_transformation_cycle(self):
        """认知转化周期 - 基于模式固化技能"""
        logger.info("🧠 [认知转化] 分析经验模式，固化技能...")
        
        try:
            from core.cognitive_transformer import cognitive_transformer
            
            # 执行认知转化
            results = cognitive_transformer.run_all_transformations()
            
            skills_formed = sum([
                results.get('experience_to_skill', {}).get('transformed', 0),
                results.get('skill_to_reflex', {}).get('transformed', 0),
                results.get('experience_to_abstract', {}).get('transformed', 0)
            ])
            
            self.stats['skills_formed'] += skills_formed
            
            logger.info(f"  ✅ 形成{skills_formed}个新技能/反射")
            
        except Exception as e:
            logger.error(f"认知转化失败: {e}")
    
    def _knowledge_cleanup_cycle(self):
        """知识清理周期 - 基于质量衰减"""
        logger.info("🗑️ [知识清理] 清理低质量知识...")
        
        from datetime import timedelta
        
        try:
            db = DatabaseManager.get("data/knowledge_store.db")
            db.execute('''
                UPDATE knowledge_items
                SET quality_score = quality_score * 0.95
                WHERE last_accessed < ?
            ''', ((datetime.now() - timedelta(days=30)).isoformat(),), commit=True)
            
            cur = db.execute('''
                DELETE FROM knowledge_items
                WHERE quality_score < 10.0
                AND knowledge_type != 'important'
            ''')
            
            deleted = cur.rowcount
            
            logger.info(f"  ✅ 清理{deleted}条低质量知识")
                
        except Exception as e:
            logger.error(f"知识清理失败: {e}")
    
    def _evolution_sandbox_cycle(self):
        """进化沙盒周期 - 模拟多智能体竞争"""
        logger.info("🏝️ [进化沙盒] 启动多智能体进化模拟...")
        
        try:
            from core.active_scheduler import active_scheduler
            
            # 运行进化沙盒
            result = active_scheduler.run_evolution_sandbox(
                num_agents=6,
                generations=10
            )
            
            if result.get('success'):
                logger.info(f"  ✅ 进化完成: 最优适应度={result.get('best_fitness', 0):.3f}")
            else:
                logger.warning(f"  ⚠️  进化沙盒未产生结果")
                
        except Exception as e:
            logger.error(f"进化沙盒失败: {e}")
    
    def _rule_generation_cycle(self):
        """规则生成周期 - 基于模式挖掘"""
        logger.info("📏 [规则生成] 挖掘经验模式，生成规则...")
        
        try:
            from core.learning import enhanced_learner
            
            # 生成规则
            rules_count = enhanced_learner.detect_and_create_rules()
            
            # 生成工具
            tools_count = enhanced_learner.auto_generate_tools()
            
            self.stats['rules_generated'] += rules_count + tools_count
            
            logger.info(f"  ✅ 生成{rules_count}条规则, {tools_count}个工具")
            
        except Exception as e:
            logger.error(f"规则生成失败: {e}")
    
    def get_status(self) -> dict:
        """获取进化状态"""
        return {
            'running': self.running,
            'cycles': self.stats['cycles'],
            'knowledge_gained': self.stats['knowledge_gained'],
            'rules_generated': self.stats['rules_generated'],
            'genes_evolved': self.stats['genes_evolved'],
            'skills_formed': self.stats['skills_formed'],
            'uptime': str(datetime.now() - self.stats.get('start_time', datetime.now()))
        }


# 全局实例
model_free_evolution = ModelFreeEvolution()


def run_model_free_evolution():
    """运行无模型进化（阻塞模式）"""
    import signal
    
    evolution = ModelFreeEvolution()
    evolution.stats['start_time'] = datetime.now()
    
    # 信号处理
    def signal_handler(sig, frame):
        logger.info("\n收到停止信号...")
        evolution.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # 启动进化
    evolution.start()
    
    logger.info("=" * 60)
    logger.info("  无模型进化系统运行中...")
    logger.info("  按 Ctrl+C 停止")
    logger.info("=" * 60)
    
    # 保持运行
    try:
        while True:
            time.sleep(3600)
            status = evolution.get_status()
            logger.info(f"📊 进化统计: 知识+{status['knowledge_gained']}, "
                       f"规则+{status['rules_generated']}, "
                       f"基因+{status['genes_evolved']}, "
                       f"技能+{status['skills_formed']}")
    except KeyboardInterrupt:
        evolution.stop()


if __name__ == "__main__":
    run_model_free_evolution()