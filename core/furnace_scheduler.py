# -*- coding: utf-8 -*-
"""
炼丹炉主调度器 - 适配开关机场景

核心能力：
1. 开机时自动检查并执行训练
2. 关机时保存状态
3. 利用碎片时间进行训练
4. 支持断点续传
"""
import time
import signal
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.furnace_state import FurnaceState
from core.furnace_trainer import FurnaceTrainer
from core.gold_extractor import GoldExtractor

logger = logging.getLogger(__name__)


class FurnaceScheduler:
    """
    炼丹炉调度器
    
    适配开关机场景：
    - 开机时自动检查并执行训练
    - 关机时保存状态
    - 利用碎片时间进行训练
    """
    
    def __init__(self,
                 trigger_threshold: int = 5,
                 check_interval: int = 300):
        """
        Args:
            trigger_threshold: 触发训练的数据阈值
            check_interval: 检查间隔（秒）
        """
        self.trigger_threshold = trigger_threshold
        self.check_interval = check_interval
        
        # 初始化组件
        self.state = FurnaceState()
        self.trainer = FurnaceTrainer(self.state)
        self.extractor = GoldExtractor()
        
        self.is_running = True
        
        # 注册信号处理（优雅关机）
        try:
            signal.signal(signal.SIGINT, self._shutdown)
            signal.signal(signal.SIGTERM, self._shutdown)
        except Exception:
            pass  # Windows可能不支持
        
        logger.info("🎛️ 炼丹炉调度器已初始化")
    
    def _shutdown(self, signum, frame):
        """优雅关机"""
        logger.info("\n👋 收到关机信号，保存状态...")
        self.is_running = False
        self.state.save()
    
    def _extract_gold(self) -> int:
        """
        提取黄金数据
        
        Returns:
            提取的数量
        """
        # 从纠错文件提取
        samples = self.extractor.extract_from_correction_file()
        
        if samples:
            for sample in samples:
                self.state.add_pending_sample(sample)
            
            logger.info(f"🔥 提炼 {len(samples)} 条黄金样本")
            logger.info(f"   待学习池: {self.state.get_pending_count()} 条")
        
        return len(samples)
    
    def run_once(self) -> Dict:
        """
        执行一次完整检查
        
        Returns:
            检查结果
        """
        logger.info("\n" + "="*60)
        logger.info(f"⏰ 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        
        # 显示当前状态
        summary = self.state.get_summary()
        logger.info(f"📊 当前状态:")
        logger.info(f"   版本: v{summary['version']}")
        logger.info(f"   待学习: {summary['pending']} 条")
        logger.info(f"   总学习: {summary['total_learned']} 条")
        logger.info(f"   总训练时间: {summary['total_training_time']} 分钟")
        logger.info(f"   有检查点: {'是' if summary['has_checkpoint'] else '否'}")
        
        # 1. 提取黄金数据
        extracted = self._extract_gold()
        
        # 2. 判断是否应该训练
        should, reason = self.trainer.should_train()
        logger.info(f"\n🔍 训练决策: {reason}")
        
        if should:
            # 获取可用时间（分钟）
            available = self.trainer._get_available_time()
            max_time = min(available, 60)  # 最多训练1小时
            
            logger.info(f"⏱️ 可用时间: {available} 分钟，本次最多训练 {max_time} 分钟")
            
            # 执行训练
            train_result = self.trainer.train(max_time_minutes=max_time)
            
            return {
                'action': 'train',
                'extracted': extracted,
                'train_result': train_result
            }
        else:
            logger.info("⏳ 跳过训练")
            
            return {
                'action': 'skip',
                'extracted': extracted,
                'reason': reason
            }
    
    def run_loop(self):
        """
        主循环（持续运行模式）
        """
        logger.info("="*60)
        logger.info("🔥 炼丹炉已启动（碎片时间模式）")
        logger.info("="*60)
        logger.info(f"   检查间隔: {self.check_interval} 秒")
        logger.info(f"   触发阈值: {self.trigger_threshold} 条")
        logger.info("   系统将在开机时自动学习")
        logger.info("   按 Ctrl+C 优雅退出")
        logger.info("="*60)
        
        # 标记上线
        self.state.set_online()
        
        while self.is_running:
            try:
                # 执行一次检查
                result = self.run_once()
                
                # 计算下次检查时间
                next_check = datetime.now().timestamp() + self.check_interval
                next_check_str = datetime.fromtimestamp(next_check).strftime('%H:%M:%S')
                
                logger.info(f"\n⏳ 下次检查: {next_check_str}")
                
                # 等待
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                logger.info("\n👋 用户中断，保存状态...")
                self.is_running = False
                self.state.save()
                break
            except Exception as e:
                logger.error(f"⚠️ 运行时异常: {e}")
                time.sleep(self.check_interval)
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        summary = self.state.get_summary()
        
        should_train, reason = self.trainer.should_train()
        available_time = self.trainer._get_available_time()
        
        return {
            'state': summary,
            'should_train': should_train,
            'train_reason': reason,
            'available_time': available_time,
            'is_training': self.trainer.is_training,
            'is_running': self.is_running
        }


def test_furnace_scheduler():
    """测试调度器"""
    print("="*60)
    print("测试炼丹炉调度器")
    print("="*60)
    print()
    
    scheduler = FurnaceScheduler(
        trigger_threshold=5,
        check_interval=60
    )
    
    # 1. 执行一次检查
    print("\n1. 执行一次检查")
    result = scheduler.run_once()
    print(f"   动作: {result['action']}")
    
    # 2. 获取状态
    print("\n2. 获取状态")
    status = scheduler.get_status()
    print(f"   版本: v{status['state']['version']}")
    print(f"   待学习: {status['state']['pending']} 条")
    print(f"   应该训练: {status['should_train']}")
    print(f"   可用时间: {status['available_time']} 分钟")
    
    print("\n✅ 测试完成")


if __name__ == "__main__":
    test_furnace_scheduler()