"""
知识索引模块 (Knowledge Index)
全局知识目录，快速定位知识存储位置
"""
import sqlite3
import threading
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path
from loguru import logger


class KnowledgeIndex:
    """知识索引 - 记录知识存放在哪里的全局目录"""
    
    MAX_TOPIC_ENTRIES = 100
    MAX_ACCESS_RECORDS = 100
    
    def __init__(self, index_path: str = "knowledge_index.db"):
        filename = Path(index_path).name
        if not filename.endswith('.db'):
            filename = filename.rsplit('.', 1)[0] + '.db'
        
        self.index_path = Path("data") / filename
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._lock = threading.Lock()
        self._init_db()
        
        logger.info(f"知识索引已初始化: {self.index_path}")
    
    def _init_db(self):
        with sqlite3.connect(self.index_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_sources (
                    name TEXT PRIMARY KEY,
                    type TEXT,
                    path TEXT,
                    description TEXT,
                    count INTEGER DEFAULT 0,
                    registered_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS topic_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    source TEXT,
                    location TEXT,
                    data TEXT,
                    indexed_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS recent_access (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    action TEXT,
                    timestamp TEXT
                )
            ''')
            
            conn.execute('CREATE INDEX IF NOT EXISTS idx_topic ON topic_index(topic)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON recent_access(timestamp)')
            
            self._ensure_default_sources(conn)
    
    def _ensure_default_sources(self, conn):
        default_sources = [
            ("experiences", "database", "experience_pool.db", "长期经验存储"),
            ("rules", "database", "learning_rules.db", "学习规则库"),
            ("tool_cache", "database", "tool_cache.db", "工具结果缓存"),
            ("vector_index", "faiss", "data/vector_index.faiss", "向量检索索引"),
        ]
        
        for name, source_type, path, desc in default_sources:
            cursor = conn.execute('SELECT 1 FROM knowledge_sources WHERE name = ?', (name,))
            if not cursor.fetchone():
                conn.execute('''
                    INSERT INTO knowledge_sources (name, type, path, description, count, registered_at)
                    VALUES (?, ?, ?, ?, 0, ?)
                ''', (name, source_type, path, desc, datetime.now().isoformat()))
    
    def register_source(self, name: str, source_type: str, path: str, description: str = ""):
        with self._lock:
            now = datetime.now().isoformat()
            with sqlite3.connect(self.index_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO knowledge_sources 
                    (name, type, path, description, count, registered_at, updated_at)
                    VALUES (?, ?, ?, ?, 
                        COALESCE((SELECT count FROM knowledge_sources WHERE name = ?), 0),
                        COALESCE((SELECT registered_at FROM knowledge_sources WHERE name = ?), ?),
                        ?)
                ''', (name, source_type, path, description, name, name, now, now))
            
            logger.info(f"注册知识源: {name} ({source_type})")
    
    def update_count(self, source_name: str, count: int):
        with self._lock:
            with sqlite3.connect(self.index_path) as conn:
                conn.execute('''
                    UPDATE knowledge_sources 
                    SET count = ?, updated_at = ?
                    WHERE name = ?
                ''', (count, datetime.now().isoformat(), source_name))
    
    def add_topic_entry(self, topic: str, entry: Dict):
        with self._lock:
            now = datetime.now().isoformat()
            
            with sqlite3.connect(self.index_path) as conn:
                conn.execute('''
                    INSERT INTO topic_index (topic, source, location, data, indexed_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    topic,
                    entry.get("source", "unknown"),
                    entry.get("location", ""),
                    json.dumps(entry, ensure_ascii=False),
                    now
                ))
                
                cursor = conn.execute('SELECT COUNT(*) FROM topic_index WHERE topic = ?', (topic,))
                count = cursor.fetchone()[0]
                
                if count > self.MAX_TOPIC_ENTRIES:
                    conn.execute('''
                        DELETE FROM topic_index 
                        WHERE topic = ? AND id IN (
                            SELECT id FROM topic_index 
                            WHERE topic = ? 
                            ORDER BY indexed_at ASC 
                            LIMIT ?
                        )
                    ''', (topic, topic, count - self.MAX_TOPIC_ENTRIES))
    
    def find_knowledge(self, query: str, limit: int = 10) -> List[Dict]:
        results = []
        query_lower = query.lower()
        
        with sqlite3.connect(self.index_path) as conn:
            cursor = conn.execute('''
                SELECT topic, source, location, data
                FROM topic_index
            ''')
            
            for row in cursor.fetchall():
                topic, source, location, data_json = row
                try:
                    entry = json.loads(data_json)
                    if query_lower in json.dumps(entry).lower():
                        results.append({
                            "topic": topic,
                            "source": source,
                            "location": location,
                            "relevance": "topic_match"
                        })
                except:
                    pass
            
            cursor = conn.execute('''
                SELECT name, path, description
                FROM knowledge_sources
            ''')
            
            for row in cursor.fetchall():
                name, path, description = row
                if query_lower in (description or "").lower():
                    results.append({
                        "topic": "general",
                        "source": name,
                        "location": path,
                        "relevance": "source_match"
                    })
        
        return results[:limit]
    
    def record_access(self, source: str, action: str):
        with self._lock:
            now = datetime.now().isoformat()
            
            with sqlite3.connect(self.index_path) as conn:
                conn.execute('''
                    INSERT INTO recent_access (source, action, timestamp)
                    VALUES (?, ?, ?)
                ''', (source, action, now))
                
                cursor = conn.execute('SELECT COUNT(*) FROM recent_access')
                count = cursor.fetchone()[0]
                
                if count > self.MAX_ACCESS_RECORDS:
                    conn.execute('''
                        DELETE FROM recent_access 
                        WHERE id IN (
                            SELECT id FROM recent_access 
                            ORDER BY timestamp ASC 
                            LIMIT ?
                        )
                    ''', (count - self.MAX_ACCESS_RECORDS,))
    
    def rebuild_index(self):
        logger.info("开始重建知识索引...")
        
        with self._lock:
            try:
                with sqlite3.connect("experience_pool.db") as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM experiences")
                    exp_count = cursor.fetchone()[0]
                self.update_count("experiences", exp_count)
            except Exception as e:
                logger.warning(f"统计经验池失败: {e}")
            
            try:
                with sqlite3.connect("learning_rules.db") as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
                    rule_count = cursor.fetchone()[0]
                self.update_count("rules", rule_count)
            except Exception as e:
                logger.warning(f"统计规则库失败: {e}")
            
            try:
                with sqlite3.connect("tool_cache.db") as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM tool_cache")
                    cache_count = cursor.fetchone()[0]
                self.update_count("tool_cache", cache_count)
            except Exception as e:
                logger.warning(f"统计工具缓存失败: {e}")
            
            try:
                with sqlite3.connect("experience_pool.db") as conn:
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
            except Exception as e:
                logger.warning(f"建立主题索引失败: {e}")
        
        logger.info("知识索引重建完成")
    
    def get_summary(self) -> str:
        lines = ["=" * 60, "知识索引摘要", "=" * 60]
        
        with sqlite3.connect(self.index_path) as conn:
            cursor = conn.execute('''
                SELECT name, type, count, description
                FROM knowledge_sources
            ''')
            
            lines.append("\n【知识源】")
            for row in cursor.fetchall():
                name, source_type, count, description = row
                lines.append(f"  {name}: {count or 0}条 ({source_type})")
            
            cursor = conn.execute('''
                SELECT topic, COUNT(*) 
                FROM topic_index 
                GROUP BY topic
            ''')
            
            lines.append("\n【主题分类】")
            for row in cursor.fetchall():
                topic, count = row
                lines.append(f"  {topic}: {count}个条目")
            
            cursor = conn.execute('''
                SELECT timestamp, source, action
                FROM recent_access
                ORDER BY timestamp DESC
                LIMIT 5
            ''')
            
            lines.append(f"\n【最近访问】")
            for row in cursor.fetchall():
                timestamp, source, action = row
                lines.append(f"  {timestamp[:19]} - {source} ({action})")
        
        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
    
    def get_source(self, name: str) -> Optional[Dict]:
        with sqlite3.connect(self.index_path) as conn:
            cursor = conn.execute('''
                SELECT name, type, path, description, count, registered_at, updated_at
                FROM knowledge_sources
                WHERE name = ?
            ''', (name,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                "name": row[0],
                "type": row[1],
                "path": row[2],
                "description": row[3],
                "count": row[4],
                "registered_at": row[5],
                "updated_at": row[6]
            }


if __name__ == "__main__":
    print("=" * 60)
    print("知识索引模块测试")
    print("=" * 60)
    
    index = KnowledgeIndex()
    
    print("\n测试1: 注册知识源")
    index.register_source(
        "custom_tools",
        "directory",
        "tools/generated",
        "动态生成的工具"
    )
    print("  ✓ 知识源已注册")
    
    print("\n测试2: 重建索引")
    index.rebuild_index()
    print("  ✓ 索引已重建")
    
    print("\n测试3: 查找知识")
    results = index.find_knowledge("code")
    print(f"  找到{len(results)}个匹配项")
    for result in results:
        print(f"    - {result['source']}: {result['location']}")
    
    print("\n测试4: 索引摘要")
    print(index.get_summary())
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
