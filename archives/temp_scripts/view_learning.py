"""
系统学习内容查看器
查看后台学习的内容和能力
"""
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime

print("\n" + "="*70)
print("📚 联盟拓荒者 - 学习内容查看器")
print("="*70)

# 1. 知识库内容
print("\n【1】知识库内容 (knowledge_store.db)")
print("-" * 70)

kb_path = "data/knowledge_store.db"
if os.path.exists(kb_path):
    try:
        conn = sqlite3.connect(kb_path)
        conn.row_factory = sqlite3.Row
        
        # 查看表结构
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cursor.fetchall()]
        print(f"  表数量: {len(tables)}")
        
        # 知识项统计
        if 'knowledge_items' in tables:
            cursor = conn.execute("SELECT COUNT(*) as count FROM knowledge_items")
            count = cursor.fetchone()['count']
            print(f"  知识项总数: {count}")
            
            if count > 0:
                # 最近的知识
                cursor = conn.execute("""
                    SELECT id, question, answer, source, created_at, quality_score
                    FROM knowledge_items
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                recent = cursor.fetchall()
                print(f"\n  最近学习的知识 (前10条):")
                for i, row in enumerate(recent, 1):
                    question = row['question'][:50] if row['question'] else "无"
                    source = row['source'] or "未知"
                    quality = row['quality_score'] or 0
                    created = row['created_at'] or "未知"
                    print(f"    {i}. [{source}] {question}... (质量:{quality}, 时间:{created})")
        
        # 搜索缓存统计
        if 'search_cache' in tables:
            cursor = conn.execute("SELECT COUNT(*) as count FROM search_cache")
            cache_count = cursor.fetchone()['count']
            print(f"\n  搜索缓存: {cache_count} 条")
        
        conn.close()
    except Exception as e:
        print(f"  ❌ 读取失败: {e}")
else:
    print("  ⚠️ 知识库不存在")

# 2. 经验池
print("\n【2】经验池 (experience_pool.db)")
print("-" * 70)

exp_path = "data/experience_pool.db"
if os.path.exists(exp_path):
    try:
        conn = sqlite3.connect(exp_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("SELECT COUNT(*) as count FROM experiences")
        count = cursor.fetchone()['count']
        print(f"  经验总数: {count}")
        
        if count > 0:
            # 按意图类型统计
            cursor = conn.execute("""
                SELECT intent_type, COUNT(*) as count, AVG(quality_score) as avg_quality
                FROM experiences
                GROUP BY intent_type
                ORDER BY count DESC
            """)
            stats = cursor.fetchall()
            print(f"\n  按意图类型统计:")
            for row in stats:
                print(f"    - {row['intent_type']}: {row['count']}次, 平均质量:{row['avg_quality']:.1f}")
            
            # 最近的经验
            cursor = conn.execute("""
                SELECT intent_type, raw_input, model_name, quality_score, timestamp
                FROM experiences
                ORDER BY timestamp DESC
                LIMIT 5
            """)
            recent = cursor.fetchall()
            print(f"\n  最近的经验 (前5条):")
            for i, row in enumerate(recent, 1):
                input_text = row['raw_input'][:40] if row['raw_input'] else "无"
                model = row['model_name'] or "未知"
                quality = row['quality_score'] or 0
                print(f"    {i}. [{row['intent_type']}] {input_text}... (模型:{model}, 质量:{quality})")
        
        conn.close()
    except Exception as e:
        print(f"  ❌ 读取失败: {e}")
else:
    print("  ⚠️ 经验池不存在")

# 3. 四层进化数据
print("\n【3】四层进化系统")
print("-" * 70)

# 行为进化
be_path = "data/behavior_evolution.db"
if os.path.exists(be_path):
    try:
        conn = sqlite3.connect(be_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("SELECT COUNT(*) as count FROM response_profiles")
        count = cursor.fetchone()['count']
        print(f"  行为进化: {count} 个回答档案")
        
        if count > 0:
            cursor = conn.execute("""
                SELECT structure_type, tone_type, 
                       AVG(user_feedback_score) as avg_feedback,
                       COUNT(*) as sample_count
                FROM response_profiles
                GROUP BY structure_type, tone_type
                ORDER BY avg_feedback DESC
                LIMIT 5
            """)
            profiles = cursor.fetchall()
            for row in profiles:
                print(f"    - {row['structure_type']}/{row['tone_type']}: 平均反馈:{row['avg_feedback']:.2f}, 样本:{row['sample_count']}")
        
        conn.close()
    except Exception as e:
        print(f"  ❌ 行为进化读取失败: {e}")
else:
    print("  ⚠️ 行为进化数据库不存在")

# 知识进化
ke_path = "data/knowledge_evolution.db"
if os.path.exists(ke_path):
    try:
        conn = sqlite3.connect(ke_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cursor.fetchall()]
        
        if 'knowledge_verifications' in tables:
            cursor = conn.execute("SELECT COUNT(*) as count FROM knowledge_verifications")
            count = cursor.fetchone()['count']
            print(f"  知识进化: {count} 次验证")
        
        conn.close()
    except Exception as e:
        print(f"  ❌ 知识进化读取失败: {e}")

# 策略进化
se_path = "data/strategy_evolution.db"
if os.path.exists(se_path):
    try:
        conn = sqlite3.connect(se_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cursor.fetchall()]
        
        if 'strategy_patterns' in tables:
            cursor = conn.execute("SELECT COUNT(*) as count FROM strategy_patterns")
            count = cursor.fetchone()['count']
            print(f"  策略进化: {count} 个策略模式")
        
        conn.close()
    except Exception as e:
        print(f"  ❌ 策略进化读取失败: {e}")

# 元学习
ml_path = "data/meta_learning.db"
if os.path.exists(ml_path):
    try:
        conn = sqlite3.connect(ml_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cursor.fetchall()]
        
        if 'learning_observations' in tables:
            cursor = conn.execute("SELECT COUNT(*) as count FROM learning_observations")
            count = cursor.fetchone()['count']
            print(f"  元学习: {count} 次观察")
        
        conn.close()
    except Exception as e:
        print(f"  ❌ 元学习读取失败: {e}")

# 4. 学习目标进度
print("\n【4】学习目标进度 (learning_progress.db)")
print("-" * 70)

lp_path = "data/learning_progress.db"
if os.path.exists(lp_path):
    try:
        conn = sqlite3.connect(lp_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("""
            SELECT target_name, target_type, progress, last_learn_time
            FROM learning_progress
            ORDER BY progress DESC
        """)
        progress = cursor.fetchall()
        
        if progress:
            print(f"  学习目标数: {len(progress)}")
            for row in progress:
                name = row['target_name']
                type_ = row['target_type']
                prog = row['progress'] or 0
                last = row['last_learn_time'] or "未学习"
                print(f"    - [{type_}] {name}: {prog:.1%} (最后学习:{last})")
        else:
            print("  暂无学习进度记录")
        
        conn.close()
    except Exception as e:
        print(f"  ❌ 读取失败: {e}")
else:
    print("  ⚠️ 学习进度数据库不存在")

# 5. 模型统计
print("\n【5】模型使用统计 (model_stats.db)")
print("-" * 70)

ms_path = "data/model_stats.db"
if os.path.exists(ms_path):
    try:
        conn = sqlite3.connect(ms_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("""
            SELECT model_name, 
                   COUNT(*) as total_calls,
                   SUM(CASE WHEN quality > 0 THEN 1 ELSE 0 END) as success_calls,
                   AVG(CASE WHEN quality > 0 THEN quality END) as avg_quality,
                   AVG(duration) as avg_duration
            FROM model_calls
            GROUP BY model_name
            ORDER BY total_calls DESC
        """)
        stats = cursor.fetchall()
        
        if stats:
            print(f"  模型数: {len(stats)}")
            for row in stats:
                model = row['model_name']
                total = row['total_calls']
                success = row['success_calls']
                quality = row['avg_quality'] or 0
                duration = row['avg_duration'] or 0
                rate = success / total if total > 0 else 0
                print(f"    - {model}: {total}次调用, 成功率{rate:.1%}, 平均质量{quality:.1f}, 平均耗时{duration:.1f}s")
        else:
            print("  暂无模型调用记录")
        
        conn.close()
    except Exception as e:
        print(f"  ❌ 读取失败: {e}")
else:
    print("  ⚠️ 模型统计数据库不存在")

# 6. 搜索缓存内容
print("\n【6】搜索缓存内容")
print("-" * 70)

cache_path = "data/knowledge_store.db"
if os.path.exists(cache_path):
    try:
        conn = sqlite3.connect(cache_path)
        conn.row_factory = sqlite3.Row
        
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row['name'] for row in cursor.fetchall()]
        
        if 'search_cache' in tables:
            cursor = conn.execute("""
                SELECT query, source, created_at
                FROM search_cache
                ORDER BY created_at DESC
                LIMIT 10
            """)
            cache = cursor.fetchall()
            
            if cache:
                print(f"  最近搜索 (前10条):")
                for i, row in enumerate(cache, 1):
                    query = row['query'][:50] if row['query'] else "无"
                    source = row['source'] or "未知"
                    print(f"    {i}. [{source}] {query}...")
            else:
                print("  暂无搜索缓存")
        
        conn.close()
    except Exception as e:
        print(f"  ❌ 读取失败: {e}")

# 7. 能力总结
print("\n" + "="*70)
print("📊 系统能力总结")
print("="*70)

capabilities = []

# 检查各项能力
if os.path.exists(kb_path):
    conn = sqlite3.connect(kb_path)
    cursor = conn.execute("SELECT COUNT(*) FROM knowledge_items")
    if cursor.fetchone()[0] > 0:
        capabilities.append("✅ 知识存储能力")
    conn.close()

if os.path.exists(exp_path):
    conn = sqlite3.connect(exp_path)
    cursor = conn.execute("SELECT COUNT(*) FROM experiences")
    if cursor.fetchone()[0] > 0:
        capabilities.append("✅ 经验积累能力")
    conn.close()

if os.path.exists(be_path):
    capabilities.append("✅ 行为进化能力")

if os.path.exists(ke_path):
    capabilities.append("✅ 知识进化能力")

if os.path.exists(se_path):
    capabilities.append("✅ 策略进化能力")

if os.path.exists(ml_path):
    capabilities.append("✅ 元学习能力")

if capabilities:
    for cap in capabilities:
        print(f"  {cap}")
else:
    print("  ⚠️ 系统尚未积累足够的学习数据")

print("\n" + "="*70)
print("查看完成")
print("="*70)