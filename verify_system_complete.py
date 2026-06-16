"""完整系统验证 - 检查所有模块是否正常工作"""
import sys
import sqlite3
from pathlib import Path

print("=" * 70)
print("联盟拓荒者 - 完整系统验证")
print("=" * 70)

test_results = []

def test(name, func):
    """测试包装器"""
    print(f"\n【{name}】")
    try:
        result = func()
        status = "✅ 通过" if result else "❌ 失败"
        test_results.append((name, result))
        print(f"结果: {status}")
        return result
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        test_results.append((name, False))
        return False

# 测试1: 核心模块导入
def test_core_imports():
    modules = [
        ("core.learning", "enhanced_learner"),
        ("core.genome_evolver", "genome_evolver"),
        ("core.cognitive_transformer", "cognitive_transformer"),
        ("core.memory_review", "memory_review"),
        ("core.active_scheduler", "active_scheduler"),
    ]
    
    for module_name, attr in modules:
        try:
            module = __import__(module_name, fromlist=[attr])
            obj = getattr(module, attr)
            print(f"  ✓ {module_name}.{attr}")
        except Exception as e:
            print(f"  ✗ {module_name}.{attr}: {e}")
            return False
    
    return True

test("核心模块导入", test_core_imports)

# 测试2: 进化模块导入
def test_evolution_imports():
    modules = [
        ("core.evolution.simulated_agent", "SimulatedAgent"),
        ("core.evolution.task_pool", "build_task_pool"),
        ("core.evolution.evolution_island", "EvolutionIsland"),
    ]
    
    for module_name, attr in modules:
        try:
            module = __import__(module_name, fromlist=[attr])
            obj = getattr(module, attr)
            print(f"  ✓ {module_name}.{attr}")
        except Exception as e:
            print(f"  ✗ {module_name}.{attr}: {e}")
            return False
    
    return True

test("进化模块导入", test_evolution_imports)

# 测试3: 数据库完整性
def test_database():
    from core.learning import enhanced_learner
    
    # 检查表结构
    with sqlite3.connect(enhanced_learner.db_path) as conn:
        conn.row_factory = sqlite3.Row
        
        # 检查knowledge_items表
        cur = conn.execute("PRAGMA table_info(knowledge_items)")
        columns = [row['name'] for row in cur.fetchall()]
        
        required = ['memory_layer', 'salience', 'emotional_valence', 
                   'context_snapshot', 'environmental_triggers']
        
        missing = [col for col in required if col not in columns]
        
        if missing:
            print(f"  ✗ 缺少字段: {missing}")
            return False
        
        print(f"  ✓ knowledge_items表完整，包含{len(columns)}个字段")
        
        # 统计知识数量
        cur = conn.execute("SELECT COUNT(*) FROM knowledge_items")
        count = cur.fetchone()[0]
        print(f"  ✓ 知识库: {count}条")
        
        return True

test("数据库完整性", test_database)

# 测试4: 基因演化引擎
def test_genome():
    from core.genome_evolver import genome_evolver
    
    # 获取基因值
    genes = genome_evolver.get_all_gene_values()
    print(f"  ✓ 基因数量: {len(genes)}")
    
    # 检查基因值
    if genes.get('G002', 0) > 0:
        print(f"  ✓ 检索阈值(G002): {genes['G002']}")
    
    # 进化统计
    stats = genome_evolver.get_evolution_stats()
    print(f"  ✓ 总基因组数: {stats['total_genomes']}")
    
    return True

test("基因演化引擎", test_genome)

# 测试5: 认知转化器
def test_cognitive():
    from core.cognitive_transformer import cognitive_transformer
    
    stats = cognitive_transformer.get_transformation_stats()
    print(f"  ✓ L3情景: {stats['l3_situations']}条")
    print(f"  ✓ L2技能: {stats['l2_skills']}个")
    print(f"  ✓ L4抽象: {stats['l4_abstractions']}条")
    
    return True

test("认知转化器", test_cognitive)

# 测试6: 进化岛沙盒
def test_evolution_sandbox():
    from core.evolution.evolution_island import EvolutionIsland
    
    # 小规模测试
    island = EvolutionIsland(
        main_db_path="data/knowledge_store.db",
        num_agents=3,
        generations=3,
        tasks_per_gen=5
    )
    
    print(f"  ✓ 任务池: {len(island.task_pool)}个")
    print(f"  ✓ 现有技能: {len(island.existing_skills)}个")
    
    # 运行进化
    result = island.run()
    
    print(f"  ✓ 最优适应度: {result['stats']['final_best_fitness']:.3f}")
    
    # 清理
    island.cleanup()
    
    return result['stats']['final_best_fitness'] > 0

test("进化岛沙盒", test_evolution_sandbox)

# 测试7: 主动调度器
def test_scheduler():
    from core.active_scheduler import ActiveScheduler
    
    scheduler = ActiveScheduler(interval_seconds=300)
    
    # 检查方法
    methods = [
        'run_evolution_sandbox',
        '_run_cognitive_transformation',
        '_run_genome_evolution',
        '_collect_fitness_stats',
        '_apply_evolved_genome',
        '_import_evolved_skills'
    ]
    
    for method in methods:
        if hasattr(scheduler, method):
            print(f"  ✓ {method}")
        else:
            print(f"  ✗ 缺少方法: {method}")
            return False
    
    return True

test("主动调度器", test_scheduler)

# 汇总结果
print("\n" + "=" * 70)
print("测试汇总")
print("=" * 70)

passed = sum(1 for _, result in test_results if result)
total = len(test_results)

print(f"\n总计: {passed}/{total} 通过")
print(f"通过率: {passed/total*100:.1f}%")

print("\n详细结果:")
for name, result in test_results:
    status = "✅" if result else "❌"
    print(f"  {status} {name}")

if passed == total:
    print("\n🎉 所有测试通过！")
    print("\n系统状态：")
    print("  ✅ 核心模块 - 完整")
    print("  ✅ 进化模块 - 完整")
    print("  ✅ 数据库 - 完整")
    print("  ✅ 基因演化 - 正常")
    print("  ✅ 认知转化 - 正常")
    print("  ✅ 进化沙盒 - 正常")
    print("  ✅ 调度器 - 完整")
    print("\n系统已就绪，可以开始进化之旅！")
else:
    print(f"\n⚠️  {total-passed}个测试失败")

print("=" * 70)