# -*- coding: utf-8 -*-
"""
炼丹炉状态管理器 - 断点续传核心

记录每一次训练的进度，支持断点续传
适配开关机场景：关机时保存状态，开机时恢复
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class FurnaceState:
    """
    炼丹炉状态管理器
    
    核心功能：
    1. 记录训练进度（检查点）
    2. 管理待学习样本
    3. 支持断点续传
    4. 持久化到文件（关机不丢失）
    """
    
    def __init__(self, state_file: str = "data/furnace_state.json"):
        """
        Args:
            state_file: 状态文件路径
        """
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()
        
        logger.info("📊 炼丹炉状态管理器已初始化")
    
    def _load(self) -> Dict:
        """加载状态"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self._default_state()
    
    def _default_state(self) -> Dict:
        """默认状态"""
        return {
            "current_version": 0,
            "total_learned_samples": 0,
            "pending_samples": [],
            "training_checkpoint": None,
            "training_history": [],
            "last_online_time": None,
            "total_training_time_minutes": 0
        }
    
    def save(self):
        """保存状态"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def add_pending_sample(self, sample: Dict):
        """
        添加待学习样本
        
        Args:
            sample: 样本数据
        """
        sample['added_at'] = datetime.now().isoformat()
        self.data["pending_samples"].append(sample)
        self.save()
        
        logger.info(f"📝 添加待学习样本，当前待学习: {len(self.data['pending_samples'])} 条")
    
    def get_pending_count(self) -> int:
        """获取待学习样本数量"""
        return len(self.data["pending_samples"])
    
    def pop_pending(self, count: int = 10) -> List[Dict]:
        """
        提取指定数量的待学习样本（先入先出）
        
        Args:
            count: 提取数量
        
        Returns:
            样本列表
        """
        samples = self.data["pending_samples"][:count]
        self.data["pending_samples"] = self.data["pending_samples"][count:]
        self.save()
        
        logger.info(f"📤 提取 {len(samples)} 条待学习样本")
        
        return samples
    
    def checkpoint(self, epoch: int, step: int, total_steps: int, loss: float):
        """
        保存训练检查点
        
        Args:
            epoch: 当前轮数
            step: 当前步数
            total_steps: 总步数
            loss: 当前损失
        """
        self.data["training_checkpoint"] = {
            "epoch": epoch,
            "step": step,
            "total_steps": total_steps,
            "loss": loss,
            "last_updated": datetime.now().isoformat()
        }
        self.save()
        
        logger.info(f"💾 保存检查点: step {step}/{total_steps}, loss {loss:.4f}")
    
    def get_checkpoint(self) -> Optional[Dict]:
        """获取检查点"""
        return self.data.get("training_checkpoint")
    
    def clear_checkpoint(self):
        """清除检查点"""
        self.data["training_checkpoint"] = None
        self.save()
    
    def record_training(self, samples: int, duration_minutes: int):
        """
        记录一次训练完成
        
        Args:
            samples: 学习的样本数
            duration_minutes: 训练时长（分钟）
        """
        self.data["current_version"] += 1
        self.data["total_learned_samples"] += samples
        self.data["total_training_time_minutes"] += duration_minutes
        
        self.data["training_history"].append({
            "date": datetime.now().isoformat(),
            "samples": samples,
            "version": self.data["current_version"],
            "duration_minutes": duration_minutes
        })
        
        self.data["training_checkpoint"] = None
        self.save()
        
        logger.info(f"✅ 记录训练完成: v{self.data['current_version']}, {samples}条, {duration_minutes}分钟")
    
    def get_version(self) -> int:
        """获取当前版本"""
        return self.data["current_version"]
    
    def set_online(self):
        """标记系统上线"""
        self.data["last_online_time"] = datetime.now().isoformat()
        self.save()
    
    def get_summary(self) -> Dict:
        """获取状态摘要"""
        return {
            "version": self.data["current_version"],
            "total_learned": self.data["total_learned_samples"],
            "pending": len(self.data["pending_samples"]),
            "total_training_time": self.data["total_training_time_minutes"],
            "has_checkpoint": self.data["training_checkpoint"] is not None,
            "last_online": self.data["last_online_time"]
        }


def test_furnace_state():
    """测试状态管理器"""
    print("="*60)
    print("测试炼丹炉状态管理器")
    print("="*60)
    print()
    
    state = FurnaceState()
    
    # 1. 添加待学习样本
    print("\n1. 添加待学习样本")
    for i in range(5):
        state.add_pending_sample({
            "instruction": f"测试问题{i+1}",
            "output": f"测试答案{i+1}",
            "source": "test"
        })
    
    print(f"   待学习样本: {state.get_pending_count()} 条")
    
    # 2. 保存检查点
    print("\n2. 保存检查点")
    state.checkpoint(epoch=0, step=50, total_steps=200, loss=2.34)
    
    checkpoint = state.get_checkpoint()
    print(f"   检查点: step {checkpoint['step']}/{checkpoint['total_steps']}")
    
    # 3. 提取样本
    print("\n3. 提取样本")
    samples = state.pop_pending(3)
    print(f"   提取数量: {len(samples)}")
    print(f"   剩余样本: {state.get_pending_count()}")
    
    # 4. 记录训练
    print("\n4. 记录训练")
    state.record_training(samples=3, duration_minutes=15)
    
    summary = state.get_summary()
    print(f"   版本: v{summary['version']}")
    print(f"   总学习: {summary['total_learned']} 条")
    print(f"   总训练时间: {summary['total_training_time']} 分钟")
    
    print("\n✅ 测试完成")


if __name__ == "__main__":
    test_furnace_state()