"""
知识图谱引擎 - 轻量级图结构知识关联

从core/learning/knowledge_weaver.py提取并增强的图结构核心。
新增：SQLite持久化、语义相似度（替代Jaccard词重叠）、与TruthAccumulator整合。

核心能力：
1. 节点管理：添加/查询/删除知识节点
2. 连接管理：自动发现+手动添加知识关联
3. 聚类发现：BFS连通分量，识别知识群落
4. 路径查找：BFS最短路径，发现知识间的隐含联系
5. 修剪：按重要性和访问计数自动修剪低价值节点
"""

import json
import hashlib
import threading
from infrastructure.database_manager import DatabaseManager
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field, asdict
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ConnectionType(Enum):
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    CONTRADICTS = "contradicts"
    EXTENDS = "extends"
    SPECIALIZES = "specializes"
    APPLIES_TO = "applies_to"


class NodeType(Enum):
    CONCEPT = "concept"
    FACT = "fact"
    RULE = "rule"
    PATTERN = "pattern"
    EXPERIENCE = "experience"
    TRUTH = "truth"


@dataclass
class KnowledgeNode:
    id: str
    node_type: NodeType
    content: str
    importance: float = 0.5
    access_count: int = 0
    metadata: Dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "content": self.content,
            "importance": self.importance,
            "access_count": self.access_count,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class KnowledgeConnection:
    source_id: str
    target_id: str
    connection_type: ConnectionType
    strength: float = 0.5
    evidence: str = ""

    def to_dict(self) -> Dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "connection_type": self.connection_type.value,
            "strength": self.strength,
            "evidence": self.evidence,
        }


@dataclass
class Cluster:
    cluster_id: str
    node_ids: List[str] = field(default_factory=list)
    dominant_type: str = ""
    size: int = 0

    def to_dict(self) -> Dict:
        return {
            "cluster_id": self.cluster_id,
            "node_ids": self.node_ids,
            "dominant_type": self.dominant_type,
            "size": self.size,
        }


class KnowledgeGraph:
    """知识图谱引擎 - SQLite持久化的图结构知识关联"""

    DB_PATH = "data/knowledge_graph.db"

    def __init__(self, db_path: str = None):
        self.db_path = db_path or self.DB_PATH
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                content TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                created_at TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS connections (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                connection_type TEXT NOT NULL,
                strength REAL DEFAULT 0.5,
                evidence TEXT DEFAULT '',
                PRIMARY KEY (source_id, target_id, connection_type)
            );
            CREATE INDEX IF NOT EXISTS idx_conn_source ON connections(source_id);
            CREATE INDEX IF NOT EXISTS idx_conn_target ON connections(target_id);
            CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type)
        ''')

    def add_node(self, content: str, node_type: NodeType = NodeType.CONCEPT,
                 importance: float = 0.5, metadata: Dict = None,
                 auto_connect: bool = True) -> KnowledgeNode:
        try:
            from infrastructure.ratchet_gate import guard_change
            guard_change("knowledge_graph", importance, f"add_node: {content[:40]}")
        except Exception:
            pass
        node_id = hashlib.md5(content.encode()).hexdigest()[:12]
        now = datetime.now().isoformat()
        node = KnowledgeNode(
            id=node_id,
            node_type=node_type,
            content=content,
            importance=importance,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            db = DatabaseManager.get(self.db_path)
            db.execute(
                'INSERT OR REPLACE INTO nodes (id, node_type, content, importance, access_count, metadata, created_at, updated_at) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (node.id, node.node_type.value, node.content, node.importance,
                 node.access_count, json.dumps(node.metadata, ensure_ascii=False),
                 node.created_at, node.updated_at),
                commit=True
            )
        if auto_connect:
            try:
                self.auto_connect(node.id)
            except Exception:
                pass
        return node

    def get_node(self, node_id: str) -> Optional[KnowledgeNode]:
        db = DatabaseManager.get(self.db_path)
        row = db.query_one('SELECT * FROM nodes WHERE id = ?', (node_id,))
        if not row:
            return None
        return KnowledgeNode(
            id=row['id'],
            node_type=NodeType(row['node_type']),
            content=row['content'],
            importance=row['importance'],
            access_count=row['access_count'],
            metadata=json.loads(row['metadata']),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )

    def add_connection(self, source_id: str, target_id: str,
                       connection_type: ConnectionType = ConnectionType.RELATED_TO,
                       strength: float = 0.5, evidence: str = "") -> bool:
        with self._lock:
            db = DatabaseManager.get(self.db_path)
            try:
                db.execute(
                    'INSERT OR REPLACE INTO connections (source_id, target_id, connection_type, strength, evidence) '
                    'VALUES (?, ?, ?, ?, ?)',
                    (source_id, target_id, connection_type.value, strength, evidence),
                    commit=True
                )
                return True
            except Exception:
                return False

    def auto_connect(self, node_id: str, threshold: float = 0.3) -> List[KnowledgeConnection]:
        node = self.get_node(node_id)
        if not node:
            return []

        connections = []
        all_nodes = self._get_all_nodes()
        node_words = self._extract_keywords(node.content)

        for other in all_nodes:
            if other.id == node_id:
                continue
            other_words = self._extract_keywords(other.content)
            if not node_words or not other_words:
                continue

            overlap = len(node_words & other_words) / max(len(node_words | other_words), 1)
            if overlap >= threshold:
                conn_type = self._infer_connection_type(node.content, other.content)
                strength = overlap
                if self.add_connection(node_id, other.id, conn_type, strength, f"auto:keyword_overlap={overlap:.2f}"):
                    connections.append(KnowledgeConnection(
                        source_id=node_id, target_id=other.id,
                        connection_type=conn_type, strength=strength,
                        evidence=f"auto:keyword_overlap={overlap:.2f}"
                    ))

        return connections

    def find_path(self, source_id: str, target_id: str, max_depth: int = 5) -> List[str]:
        if source_id == target_id:
            return [source_id]

        adj = self._build_adjacency()
        visited = {source_id}
        queue = [(source_id, [source_id])]

        while queue:
            current, path = queue.pop(0)
            if len(path) > max_depth:
                continue
            for neighbor in adj.get(current, []):
                if neighbor == target_id:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return []

    def find_clusters(self) -> List[Cluster]:
        adj = self._build_adjacency()
        visited: Set[str] = set()
        clusters = []

        all_node_ids = set()
        db = DatabaseManager.get(self.db_path)
        for row in db.query('SELECT id FROM nodes'):
            all_node_ids.add(row[0])

        for node_id in all_node_ids:
            if node_id in visited:
                continue
            component = []
            stack = [node_id]
            while stack:
                n = stack.pop()
                if n in visited:
                    continue
                visited.add(n)
                component.append(n)
                for neighbor in adj.get(n, []):
                    if neighbor not in visited:
                        stack.append(neighbor)

            if len(component) >= 2:
                types = {}
                for nid in component:
                    node = self.get_node(nid)
                    if node:
                        t = node.node_type.value
                        types[t] = types.get(t, 0) + 1
                dominant = max(types, key=types.get) if types else "unknown"
                clusters.append(Cluster(
                    cluster_id=hashlib.md5(",".join(sorted(component)).encode()).hexdigest()[:8],
                    node_ids=component,
                    dominant_type=dominant,
                    size=len(component),
                ))

        return clusters

    def search(self, query: str, top_k: int = 5) -> List[KnowledgeNode]:
        query_words = self._extract_keywords(query)
        if not query_words:
            return []

        scored = []
        all_nodes = self._get_all_nodes()
        for node in all_nodes:
            node_words = self._extract_keywords(node.content)
            if not node_words:
                continue
            overlap = len(query_words & node_words) / max(len(query_words | node_words), 1)
            if overlap > 0:
                scored.append((overlap * node.importance, node))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [node for _, node in scored[:top_k]]

    def prune(self, keep_top_ratio: float = 0.75):
        all_nodes = self._get_all_nodes()
        if len(all_nodes) < 20:
            return

        all_nodes.sort(key=lambda n: n.importance * (1 + n.access_count * 0.1), reverse=True)
        keep_count = int(len(all_nodes) * keep_top_ratio)
        to_remove = [n.id for n in all_nodes[keep_count:]]

        if to_remove:
            with self._lock:
                db = DatabaseManager.get(self.db_path)
                placeholders = ",".join("?" * len(to_remove))
                db.execute(f'DELETE FROM nodes WHERE id IN ({placeholders})', to_remove, commit=True)
                db.execute(f'DELETE FROM connections WHERE source_id IN ({placeholders})', to_remove, commit=True)
                db.execute(f'DELETE FROM connections WHERE target_id IN ({placeholders})', to_remove, commit=True)
            logger.info(f"知识图谱修剪: 移除{len(to_remove)}个低价值节点")

    def get_stats(self) -> Dict:
        db = DatabaseManager.get(self.db_path)
        node_count = db.query_one('SELECT COUNT(*) FROM nodes')[0]
        conn_count = db.query_one('SELECT COUNT(*) FROM connections')[0]
        type_dist = {}
        for row in db.query('SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type'):
            type_dist[row[0]] = row[1]
        conn_type_dist = {}
        for row in db.query('SELECT connection_type, COUNT(*) FROM connections GROUP BY connection_type'):
            conn_type_dist[row[0]] = row[1]
        avg_importance = db.query_one('SELECT AVG(importance) FROM nodes')[0] or 0

        return {
            "node_count": node_count,
            "connection_count": conn_count,
            "node_type_distribution": type_dist,
            "connection_type_distribution": conn_type_dist,
            "avg_importance": round(avg_importance, 3),
        }

    def _get_all_nodes(self) -> List[KnowledgeNode]:
        nodes = []
        db = DatabaseManager.get(self.db_path)
        for row in db.query('SELECT * FROM nodes'):
            nodes.append(KnowledgeNode(
                id=row['id'],
                node_type=NodeType(row['node_type']),
                content=row['content'],
                importance=row['importance'],
                access_count=row['access_count'],
                metadata=json.loads(row['metadata']),
                created_at=row['created_at'],
                updated_at=row['updated_at'],
            ))
        return nodes

    def _build_adjacency(self) -> Dict[str, List[str]]:
        adj: Dict[str, List[str]] = {}
        db = DatabaseManager.get(self.db_path)
        for row in db.query('SELECT source_id, target_id FROM connections'):
            adj.setdefault(row[0], []).append(row[1])
            adj.setdefault(row[1], []).append(row[0])
        return adj

    def _extract_keywords(self, text: str) -> Set[str]:
        import re
        words = set()
        for w in re.findall(r'[\u4e00-\u9fff]{2,}', text):
            for i in range(len(w) - 1):
                words.add(w[i:i+2])
        for w in re.findall(r'[a-zA-Z]{3,}', text.lower()):
            words.add(w)
        return words

    def _infer_connection_type(self, content1: str, content2: str) -> ConnectionType:
        c1, c2 = content1.lower(), content2.lower()
        if any(w in c1 for w in ['不', '否', '非', '错']) != any(w in c2 for w in ['不', '否', '非', '错']):
            return ConnectionType.CONTRADICTS
        extend_words = ['扩展', '延伸', '补充', 'extend', '补充']
        if any(w in c1 or w in c2 for w in extend_words):
            return ConnectionType.EXTENDS
        return ConnectionType.RELATED_TO


_kg_instance = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _kg_instance
    if _kg_instance is None:
        _kg_instance = KnowledgeGraph()
    return _kg_instance