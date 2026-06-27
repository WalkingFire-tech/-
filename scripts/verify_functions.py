#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统功能核对脚本

逐一核对每个功能模块是否正常工作
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_instant_learning():
    """测试即时学习系统"""
    print("\n【测试1: 即时学习系统】")
    print("-"*60)
    
    try:
        from core.instant_learning import InstantLearningSystem
        
        system = InstantLearningSystem()
        
        # 测试即时学习
        result = system.learn_instantly(
            concept="测试概念",
            assertion="测试内容",
            source='test'
        )
        
        # 测试检索
        knowledge, confidence = system.retrieve_knowledge("测试概念")
        
        # 获取统计
        stats = system.get_knowledge_stats()
        
        print(f"   ✅ 即时学习: {result['action']}")
        print(f"   ✅ 知识检索: 找到 {len(knowledge)} 条")
        print(f"   ✅ 知识统计: {stats['total_facts']} 条")
        
        return True
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        return False


def test_gold_extractor():
    """测试黄金数据提取器"""
    print("\n【测试2: 黄金数据提取器】")
    print("-"*60)
    
    try:
        from core.gold_extractor import GoldExtractor
        
        extractor = GoldExtractor()
        
        # 测试提取
        samples = extractor.extract_from_correction_file()
        
        # 获取待训练数量
        pending_count = extractor.get_pending_count()
        
        print(f"   ✅ 提取纠错: {len(samples)} 条")
        print(f"   ✅ 待训练池: {pending_count} 条")
        
        return True
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        return False


def test_furnace_state():
    """测试炼丹炉状态管理"""
    print("\n【测试3: 炼丹炉状态管理】")
    print("-"*60)
    
    try:
        from core.furnace_state import FurnaceState
        
        state = FurnaceState()
        
        # 测试状态操作
        summary = state.get_summary()
        
        # 测试检查点
        state.checkpoint(epoch=0, step=10, total_steps=100, loss=2.5)
        checkpoint = state.get_checkpoint()
        
        print(f"   ✅ 状态加载: v{summary['version']}")
        print(f"   ✅ 检查点保存: step {checkpoint['step']}/{checkpoint['total_steps']}")
        
        return True
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        return False


def test_furnace_scheduler():
    """测试炼丹炉调度器"""
    print("\n【测试4: 炼丹炉调度器】")
    print("-"*60)
    
    try:
        from core.furnace_scheduler import FurnaceScheduler
        
        scheduler = FurnaceScheduler()
        
        # 获取状态
        status = scheduler.get_status()
        
        print(f"   ✅ 调度器初始化: 成功")
        print(f"   ✅ 应该训练: {status['should_train']}")
        print(f"   ✅ 可用时间: {status['available_time']} 分钟")
        
        return True
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        return False


def test_learn_command():
    """测试/learn命令"""
    print("\n【测试5: /learn命令】")
    print("-"*60)
    
    try:
        from core.learn_command import LearnCommand
        
        learn = LearnCommand()
        
        # 测试从纠错学习
        result = learn.learn_from_correction(
            question="测试问题",
            wrong_answer="错误答案",
            correct_answer="正确答案",
            issues=["测试问题"]
        )
        
        # 列出技能
        skills = learn.list_skills()
        
        print(f"   ✅ 技能创建: {result['status']}")
        print(f"   ✅ 技能列表: {len(skills)} 个")
        
        return True
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        return False


def test_skill_tree():
    """测试技能树"""
    print("\n【测试6: 技能树系统】")
    print("-"*60)
    
    try:
        from core.skill_tree import SkillTree
        
        skill_tree = SkillTree()
        
        print(f"   ✅ 技能树加载: {len(skill_tree.skills)} 个技能")
        
        # 列出技能
        for skill_id, skill in list(skill_tree.skills.items())[:5]:
            print(f"      - {skill.name}: {skill.skill_type}")
        
        return True
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("="*70)
    print("🔍 系统功能核对")
    print("="*70)
    
    results = []
    
    # 运行所有测试
    results.append(("即时学习系统", test_instant_learning()))
    results.append(("黄金数据提取器", test_gold_extractor()))
    results.append(("炼丹炉状态管理", test_furnace_state()))
    results.append(("炼丹炉调度器", test_furnace_scheduler()))
    results.append(("/learn命令", test_learn_command()))
    results.append(("技能树系统", test_skill_tree()))
    
    # 显示结果
    print("\n" + "="*70)
    print("📊 测试结果摘要")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"   {status} {name}")
    
    print()
    print(f"   通过: {passed}/{total}")
    print(f"   状态: {'健康' if passed == total else '有问题'}")
    print()
    
    if passed == total:
        print("✅ 所有功能核对通过！")
    else:
        print("⚠️  部分功能存在问题，请检查！")


if __name__ == "__main__":
    main()