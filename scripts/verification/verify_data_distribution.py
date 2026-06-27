#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""三刀实施效果验证"""
import sqlite3

print('=' * 70)
print('📊 三刀实施效果验证')
print('=' * 70)

# 1. 经验池success分布
print('\n[1] 经验池success分布')
print('-' * 50)
try:
    conn = sqlite3.connect('data/experience_pool.db')
    
    # 总数
    total = conn.execute('SELECT COUNT(*) FROM experiences').fetchone()[0]
    print(f'  总数: {total}条')
    
    # success分布
    dist = conn.execute('SELECT success, COUNT(*) FROM experiences GROUP BY success').fetchall()
    for success, cnt in dist:
        pct = cnt / total * 100
        print(f'  success={success}: {cnt}条 ({pct:.1f}%)')
    
    # 质量分布
    print('\n  质量分数分布:')
    quality_dist = conn.execute('''
        SELECT 
            CASE 
                WHEN quality_score >= 80 THEN 'high(>=80)'
                WHEN quality_score >= 50 THEN 'medium(50-79)'
                ELSE 'low(<50)'
            END as level,
            COUNT(*) as cnt
        FROM experiences
        GROUP BY level
    ''').fetchall()
    for level, cnt in quality_dist:
        print(f'    {level}: {cnt}条')
    
    conn.close()
except Exception as e:
    print(f'  错误: {e}')

# 2. 反思日志置信度分布
print('\n[2] 反思日志置信度分布')
print('-' * 50)
try:
    conn = sqlite3.connect('logs/campfire_log.db')
    
    total = conn.execute('SELECT COUNT(*) FROM reflection_log').fetchone()[0]
    print(f'  总数: {total}条')
    
    # 置信度分布
    conf_dist = conn.execute('''
        SELECT 
            CASE 
                WHEN confidence >= 0.8 THEN 'high(>=0.8)'
                WHEN confidence >= 0.6 THEN 'medium(0.6-0.8)'
                WHEN confidence >= 0.4 THEN 'low(0.4-0.6)'
                ELSE 'very_low(<0.4)'
            END as level,
            COUNT(*) as cnt
        FROM reflection_log
        GROUP BY level
    ''').fetchall()
    for level, cnt in conf_dist:
        print(f'  {level}: {cnt}条')
    
    # 平均置信度
    avg = conn.execute('SELECT AVG(confidence) FROM reflection_log').fetchone()[0]
    print(f'  平均置信度: {avg:.2%}')
    
    conn.close()
except Exception as e:
    print(f'  错误: {e}')

# 3. 学习规则置信度分布
print('\n[3] 学习规则置信度分布')
print('-' * 50)
try:
    conn = sqlite3.connect('data/learning_rules.db')
    
    total = conn.execute('SELECT COUNT(*) FROM learning_rules').fetchone()[0]
    print(f'  总数: {total}条')
    
    # 置信度分布
    conf_dist = conn.execute('''
        SELECT 
            CASE 
                WHEN confidence >= 0.8 THEN 'very_high(>=0.8)'
                WHEN confidence >= 0.6 THEN 'high(0.6-0.8)'
                WHEN confidence >= 0.4 THEN 'medium(0.4-0.6)'
                ELSE 'low(<0.4)'
            END as level,
            COUNT(*) as cnt
        FROM learning_rules
        GROUP BY level
    ''').fetchall()
    for level, cnt in conf_dist:
        print(f'  {level}: {cnt}条')
    
    # 按来源统计
    print('\n  按来源统计:')
    sources = conn.execute('SELECT source, COUNT(*) as cnt FROM learning_rules GROUP BY source').fetchall()
    for source, cnt in sources:
        print(f'    {source}: {cnt}条')
    
    # 按状态统计
    print('\n  按状态统计:')
    statuses = conn.execute('SELECT status, COUNT(*) as cnt FROM learning_rules GROUP BY status').fetchall()
    for status, cnt in statuses:
        print(f'    {status}: {cnt}条')
    
    conn.close()
except Exception as e:
    print(f'  错误: {e}')

print('\n' + '=' * 70)