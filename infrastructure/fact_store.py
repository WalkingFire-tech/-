"""
客观事实锚点存储层
用于存储和验证确定性知识的三元组

核心理念：让系统具备"客观是非观"，不再唯用户情绪马首是瞻
"""
import sqlite3
import hashlib
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class FactStore:
    """
    事实断言存储器
    
    存储结构化的事实三元组 (subject, predicate, object)
    用于客观验证回答的正确性
    """
    
    def __init__(self, db_path: str = "data/fact_assertions.db"):
        self.db_path = db_path
        self._init_database()
        logger.info(f"📚 事实锚点库已初始化: {db_path}")
    
    def _init_database(self):
        """初始化数据库表结构"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS fact_assertions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_hash TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object TEXT NOT NULL,
                    source TEXT DEFAULT 'manual_seed',
                    confidence REAL DEFAULT 0.9,
                    is_negation BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('CREATE INDEX IF NOT EXISTS idx_question_hash ON fact_assertions(question_hash)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_subject ON fact_assertions(subject)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_predicate ON fact_assertions(predicate)')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS correction_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_hash TEXT NOT NULL,
                    old_assertion TEXT,
                    new_assertion TEXT,
                    correction_source TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    @staticmethod
    def hash_question(question: str) -> str:
        """生成问题的MD5哈希"""
        return hashlib.md5(question.encode('utf-8')).hexdigest()
    
    def add_assertion(
        self,
        question: str,
        subject: str,
        predicate: str,
        obj: str,
        source: str = "manual_seed",
        confidence: float = 0.9,
        is_negation: bool = False
    ) -> int:
        """
        添加事实断言
        
        Args:
            question: 关联的问题
            subject: 主语 (如 "冰雹")
            predicate: 谓语/关系 (如 "形成原因")
            obj: 宾语/值 (如 "过冷水滴冻结")
            source: 来源标识
            confidence: 置信度
            is_negation: 是否为否定性断言（纠错）
        
        Returns:
            插入的记录ID
        """
        question_hash = self.hash_question(question)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO fact_assertions 
                (question_hash, subject, predicate, object, source, confidence, is_negation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (question_hash, subject, predicate, obj, source, confidence, is_negation))
            
            assertion_id = cursor.lastrowid
            conn.commit()
        
        logger.info(f"✅ 添加事实断言: ({subject}, {predicate}, {obj}) <- {source}")
        return assertion_id
    
    def add_correction(
        self,
        question: str,
        old_subject: str,
        old_predicate: str,
        old_obj: str,
        new_subject: str,
        new_predicate: str,
        new_obj: str,
        correction_source: str = "user_correction"
    ):
        """
        添加纠错断言
        
        将旧断言标记为否定，添加新断言
        """
        question_hash = self.hash_question(question)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO fact_assertions 
                (question_hash, subject, predicate, object, source, confidence, is_negation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (question_hash, old_subject, old_predicate, old_obj, correction_source, 0.0, True))
            
            conn.execute('''
                INSERT INTO fact_assertions 
                (question_hash, subject, predicate, object, source, confidence, is_negation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (question_hash, new_subject, new_predicate, new_obj, correction_source, 0.95, False))
            
            conn.execute('''
                INSERT INTO correction_history
                (question_hash, old_assertion, new_assertion, correction_source)
                VALUES (?, ?, ?, ?)
            ''', (question_hash, 
                  f"({old_subject}, {old_predicate}, {old_obj})",
                  f"({new_subject}, {new_predicate}, {new_obj})",
                  correction_source))
            
            conn.commit()
        
        logger.info(f"🔧 纠错已记录: ({old_subject}, {old_predicate}, {old_obj}) → ({new_subject}, {new_predicate}, {new_obj})")
    
    def get_assertions(self, question: str) -> List[Dict]:
        """获取问题关联的所有事实断言"""
        question_hash = self.hash_question(question)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT subject, predicate, object, source, confidence, is_negation
                FROM fact_assertions
                WHERE question_hash = ? AND is_negation = 0
                ORDER BY confidence DESC
            ''', (question_hash,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_negations(self, question: str) -> List[Dict]:
        """获取问题关联的否定性断言（错误示例）"""
        question_hash = self.hash_question(question)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT subject, predicate, object, source
                FROM fact_assertions
                WHERE question_hash = ? AND is_negation = 1
            ''', (question_hash,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def check_assertion_exists(
        self,
        question: str,
        subject: str,
        predicate: str,
        obj: str
    ) -> bool:
        """检查断言是否已存在"""
        question_hash = self.hash_question(question)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT COUNT(*) FROM fact_assertions
                WHERE question_hash = ? AND subject = ? AND predicate = ? AND object = ?
            ''', (question_hash, subject, predicate, obj))
            
            return cursor.fetchone()[0] > 0
    
    def search_by_keywords(self, query: str, limit: int = 5) -> List[Dict]:
        """按关键词模糊搜索相关事实断言（subject/predicate/object匹配）"""
        import re
        
        stop_words = {'是什么', '为什么', '怎么样', '如何', '怎么', '怎样', '请问', '能否', '可以', '的是', '有什么', '哪些', '什么', '是否', '需要', '知道', '告诉', '解释', '说明', '分析', '的吗', '的了', '形成', '原因', '过程', '原理', '机制', '作用'}
        
        chunks = re.split(r'[？?！!，,。.、\s：:；;]+', query)
        keywords = []
        for chunk in chunks:
            chunk = chunk.strip()
            if chunk in stop_words or len(chunk) < 2:
                continue
            
            for length in [2, 3, 4]:
                for i in range(len(chunk) - length + 1):
                    sub = chunk[i:i+length]
                    if all('\u4e00' <= c <= '\u9fff' for c in sub) and sub not in stop_words:
                        keywords.append(sub)
            
            if len(chunk) >= 2 and chunk not in stop_words and chunk not in keywords:
                keywords.append(chunk[:4])
        
        if not keywords:
            keywords = [query[:min(4, len(query))]]
        
        results = []
        seen_keys = set()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            for kw in keywords[:10]:
                cursor = conn.execute('''
                    SELECT subject, predicate, object, source, confidence
                    FROM fact_assertions
                    WHERE is_negation = 0 AND (
                        subject LIKE ? OR predicate LIKE ? OR object LIKE ?
                    )
                    ORDER BY confidence DESC
                    LIMIT ?
                ''', (f"%{kw}%", f"%{kw}%", f"%{kw}%", limit))
                for row in cursor.fetchall():
                    d = dict(row)
                    key = (d['subject'], d['predicate'], d['object'])
                    if key not in seen_keys:
                        seen_keys.add(key)
                        results.append(d)
                        if len(results) >= limit:
                            return results
        return results
        return results

    def extract_and_store(self, question: str, response: str, source: str = "auto_extract") -> int:
        """从高质量回复中自动提取事实三元组并存储"""
        import re
        
        cleaned = re.sub(r'#{1,6}\s*', '', response)
        cleaned = re.sub(r'\*{1,2}([^*]+)\*{1,2}', r'\1', cleaned)
        cleaned = re.sub(r'^[-*]\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^\d+\.\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'---+', '', cleaned)
        cleaned = re.sub(r'⚠️.*?(?:\n|$)', '', cleaned)
        cleaned = re.sub(r'💡.*?(?:\n|$)', '', cleaned)
        cleaned = re.sub(r'[《》「」【】]', '', cleaned)
        
        sentences = re.split(r'[。！？\n]', cleaned)
        stored = 0
        
        noise_prefixes = ['确定', '很可能', '推论', '推理', '反面', '确定性', '第一步', '第二步', '第三步', 
                          '第四步', '综合', '最终', '区分', '事实', '反面观点', '我们', '这', '以上',
                          '当', '原本', '结果', '其中', '而', '但', '由于', '如果', '虽然', '因此',
                          '所以', '然而', '不过', '同时', '此外', '另外', '即', '例如', '如']
        
        for sent in sentences:
            sent = sent.strip()
            sent = re.sub(r'^[：:、，,；;]\s*', '', sent)
            if len(sent) < 8 or len(sent) > 80:
                continue
            
            if any(sent.startswith(p) for p in noise_prefixes):
                continue
            
            patterns = [
                (r'^([^，。、：：\s]{2,8})是指([^，。！？\s]{2,30})$', '是指'),
                (r'^([^，。、：：\s]{2,8})的原理是([^，。！？\s]{2,30})$', '原理'),
                (r'^([^，。、：：\s]{2,8})的作用是([^，。！？\s]{2,30})$', '作用'),
                (r'^([^，。、：：\s]{2,8})由([^，。！？\s]{2,20})组成$', '由...组成'),
                (r'^([^，。、：：\s]{2,8})属于([^，。！？\s]{2,20})$', '属于'),
                (r'^([^，。、：：\s]{2,8})包括([^，。！？\s]{2,20})$', '包括'),
                (r'^([^，。、：：\s]{2,8})会导致([^，。！？\s]{2,25})$', '导致'),
                (r'^([^，。、：：\s]{2,8})因为([^，。！？\s]{2,25})$', '因为'),
                (r'^([^，。、：：\s]{2,8})是([^，。！？\s]{2,25})$', '是'),
                (r'^([^，。、：：\s]{2,8})可以([^，。！？\s]{2,20})$', '可以'),
            ]
            
            for pattern, pred in patterns:
                m = re.match(pattern, sent)
                if m:
                    subj = m.group(1).strip()
                    obj = m.group(2).strip()
                    
                    if any(c in subj for c in '()（）[]【】{}<>《》'):
                        continue
                    if any(c in obj for c in '()（）[]【】{}<>《》'):
                        continue
                    if subj == obj:
                        continue
                    if len(subj) < 2 or len(obj) < 2:
                        continue
                    
                    if not self.check_assertion_exists(question, subj, pred, obj):
                        self.add_assertion(
                            question=question,
                            subject=subj,
                            predicate=pred,
                            obj=obj,
                            source=source,
                            confidence=0.7
                        )
                        stored += 1
                    break
        
        if stored > 0:
            logger.info(f"📚 自动提取{stored}条事实三元组: {question[:30]}")
        return stored

    def get_stats(self) -> Dict:
        """获取统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute('SELECT COUNT(*) FROM fact_assertions').fetchone()[0]
            positive = conn.execute('SELECT COUNT(*) FROM fact_assertions WHERE is_negation = 0').fetchone()[0]
            negations = conn.execute('SELECT COUNT(*) FROM fact_assertions WHERE is_negation = 1').fetchone()[0]
            corrections = conn.execute('SELECT COUNT(*) FROM correction_history').fetchone()[0]
            
            return {
                'total': total,
                'positive': positive,
                'negations': negations,
                'corrections': corrections
            }


fact_store = FactStore()