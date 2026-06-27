#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""深度架构审核"""
import sqlite3
from pathlib import Path
import json

print("=" * 70)
print("🔍 深度架构审核 - 数据流与闭环验证")
print("=" * 70)

# 1. 经验池检查
print("\n[1] 经验池 (Experience Pool)")
exp_db = Path('data/experience_pool.db')
if exp_db.exists():
    conn = sqlite3.connect(str(exp_db))
    try:
        count = conn.execute('SELECT COUNT(*) FROM experiences').fetchone()[0]
        print(f"  总数: {count}条")
        
        success = conn.execute('SELECT COUNT(*) FROM experiences WHERE success=1').fetchone()[0]
        print(f"  成功: {success}条 ({success/count*100:.1f}%)")
        
        # 意图分布
        intents = conn.execute('SELECT intent_type, COUNT(*) as cnt FROM experiences GROUP BY intent_type ORDER BY cnt DESC LIMIT 5').fetchall()
        print(f"  意图分布: {dict(intents)}")
        
        # 质量分数分布
        high_quality = conn.execute('SELECT COUNT(*) FROM experiences WHERE quality_score >= 70').fetchone()[0]
        print(f"  高质量(≥70分): {high_quality}条")
        
    except Exception as e:
        print(f"  ❌ 查询失败: {e}")
    conn.close()
else:
    print("  ❌ 经验池不存在")

# 2. 反思日志
print("\n[2] 反思日志 (Reflection Log)")
ref_db = Path('logs/campfire_log.db')
if ref_db.exists():
    conn = sqlite3.connect(str(ref_db))
    try:
        count = conn.execute('SELECT COUNT(*) FROM reflection_log').fetchone()[0]
        print(f"  总数: {count}条")
        
        # 平均置信度
        avg_conf = conn.execute('SELECT AVG(confidence) FROM reflection_log').fetchone()[0]
        print(f"  平均置信度: {avg_conf:.2%}" if avg_conf else "  平均置信度: N/A")
        
        # 工具调用统计
        tool_calls = conn.execute('SELECT COUNT(*) FROM reflection_log WHERE tool_calls != "[]"').fetchone()[0]
        print(f"  有工具调用: {tool_calls}条")
        
    except Exception as e:
        print(f"  ❌ 查询失败: {e}")
    conn.close()
else:
    print("  ❌ 反思日志不存在")

# 3. 学习规则
print("\n[3] 学习规则 (Learning Rules)")
rules_db = Path('data/learning_rules.db')
if rules_db.exists():
    conn = sqlite3.connect(str(rules_db))
    try:
        count = conn.execute('SELECT COUNT(*) FROM learning_rules').fetchone()[0]
        print(f"  总数: {count}条")
        
        active = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'").fetchone()[0]
        print(f"  活跃: {active}条")
        
        # 按来源统计
        sources = conn.execute('SELECT source, COUNT(*) as cnt FROM learning_rules GROUP BY source').fetchall()
        print(f"  来源分布: {dict(sources)}")
        
    except Exception as e:
        print(f"  ❌ 查询失败: {e}")
    conn.close()
else:
    print("  ⚠️ 规则库不存在（归纳器未产出）")

# 4. 微调样本
print("\n[4] 微调样本 (Fine-tune Samples)")
finetune_dir = Path('data/finetune/queue')
if finetune_dir.exists():
    jsonl_files = list(finetune_dir.glob('*.jsonl'))
    total_samples = 0
    for f in jsonl_files:
        with open(f, 'r', encoding='utf-8') as file:
            total_samples += sum(1 for _ in file)
    print(f"  总数: {total_samples}条")
    print(f"  文件数: {len(jsonl_files)}个")
else:
    print("  ⚠️ 微调队列不存在")

# 5. 闭环数据检查
print("\n[5] 闭环数据流检查")
sft_dir = Path('data/sft')
if sft_dir.exists():
    jsonl_files = list(sft_dir.glob('*.jsonl'))
    total = 0
    for f in jsonl_files:
        with open(f, 'r', encoding='utf-8') as file:
            total += sum(1 for _ in file)
    print(f"  SFT数据: {total}条 ({len(jsonl_files)}个文件)")
else:
    print("  ⚠️ SFT数据目录不存在")

print("\n" + "=" * 70)
print("📊 闭环完整性评估")
print("=" * 70)

# 评估闭环完整性
issues = []

if exp_db.exists():
    conn = sqlite3.connect(str(exp_db))
    count = conn.execute('SELECT COUNT(*) FROM experiences').fetchone()[0]
    conn.close()
    if count < 100:
        issues.append(f"经验池数据不足({count}<100)")
else:
    issues.append("经验池不存在")

if ref_db.exists():
    conn = sqlite3.connect(str(ref_db))
    count = conn.execute('SELECT COUNT(*) FROM reflection_log').fetchone()[0]
    conn.close()
    if count < 10:
        issues.append(f"反思日志不足({count}<10)")
else:
    issues.append("反思日志不存在")

if not rules_db.exists():
    issues.append("❌ 学习规则库不存在 - 归纳器未产出任何规则")

if issues:
    print("\n⚠️ 发现问题:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
else:
    print("\n✅ 闭环完整，数据流畅通")