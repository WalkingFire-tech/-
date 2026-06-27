#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证knowledge_store创建"""
import sys
sys.path.insert(0, '.')

print("=" * 70)
print("🔍 KnowledgeStore 验证")
print("=" * 70)

from data.knowledge_store import KnowledgeStore

ks = KnowledgeStore()

print("\n[1] 初始化状态")
print("-" * 50)
print(f"  数据库路径: {ks.db_path}")
print(f"  向量引擎: {'启用' if ks.use_embeddings else '降级模式'}")
print(f"  Collection: {ks.collection_name}")

print("\n[2] 添加知识测试")
print("-" * 50)

knowledge_id = ks.add_knowledge(
    text="Python是一种高级编程语言，由Guido van Rossum创建。",
    category="programming",
    source="test",
    confidence=0.9,
    tags=["python", "programming"]
)

print(f"  知识ID: {knowledge_id}")
print(f"  添加成功: ✓")

print("\n[3] 搜索测试")
print("-" * 50)

results = ks.search("Python编程语言", top_k=3)
print(f"  搜索结果数: {len(results)}")
if results:
    print(f"  第一条: {results[0].get('summary', 'N/A')[:50]}...")

print("\n[4] 统计信息")
print("-" * 50)

stats = ks.get_stats()
print(f"  总条目数: {stats['total_entries']}")
print(f"  分类: {stats['categories']}")
print(f"  平均置信度: {stats['avg_confidence']:.2f}")

print("\n[5] exists()检查")
print("-" * 50)
print(f"  知识库存在: {ks.exists()}")

print("\n" + "=" * 70)
print("✅ KnowledgeStore 验证完成")
print("=" * 70)