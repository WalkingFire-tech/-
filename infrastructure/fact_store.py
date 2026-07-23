"""
统一事实锚点存储层

整合V1查询能力 + V2衰减/优先级 + V3版本控制/回滚
数据库: data/fact_assertions.db（兼容V1数据）

核心能力：
- V1: search_by_keywords(中文NLP) + extract_and_store(自动三元组) + get_negations
- V2: apply_decay(置信度衰减) + mark_used(使用追踪) + _should_override(7级来源优先级)
- V3: rollback_to_version(版本回滚) + superseded_by链式引用
"""
import hashlib
import json
import threading
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from infrastructure.database_manager import DatabaseManager

_write_lock = threading.Lock()


class FactStore:
    """
    事实断言存储器
    
    存储结构化的事实三元组 (subject, predicate, object)
    用于客观验证回答的正确性
    """
    
    def __init__(self, db_path: str = "data/fact_assertions.db"):
        self.db_path = db_path
        self._lock = _write_lock
        self._init_database()
        logger.info(f"📚 事实锚点库已初始化: {db_path}")
    
    def _db(self):
        return DatabaseManager.get(self.db_path)
    
    def _write_op(self, func, *args, **kwargs):
        """线程安全的写操作"""
        with self._lock:
            db = self._db()
            try:
                result = db.transaction(func, *args, **kwargs)
                return result
            except Exception:
                raise
    
    def _init_database(self):
        """初始化数据库表结构"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        db = self._db()
        db.executescript('''
            CREATE TABLE IF NOT EXISTS fact_assertions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_hash TEXT NOT NULL,
                question TEXT DEFAULT '',
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                source TEXT DEFAULT 'manual_seed',
                confidence REAL DEFAULT 0.9,
                is_negation BOOLEAN DEFAULT 0,
                is_seed BOOLEAN DEFAULT 0,
                version INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT 1,
                superseded_by INTEGER DEFAULT NULL,
                last_used TIMESTAMP,
                use_count INTEGER DEFAULT 0,
                decay_factor REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_question_hash ON fact_assertions(question_hash);
            CREATE INDEX IF NOT EXISTS idx_subject ON fact_assertions(subject);
            CREATE INDEX IF NOT EXISTS idx_predicate ON fact_assertions(predicate)
        ''')
        
        for alter_sql in [
            'ALTER TABLE fact_assertions ADD COLUMN question TEXT DEFAULT ""',
            'ALTER TABLE fact_assertions ADD COLUMN is_seed BOOLEAN DEFAULT 0',
            'ALTER TABLE fact_assertions ADD COLUMN version INTEGER DEFAULT 1',
            'ALTER TABLE fact_assertions ADD COLUMN is_active BOOLEAN DEFAULT 1',
            'ALTER TABLE fact_assertions ADD COLUMN superseded_by INTEGER DEFAULT NULL',
            'ALTER TABLE fact_assertions ADD COLUMN last_used TIMESTAMP',
            'ALTER TABLE fact_assertions ADD COLUMN use_count INTEGER DEFAULT 0',
            'ALTER TABLE fact_assertions ADD COLUMN decay_factor REAL DEFAULT 1.0',
        ]:
            try:
                db.execute(alter_sql, commit=True)
            except Exception:
                logger.warning("操作降级跳过")
        
        try:
            db.execute('CREATE INDEX IF NOT EXISTS idx_active ON fact_assertions(is_active)', commit=True)
        except Exception:
            logger.warning("操作降级跳过")
        
        db.executescript('''
            CREATE TABLE IF NOT EXISTS correction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_hash TEXT NOT NULL,
                old_assertion TEXT,
                new_assertion TEXT,
                correction_source TEXT,
                old_assertion_id INTEGER,
                new_assertion_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS confidence_decay_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assertion_id INTEGER NOT NULL,
                old_confidence REAL,
                new_confidence REAL,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
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
        question_hash = self.hash_question(question)

        def _do(conn):
            cursor = conn.execute('''
                INSERT INTO fact_assertions 
                (question_hash, subject, predicate, object, source, confidence, is_negation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (question_hash, subject, predicate, obj, source, confidence, is_negation))
            return cursor.lastrowid

        assertion_id = self._write_op(_do)
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
        question_hash = self.hash_question(question)

        def _do(conn):
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

        self._write_op(_do)
        logger.info(f"🔧 纠错已记录: ({old_subject}, {old_predicate}, {old_obj}) → ({new_subject}, {new_predicate}, {new_obj})")
    
    def get_assertions(self, question: str) -> List[Dict]:
        """获取问题关联的所有事实断言"""
        question_hash = self.hash_question(question)
        
        db = self._db()
        rows = db.query('''
            SELECT subject, predicate, object, source, confidence, is_negation
            FROM fact_assertions
            WHERE question_hash = ? AND is_negation = 0
            ORDER BY confidence DESC
        ''', (question_hash,))
        
        return [dict(row) for row in rows]
    
    def get_negations(self, question: str) -> List[Dict]:
        """获取问题关联的否定性断言（错误示例）"""
        question_hash = self.hash_question(question)
        
        db = self._db()
        rows = db.query('''
            SELECT subject, predicate, object, source
            FROM fact_assertions
            WHERE question_hash = ? AND is_negation = 1
        ''', (question_hash,))
        
        return [dict(row) for row in rows]
    
    def check_assertion_exists(
        self,
        question: str,
        subject: str,
        predicate: str,
        obj: str
    ) -> bool:
        """检查断言是否已存在"""
        question_hash = self.hash_question(question)
        
        db = self._db()
        row = db.query_one('''
            SELECT COUNT(*) FROM fact_assertions
            WHERE question_hash = ? AND subject = ? AND predicate = ? AND object = ?
        ''', (question_hash, subject, predicate, obj))
        
        return row[0] > 0
    
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
        db = self._db()
        for kw in keywords[:10]:
            rows = db.query('''
                SELECT subject, predicate, object, source, confidence
                FROM fact_assertions
                WHERE is_negation = 0 AND (
                    subject LIKE ? OR predicate LIKE ? OR object LIKE ?
                )
                ORDER BY confidence DESC
                LIMIT ?
            ''', (f"%{kw}%", f"%{kw}%", f"%{kw}%", limit))
            for row in rows:
                d = dict(row)
                key = (d['subject'], d['predicate'], d['object'])
                if key not in seen_keys:
                    seen_keys.add(key)
                    results.append(d)
                    if len(results) >= limit:
                        return results
        return results


    def extract_and_store(self, question: str, response: str, source: str = "auto_extract") -> int:
        """从高质量回复中自动提取事实三元组并存储"""
        import re

        try:
            from core.knowledge_status_manager import KnowledgeStatusManager
            _ksm = KnowledgeStatusManager()
            _status = _ksm.get_status(subject, predicate, object)
            if _status == "deprecated":
                logger.info(f"知识已废弃，跳过入库: {subject}")
                return 0
        except Exception:
            pass

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
                          '所以', '然而', '不过', '同时', '此外', '另外', '即', '例如', '如',
                          '关键', '核心', '重要', '基本', '根本', '主要', '前提', '结论', '总结',
                          '逻辑', '推论', '支持', '反对', '注意', '需要', '应该', '必须', '可以',
                          '能够', '可能', '一定', '必然', '显然', '当然', '确实', '实际上',
                          '换句话', '也就是说', '换言之', '简而言之', '总而言之']
        
        markdown_chars = ['**', '##', '###', '- ', '* ', '> ', '|', '```', '---', '💡', '⚠️', '✅', '❌']
        
        for sent in sentences:
            sent = sent.strip()
            sent = re.sub(r'^[：:、，,；;]\s*', '', sent)
            if len(sent) < 8 or len(sent) > 80:
                continue
            
            if any(sent.startswith(p) for p in noise_prefixes):
                continue
            
            if any(mc in sent for mc in markdown_chars):
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
            
            if stored >= 1:
                break
        
        if stored > 0:
            logger.info(f"📚 自动提取{stored}条事实三元组: {question[:30]}")
        return stored

    def get_stats(self) -> Dict:
        """获取统计信息"""
        db = self._db()
        total = db.query_one('SELECT COUNT(*) FROM fact_assertions')[0]
        positive = db.query_one('SELECT COUNT(*) FROM fact_assertions WHERE is_negation = 0')[0]
        negations = db.query_one('SELECT COUNT(*) FROM fact_assertions WHERE is_negation = 1')[0]
        corrections = db.query_one('SELECT COUNT(*) FROM correction_history')[0]
        by_source = {}
        for row in db.query('SELECT source, COUNT(*) FROM fact_assertions GROUP BY source'):
            by_source[row[0]] = row[1]
        
        return {
            'total': total,
            'positive': positive,
            'negations': negations,
            'corrections': corrections,
            'by_source': by_source,
        }

    def mark_used(self, assertion_id: int):
        db = self._db()
        db.execute(
            'UPDATE fact_assertions SET use_count = use_count + 1, last_used = ? WHERE id = ?',
            (datetime.now().isoformat(), assertion_id), commit=True
        )

    def apply_decay(self, days_unused: int = 30, decay_rate: float = 0.95):
        cutoff = datetime.now().timestamp() - days_unused * 86400
        decayed = 0

        db = self._db()
        rows = db.query(
            'SELECT id, confidence, use_count, last_used FROM fact_assertions WHERE is_negation = 0 AND is_active = 1'
        )
        for row in rows:
            last = row['last_used']
            if last:
                try:
                    last_ts = datetime.fromisoformat(last).timestamp()
                    if last_ts < cutoff:
                        use_count = row['use_count']
                        confidence = row['confidence']
                        row_id = row['id']
                        use_boost = min(use_count * 0.01, 0.1)
                        new_conf = max(0.1, confidence * decay_rate + use_boost)
                        if new_conf < confidence:
                            db.execute(
                                'UPDATE fact_assertions SET confidence = ?, decay_factor = ? WHERE id = ?',
                                (new_conf, decay_rate, row_id), commit=True
                            )
                            db.execute(
                                'INSERT INTO confidence_decay_log (assertion_id, old_confidence, new_confidence, reason) VALUES (?, ?, ?, ?)',
                                (row_id, confidence, new_conf, f'unused_{days_unused}d'), commit=True
                            )
                            decayed += 1
                except Exception:
                    logger.warning("操作降级跳过")

        if decayed > 0:
            logger.info(f"📉 置信度衰减: {decayed}条断言已衰减")
        return decayed

    def _should_override(self, existing_conf: float, existing_source: str,
                         new_conf: float, new_source: str) -> bool:
        """7级来源优先级覆盖判断（V2能力）"""
        priority = {
            'user_correction': 7,
            'manual_seed': 6,
            'verified_source': 5,
            'chat_auto': 4,
            'auto_extract': 3,
            'external_search': 2,
            'unknown': 1,
        }
        existing_prio = priority.get(existing_source, 1)
        new_prio = priority.get(new_source, 1)
        if new_prio > existing_prio:
            return True
        if new_prio == existing_prio and new_conf > existing_conf:
            return True
        return False

    def get_active_assertions(self, question: str) -> List[Dict]:
        """获取有效断言（V3能力，版本感知）"""
        question_hash = self.hash_question(question)
        db = self._db()
        rows = db.query('''
            SELECT id, subject, predicate, object, source, confidence, version, is_negation
            FROM fact_assertions
            WHERE question_hash = ? AND is_active = 1 AND is_negation = 0
            ORDER BY confidence DESC
        ''', (question_hash,))
        return [dict(row) for row in rows]

    def get_assertion_history(self, question: str, subject: str, predicate: str) -> List[Dict]:
        """断言历史版本（V3能力）"""
        question_hash = self.hash_question(question)
        db = self._db()
        rows = db.query('''
            SELECT id, object, source, confidence, version, is_active, superseded_by, created_at
            FROM fact_assertions
            WHERE question_hash = ? AND subject = ? AND predicate = ?
            ORDER BY version DESC
        ''', (question_hash, subject, predicate))
        return [dict(row) for row in rows]

    def rollback_to_version(self, assertion_id: int, target_version: int) -> bool:
        db = self._db()
        def _do(conn):
            current = conn.execute('SELECT id, question_hash, subject, predicate FROM fact_assertions WHERE id = ?', (assertion_id,)).fetchone()
            if not current:
                return False
            target = conn.execute(
                'SELECT id FROM fact_assertions WHERE question_hash = ? AND subject = ? AND predicate = ? AND version = ?',
                (current['question_hash'], current['subject'], current['predicate'], target_version)
            ).fetchone()
            if not target:
                return False
            conn.execute('UPDATE fact_assertions SET is_active = 0 WHERE question_hash = ? AND subject = ? AND predicate = ? AND id != ?',
                         (current['question_hash'], current['subject'], current['predicate'], target['id']))
            conn.execute('UPDATE fact_assertions SET is_active = 1 WHERE id = ?', (target['id'],))
            return True

        result = db.transaction(_do)
        if result:
            logger.info(f"🔄 断言回滚: id={assertion_id} → version={target_version}")
        return result


fact_store = FactStore()
