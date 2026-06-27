#!/usr/bin/env python
"""
一次性脚本：将255条闭环数据集注入经验池
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

def seed_experience_pool():
    """将JSONL数据导入经验池"""
    
    # 查找所有闭环数据文件
    data_files = list(Path("data").glob("*closed_loop*.jsonl"))
    data_files.extend(list(Path("data/sft").glob("*.jsonl")))
    
    if not data_files:
        print("❌ 未找到闭环数据文件")
        return
    
    print(f"找到 {len(data_files)} 个数据文件:")
    for f in data_files:
        print(f"  - {f}")
    
    # 连接经验池数据库
    db_path = Path("data/experience_pool.db")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    pass
    
    count = 0
    
    for jsonl_file in data_files:
        print(f"\n处理: {jsonl_file}")
        
        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    try:
                        data = json.loads(line)
                        
                        # 适配不同的数据结构
                        query = (
                            data.get("instruction") or 
                            data.get("query") or 
                            data.get("question") or
                            data.get("input", "")
                        )
                        
                        final_answer = (
                            data.get("output") or 
                            data.get("response") or 
                            data.get("answer", "")
                        )
                        
                        confidence = data.get("confidence", 0.5)
                        
                        cursor.execute('''
                            INSERT INTO experiences 
                            (timestamp, intent_type, raw_input, plan, model_name, quality_score, user_feedback, success, duration, response)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            datetime.utcnow().isoformat(),
                            data.get("intent", "general"),
                            query[:500] if query else "",
                            "",
                            data.get("model", "unknown"),
                            int(confidence * 100),
                            None,
                            1 if confidence > 0.7 else 0,
                            0.0,
                            final_answer[:500] if final_answer else ""
                        ))
                        
                        count += 1
                        
                    except Exception as e:
                        print(f"  跳过无效行: {str(e)[:50]}")
                        continue
                        
        except Exception as e:
            print(f"  文件读取失败: {e}")
            continue
    
    conn.commit()
    
    # 验证
    total = cursor.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"✅ 成功导入 {count} 条新经验")
    print(f"✅ 经验池总计: {total} 条")
    print(f"{'='*60}")

if __name__ == "__main__":
    seed_experience_pool()