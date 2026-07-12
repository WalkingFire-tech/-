"""
基于语义的知识缺失检测器 - 零硬编码版

核心设计：
1. 使用向量检索进行语义匹配
2. 所有词汇、阈值从数据库/配置文件加载
3. 支持学习新领域和新表达
4. 降级策略：语义失败时使用规则
"""

import json
import numpy as np
from infrastructure.database_manager import DatabaseManager
from typing import Tuple, List, Optional, Dict
from pathlib import Path
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class SemanticGapDetector:
    """基于语义的知识缺失检测器 - 零硬编码版"""

    def __init__(self, db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
        self._embedding_model = None
        self._domain_embeddings = {}
        self._knowledge_embeddings = {}
        self.config = self._load_config()
        self._init_database()
        self._init_embedding()
        self._init_uncertainty_words()

        logger.info("🔍 语义知识检测器已初始化（零硬编码版）")

    def _load_config(self) -> Dict:
        """加载配置"""
        config_file = Path("config/detector_config.json")
        default_config = {
            "domain_confidence_threshold": 0.5,
            "coverage_threshold": 0.3,
            "confidence_threshold": 0.5,
            "response_min_length": 50,
            "semantic_similarity_threshold": 0.5,
            "learn_keywords": ["如何", "为什么", "原理", "详解", "深入", "请教", "推荐", "选型"]
        }

        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return {**default_config, **json.load(f)}
            except Exception:
                return default_config

        config_file.parent.mkdir(exist_ok=True)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)

        return default_config

    def _init_database(self):
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(exist_ok=True)

        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS domain_knowledge (
                domain TEXT PRIMARY KEY,
                keywords TEXT,
                description TEXT,
                embedding TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS knowledge_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT,
                question TEXT,
                answer TEXT,
                embedding TEXT,
                quality_score REAL DEFAULT 0.5,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS uncertainty_words (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT,
                language TEXT DEFAULT 'zh',
                confidence REAL DEFAULT 0.8,
                created_at TEXT,
                UNIQUE(word)
            );

            CREATE TABLE IF NOT EXISTS validation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT,
                has_gap INTEGER,
                reason TEXT,
                confidence REAL,
                validated_at TEXT
            );
        ''')

    def _init_embedding(self):
        """初始化嵌入模型"""
        try:
            import os
            os.environ['HF_HUB_OFFLINE'] = '1'
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ 嵌入模型已加载")
        except Exception as e:
            logger.warning(f"⚠️ 嵌入模型加载失败，将使用规则降级: {e}")

    def _init_uncertainty_words(self):
        """从数据库加载不确定性词汇"""
        try:
            db = DatabaseManager.get(self.db_path)
            row = db.query_one("SELECT COUNT(*) FROM uncertainty_words")
            if row[0] == 0:
                self._load_default_uncertainty_words()
        except Exception as e:
            logger.warning(f"加载不确定性词汇失败: {e}")

    def _load_default_uncertainty_words(self):
        """从配置文件加载默认不确定性词汇"""
        word_file = Path("config/uncertainty_words.json")
        default_words = [
            "可能", "不确定", "不清楚", "不太确定", "也许", "大概",
            "应该是", "不了解", "不知道", "maybe", "perhaps",
            "uncertain", "likely", "probably"
        ]

        if word_file.exists():
            try:
                with open(word_file, 'r', encoding='utf-8') as f:
                    words = json.load(f)
            except Exception:
                words = default_words
        else:
            word_file.parent.mkdir(exist_ok=True)
            with open(word_file, 'w', encoding='utf-8') as f:
                json.dump(default_words, f, ensure_ascii=False, indent=2)
            words = default_words

        db = DatabaseManager.get(self.db_path)
        for word in words:
            db.execute(
                "INSERT OR IGNORE INTO uncertainty_words (word, created_at) VALUES (?, ?)",
                (word, datetime.now().isoformat()),
                commit=True
            )

    def _get_uncertainty_words(self) -> List[str]:
        """从数据库获取不确定性词汇"""
        try:
            db = DatabaseManager.get(self.db_path)
            rows = db.query("SELECT word FROM uncertainty_words")
            return [row[0] for row in rows]
        except Exception:
            return []

    def _contains_uncertainty_semantic(self, response: str) -> bool:
        """检测不确定性（使用数据库词汇）"""
        uncertainty_words = self._get_uncertainty_words()
        if not uncertainty_words:
            return False

        response_lower = response.lower()
        for word in uncertainty_words:
            if word.lower() in response_lower:
                return True
        return False

    def learn_uncertainty_word(self, word: str):
        """学习新的不确定性词汇"""
        db = DatabaseManager.get(self.db_path)
        db.execute(
            "INSERT OR IGNORE INTO uncertainty_words (word, created_at) VALUES (?, ?)",
            (word, datetime.now().isoformat()),
            commit=True
        )
        logger.info(f"📚 学习不确定性词汇: {word}")

    def detect_knowledge_gap(
        self,
        user_query: str,
        response: str,
        confidence: float = 1.0
    ) -> Tuple[bool, str, List[str]]:
        """检测知识缺失"""
        issues = []

        domain, domain_conf = self._identify_domain_semantic(user_query)

        if domain and domain_conf > self.config["domain_confidence_threshold"]:
            coverage = self._get_domain_coverage(domain, user_query)
            if coverage < self.config["coverage_threshold"]:
                issues.append(f"领域 '{domain}' 知识覆盖不足 ({coverage:.1%})")
                return True, f"领域知识不足: {domain}", issues

        if self._contains_uncertainty_semantic(response):
            issues.append("回答中存在不确定性表述")
            return True, "回答包含不确定性", issues

        if confidence < self.config["confidence_threshold"]:
            issues.append(f"置信度过低: {confidence:.2f}")
            return True, "置信度过低", issues

        if len(response) < self.config["response_min_length"]:
            issues.append("响应过短")
            return True, "响应过短", issues

        return False, "", issues

    def _identify_domain_semantic(self, query: str) -> Tuple[Optional[str], float]:
        """语义领域识别"""
        if not self._embedding_model:
            return self._identify_domain_keyword(query)

        try:
            domains = self._get_domain_embeddings()
            if not domains:
                return self._identify_domain_keyword(query)

            query_vec = self._embedding_model.encode(query)
            from sklearn.metrics.pairwise import cosine_similarity

            best_domain = None
            best_score = 0.0

            for domain, domain_vec in domains.items():
                score = cosine_similarity([query_vec], [domain_vec])[0][0]
                if score > best_score:
                    best_score = score
                    best_domain = domain

            threshold = self.config.get("semantic_similarity_threshold", 0.5)
            if best_score > threshold:
                return best_domain, float(best_score)

        except Exception as e:
            logger.debug(f"语义领域识别失败: {e}")

        return self._identify_domain_keyword(query)

    def _identify_domain_keyword(self, query: str) -> Tuple[Optional[str], float]:
        """关键词降级识别"""
        try:
            db = DatabaseManager.get(self.db_path)
            rows = db.query("SELECT domain, keywords FROM domain_knowledge")
            for domain, keywords_json in rows:
                if not keywords_json:
                    continue
                keywords = json.loads(keywords_json)
                for kw in keywords:
                    if kw in query:
                        return domain, 0.7
        except Exception:
            pass
        return None, 0.0

    def _get_domain_embeddings(self) -> Dict[str, np.ndarray]:
        """获取领域嵌入向量"""
        if self._domain_embeddings:
            return self._domain_embeddings

        try:
            db = DatabaseManager.get(self.db_path)
            rows = db.query(
                "SELECT domain, embedding FROM domain_knowledge WHERE embedding IS NOT NULL"
            )
            for domain, embedding_json in rows:
                if embedding_json:
                    self._domain_embeddings[domain] = np.array(
                        json.loads(embedding_json)
                    )
        except Exception:
            pass

        return self._domain_embeddings

    def _get_domain_coverage(self, domain: str, query: str) -> float:
        """计算领域覆盖度（语义优先）"""
        if self._embedding_model:
            try:
                domain_knowledge = self._get_domain_knowledge_vectors(domain)
                if domain_knowledge:
                    query_vec = self._embedding_model.encode(query)
                    from sklearn.metrics.pairwise import cosine_similarity

                    max_sim = max(
                        cosine_similarity([query_vec], [kv])[0][0]
                        for kv in domain_knowledge
                    )
                    return min(1.0, max_sim * 2)
            except Exception:
                pass

        return self._get_domain_coverage_count(domain)

    def _get_domain_coverage_count(self, domain: str) -> float:
        """基于数量的覆盖度计算"""
        try:
            db = DatabaseManager.get(self.db_path)
            row = db.query_one(
                "SELECT COUNT(*) FROM knowledge_items WHERE domain = ?",
                (domain,)
            )
            count = row[0]
            return min(1.0, count / 5)
        except Exception:
            return 0.0

    def _get_domain_knowledge_vectors(self, domain: str) -> List[np.ndarray]:
        """获取领域内知识的向量"""
        try:
            db = DatabaseManager.get(self.db_path)
            rows = db.query(
                "SELECT embedding FROM knowledge_items WHERE domain = ? AND embedding IS NOT NULL",
                (domain,)
            )
            return [np.array(json.loads(row[0])) for row in rows]
        except Exception:
            return []

    def learn_domain(self, domain: str, keywords: List[str], description: str = ""):
        """学习新领域"""
        text_for_embedding = description or domain
        if keywords and not description:
            text_for_embedding = f"{domain}: {' '.join(keywords)}"

        embedding_json = None
        if self._embedding_model:
            try:
                embedding = self._embedding_model.encode(text_for_embedding)
                embedding_json = json.dumps(embedding.tolist())
            except Exception:
                pass

        db = DatabaseManager.get(self.db_path)
        db.execute(
            "INSERT OR REPLACE INTO domain_knowledge (domain, keywords, description, embedding, created_at) VALUES (?, ?, ?, ?, ?)",
            (domain, json.dumps(keywords, ensure_ascii=False), description, embedding_json, datetime.now().isoformat()),
            commit=True
        )

        if embedding_json:
            self._domain_embeddings[domain] = np.array(json.loads(embedding_json))

        logger.info(f"📚 学习新领域: {domain}")

    def add_knowledge(self, domain: str, question: str, answer: str, quality: float = 0.5):
        """添加知识条目（含向量）"""
        embedding_json = None
        if self._embedding_model and question:
            try:
                embedding = self._embedding_model.encode(question)
                embedding_json = json.dumps(embedding.tolist())
            except Exception:
                pass

        db = DatabaseManager.get(self.db_path)
        db.execute(
            "INSERT INTO knowledge_items (domain, question, answer, embedding, quality_score, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (domain, question, answer, embedding_json, quality, datetime.now().isoformat()),
            commit=True
        )

    def should_learn_externally(self, user_query: str, response: str,
                               confidence: float = 1.0) -> Tuple[bool, str]:
        """判断是否应该外部学习"""
        has_gap, reason, _ = self.detect_knowledge_gap(user_query, response, confidence)

        if has_gap:
            return True, f"检测到知识缺失: {reason}"

        learn_keywords = self.config.get("learn_keywords", ["如何", "为什么", "原理", "详解", "深入", "请教", "推荐", "选型"])
        if any(kw in user_query for kw in learn_keywords):
            return True, "学习型问题，建议外部学习"

        return False, ""


semantic_detector = SemanticGapDetector()
