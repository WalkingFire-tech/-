"""
知识网络编织 - 建立知识与知识之间的连接

核心理念：知识不是孤立的，而是相互连接的网络
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime
from enum import Enum


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
    HYPOTHESIS = "hypothesis"


@dataclass
class Node:
    node_id: str
    type: NodeType
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    importance: float = 0.5


@dataclass
class Connection:
    source_id: str
    target_id: str
    type: ConnectionType
    strength: float = 1.0
    evidence: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Network:
    nodes: Dict[str, Node]
    connections: List[Connection]
    clusters: Dict[str, Set[str]]


@dataclass
class WeavingResult:
    nodes_added: int
    connections_added: int
    clusters_updated: int
    insights: List[str]


class KnowledgeWeaver:
    """
    知识网络编织器
    
    构建知识图谱，发现知识间的隐含关系
    """
    
    def __init__(self, max_nodes: int = 10000):
        self.max_nodes = max_nodes
        self.nodes: Dict[str, Node] = {}
        self.connections: List[Connection] = []
        self.connection_index: Dict[str, List[Connection]] = {}
        self.clusters: Dict[str, Set[str]] = {}
        self.similarity_threshold = 0.6
    
    def add_node(
        self,
        content: Any,
        node_type: NodeType = NodeType.CONCEPT,
        metadata: Dict[str, Any] = None,
    ) -> str:
        if len(self.nodes) >= self.max_nodes:
            self._prune_low_importance_nodes()
        
        node_id = self._generate_node_id(content, node_type)
        
        if node_id in self.nodes:
            self.nodes[node_id].access_count += 1
            return node_id
        
        node = Node(
            node_id=node_id,
            type=node_type,
            content=content,
            metadata=metadata or {},
        )
        
        self.nodes[node_id] = node
        self.connection_index[node_id] = []
        
        self._auto_connect(node)
        
        return node_id
    
    def _generate_node_id(self, content: Any, node_type: NodeType) -> str:
        import hashlib
        content_str = str(content)
        hash_val = hashlib.md5(content_str.encode()).hexdigest()[:12]
        return f"{node_type.value}_{hash_val}"
    
    def connect(
        self,
        source_id: str,
        target_id: str,
        connection_type: ConnectionType,
        strength: float = 1.0,
        evidence: str = None,
    ) -> bool:
        if source_id not in self.nodes or target_id not in self.nodes:
            return False
        
        existing = self._find_connection(source_id, target_id, connection_type)
        if existing:
            existing.strength = max(existing.strength, strength)
            if evidence:
                existing.evidence.append(evidence)
            return True
        
        connection = Connection(
            source_id=source_id,
            target_id=target_id,
            type=connection_type,
            strength=strength,
            evidence=[evidence] if evidence else [],
        )
        
        self.connections.append(connection)
        self.connection_index[source_id].append(connection)
        self.connection_index[target_id].append(connection)
        
        return True
    
    def _find_connection(
        self,
        source_id: str,
        target_id: str,
        connection_type: ConnectionType,
    ) -> Optional[Connection]:
        for conn in self.connection_index.get(source_id, []):
            if conn.target_id == target_id and conn.type == connection_type:
                return conn
        return None
    
    def _auto_connect(self, node: Node) -> None:
        similar_nodes = self._find_similar_nodes(node)
        
        for similar_node, similarity in similar_nodes:
            if similarity >= self.similarity_threshold:
                self.connect(
                    node.node_id,
                    similar_node.node_id,
                    ConnectionType.RELATED_TO,
                    strength=similarity,
                    evidence="auto_similarity",
                )
    
    def _find_similar_nodes(self, node: Node) -> List[Tuple[Node, float]]:
        similarities = []
        
        for other_id, other_node in self.nodes.items():
            if other_id == node.node_id:
                continue
            
            similarity = self._calculate_similarity(node, other_node)
            if similarity > 0:
                similarities.append((other_node, similarity))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:10]
    
    def _calculate_similarity(self, node1: Node, node2: Node) -> float:
        if node1.type != node2.type:
            score = 0.3
        else:
            score = 0.5
        
        content1 = str(node1.content).lower()
        content2 = str(node2.content).lower()
        
        words1 = set(content1.split())
        words2 = set(content2.split())
        
        if words1 and words2:
            overlap = len(words1 & words2)
            union = len(words1 | words2)
            jaccard = overlap / union if union > 0 else 0
            score += jaccard * 0.5
        
        return min(1.0, score)
    
    def weave(self, nodes: List[Tuple[Any, NodeType]]) -> WeavingResult:
        added_nodes = 0
        added_connections = 0
        
        node_ids = []
        for content, node_type in nodes:
            node_id = self.add_node(content, node_type)
            node_ids.append(node_id)
            added_nodes += 1
        
        for i, source_id in enumerate(node_ids):
            for j, target_id in enumerate(node_ids):
                if i >= j:
                    continue
                
                if self._should_connect(source_id, target_id):
                    conn_type = self._infer_connection_type(source_id, target_id)
                    if self.connect(source_id, target_id, conn_type):
                        added_connections += 1
        
        clusters_updated = self._update_clusters()
        
        insights = self._extract_insights()
        
        return WeavingResult(
            nodes_added=added_nodes,
            connections_added=added_connections,
            clusters_updated=clusters_updated,
            insights=insights,
        )
    
    def _should_connect(self, source_id: str, target_id: str) -> bool:
        source = self.nodes[source_id]
        target = self.nodes[target_id]
        
        similarity = self._calculate_similarity(source, target)
        return similarity >= self.similarity_threshold
    
    def _infer_connection_type(
        self,
        source_id: str,
        target_id: str,
    ) -> ConnectionType:
        source = self.nodes[source_id]
        target = self.nodes[target_id]
        
        source_str = str(source.content).lower()
        target_str = str(target.content).lower()
        
        if "extend" in source_str or "extend" in target_str:
            return ConnectionType.EXTENDS
        elif "depend" in source_str or "depend" in target_str:
            return ConnectionType.DEPENDS_ON
        elif "apply" in source_str or "apply" in target_str:
            return ConnectionType.APPLIES_TO
        elif "special" in source_str or "special" in target_str:
            return ConnectionType.SPECIALIZES
        
        return ConnectionType.RELATED_TO
    
    def _update_clusters(self) -> int:
        visited = set()
        new_clusters = {}
        cluster_id = 0
        
        for node_id in self.nodes:
            if node_id in visited:
                continue
            
            cluster = self._find_cluster(node_id)
            if len(cluster) > 1:
                new_clusters[f"cluster_{cluster_id}"] = cluster
                cluster_id += 1
                visited.update(cluster)
        
        self.clusters = new_clusters
        return len(self.clusters)
    
    def _find_cluster(self, start_id: str) -> Set[str]:
        cluster = set()
        queue = [start_id]
        
        while queue:
            current = queue.pop(0)
            if current in cluster:
                continue
            
            cluster.add(current)
            
            for conn in self.connection_index.get(current, []):
                neighbor = conn.target_id if conn.source_id == current else conn.source_id
                if neighbor not in cluster and conn.strength >= 0.5:
                    queue.append(neighbor)
        
        return cluster
    
    def _extract_insights(self) -> List[str]:
        insights = []
        
        for cluster_name, cluster_nodes in self.clusters.items():
            if len(cluster_nodes) >= 3:
                insights.append(f"发现知识群落: {cluster_name} ({len(cluster_nodes)}个节点)")
        
        high_importance = [
            node for node in self.nodes.values()
            if node.importance >= 0.8
        ]
        if high_importance:
            insights.append(f"高重要性知识: {len(high_importance)}个")
        
        return insights
    
    def query(
        self,
        node_id: str,
        connection_types: List[ConnectionType] = None,
        max_depth: int = 2,
    ) -> Dict[str, Any]:
        if node_id not in self.nodes:
            return {"node": None, "neighbors": []}
        
        node = self.nodes[node_id]
        node.access_count += 1
        
        neighbors = self._get_neighbors(node_id, connection_types)
        
        if max_depth > 1:
            for neighbor_id in list(neighbors.keys()):
                deeper = self._get_neighbors(neighbor_id, connection_types)
                for deep_id, deep_info in deeper.items():
                    if deep_id not in neighbors and deep_id != node_id:
                        neighbors[deep_id] = {
                            **deep_info,
                            "depth": 2,
                        }
        
        return {
            "node": {
                "id": node.node_id,
                "type": node.type.value,
                "content": node.content,
            },
            "neighbors": neighbors,
        }
    
    def _get_neighbors(
        self,
        node_id: str,
        connection_types: List[ConnectionType] = None,
    ) -> Dict[str, Dict]:
        neighbors = {}
        
        for conn in self.connection_index.get(node_id, []):
            if connection_types and conn.type not in connection_types:
                continue
            
            neighbor_id = conn.target_id if conn.source_id == node_id else conn.source_id
            
            if neighbor_id not in self.nodes:
                continue
            
            neighbor = self.nodes[neighbor_id]
            neighbors[neighbor_id] = {
                "type": neighbor.type.value,
                "content": neighbor.content,
                "connection": conn.type.value,
                "strength": conn.strength,
                "depth": 1,
            }
        
        return neighbors
    
    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 5,
    ) -> List[str]:
        if source_id not in self.nodes or target_id not in self.nodes:
            return []
        
        if source_id == target_id:
            return [source_id]
        
        visited = {source_id}
        queue = [(source_id, [source_id])]
        
        while queue:
            current, path = queue.pop(0)
            
            if len(path) > max_length:
                continue
            
            for conn in self.connection_index.get(current, []):
                neighbor = conn.target_id if conn.source_id == current else conn.source_id
                
                if neighbor == target_id:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return []
    
    def _prune_low_importance_nodes(self) -> None:
        sorted_nodes = sorted(
            self.nodes.items(),
            key=lambda x: (x[1].importance, x[1].access_count),
        )
        
        remove_count = len(self.nodes) // 4
        
        for node_id, _ in sorted_nodes[:remove_count]:
            self._remove_node(node_id)
    
    def _remove_node(self, node_id: str) -> None:
        if node_id not in self.nodes:
            return
        
        del self.nodes[node_id]
        
        self.connections = [
            conn for conn in self.connections
            if conn.source_id != node_id and conn.target_id != node_id
        ]
        
        del self.connection_index[node_id]
        
        for other_id in self.connection_index:
            self.connection_index[other_id] = [
                conn for conn in self.connection_index[other_id]
                if conn.source_id != node_id and conn.target_id != node_id
            ]
    
    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_nodes": len(self.nodes),
            "total_connections": len(self.connections),
            "total_clusters": len(self.clusters),
            "node_types": {
                t.value: sum(1 for n in self.nodes.values() if n.type == t)
                for t in NodeType
            },
            "connection_types": {
                t.value: sum(1 for c in self.connections if c.type == t)
                for t in ConnectionType
            },
            "average_connections": (
                len(self.connections) * 2 / len(self.nodes)
                if self.nodes else 0
            ),
        }
    
    def export_network(self) -> Network:
        return Network(
            nodes=self.nodes.copy(),
            connections=self.connections.copy(),
            clusters=self.clusters.copy(),
        )