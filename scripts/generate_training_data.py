"""
基于知识库生成训练数据
使用DeepSeek等模型扩展知识
"""
import json
import os
from pathlib import Path
from typing import List, Dict

def generate_qa_pairs_from_knowledge(
    subject: str,
    predicate: str,
    obj: str,
    num_variations: int = 3
) -> List[Dict]:
    """
    基于一条知识生成多个问答对
    
    Args:
        subject: 主体
        predicate: 谓词
        obj: 客体
        num_variations: 变体数量
    
    Returns:
        问答对列表
    """
    qa_pairs = []
    
    # 1. 直接问答
    qa_pairs.append({
        "instruction": f"什么是{subject}的{predicate}？",
        "input": "",
        "output": f"{subject}{predicate}{obj}。"
    })
    
    # 2. 解释型问答
    if predicate == "定义":
        qa_pairs.append({
            "instruction": f"请解释什么是{subject}",
            "input": "",
            "output": f"{subject}是{obj}。这个概念是理解相关领域的基础。"
        })
    
    # 3. 对比型问答
    if predicate in ["特点", "优势", "应用"]:
        qa_pairs.append({
            "instruction": f"{subject}有哪些{predicate}？",
            "input": "",
            "output": f"{subject}的主要{predicate}包括：{obj}。这些{predicate}使得{subject}在实际应用中具有重要价值。"
        })
    
    # 4. 实践型问答
    if predicate in ["方法", "流程", "步骤"]:
        qa_pairs.append({
            "instruction": f"如何进行{subject}？",
            "input": "",
            "output": f"{subject}的主要{predicate}：{obj}。按照这些步骤操作可以提高效率和效果。"
        })
    
    return qa_pairs[:num_variations]


def generate_from_knowledge_base():
    """从知识库生成训练数据"""
    import sqlite3
    
    db_path = 'data/alliance.db'
    if not os.path.exists(db_path):
        print("❌ 知识库不存在")
        return []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    query = """
    SELECT subject, predicate, object
    FROM fact_assertions
    WHERE is_active = 1
    """
    
    cursor = conn.execute(query)
    rows = cursor.fetchall()
    
    all_qa_pairs = []
    for row in rows:
        qa_pairs = generate_qa_pairs_from_knowledge(
            row['subject'],
            row['predicate'],
            row['object']
        )
        all_qa_pairs.extend(qa_pairs)
    
    conn.close()
    
    return all_qa_pairs


def generate_with_deepseek(prompt: str, api_key: str = None) -> str:
    """
    使用DeepSeek生成数据
    
    Args:
        prompt: 生成提示词
        api_key: DeepSeek API Key
    
    Returns:
        生成的内容
    """
    if not api_key:
        return None
    
    try:
        import openai
        
        client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1"
        )
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个数据生成专家，负责生成高质量的问答数据。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"❌ DeepSeek调用失败: {e}")
        return None


def generate_extended_data(api_key: str = None):
    """
    使用DeepSeek扩展知识库数据
    
    Args:
        api_key: DeepSeek API Key
    """
    import sqlite3
    
    db_path = 'data/alliance.db'
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    query = """
    SELECT subject, predicate, object
    FROM fact_assertions
    WHERE is_active = 1 AND predicate = '定义'
    LIMIT 10
    """
    
    cursor = conn.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    extended_data = []
    
    for row in rows:
        knowledge = f"{row['subject']}{row['predicate']}{row['object']}"
        
        # 生成提示词
        prompt = f"""你是一个数据生成专家。请根据以下知识点，生成3个不同的问题，并为每个问题提供详细、准确的回答。

知识点：{knowledge}

要求：
1. 问题要多样化（定义、应用、对比等）
2. 回答要逻辑清晰，覆盖知识点的核心内容
3. 回答要详细，至少100字

请按以下格式输出：
问题1: ...
回答1: ...

问题2: ...
回答2: ...

问题3: ...
回答3: ...
"""
        
        if api_key:
            print(f"\n生成: {row['subject']}...")
            content = generate_with_deepseek(prompt, api_key)
            
            if content:
                # 解析生成的内容
                # 这里简化处理，实际应该更仔细地解析
                extended_data.append({
                    "instruction": f"详细解释{row['subject']}",
                    "input": "",
                    "output": content,
                    "source": "deepseek_generated"
                })
        else:
            # 不使用API，使用模板生成
            extended_data.append({
                "instruction": f"请详细介绍{row['subject']}，包括其定义、特点和应用",
                "input": "",
                "output": f"{knowledge}。\n\n{row['subject']}是机器学习领域的重要概念。它在实际应用中具有广泛的价值，能够帮助解决各种复杂问题。理解{row['subject']}对于深入学习相关技术至关重要。",
                "source": "template_generated"
            })
    
    return extended_data


def save_training_data(data: List[Dict], filename: str):
    """保存训练数据"""
    output_dir = Path('data/generated')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / filename
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"✅ 已保存: {output_file}")
    print(f"   数量: {len(data)}条")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="生成训练数据")
    parser.add_argument('--api-key', type=str, help='DeepSeek API Key')
    parser.add_argument('--output', type=str, default='generated_training_data.jsonl', help='输出文件名')
    args = parser.parse_args()
    
    print("=" * 60)
    print("基于知识库生成训练数据")
    print("=" * 60)
    
    print("\n[1] 从知识库生成基础问答对...")
    qa_pairs = generate_from_knowledge_base()
    print(f"   生成: {len(qa_pairs)}条")
    
    print("\n[2] 扩展生成详细问答...")
    extended = generate_extended_data(args.api_key)
    print(f"   生成: {len(extended)}条")
    
    print("\n[3] 合并并保存...")
    all_data = qa_pairs + extended
    save_training_data(all_data, args.output)
    
    print("\n" + "=" * 60)
    print(f"✅ 总计生成: {len(all_data)}条训练数据")
    print("=" * 60)
    
    if not args.api_key:
        print("\n💡 提示: 使用 --api-key 参数可以调用DeepSeek生成更高质量的数据")