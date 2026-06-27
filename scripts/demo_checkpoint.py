#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
断点续传式进化架构完整演示

展示：
1. 系统开机 → 自动检查状态
2. 有待学习数据 → 开始训练
3. 训练中断 → 保存检查点
4. 系统关机 → 状态持久化
5. 再次开机 → 从检查点继续
"""
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.furnace_state import FurnaceState
from core.furnace_trainer import FurnaceTrainer
from core.gold_extractor import GoldExtractor


def demonstrate_checkpoint_training():
    """演示断点续传训练"""
    print("="*70)
    print("🧬 断点续传式进化演示")
    print("="*70)
    print()
    
    # ========== 场景1: 系统开机 ==========
    print("【场景1: 系统开机】")
    print("-"*70)
    print("用户: 打开电脑，系统启动...")
    
    state = FurnaceState()
    trainer = FurnaceTrainer(state)
    extractor = GoldExtractor()
    
    # 显示状态
    summary = state.get_summary()
    print(f"系统: 📊 状态检查:")
    print(f"      - 版本: v{summary['version']}")
    print(f"      - 待学习: {summary['pending']} 条")
    print(f"      - 总学习: {summary['total_learned']} 条")
    print(f"      - 有检查点: {'是' if summary['has_checkpoint'] else '否'}")
    print()
    
    # ========== 场景2: 提取黄金数据 ==========
    print("【场景2: 提取黄金数据】")
    print("-"*70)
    print("系统: 🔍 检查最近的对话记录...")
    
    samples = extractor.extract_from_correction_file()
    if samples:
        for sample in samples[:5]:  # 只添加5条用于演示
            state.add_pending_sample(sample)
    
    print(f"系统: ✅ 提取 {len(samples[:5])} 条黄金样本")
    print(f"      待学习池: {state.get_pending_count()} 条")
    print()
    
    # ========== 场景3: 开始训练 ==========
    print("【场景3: 开始训练】")
    print("-"*70)
    
    should, reason = trainer.should_train()
    print(f"系统: 🔍 训练决策: {reason}")
    
    if should:
        print("系统: 🔥 开始训练...")
        
        # 模拟训练过程（会被中断）
        print("系统:    Step 0/100, Loss: 2.50")
        time.sleep(1)
        
        print("系统:    Step 10/100, Loss: 2.35")
        state.checkpoint(epoch=0, step=10, total_steps=100, loss=2.35)
        time.sleep(1)
        
        print("系统:    Step 20/100, Loss: 2.20")
        state.checkpoint(epoch=0, step=20, total_steps=100, loss=2.20)
        time.sleep(1)
        
        print()
        print("用户: ⚠️ 我要用电脑了，暂停训练！")
        print()
        
        # ========== 场景4: 训练中断 ==========
        print("【场景4: 训练中断，保存检查点】")
        print("-"*70)
        
        checkpoint = state.get_checkpoint()
        print(f"系统: 💾 保存检查点:")
        print(f"      - Step: {checkpoint['step']}/{checkpoint['total_steps']}")
        print(f"      - Loss: {checkpoint['loss']:.4f}")
        print(f"      - 时间: {checkpoint['last_updated'][:19]}")
        print()
        
        # ========== 场景5: 系统关机 ==========
        print("【场景5: 系统关机】")
        print("-"*70)
        print("用户: 关闭电脑...")
        state.save()
        print("系统: ✅ 状态已保存到 data/furnace_state.json")
        print()
        
        # ========== 场景6: 再次开机 ==========
        print("【场景6: 再次开机，从检查点继续】")
        print("-"*70)
        print("用户: 重新打开电脑...")
        
        # 重新加载状态
        state2 = FurnaceState()
        trainer2 = FurnaceTrainer(state2)
        
        summary2 = state2.get_summary()
        print(f"系统: 📊 状态检查:")
        print(f"      - 版本: v{summary2['version']}")
        print(f"      - 待学习: {summary2['pending']} 条")
        print(f"      - 有检查点: {'是' if summary2['has_checkpoint'] else '否'}")
        
        checkpoint2 = state2.get_checkpoint()
        if checkpoint2:
            print(f"      - 检查点: step {checkpoint2['step']}/{checkpoint2['total_steps']}")
        
        print()
        print("系统: 🔥 继续上次训练...")
        print(f"      从 step {checkpoint2['step']} 继续")
        
        # 继续训练
        for step in range(checkpoint2['step'] + 10, 100, 10):
            loss = 2.20 - (step / 100) * 0.5
            print(f"系统:    Step {step}/100, Loss: {loss:.2f}")
            state2.checkpoint(epoch=0, step=step, total_steps=100, loss=loss)
            time.sleep(0.5)
        
        # 训练完成
        state2.record_training(samples=5, duration_minutes=10)
        
        print()
        print("系统: ✅ 训练完成！")
        print(f"      新版本: v{state2.get_version()}")
        print()
    
    # ========== 总结 ==========
    print("="*70)
    print("✅ 断点续传式进化演示完成")
    print("="*70)
    print()
    
    print("💡 核心机制:")
    print("   1. 训练中断 → 自动保存检查点")
    print("   2. 系统关机 → 状态持久化到文件")
    print("   3. 再次开机 → 从检查点继续训练")
    print("   4. 完全不浪费计算资源")
    print()
    
    print("🎯 与传统训练的对比:")
    print("   传统方式: 训练中断 → 进度丢失 → 从头开始")
    print("   断点续传: 训练中断 → 保存检查点 → 继续训练")
    print()
    
    print("🔥 启动炼丹炉:")
    print("   python scripts/start_furnace.py")
    print("   或双击 start_furnace.bat")
    print()


if __name__ == "__main__":
    demonstrate_checkpoint_training()