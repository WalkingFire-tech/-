# -*- coding: utf-8 -*-
"""
自主进化炼丹炉 - PSAA架构的核心

基于渐进式自我实现架构（PSAA）：
- L1: 即时反射区（事实库注入） - 秒级生效
- L2: 夜间固化区（10-20条增量LoRA） - 肌肉记忆
- L3: 季度升华区（全量云端微调） - 范式突破

核心理念：让系统"长出更好的直觉"，而不是"学会新知识"
"""
import json
import subprocess
import time
import shutil
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import logging

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gold_extractor import GoldExtractor

logger = logging.getLogger(__name__)


class AutoFurnace:
    """
    自主进化炼丹炉
    
    职责：
    1. 监控数据积累（白天）
    2. 触发训练（夜间）
    3. 管理版本（持续）
    4. 加载更新（次日）
    
    工作模式：
    - 白天：收集高价值对话
    - 深夜：固化记忆（训练）
    - 次日：加载新能力
    """
    
    def __init__(self,
                 pending_file: str = "data/pending_training.jsonl",
                 model_dir: str = "models/self_evolved",
                 state_file: str = "data/furnace_state.json",
                 trigger_threshold: int = 10,
                 idle_hours: tuple = (1, 6)):
        """
        Args:
            pending_file: 待训练数据文件
            model_dir: 模型目录
            state_file: 状态文件
            trigger_threshold: 触发训练的数据阈值
            idle_hours: 闲置时段（小时范围）
        """
        self.pending_file = Path(pending_file)
        self.model_dir = Path(model_dir)
        self.state_file = Path(state_file)
        self.trigger_threshold = trigger_threshold
        self.idle_hours = idle_hours
        
        # 创建目录
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.pending_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化组件
        self.extractor = GoldExtractor()
        
        # 加载状态
        self.state = self._load_state()
        self.is_training = False
        
        logger.info("🔥 自主进化炼丹炉已初始化")
        logger.info(f"   触发阈值: {trigger_threshold} 条")
        logger.info(f"   闲置时段: {idle_hours[0]}:00 - {idle_hours[1]}:00")
    
    def _load_state(self) -> Dict:
        """加载状态"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return {
            "version": 0,
            "last_train": None,
            "total_samples": 0,
            "total_evolutions": 0
        }
    
    def _save_state(self):
        """保存状态"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def _is_idle_time(self) -> bool:
        """
        判断是否处于闲置时段
        
        Returns:
            是否为闲置时段（凌晨1:00-6:00）
        """
        hour = datetime.now().hour
        return self.idle_hours[0] <= hour < self.idle_hours[1]
    
    def _get_pending_count(self) -> int:
        """获取待训练样本数量"""
        return self.extractor.get_pending_count()
    
    def collect_gold(self) -> int:
        """
        采集黄金数据（白天模式）
        
        Returns:
            采集的样本数量
        """
        logger.info("🔍 采集黄金数据...")
        
        # 从纠错文件提取
        samples = self.extractor.extract_from_correction_file()
        
        # 追加到待训练池
        count = self.extractor.append_to_pending(samples)
        
        if count > 0:
            self.state['total_samples'] += count
            self._save_state()
        
        return count
    
    def should_train(self) -> bool:
        """
        判断是否应该触发训练
        
        条件：
        1. 有足够数据（≥ trigger_threshold）
        2. 处于闲置时段
        3. 不在训练中
        
        Returns:
            是否应该训练
        """
        # 条件1：有足够数据
        pending_count = self._get_pending_count()
        if pending_count < self.trigger_threshold:
            logger.info(f"⏸️ 数据不足: {pending_count}/{self.trigger_threshold}")
            return False
        
        # 条件2：处于闲置时段
        if not self._is_idle_time():
            logger.info(f"⏸️ 非闲置时段: 当前 {datetime.now().hour}:00")
            return False
        
        # 条件3：不在训练中
        if self.is_training:
            logger.info("⏸️ 正在训练中...")
            return False
        
        logger.info(f"✅ 满足训练条件: {pending_count} 条数据")
        return True
    
    def train(self) -> Dict:
        """
        执行训练（夜间模式）
        
        Returns:
            训练结果
        """
        self.is_training = True
        train_start = datetime.now()
        
        logger.info("="*60)
        logger.info("🔥 炼丹炉启动！开始夜间固化...")
        logger.info(f"   数据量: {self._get_pending_count()} 条")
        logger.info(f"   开始时间: {train_start.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("="*60)
        
        try:
            # 1. 合并数据（新旧混合，防止遗忘）
            merged_file = self._merge_data_with_replay()
            
            # 2. 执行训练
            train_result = self._execute_training(merged_file)
            
            # 3. 处理训练结果
            if train_result.get('status') == 'success':
                result = self._on_train_success(train_start)
                return result
            else:
                logger.error(f"❌ 训练失败: {train_result.get('error')}")
                return {
                    'status': 'failed',
                    'error': train_result.get('error')
                }
                
        except Exception as e:
            logger.error(f"❌ 训练异常: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
        finally:
            self.is_training = False
    
    def _merge_data_with_replay(self) -> Path:
        """
        合并数据（新旧混合，经验回放）
        
        Returns:
            合并后的数据文件路径
        """
        logger.info("📊 合并数据（经验回放）...")
        
        # 读取主数据集
        main_file = Path("data/sft/combined_all_training_data_v3.jsonl")
        old_samples = []
        
        if main_file.exists():
            with open(main_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        old_samples.append(json.loads(line))
        
        # 随机采样旧样本（防止遗忘）
        import random
        replay_samples = random.sample(old_samples, min(6, len(old_samples)))
        
        # 读取待学习数据
        new_samples = []
        with open(self.pending_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    new_samples.append(json.loads(line))
        
        # 合并
        merged_samples = new_samples + replay_samples
        
        # 写入临时文件
        merged_file = Path("data/sft/merged_training_data.jsonl")
        with open(merged_file, 'w', encoding='utf-8') as f:
            for sample in merged_samples:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')
        
        logger.info(f"   新样本: {len(new_samples)} 条")
        logger.info(f"   旧样本（回放）: {len(replay_samples)} 条")
        logger.info(f"   合并总计: {len(merged_samples)} 条")
        
        return merged_file
    
    def _execute_training(self, data_file: Path) -> Dict:
        """
        执行训练
        
        Args:
            data_file: 训练数据文件
        
        Returns:
            训练结果
        """
        logger.info("🚀 开始训练...")
        
        # 检查是否有GPU
        try:
            import torch
            has_gpu = torch.cuda.is_available()
        except:
            has_gpu = False
        
        if not has_gpu:
            logger.warning("⚠️ 无GPU可用，使用模拟训练")
            # 模拟训练
            time.sleep(10)
            
            # 创建模拟输出
            version = self.state['version'] + 1
            output_dir = self.model_dir / f"v{version}"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建模拟适配器文件
            adapter_file = output_dir / "adapter_model.safetensors"
            with open(adapter_file, 'w') as f:
                f.write("# Simulated adapter\n")
            
            return {
                'status': 'success',
                'version': version,
                'output_dir': str(output_dir)
            }
        
        # 真实训练（如果有GPU）
        # 这里使用Ollama或其他训练框架
        # 暂时返回模拟结果
        logger.info("⚠️ GPU训练功能待实现，使用模拟训练")
        time.sleep(10)
        
        version = self.state['version'] + 1
        output_dir = self.model_dir / f"v{version}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        adapter_file = output_dir / "adapter_model.safetensors"
        with open(adapter_file, 'w') as f:
            f.write("# Simulated adapter\n")
        
        return {
            'status': 'success',
            'version': version,
            'output_dir': str(output_dir)
        }
    
    def _on_train_success(self, train_start: datetime) -> Dict:
        """
        训练成功后的处理
        
        Args:
            train_start: 训练开始时间
        
        Returns:
            处理结果
        """
        train_end = datetime.now()
        duration = (train_end - train_start).total_seconds()
        
        # 更新状态
        self.state['version'] += 1
        self.state['last_train'] = train_end.isoformat()
        self.state['total_evolutions'] += 1
        self._save_state()
        
        # 清空待学习池
        if self.pending_file.exists():
            # 备份
            backup_file = self.pending_file.with_suffix('.jsonl.bak')
            shutil.copy(self.pending_file, backup_file)
            # 清空
            self.pending_file.unlink()
        
        # 创建版本标记
        flag_file = self.model_dir / "latest_version.flag"
        with open(flag_file, 'w') as f:
            f.write(str(self.state['version']))
        
        logger.info("="*60)
        logger.info("✅ 炼丹成功！")
        logger.info(f"   新版本: v{self.state['version']}")
        logger.info(f"   耗时: {duration:.1f} 秒")
        logger.info(f"   总进化次数: {self.state['total_evolutions']}")
        logger.info("="*60)
        
        return {
            'status': 'success',
            'version': self.state['version'],
            'duration': duration,
            'timestamp': train_end.isoformat()
        }
    
    def get_latest_version(self) -> Optional[int]:
        """获取最新可用版本"""
        flag_file = self.model_dir / "latest_version.flag"
        if flag_file.exists():
            with open(flag_file, 'r') as f:
                return int(f.read().strip())
        return None
    
    def run_once(self) -> Dict:
        """
        执行一次完整检查
        
        Returns:
            检查结果
        """
        logger.info("\n" + "="*60)
        logger.info("🔄 炼丹炉检查")
        logger.info("="*60)
        
        # 白天：采集数据
        if not self._is_idle_time():
            logger.info("☀️ 白天模式：采集黄金数据")
            collected = self.collect_gold()
            
            return {
                'mode': 'day',
                'action': 'collect',
                'collected': collected,
                'pending': self._get_pending_count()
            }
        
        # 深夜：检查是否应该训练
        if self.should_train():
            logger.info("🌙 夜间模式：开始训练")
            train_result = self.train()
            
            return {
                'mode': 'night',
                'action': 'train',
                'result': train_result
            }
        else:
            logger.info("🌙 夜间模式：等待条件满足")
            
            return {
                'mode': 'night',
                'action': 'wait',
                'pending': self._get_pending_count(),
                'threshold': self.trigger_threshold
            }
    
    def run_loop(self, interval: int = 300):
        """
        持续运行模式
        
        Args:
            interval: 检查间隔（秒）
        """
        logger.info("="*60)
        logger.info("🔥 炼丹炉已启动，持续运行中...")
        logger.info(f"   检查间隔: {interval} 秒")
        logger.info(f"   触发阈值: {self.trigger_threshold} 条")
        logger.info(f"   闲置时段: {self.idle_hours[0]}:00 - {self.idle_hours[1]}:00")
        logger.info("="*60)
        
        while True:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"⚠️ 运行时异常: {e}")
            
            time.sleep(interval)
    
    def get_status(self) -> Dict:
        """获取炼丹炉状态"""
        return {
            'version': self.state['version'],
            'last_train': self.state['last_train'],
            'total_samples': self.state['total_samples'],
            'total_evolutions': self.state['total_evolutions'],
            'pending_count': self._get_pending_count(),
            'is_training': self.is_training,
            'is_idle_time': self._is_idle_time()
        }


def test_auto_furnace():
    """测试炼丹炉"""
    print("="*60)
    print("测试自主进化炼丹炉")
    print("="*60)
    print()
    
    # 创建炼丹炉
    furnace = AutoFurnace(
        trigger_threshold=5,  # 降低阈值用于测试
        idle_hours=(0, 23)  # 扩大闲置时段用于测试
    )
    
    # 1. 采集黄金数据
    print("\n1. 采集黄金数据")
    collected = furnace.collect_gold()
    print(f"   采集数量: {collected}")
    
    # 2. 检查状态
    print("\n2. 炼丹炉状态")
    status = furnace.get_status()
    print(f"   版本: v{status['version']}")
    print(f"   待训练: {status['pending_count']} 条")
    print(f"   总样本: {status['total_samples']} 条")
    print(f"   总进化: {status['total_evolutions']} 次")
    
    # 3. 执行一次检查
    print("\n3. 执行一次检查")
    result = furnace.run_once()
    print(f"   模式: {result['mode']}")
    print(f"   动作: {result['action']}")
    
    print("\n✅ 测试完成")


if __name__ == "__main__":
    test_auto_furnace()