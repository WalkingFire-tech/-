# -*- coding: utf-8 -*-
"""
即时学习系统 - 不训练也能进化

核心能力：
1. 在回答前自动检索事实库
2. 发现知识缺口时主动询问
3. 将纠错立即写入事实库
4. 形成真正的"渐进式学习"闭环

这是真正的"像人一样学习"的机制。
"""
import json
from infrastructure.database_manager import DatabaseManager
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class InstantLearningSystem:
    """
    即时学习系统
    
    让系统具备"秒级学习"能力：
    - 回答前检索事实库
    - 发现缺口主动询问
    - 纠错立即生效
    - 无需重新训练
    """
    
    def __init__(self, 
                 fact_db_path: str = "./data/fact_assertions_v2.db",
                 knowledge_log_path: str = "./logs/instant_learning.json"):
        """
        Args:
            fact_db_path: 事实库路径
            knowledge_log_path: 学习日志路径
        """
        self.fact_db_path = Path(fact_db_path)
        self.knowledge_log_path = Path(knowledge_log_path)
        self.knowledge_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.fact_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化事实库
        self._init_fact_db()
        
        # 加载学习日志
        self.learning_log = self._load_learning_log()
        
        logger.info("📚 即时学习系统已初始化")
        logger.info(f"   事实库: {fact_db_path}")
    
    def _init_fact_db(self):
        """初始化事实库"""
        db = DatabaseManager.get(self.fact_db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                concept TEXT NOT NULL,
                assertion TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                source TEXT DEFAULT 'user_correction',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                access_count INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_concept ON facts(concept);
            CREATE INDEX IF NOT EXISTS idx_assertion ON facts(assertion);
        ''')
        
        logger.info("✅ 事实库已初始化")
    
    def _load_learning_log(self) -> List[Dict]:
        """加载学习日志"""
        if self.knowledge_log_path.exists():
            with open(self.knowledge_log_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_learning_log(self):
        """保存学习日志"""
        with open(self.knowledge_log_path, 'w', encoding='utf-8') as f:
            json.dump(self.learning_log, f, ensure_ascii=False, indent=2)
    
    def retrieve_knowledge(self, question: str, top_k: int = 5) -> Tuple[List[Dict], float]:
        """
        检索知识（回答前调用）
        
        Args:
            question: 用户问题
            top_k: 返回top-k条相关知识
        
        Returns:
            (相关知识列表, 置信度)
        """
        # 提取关键词
        keywords = self._extract_keywords(question)
        
        # 检索事实库
        db = DatabaseManager.get(self.fact_db_path)
        
        results = []
        for keyword in keywords:
            rows = db.query('''
                SELECT concept, assertion, confidence, source, created_at, access_count
                FROM facts
                WHERE concept LIKE ? OR assertion LIKE ?
                ORDER BY confidence DESC, access_count DESC
                LIMIT ?
            ''', (f'%{keyword}%', f'%{keyword}%', top_k))
            
            for row in rows:
                results.append({
                    'concept': row[0],
                    'assertion': row[1],
                    'confidence': row[2],
                    'source': row[3],
                    'created_at': row[4],
                    'access_count': row[5],
                    'matched_keyword': keyword
                })
        
        # 去重
        seen = set()
        unique_results = []
        for item in results:
            key = item['concept']
            if key not in seen:
                seen.add(key)
                unique_results.append(item)
        
        # 计算置信度
        confidence = 0.0
        if unique_results:
            confidence = sum(r['confidence'] for r in unique_results) / len(unique_results)
        
        logger.info(f"🔍 检索知识: 找到 {len(unique_results)} 条相关知识, 置信度 {confidence:.2f}")
        
        return unique_results[:top_k], confidence
    
    def detect_knowledge_gap(self, question: str, retrieved_knowledge: List[Dict]) -> Optional[str]:
        """
        检测知识缺口
        
        Args:
            question: 用户问题
            retrieved_knowledge: 检索到的知识
        
        Returns:
            如果有缺口，返回提示信息；否则返回None
        """
        # 如果没有检索到相关知识，说明有缺口
        if not retrieved_knowledge:
            gap_message = f"⚠️ 我目前对这个问题还不够了解。您能告诉我正确的理解吗？我会立即记住。"
            logger.info(f"🚨 检测到知识缺口: {question[:50]}...")
            return gap_message
        
        # 如果检索到的知识置信度较低，也提示缺口
        avg_confidence = sum(k['confidence'] for k in retrieved_knowledge) / len(retrieved_knowledge)
        if avg_confidence < 0.5:
            gap_message = f"⚠️ 我对这个问题有些不确定。您能帮我确认一下吗？"
            logger.info(f"⚠️ 知识置信度较低: {avg_confidence:.2f}")
            return gap_message
        
        return None
    
    def learn_instantly(self, 
                       concept: str, 
                       assertion: str, 
                       source: str = 'user_correction',
                       confidence: float = 1.0) -> Dict:
        """
        即时学习（秒级生效）
        
        Args:
            concept: 概念
            assertion: 断言/知识
            source: 来源
            confidence: 置信度
        
        Returns:
            学习结果
        """
        logger.info(f"📚 即时学习: {concept[:30]}...")
        
        # 写入事实库
        db = DatabaseManager.get(self.fact_db_path)
        
        now = datetime.now().isoformat()
        
        existing = db.query_one('SELECT id FROM facts WHERE concept = ?', (concept,))
        
        if existing:
            db.execute('''
                UPDATE facts 
                SET assertion = ?, confidence = ?, source = ?, updated_at = ?
                WHERE concept = ?
            ''', (assertion, confidence, source, now, concept), commit=True)
            
            action = 'updated'
        else:
            db.execute('''
                INSERT INTO facts (concept, assertion, confidence, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (concept, assertion, confidence, source, now, now), commit=True)
            
            action = 'inserted'
        
        # 记录学习日志
        learning_record = {
            'timestamp': now,
            'type': 'instant_learning',
            'concept': concept,
            'assertion': assertion[:100],  # 只记录前100字符
            'source': source,
            'confidence': confidence,
            'action': action
        }
        
        self.learning_log.append(learning_record)
        self._save_learning_log()
        
        logger.info(f"✅ 即时学习完成: {action}")
        
        return {
            'status': 'success',
            'action': action,
            'concept': concept,
            'timestamp': now
        }
    
    def batch_learn(self, knowledge_items: List[Dict]) -> Dict:
        """
        批量学习
        
        Args:
            knowledge_items: 知识项列表
                [
                    {'concept': '...', 'assertion': '...', 'source': '...'},
                    ...
                ]
        
        Returns:
            学习结果
        """
        logger.info(f"📚 批量学习: {len(knowledge_items)} 条知识")
        
        results = []
        for item in knowledge_items:
            result = self.learn_instantly(
                concept=item['concept'],
                assertion=item['assertion'],
                source=item.get('source', 'batch_import'),
                confidence=item.get('confidence', 1.0)
            )
            results.append(result)
        
        # 统计
        inserted = len([r for r in results if r['action'] == 'inserted'])
        updated = len([r for r in results if r['action'] == 'updated'])
        
        logger.info(f"✅ 批量学习完成: 新增 {inserted} 条, 更新 {updated} 条")
        
        return {
            'status': 'success',
            'total': len(knowledge_items),
            'inserted': inserted,
            'updated': updated,
            'results': results
        }
    
    def get_knowledge_stats(self) -> Dict:
        """
        获取知识统计
        
        Returns:
            知识统计信息
        """
        db = DatabaseManager.get(self.fact_db_path)
        
        total_facts = db.query_one('SELECT COUNT(*) FROM facts')[0]
        
        by_source = dict(db.query('SELECT source, COUNT(*) FROM facts GROUP BY source'))
        
        avg_confidence = db.query_one('SELECT AVG(confidence) FROM facts')[0] or 0.0
        
        recent = db.query('SELECT concept, created_at FROM facts ORDER BY created_at DESC LIMIT 5')
        
        return {
            'total_facts': total_facts,
            'by_source': by_source,
            'avg_confidence': avg_confidence,
            'recent_learning': [
                {'concept': r[0], 'created_at': r[1]} 
                for r in recent
            ]
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        提取关键词
        
        Args:
            text: 文本
        
        Returns:
            关键词列表
        """
        # 简单的关键词提取
        # 去除停用词
        stopwords = {'的', '是', '在', '有', '和', '了', '这', '那', '我', '你', '他', '她', '它'}
        
        # 分词（简单按空格和标点分割）
        import re
        words = re.findall(r'[\u4e00-\u9fa5]+|[a-zA-Z]+', text)
        
        # 过滤
        keywords = [w for w in words if w not in stopwords and len(w) > 1]
        
        return keywords[:10]  # 最多10个关键词


def test_instant_learning():
    """测试即时学习系统"""
    print("="*60)
    print("测试即时学习系统")
    print("="*60)
    print()
    
    # 创建系统
    system = InstantLearningSystem()
    
    # 1. 即时学习
    print("\n1. 即时学习测试")
    result = system.learn_instantly(
        concept="深度学习的特点",
        assertion="深度学习的特点包括：1. 自动特征提取 2. 端到端学习 3. 层次化表示学习 4. 数据驱动与规模效应 5. 可扩展性",
        source="user_correction"
    )
    print(f"   状态: {result['status']}")
    print(f"   动作: {result['action']}")
    
    # 2. 检索知识
    print("\n2. 检索知识测试")
    knowledge, confidence = system.retrieve_knowledge("什么是深度学习的特点？")
    print(f"   找到 {len(knowledge)} 条知识")
    print(f"   置信度: {confidence:.2f}")
    if knowledge:
        print(f"   示例: {knowledge[0]['concept']}")
    
    # 3. 检测知识缺口
    print("\n3. 检测知识缺口测试")
    gap = system.detect_knowledge_gap("什么是量子计算的原理？", [])
    if gap:
        print(f"   缺口提示: {gap}")
    
    # 4. 知识统计
    print("\n4. 知识统计")
    stats = system.get_knowledge_stats()
    print(f"   总知识数: {stats['total_facts']}")
    print(f"   平均置信度: {stats['avg_confidence']:.2f}")
    print(f"   按来源: {stats['by_source']}")
    
    print("\n✅ 测试完成")


if __name__ == "__main__":
    test_instant_learning()