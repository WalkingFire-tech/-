"""
准备SFT微调流程
将交互数据转换为训练格式
"""
import json
import os
from datetime import datetime
from pathlib import Path

def export_for_sft():
    """导出SFT训练数据"""
    import sqlite3
    
    db_path = 'data/interaction_data.db'
    if not os.path.exists(db_path):
        print("❌ 数据库不存在")
        return 0
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # 查询高质量数据
    query = """
    SELECT 
        question,
        response,
        feedback_type,
        feedback_content,
        objective_score,
        total_score
    FROM interactions
    WHERE 
        (feedback_type = 'positive' OR feedback_type = 'correction')
        AND objective_score >= 50
    ORDER BY timestamp DESC
    """
    
    cursor = conn.execute(query)
    rows = cursor.fetchall()
    
    if not rows:
        print("⚠️ 没有符合条件的数据")
        conn.close()
        return 0
    
    # 转换为Alpaca格式
    sft_data = []
    for row in rows:
        # 对于纠错数据，使用纠错内容作为标准输出
        output = row['response']
        if row['feedback_type'] == 'correction' and row['feedback_content']:
            output = row['feedback_content']
        
        item = {
            "instruction": "请回答以下问题",
            "input": row['question'],
            "output": output,
            "metadata": {
                "feedback_type": row['feedback_type'],
                "objective_score": row['objective_score'],
                "total_score": row['total_score']
            }
        }
        sft_data.append(item)
    
    # 保存为JSONL
    output_dir = Path('data/sft')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'training_data_{timestamp}.jsonl'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in sft_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    conn.close()
    
    print(f"✅ 导出完成:")
    print(f"   文件: {output_file}")
    print(f"   数量: {len(sft_data)}条")
    
    return len(sft_data)


def export_with_knowledge():
    """导出包含知识库的训练数据"""
    import sqlite3
    
    # 从知识库导出
    kb_path = 'data/alliance.db'
    if not os.path.exists(kb_path):
        print("❌ 知识库不存在")
        return 0
    
    conn = sqlite3.connect(kb_path)
    conn.row_factory = sqlite3.Row
    
    query = """
    SELECT subject, predicate, object, question
    FROM fact_assertions
    WHERE is_active = 1
    """
    
    cursor = conn.execute(query)
    rows = cursor.fetchall()
    
    # 转换为问答格式
    sft_data = []
    for row in rows:
        question = row['question'] or f"{row['subject']}的{row['predicate']}"
        answer = f"{row['subject']}{row['predicate']}{row['object']}"
        
        item = {
            "instruction": "请回答以下问题",
            "input": question,
            "output": answer
        }
        sft_data.append(item)
    
    # 保存
    output_dir = Path('data/sft')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f'knowledge_data_{timestamp}.jsonl'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in sft_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    conn.close()
    
    print(f"✅ 知识导出完成:")
    print(f"   文件: {output_file}")
    print(f"   数量: {len(sft_data)}条")
    
    return len(sft_data)


def merge_training_data():
    """合并所有训练数据"""
    import glob
    
    sft_dir = Path('data/sft')
    if not sft_dir.exists():
        print("❌ 没有训练数据")
        return
    
    all_data = []
    for file in sft_dir.glob('*.jsonl'):
        with open(file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    all_data.append(json.loads(line))
    
    # 去重（基于input）
    seen = set()
    unique_data = []
    for item in all_data:
        key = item['input']
        if key not in seen:
            seen.add(key)
            unique_data.append(item)
    
    # 保存合并文件
    output_file = sft_dir / 'merged_training_data.jsonl'
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in unique_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"✅ 合并完成:")
    print(f"   文件: {output_file}")
    print(f"   原始: {len(all_data)}条")
    print(f"   去重: {len(unique_data)}条")


if __name__ == "__main__":
    print("=" * 60)
    print("SFT训练数据准备")
    print("=" * 60)
    
    print("\n[1] 导出交互数据...")
    count1 = export_for_sft()
    
    print("\n[2] 导出知识库数据...")
    count2 = export_with_knowledge()
    
    print("\n[3] 合并训练数据...")
    merge_training_data()
    
    print("\n" + "=" * 60)
    print(f"总计: {count1 + count2}条训练数据")
    print("=" * 60)