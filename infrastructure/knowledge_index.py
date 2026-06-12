"""
知识索引模块 (Knowledge Index)
全局知识目录，快速定位知识存储位置
"""
import json
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from loguru import logger


class KnowledgeIndex:
    """知识索引 - 记录知识存放在哪里的全局目录"""
    
    def __init__(self, index_path: str = "knowledge_index.json"):
        self.index_path = Path(index_path)
        self.index = self._load_index()
        
    def _load_index(self) -> Dict:
        """加载索引"""
        if self.index_path.exists():
            try:
                with open(self.index_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                logger.warning("索引文件损坏，创建新索引")
        
        # 默认索引结构
        return {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "knowledge_sources": {
                "experiences": {
                    "type": "database",
                    "path": "experience_pool.db",
                    "description": "长期经验存储",
                    "count": 0
                },
                "rules": {
                    "type": "database",
                    "path": "learning_rules.db",
                    "description": "学习规则库",
                    "count": 0
                },
                "tool_cache": {
                    "type": "database",
                    "path": "tool_cache.db",
                    "description": "工具结果缓存",
                    "count": 0
                },
                "vector_index": {
                    "type": "faiss",
                    "path": "data/vector_index.faiss",
                    "description": "向量检索索引",
                    "dimension": 384
                }
            },
            "topic_index": {},  # 按主题分类的索引
            "recent_access": []  # 最近访问记录
        }
    
    def save(self):
        """保存索引"""
        self.index["updated_at"] = datetime.now().isoformat()
        
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, ensure_ascii=False, indent=2)
        
        logger.debug(f"知识索引已保存: {self.index_path}")
    
    def register_source(self, name: str, source_type: str, path: str, description: str = ""):
        """
        注册知识源
        
        Args:
            name: 知识源名称
            source_type: 类型（database/file/faiss等）
            path: 存储路径
            description: 描述
        """
        self.index["knowledge_sources"][name] = {
            "type": source_type,
            "path": path,
            "description": description,
            "registered_at": datetime.now().isoformat()
        }
        
        self.save()
        logger.info(f"注册知识源: {name} ({source_type})")
    
    def update_count(self, source_name: str, count: int):
        """更新知识源计数"""
        if source_name in self.index["knowledge_sources"]:
            self.index["knowledge_sources"][source_name]["count"] = count
            self.save()
    
    def add_topic_entry(self, topic: str, entry: Dict):
        """
        添加主题索引条目
        
        Args:
            topic: 主题（如 code/chat/question）
            entry: 条目信息
        """
        if topic not in self.index["topic_index"]:
            self.index["topic_index"][topic] = []
        
        entry["indexed_at"] = datetime.now().isoformat()
        self.index["topic_index"][topic].append(entry)
        
        self.save()
    
    def find_knowledge(self, query: str, limit: int = 10) -> List[Dict]:
        """
        查找知识位置
        
        Args:
            query: 查询关键词
            limit: 返回数量限制
        
        Returns:
            知识位置列表
        """
        results = []
        query_lower = query.lower()
        
        # 搜索主题索引
        for topic, entries in self.index["topic_index"].items():
            for entry in entries:
                # 简单关键词匹配
                if query_lower in json.dumps(entry).lower():
                    results.append({
                        "topic": topic,
                        "source": entry.get("source", "unknown"),
                        "location": entry.get("location", ""),
                        "relevance": "topic_match"
                    })
        
        # 搜索知识源描述
        for name, source in self.index["knowledge_sources"].items():
            if query_lower in source.get("description", "").lower():
                results.append({
                    "topic": "general",
                    "source": name,
                    "location": source["path"],
                    "relevance": "source_match"
                })
        
        return results[:limit]
    
    def record_access(self, source: str, action: str):
        """记录访问"""
        access_record = {
            "source": source,
            "action": action,
            "timestamp": datetime.now().isoformat()
        }
        
        self.index["recent_access"].append(access_record)
        
        # 只保留最近100条访问记录
        if len(self.index["recent_access"]) > 100:
            self.index["recent_access"] = self.index["recent_access"][-100:]
        
        self.save()
    
    def rebuild_index(self):
        """重建索引（扫描所有知识源）"""
        logger.info("开始重建知识索引...")
        
        # 统计经验池
        try:
            conn = sqlite3.connect("experience_pool.db")
            cursor = conn.execute("SELECT COUNT(*) FROM experiences")
            exp_count = cursor.fetchone()[0]
            conn.close()
            
            self.update_count("experiences", exp_count)
        except:
            pass
        
        # 统计规则库
        try:
            conn = sqlite3.connect("learning_rules.db")
            cursor = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            rule_count = cursor.fetchone()[0]
            conn.close()
            
            self.update_count("rules", rule_count)
        except:
            pass
        
        # 统计工具缓存
        try:
            conn = sqlite3.connect("tool_cache.db")
            cursor = conn.execute("SELECT COUNT(*) FROM tool_cache")
            cache_count = cursor.fetchone()[0]
            conn.close()
            
            self.update_count("tool_cache", cache_count)
        except:
            pass
        
        # 按意图类型建立主题索引
        try:
            conn = sqlite3.connect("experience_pool.db")
            cursor = conn.execute("""
                SELECT intent_type, COUNT(*) 
                FROM experiences 
                GROUP BY intent_type
            """)
            
            for row in cursor.fetchall():
                intent_type, count = row
                self.add_topic_entry(intent_type, {
                    "source": "experiences",
                    "location": "experience_pool.db",
                    "count": count,
                    "description": f"{count}条{intent_type}类型经验"
                })
            
            conn.close()
        except:
            pass
        
        logger.info("知识索引重建完成")
        self.save()
    
    def get_summary(self) -> str:
        """获取索引摘要"""
        lines = ["=" * 60, "知识索引摘要", "=" * 60]
        
        lines.append("\n【知识源】")
        for name, source in self.index["knowledge_sources"].items():
            count = source.get("count", 0)
            lines.append(f"  {name}: {count}条 ({source['type']})")
        
        lines.append("\n【主题分类】")
        for topic, entries in self.index["topic_index"].items():
            lines.append(f"  {topic}: {len(entries)}个条目")
        
        lines.append(f"\n【最近访问】")
        recent = self.index["recent_access"][-5:]
        for record in recent:
            lines.append(
                f"  {record['timestamp'][:19]} - {record['source']} ({record['action']})"
            )
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)


if __name__ == "__main__":
    # 测试知识索引
    print("=" * 60)
    print("知识索引模块测试")
    print("=" * 60)
    
    index = KnowledgeIndex()
    
    # 测试1: 注册知识源
    print("\n测试1: 注册知识源")
    index.register_source(
        "custom_tools",
        "directory",
        "tools/generated",
        "动态生成的工具"
    )
    print("  ✓ 知识源已注册")
    
    # 测试2: 重建索引
    print("\n测试2: 重建索引")
    index.rebuild_index()
    print("  ✓ 索引已重建")
    
    # 测试3: 查找知识
    print("\n测试3: 查找知识")
    results = index.find_knowledge("code")
    print(f"  找到{len(results)}个匹配项")
    for result in results:
        print(f"    - {result['source']}: {result['location']}")
    
    # 测试4: 获取摘要
    print("\n测试4: 索引摘要")
    print(index.get_summary())
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)