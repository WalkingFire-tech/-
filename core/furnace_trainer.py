# -*- coding: utf-8 -*-
"""
碎片时间训练器 - 核心进化逻辑

利用任何可用的时间窗口进行增量训练
支持断点续传：关机时保存进度，开机时继续
"""
import json
import subprocess
import time
import shutil
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.furnace_state import FurnaceState

logger = logging.getLogger(__name__)


class FurnaceTrainer:
    """
    碎片时间训练器
    
    核心能力：
    1. 估算可用时间窗口
    2. 执行增量训练
    3. 支持断点续传
    4. 自动控制训练时长
    """
    
    def __init__(self, state: FurnaceState):
        """
        Args:
            state: 状态管理器
        """
        self.state = state
        self.model_dir = Path("models/self_evolved")
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.is_training = False
        self.last_heartbeat = datetime.now()
        
        logger.info("🔥 碎片时间训练器已初始化")
    
    def _get_available_time(self) -> int:
        """
        估算当前可用的训练时间
        
        Returns:
            预计可用的分钟数（基于用户使用模式）
        """
        hour = datetime.now().hour
        
        # 根据时间段估算可用时间
        if 0 <= hour < 6:
            return 180  # 深夜，有3小时
        elif 6 <= hour < 9:
            return 60   # 早晨，有1小时
        elif 12 <= hour < 14:
            return 30   # 午休，有30分钟
        elif 22 <= hour < 24:
            return 90   # 晚间，有1.5小时
        else:
            return 15   # 其他时间，只有15分钟
    
    def _min_training_time(self) -> int:
        """
        单次训练最少需要的时间（分钟）
        
        Returns:
            最小训练时间
        """
        # 1.5B模型 + 10条数据 ≈ 10-15分钟
        return 15
    
    def should_train(self) -> tuple:
        """
        判断是否应该启动训练
        
        Returns:
            (是否训练, 原因)
        """
        # 1. 检查是否有待学习数据
        pending_count = self.state.get_pending_count()
        if pending_count < 5:
            return False, f"待学习数据不足 ({pending_count}/5)"
        
        # 2. 检查是否有足够的时间窗口
        available = self._get_available_time()
        if available < self._min_training_time():
            return False, f"时间窗口太短 ({available}分钟 < {self._min_training_time()}分钟)"
        
        # 3. 检查是否已有检查点（可继续上次的训练）
        checkpoint = self.state.get_checkpoint()
        if checkpoint:
            return True, f"继续上次训练 (step {checkpoint['step']}/{checkpoint['total_steps']})"
        
        # 4. 开始新训练
        version = self.state.get_version()
        return True, f"开始新一轮训练 (版本 v{version + 1}, {pending_count}条)"
    
    def train(self, max_time_minutes: Optional[int] = None) -> Dict:
        """
        执行训练（自动控制时长）
        
        Args:
            max_time_minutes: 最大训练时间，None表示不限制
        
        Returns:
            训练结果
        """
        if self.is_training:
            logger.warning("⏳ 已有训练在运行中")
            return {'status': 'already_training'}
        
        self.is_training = True
        start_time = datetime.now()
        
        logger.info("="*60)
        logger.info("🔥 开始碎片时间训练")
        logger.info("="*60)
        
        try:
            # 1. 获取待学习数据
            pending = self.state.pop_pending(10)
            if not pending:
                logger.warning("📭 没有待学习数据")
                self.is_training = False
                return {'status': 'no_data'}
            
            # 2. 合并数据到主数据集
            self._merge_pending_data(pending)
            
            # 3. 获取检查点（如果有）
            checkpoint = self.state.get_checkpoint()
            
            # 4. 执行训练
            logger.info(f"📊 训练数据: {len(pending)} 条")
            logger.info(f"⏱️ 最大训练时间: {max_time_minutes or '不限制'} 分钟")
            
            # 模拟训练（实际应该调用训练框架）
            train_result = self._execute_training_simulated(
                pending=pending,
                checkpoint=checkpoint,
                max_time_minutes=max_time_minutes
            )
            
            # 5. 处理训练结果
            end_time = datetime.now()
            duration = int((end_time - start_time).total_seconds() / 60)
            
            if train_result['status'] == 'completed':
                # 训练完成
                self.state.record_training(
                    samples=len(pending),
                    duration_minutes=duration
                )
                self._create_version_marker()
                
                logger.info("="*60)
                logger.info(f"✅ 训练完成！版本 v{self.state.get_version()}")
                logger.info(f"   耗时: {duration} 分钟")
                logger.info("="*60)
                
                return {
                    'status': 'completed',
                    'version': self.state.get_version(),
                    'duration': duration
                }
            else:
                # 训练暂停（保存了检查点）
                logger.info("="*60)
                logger.info("⏸️ 训练暂停，已保存检查点")
                logger.info("   下次将从中断处继续")
                logger.info("="*60)
                
                return {
                    'status': 'paused',
                    'checkpoint': self.state.get_checkpoint()
                }
                
        except Exception as e:
            logger.error(f"❌ 训练异常: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            self.is_training = False
    
    def _merge_pending_data(self, pending: list):
        """
        合并待学习数据到主数据集
        
        Args:
            pending: 待学习数据
        """
        main_file = Path("data/sft/training_data.jsonl")
        main_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(main_file, 'a', encoding='utf-8') as mf:
            for sample in pending:
                mf.write(json.dumps(sample, ensure_ascii=False) + '\n')
        
        logger.info(f"📊 合并数据: {len(pending)} 条")
    
    def _execute_training_simulated(self, 
                                   pending: list,
                                   checkpoint: Optional[Dict],
                                   max_time_minutes: Optional[int]) -> Dict:
        """
        执行训练（模拟版）
        
        实际应该调用LLaMA Factory或其他训练框架
        
        Args:
            pending: 训练数据
            checkpoint: 检查点
            max_time_minutes: 最大训练时间
        
        Returns:
            训练结果
        """
        # 模拟训练过程
        total_steps = 100
        start_step = checkpoint['step'] if checkpoint else 0
        
        logger.info(f"🚀 开始训练: step {start_step} -> {total_steps}")
        
        start = time.time()
        
        # 模拟训练步骤
        for step in range(start_step, total_steps):
            # 模拟训练一步
            time.sleep(0.5)  # 每步0.5秒
            
            # 计算损失（模拟）
            loss = 2.5 - (step / total_steps) * 0.5
            
            # 每10步保存一次检查点
            if step % 10 == 0:
                self.state.checkpoint(
                    epoch=0,
                    step=step,
                    total_steps=total_steps,
                    loss=loss
                )
            
            # 检查是否超时
            if max_time_minutes:
                elapsed = time.time() - start
                # 简化：训练20步后暂停
                if step - start_step >= 20:
                    logger.info(f"⏰ 达到训练限制，暂停")
                    return {'status': 'paused'}
        
        # 训练完成
        return {'status': 'completed'}
    
    def _create_version_marker(self):
        """创建版本标记"""
        version = self.state.get_version()
        flag_file = self.model_dir / "latest_version.flag"
        with open(flag_file, 'w') as f:
            f.write(str(version))
        
        logger.info(f"✅ 创建版本标记: v{version}")


def test_furnace_trainer():
    """测试碎片时间训练器"""
    print("="*60)
    print("测试碎片时间训练器")
    print("="*60)
    print()
    
    from core.furnace_state import FurnaceState
    
    state = FurnaceState()
    trainer = FurnaceTrainer(state)
    
    # 1. 添加测试数据
    print("\n1. 添加测试数据")
    for i in range(10):
        state.add_pending_sample({
            "instruction": f"测试问题{i+1}",
            "output": f"测试答案{i+1}",
            "source": "test"
        })
    
    # 2. 判断是否应该训练
    print("\n2. 判断是否应该训练")
    should, reason = trainer.should_train()
    print(f"   应该训练: {should}")
    print(f"   原因: {reason}")
    
    # 3. 执行训练
    if should:
        print("\n3. 执行训练")
        result = trainer.train(max_time_minutes=5)
        print(f"   状态: {result['status']}")
    
    print("\n✅ 测试完成")


if __name__ == "__main__":
    test_furnace_trainer()