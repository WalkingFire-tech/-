"""
进化调度器 - 协调各层的进化任务

职责：定期触发各层的进化任务，协调进化流程
"""

from typing import Dict, List, Optional
import threading
import time
from datetime import datetime
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class EvolutionScheduler:
    """
    进化调度器
    
    定期触发各层的进化任务，协调进化流程。
    """
    
    def __init__(self):
        self._running = False
        self._thread = None
        
        self._behavior_engine = None
        self._knowledge_engine = None
        self._strategy_engine = None
        self._meta_learner = None
        
        self._last_behavior_run: Optional[datetime] = None
        self._last_knowledge_run: Optional[datetime] = None
        self._last_strategy_run: Optional[datetime] = None
        self._last_meta_run: Optional[datetime] = None
        
        self._init_components()
    
    def _init_components(self):
        """初始化各层组件"""
        try:
            from core.evolution.behavior_evolution import get_behavior_evolution_engine
            self._behavior_engine = get_behavior_evolution_engine()
            logger.info("✅ 行为进化层已加载")
        except Exception as e:
            logger.warning(f"行为进化引擎加载失败: {e}")
        
        try:
            from core.evolution.knowledge_evolution import get_knowledge_evolution_engine
            self._knowledge_engine = get_knowledge_evolution_engine()
            logger.info("✅ 知识进化层已加载")
        except Exception as e:
            logger.warning(f"知识进化引擎加载失败: {e}")
        
        try:
            from core.evolution.strategy_evolution import get_strategy_evolution_engine
            self._strategy_engine = get_strategy_evolution_engine()
            logger.info("✅ 策略进化层已加载")
        except Exception as e:
            logger.warning(f"策略进化引擎加载失败: {e}")
        
        try:
            from core.evolution.meta_learning import get_meta_learner
            self._meta_learner = get_meta_learner()
            logger.info("✅ 元学习层已加载")
        except Exception as e:
            logger.warning(f"元学习层加载失败: {e}")
    
    def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("进化调度器已在运行")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._thread.start()
        logger.info("🚀 进化调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        
        if self._meta_learner:
            try:
                self._meta_learner.stop_auto_learning()
            except Exception as e:
                logger.debug(f"停止元学习失败: {e}")
        
        logger.info("🛑 进化调度器已停止")
    
    def _scheduler_loop(self):
        """调度器主循环"""
        behavior_interval = 3600
        knowledge_interval = 6 * 3600
        strategy_interval = 12 * 3600
        meta_interval = 6 * 3600
        
        if self._meta_learner:
            try:
                self._meta_learner.start_auto_learning(interval_hours=6)
            except Exception as e:
                logger.warning(f"启动元学习自动模式失败: {e}")
        
        logger.info("📋 进化任务调度已配置")
        
        while self._running:
            try:
                current_time = datetime.now()
                
                if self._should_run(self._last_behavior_run, behavior_interval):
                    self._run_behavior_evolution()
                    self._last_behavior_run = current_time
                
                if self._should_run(self._last_knowledge_run, knowledge_interval):
                    self._run_knowledge_evolution()
                    self._last_knowledge_run = current_time
                
                if self._should_run(self._last_strategy_run, strategy_interval):
                    self._run_strategy_evolution()
                    self._last_strategy_run = current_time
                
                if self._should_run(self._last_meta_run, meta_interval):
                    self._run_meta_learning()
                    self._last_meta_run = current_time
                
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"调度器循环异常: {e}")
                time.sleep(60)
    
    def _should_run(self, last_run: Optional[datetime], interval: int) -> bool:
        """判断是否应该运行"""
        if last_run is None:
            return True
        
        elapsed = (datetime.now() - last_run).total_seconds()
        return elapsed >= interval
    
    def _run_behavior_evolution(self):
        """运行行为进化"""
        logger.debug("🔄 执行行为进化任务...")
        try:
            if self._behavior_engine:
                self._behavior_engine._update_style_stats()
                self._behavior_engine._update_tone_stats()
                stats = self._behavior_engine.get_statistics()
                
                if stats.get('total_profiles', 0) > 0:
                    logger.debug(f"行为进化完成: {stats['total_profiles']} 个档案, {stats['profiles_with_feedback']} 个有反馈")
                else:
                    logger.debug("行为进化完成: 无档案数据")
        except Exception as e:
            logger.error(f"行为进化失败: {e}")
    
    def _run_knowledge_evolution(self):
        """运行知识进化"""
        logger.debug("🔄 执行知识进化任务...")
        try:
            if self._knowledge_engine:
                pending = self._knowledge_engine.get_pending_conflicts()
                stats = self._knowledge_engine.get_statistics()
                
                if pending:
                    logger.info(f"发现 {len(pending)} 个待处理知识冲突")
                    for conflict in pending[:3]:
                        logger.info(f"  - 冲突: {conflict.knowledge_id_a} vs {conflict.knowledge_id_b} ({conflict.conflict_type})")
                else:
                    logger.debug(f"知识进化完成: {stats['total_verifications']} 次验证, 无待处理冲突")
        except Exception as e:
            logger.error(f"知识进化失败: {e}")
    
    def _run_strategy_evolution(self):
        """运行策略进化"""
        logger.debug("🔄 执行策略进化任务...")
        try:
            if self._strategy_engine:
                intent_opts = self._strategy_engine.get_intent_optimizations(limit=5)
                router_opts = self._strategy_engine.get_router_optimizations(limit=5)
                stats = self._strategy_engine.get_statistics()
                
                high_priority = [o for o in intent_opts if o.get('priority') == 'high']
                
                if high_priority:
                    logger.warning(f"发现 {len(high_priority)} 个高优先级意图优化建议")
                    for opt in high_priority[:2]:
                        logger.warning(f"  - {opt['intent_type']}: {opt['pattern_text'][:30]}... (成功率: {opt['success_rate']:.1%})")
                else:
                    logger.debug(f"策略进化完成: {stats['total_intent_patterns']} 个模式, 无高优先级优化")
        except Exception as e:
            logger.error(f"策略进化失败: {e}")
    
    def _run_meta_learning(self):
        """运行元学习"""
        logger.debug("🔄 执行元学习任务...")
        try:
            if self._meta_learner:
                patterns = self._meta_learner.get_active_patterns()
                stats = self._meta_learner.get_statistics()
                
                declining = [p for p in patterns if p.pattern_type == "declining"]
                volatile = [p for p in patterns if p.pattern_type == "volatile"]
                
                if declining:
                    logger.warning(f"检测到 {len(declining)} 个下降趋势")
                    for p in declining[:2]:
                        logger.warning(f"  - {p.description}")
                
                if volatile:
                    logger.warning(f"检测到 {len(volatile)} 个波动模式")
                    for p in volatile[:2]:
                        logger.warning(f"  - {p.description}")
                
                if not declining and not volatile:
                    logger.debug(f"元学习完成: {stats['total_observations']} 次观察, 系统稳定")
        except Exception as e:
            logger.error(f"元学习失败: {e}")
    
    def run_all_now(self):
        """立即运行所有进化任务"""
        logger.info("🚀 立即执行所有进化任务...")
        
        self._run_behavior_evolution()
        self._run_knowledge_evolution()
        self._run_strategy_evolution()
        self._run_meta_learning()
        
        logger.info("✅ 所有进化任务执行完成")
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        return {
            "running": self._running,
            "components": {
                "behavior_evolution": self._behavior_engine is not None,
                "knowledge_evolution": self._knowledge_engine is not None,
                "strategy_evolution": self._strategy_engine is not None,
                "meta_learning": self._meta_learner is not None
            },
            "last_run": {
                "behavior": self._last_behavior_run.isoformat() if self._last_behavior_run else None,
                "knowledge": self._last_knowledge_run.isoformat() if self._last_knowledge_run else None,
                "strategy": self._last_strategy_run.isoformat() if self._last_strategy_run else None,
                "meta": self._last_meta_run.isoformat() if self._last_meta_run else None
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def get_evolution_report(self) -> Dict:
        """获取完整的进化报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "scheduler_status": self.get_status(),
            "behavior_evolution": None,
            "knowledge_evolution": None,
            "strategy_evolution": None,
            "meta_learning": None
        }
        
        try:
            if self._behavior_engine:
                report["behavior_evolution"] = self._behavior_engine.get_evolution_report()
        except Exception as e:
            logger.debug(f"获取行为进化报告失败: {e}")
        
        try:
            if self._knowledge_engine:
                report["knowledge_evolution"] = self._knowledge_engine.get_evolution_report()
        except Exception as e:
            logger.debug(f"获取知识进化报告失败: {e}")
        
        try:
            if self._strategy_engine:
                report["strategy_evolution"] = self._strategy_engine.get_evolution_report()
        except Exception as e:
            logger.debug(f"获取策略进化报告失败: {e}")
        
        try:
            if self._meta_learner:
                report["meta_learning"] = self._meta_learner.get_learning_report()
        except Exception as e:
            logger.debug(f"获取元学习报告失败: {e}")
        
        return report


_evolution_scheduler: Optional[EvolutionScheduler] = None


def get_evolution_scheduler() -> EvolutionScheduler:
    """获取进化调度器单例"""
    global _evolution_scheduler
    if _evolution_scheduler is None:
        _evolution_scheduler = EvolutionScheduler()
    return _evolution_scheduler


def start_evolution_scheduler():
    """启动进化调度器（便捷函数）"""
    scheduler = get_evolution_scheduler()
    scheduler.start()


def stop_evolution_scheduler():
    """停止进化调度器（便捷函数）"""
    scheduler = get_evolution_scheduler()
    scheduler.stop()