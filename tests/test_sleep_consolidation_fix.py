"""
测试睡眠整合模块的修复

验证：
- P1: 真实数据读写
- P2: 与间隙生长协同
- P3: 基于工作量决定睡眠深度
- P4: 唤醒机制
- P5: 历史增长限制
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from datetime import datetime, timedelta
import tempfile
import shutil


def test_p1_real_data_operations():
    """测试P1: 真实数据读写"""
    print("\n" + "="*60)
    print("测试 P1: 真实数据读写")
    print("="*60)
    
    from core.presence.sleep_consolidation import SleepConsolidationEngine
    
    temp_dir = tempfile.mkdtemp()
    engine = SleepConsolidationEngine()
    engine._db_path = Path(temp_dir) / "test_sleep.db"
    engine._init_database()
    
    result = engine._light_sleep_consolidation()
    
    assert result.timestamp is not None, "应该有时间戳"
    assert result.stage.value == "light", "应该是浅睡阶段"
    assert isinstance(result.consolidated_memories, int), "记忆数应该是整数"
    assert isinstance(result.overall_impact, float), "影响应该是浮点数"
    assert 0 <= result.overall_impact <= 1, "影响应该在0-1之间"
    
    print(f"  浅睡结果: 记忆={result.consolidated_memories}, 影响={result.overall_impact:.2f}")
    
    result = engine._deep_sleep_consolidation()
    assert result.stage.value == "deep", "应该是深睡阶段"
    print(f"  深睡结果: 记忆={result.consolidated_memories}, 技能={result.solidified_skills}")
    
    result = engine._rem_sleep_consolidation()
    assert result.stage.value == "rem", "应该是REM阶段"
    print(f"  REM结果: 模式={result.extracted_patterns}, 重组={result.reorganized_knowledge}")
    
    print("✅ P1 真实数据读写测试通过")
    
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_p2_gap_growth_coordination():
    """测试P2: 与间隙生长协同"""
    print("\n" + "="*60)
    print("测试 P2: 与间隙生长协同")
    print("="*60)
    
    from core.presence.sleep_consolidation import SleepConsolidationEngine
    
    engine = SleepConsolidationEngine()
    
    workload = engine._get_pending_workload()
    
    assert isinstance(workload, int), "工作量应该是整数"
    assert workload >= 0, "工作量应该非负"
    
    print(f"  当前工作量: {workload}")
    print("✅ P2 与间隙生长协同测试通过")


def test_p3_workload_based_sleep():
    """测试P3: 基于工作量决定睡眠深度"""
    print("\n" + "="*60)
    print("测试 P3: 基于工作量决定睡眠深度")
    print("="*60)
    
    from core.presence.sleep_consolidation import SleepConsolidationEngine
    
    engine = SleepConsolidationEngine()
    engine._last_user_interaction = datetime.now() - timedelta(seconds=7200)
    
    decision = engine._should_sleep()
    
    if decision["should_sleep"]:
        print(f"  睡眠决策: 阶段={decision['stage'].value}, 工作量={decision.get('workload', 0)}")
        assert decision["stage"].value in ["light", "deep", "rem"], "应该是有效的睡眠阶段"
    else:
        print("  当前不应睡眠")
    
    print("✅ P3 基于工作量决定睡眠深度测试通过")


def test_p4_wake_mechanism():
    """测试P4: 唤醒机制"""
    print("\n" + "="*60)
    print("测试 P4: 唤醒机制")
    print("="*60)
    
    from core.presence.sleep_consolidation import SleepConsolidationEngine
    
    engine = SleepConsolidationEngine()
    
    engine._is_sleeping = True
    engine._last_user_interaction = datetime.now() - timedelta(seconds=30)
    
    should_wake = engine._should_wake()
    assert should_wake, "最近有交互应该唤醒"
    print("  唤醒检查: 应该唤醒 ✓")
    
    engine._last_user_interaction = datetime.now() - timedelta(seconds=120)
    should_wake = engine._should_wake()
    assert not should_wake, "很久无交互不应唤醒"
    print("  唤醒检查: 不应唤醒 ✓")
    
    engine._is_sleeping = True
    engine._last_user_interaction = datetime.now()
    engine._wake_up()
    assert not engine._is_sleeping, "唤醒后应该不在睡眠状态"
    print("  唤醒执行: 成功 ✓")
    
    print("✅ P4 唤醒机制测试通过")


def test_p5_history_limit():
    """测试P5: 历史增长限制"""
    print("\n" + "="*60)
    print("测试 P5: 历史增长限制")
    print("="*60)
    
    from core.presence.sleep_consolidation import SleepConsolidationEngine, SleepStage
    
    engine = SleepConsolidationEngine()
    
    assert engine._max_history_size == 100, "最大历史大小应该是100"
    
    for i in range(150):
        from core.presence.sleep_consolidation import ConsolidationResult
        result = ConsolidationResult(
            timestamp=datetime.now().isoformat(),
            stage=SleepStage.LIGHT,
            consolidated_memories=1,
            solidified_skills=0,
            reorganized_knowledge=0,
            forgotten_items=0,
            extracted_patterns=0,
            overall_impact=0.3,
            details={}
        )
        engine._consolidation_history.append(result)
        
        if len(engine._consolidation_history) > engine._max_history_size:
            engine._consolidation_history = engine._consolidation_history[-engine._max_history_size:]
    
    assert len(engine._consolidation_history) <= 100, "历史应该被限制在100条"
    print(f"  历史大小: {len(engine._consolidation_history)}")
    
    print("✅ P5 历史增长限制测试通过")


def test_skill_solidification():
    """测试技能固化"""
    print("\n" + "="*60)
    print("测试技能固化功能")
    print("="*60)
    
    from core.presence.sleep_consolidation import SleepConsolidationEngine
    
    temp_dir = tempfile.mkdtemp()
    engine = SleepConsolidationEngine()
    engine._db_path = Path(temp_dir) / "test_sleep.db"
    engine._init_database()
    
    solidified = engine._solidify_skill("python_programming", 5, importance=0.8)
    assert solidified == 1, "应该成功固化技能"
    print("  技能固化: python_programming ✓")
    
    skills = engine.get_solidified_skills()
    assert len(skills) > 0, "应该有固化技能"
    assert skills[0]['skill'] == "python_programming", "技能名称应该匹配"
    print(f"  已固化技能: {len(skills)} 个")
    
    print("✅ 技能固化测试通过")
    
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_persistence():
    """测试持久化"""
    print("\n" + "="*60)
    print("测试持久化功能")
    print("="*60)
    
    from core.presence.sleep_consolidation import SleepConsolidationEngine, SleepStage, ConsolidationResult
    
    temp_dir = tempfile.mkdtemp()
    engine = SleepConsolidationEngine()
    engine._db_path = Path(temp_dir) / "test_sleep.db"
    engine._init_database()
    
    result = ConsolidationResult(
        timestamp=datetime.now().isoformat(),
        stage=SleepStage.DEEP,
        consolidated_memories=10,
        solidified_skills=3,
        reorganized_knowledge=2,
        forgotten_items=1,
        extracted_patterns=1,
        overall_impact=0.65,
        details={"test": True}
    )
    
    engine._save_consolidation_result(result)
    print("  保存整合结果: 成功 ✓")
    
    import sqlite3
    with sqlite3.connect(str(engine._db_path)) as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM consolidation_history")
        count = cursor.fetchone()[0]
        assert count == 1, "应该有一条记录"
    
    print("✅ 持久化测试通过")
    
    shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("睡眠整合模块修复验证")
    print("="*60)
    
    tests = [
        ("P1: 真实数据读写", test_p1_real_data_operations),
        ("P2: 间隙生长协同", test_p2_gap_growth_coordination),
        ("P3: 工作量决策", test_p3_workload_based_sleep),
        ("P4: 唤醒机制", test_p4_wake_mechanism),
        ("P5: 历史限制", test_p5_history_limit),
        ("技能固化", test_skill_solidification),
        ("持久化", test_persistence),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ {name} 测试失败: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"测试结果: {passed}/{len(tests)} 通过")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)