#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动碎片时间炼丹炉

使用方式：
    # 持续运行模式（推荐）
    python scripts/start_furnace.py
    
    # 单次检查模式
    python scripts/start_furnace.py --once
    
    # 自定义配置
    python scripts/start_furnace.py --interval 600 --threshold 10
"""
import sys
from pathlib import Path
import argparse

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.furnace_scheduler import FurnaceScheduler


def main():
    parser = argparse.ArgumentParser(description="联盟拓荒者 - 碎片时间炼丹炉")
    parser.add_argument("--once", action="store_true", help="只执行一次检查")
    parser.add_argument("--interval", type=int, default=300, help="检查间隔（秒），默认300秒")
    parser.add_argument("--threshold", type=int, default=5, help="触发训练的数据阈值，默认5条")
    
    args = parser.parse_args()
    
    # 创建调度器
    scheduler = FurnaceScheduler(
        trigger_threshold=args.threshold,
        check_interval=args.interval
    )
    
    # 显示配置
    print("\n" + "="*70)
    print("🔥 联盟拓荒者 - 碎片时间炼丹炉")
    print("="*70)
    print(f"   触发阈值: {args.threshold} 条黄金数据")
    print(f"   检查间隔: {args.interval} 秒")
    print("="*70)
    print()
    
    # 显示当前状态
    status = scheduler.get_status()
    print("📊 当前状态:")
    print(f"   版本: v{status['state']['version']}")
    print(f"   待学习: {status['state']['pending']} 条")
    print(f"   总学习: {status['state']['total_learned']} 条")
    print(f"   总训练时间: {status['state']['total_training_time']} 分钟")
    print(f"   有检查点: {'是' if status['state']['has_checkpoint'] else '否'}")
    print(f"   可用时间: {status['available_time']} 分钟")
    print()
    
    # 执行
    if args.once:
        print("🔄 执行单次检查...")
        result = scheduler.run_once()
        print(f"\n✅ 检查完成")
        print(f"   动作: {result['action']}")
    else:
        print("🔄 持续运行模式...")
        print("   按 Ctrl+C 优雅退出")
        print()
        scheduler.run_loop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 炼丹炉已停止")
        sys.exit(0)