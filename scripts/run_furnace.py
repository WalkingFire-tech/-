#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动自主进化炼丹炉

使用方式：
    # 持续运行模式（后台）
    python scripts/run_furnace.py
    
    # 单次检查模式
    python scripts/run_furnace.py --once
    
    # 自定义检查间隔
    python scripts/run_furnace.py --interval 600
"""
import sys
from pathlib import Path
import argparse

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.auto_furnace import AutoFurnace


def main():
    parser = argparse.ArgumentParser(description="联盟拓荒者 - 自主进化炼丹炉")
    parser.add_argument("--once", action="store_true", help="只执行一次检查")
    parser.add_argument("--interval", type=int, default=300, help="检查间隔（秒），默认300秒")
    parser.add_argument("--threshold", type=int, default=10, help="触发训练的数据阈值，默认10条")
    parser.add_argument("--idle-start", type=int, default=1, help="闲置时段开始（小时），默认1点")
    parser.add_argument("--idle-end", type=int, default=6, help="闲置时段结束（小时），默认6点")
    
    args = parser.parse_args()
    
    # 创建炼丹炉
    furnace = AutoFurnace(
        trigger_threshold=args.threshold,
        idle_hours=(args.idle_start, args.idle_end)
    )
    
    # 显示配置
    print("\n" + "="*70)
    print("🔥 联盟拓荒者 - 自主进化炼丹炉")
    print("="*70)
    print(f"   触发阈值: {args.threshold} 条黄金数据")
    print(f"   闲置时段: {args.idle_start}:00 - {args.idle_end}:00")
    print(f"   检查间隔: {args.interval} 秒")
    print("="*70)
    print()
    
    # 获取当前状态
    status = furnace.get_status()
    print("📊 当前状态:")
    print(f"   版本: v{status['version']}")
    print(f"   待训练: {status['pending_count']} 条")
    print(f"   总样本: {status['total_samples']} 条")
    print(f"   总进化: {status['total_evolutions']} 次")
    print(f"   上次训练: {status['last_train'] or '从未'}")
    print()
    
    # 执行
    if args.once:
        print("🔄 执行单次检查...")
        result = furnace.run_once()
        print(f"\n✅ 检查完成")
        print(f"   模式: {result['mode']}")
        print(f"   动作: {result['action']}")
    else:
        print("🔄 持续运行模式...")
        print("   按 Ctrl+C 停止")
        print()
        furnace.run_loop(interval=args.interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 炼丹炉已停止")
        sys.exit(0)