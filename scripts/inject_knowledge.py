"""
知识注入工具
让用户可以直接向系统注入知识，而不是通过问答方式
"""
import sys
sys.path.insert(0, '.')

from infrastructure.versioned_fact_store import VersionedFactStore

def inject_knowledge():
    store = VersionedFactStore()
    
    print("=" * 60)
    print("知识注入工具")
    print("=" * 60)
    print("\n格式: <主体> <关系> <客体>")
    print("示例: 机器学习 定义 从数据中学习规律的AI技术")
    print("输入 'quit' 退出\n")
    
    while True:
        try:
            line = input("知识> ").strip()
            if line.lower() == 'quit':
                break
            
            parts = line.split(None, 2)
            if len(parts) < 3:
                print("❌ 格式错误，需要: 主体 关系 客体")
                continue
            
            subject, relation, obj = parts
            question = f"{subject}的{relation}"
            
            fact_id = store.add_assertion(
                question=question,
                subject=subject,
                predicate=relation,
                obj=obj,
                source="user_injection",
                confidence=0.9
            )
            
            print(f"✅ 已注入: {subject} -> {relation} -> {obj} (ID={fact_id})")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    print("\n知识注入完成")

def inject_from_text(text_block: str):
    """从文本块批量注入知识"""
    store = VersionedFactStore()
    
    lines = text_block.strip().split('\n')
    count = 0
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        parts = line.split(None, 2)
        if len(parts) >= 3:
            subject, relation, obj = parts
            question = f"{subject}的{relation}"
            store.add_assertion(
                question=question,
                subject=subject,
                predicate=relation,
                obj=obj,
                source="batch_injection",
                confidence=0.85
            )
            count += 1
    
    return count

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="知识注入工具")
    parser.add_argument('--batch', type=str, help="批量注入文本文件路径")
    args = parser.parse_args()
    
    if args.batch:
        with open(args.batch, 'r', encoding='utf-8') as f:
            text = f.read()
        count = inject_from_text(text)
        print(f"✅ 批量注入完成: {count}条知识")
    else:
        inject_knowledge()