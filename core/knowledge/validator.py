"""
基于知识库的推荐验证器 - 零硬编码版

核心设计：
1. 所有知识存储在数据库中
2. 兼容关系通过学习机制积累
3. 支持动态添加类别和实体
4. 使用语义匹配验证推荐
"""

import json

import re
import hashlib
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
from infrastructure.database_manager import DatabaseManager

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class KnowledgeBasedValidator:
    """基于知识库的推荐验证器 - 零硬编码版"""

    def __init__(self, db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
        self._init_database()
        self._load_initial_knowledge()

        logger.info("✅ 知识库推荐验证器已初始化")

    def _init_database(self):
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(exist_ok=True)

        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS category_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                keyword TEXT,
                created_at TEXT,
                UNIQUE(category, keyword)
            );
            CREATE TABLE IF NOT EXISTS entity_mapping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT,
                pattern TEXT,
                confidence REAL,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS type_compatibility (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type_a TEXT,
                type_b TEXT,
                confidence REAL DEFAULT 0.5,
                occurrences INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(type_a, type_b)
            );
            CREATE TABLE IF NOT EXISTS validation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT,
                recommendation TEXT,
                is_valid INTEGER,
                issues TEXT,
                confidence REAL,
                validated_at TEXT
            )
        ''')

    def _load_initial_knowledge(self):
        """从外部配置文件加载初始知识"""
        db = DatabaseManager.get(self.db_path)
        row = db.query_one("SELECT COUNT(*) FROM category_mapping")
        if row[0] > 0:
            return

        init_data = self._load_init_file()
        if not init_data:
            logger.info("⚠️ 无初始知识文件，以空知识库启动")
            return

        for category, keyword in init_data.get("category_keywords", []):
            db.execute(
                "INSERT OR IGNORE INTO category_mapping (category, keyword, created_at) VALUES (?, ?, ?)",
                (category, keyword, datetime.now().isoformat())
            )

        for entity_type, pattern, confidence in init_data.get("entity_patterns", []):
            db.execute(
                "INSERT INTO entity_mapping (entity_type, pattern, confidence, created_at) VALUES (?, ?, ?, ?)",
                (entity_type, pattern, confidence, datetime.now().isoformat())
            )

        for type_a, type_b, confidence in init_data.get("type_compatibilities", []):
            db.execute(
                "INSERT OR IGNORE INTO type_compatibility (type_a, type_b, confidence, occurrences, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (type_a, type_b, confidence, 1, datetime.now().isoformat(), datetime.now().isoformat())
            )

        db.execute("SELECT 1", commit=True)
        logger.info("✅ 初始知识已加载")

    def _load_init_file(self) -> dict:
        """加载初始化配置文件"""
        init_file = Path("data/initial_knowledge.json")
        default_data = {
            "category_keywords": [
                ["电池保护", "保护板"],
                ["电池保护", "BMS"],
                ["电池保护", "电池保护"],
                ["LED驱动", "LED"],
                ["LED驱动", "背光"],
                ["电源管理", "电源管理"],
                ["充电管理", "充电"],
                ["电机控制", "电机"],
                ["传感器", "传感器"]
            ],
            "entity_patterns": [
                ["电池保护", "BQ769", 0.9],
                ["电池保护", "BQ779", 0.9],
                ["LED驱动", "TPS611", 0.9]
            ],
            "type_compatibilities": [
                ["电池保护", "电源管理", 0.7],
                ["充电管理", "电源管理", 0.7]
            ]
        }

        if init_file.exists():
            try:
                with open(init_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载初始知识文件失败: {e}")

        try:
            init_file.parent.mkdir(exist_ok=True)
            with open(init_file, 'w', encoding='utf-8') as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ 已创建初始知识文件: {init_file}")
        except Exception as e:
            logger.warning(f"创建初始知识文件失败: {e}")

        return default_data

    def validate_recommendation(self, user_query: str, recommendation: str,
                               llm_adapter=None) -> Dict:
        """验证推荐是否匹配需求"""
        required_types = self._identify_requirements(user_query)
        recommended_type = self._identify_entity_type(recommendation)

        if not required_types:
            return self._fallback_validation(user_query, recommendation, llm_adapter)

        if not recommended_type:
            return self._fallback_validation(user_query, recommendation, llm_adapter)

        issues = []
        is_valid = False
        confidence = 0.0

        for req in required_types:
            if self._is_compatible(req, recommended_type):
                is_valid = True
                confidence = 0.9
                break

        if not is_valid:
            issues.append(f"需求 '{', '.join(required_types)}' 与推荐 '{recommended_type}' 不匹配")
            confidence = 0.2

        result = {
            'is_valid': is_valid,
            'confidence': confidence,
            'required_types': required_types,
            'recommended_type': recommended_type,
            'issues': issues,
            'recommendation': recommendation
        }

        self._record_validation(user_query, recommendation, is_valid, issues, confidence)
        return result

    def _identify_requirements(self, query: str) -> List[str]:
        """从知识库查询需求类型（纯 Python 匹配，无 SQL 拼接）"""
        categories = []
        try:
            db = DatabaseManager.get(self.db_path)
            rows = db.query("SELECT category, keyword FROM category_mapping")
            for row in rows:
                if row['keyword'] in query:
                    categories.append(row['category'])
        except Exception as e:
            logger.debug(f"需求识别失败: {e}")
        return list(set(categories))

    def _identify_entity_type(self, text: str) -> Optional[str]:
        """从知识库识别实体类型"""
        try:
            db = DatabaseManager.get(self.db_path)
            rows = db.query("SELECT entity_type, pattern, confidence FROM entity_mapping")
            best_type = None
            best_score = 0.0

            for row in rows:
                if row['pattern'] in text:
                    if row['confidence'] > best_score:
                        best_score = row['confidence']
                        best_type = row['entity_type']

            return best_type
        except Exception as e:
            logger.debug(f"实体识别失败: {e}")
            return None

    def _is_compatible(self, type_a: str, type_b: str) -> bool:
        """从知识库查询类型兼容性"""
        if type_a == type_b:
            return True

        try:
            db = DatabaseManager.get(self.db_path)
            row = db.query_one('''
                SELECT confidence FROM type_compatibility
                WHERE (type_a = ? AND type_b = ?)
                   OR (type_a = ? AND type_b = ?)
                ORDER BY confidence DESC
                LIMIT 1
            ''', (type_a, type_b, type_b, type_a))
            if row:
                return row['confidence'] > 0.5
        except Exception as e:
            logger.debug(f"兼容性查询失败: {e}")

        return False

    def _fallback_validation(self, query: str, recommendation: str, llm_adapter) -> Dict:
        """降级验证"""
        result = {
            'is_valid': None,
            'confidence': 0.5,
            'required_types': [],
            'recommended_type': None,
            'issues': ["无法识别需求或推荐类型"],
            'recommendation': recommendation
        }

        if llm_adapter:
            try:
                llm_result = self._llm_validate(query, recommendation, llm_adapter)
                if llm_result:
                    result.update(llm_result)
            except Exception as e:
                logger.debug(f"LLM验证失败: {e}")

        self._record_validation(query, recommendation, result.get('is_valid'), result.get('issues', []), result.get('confidence', 0.5))
        return result

    def _llm_validate(self, query: str, recommendation: str, llm_adapter) -> Dict:
        """使用 LLM 进行验证"""
        try:
            prompt = f"""验证推荐是否正确：

用户需求：{query}

推荐内容：{recommendation}

请判断：
1. 推荐是否满足需求？
2. 是否存在明显错误？

以JSON格式返回：
{{"is_valid": true/false, "confidence": 0.0-1.0, "issues": ["问题"]}}
"""

            response = llm_adapter.generate(prompt, task_type="validation")
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except Exception as e:
            logger.debug(f"LLM验证失败: {e}")

        return {}

    def _record_validation(self, query: str, recommendation: str,
                           is_valid: Optional[bool], issues: List[str],
                           confidence: float):
        """记录验证历史"""
        try:
            query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
            db = DatabaseManager.get(self.db_path)
            db.execute('''
                INSERT INTO validation_history
                (query_hash, recommendation, is_valid, issues, confidence, validated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                query_hash,
                recommendation[:500],
                1 if is_valid else 0 if is_valid is not None else -1,
                json.dumps(issues, ensure_ascii=False),
                confidence,
                datetime.now().isoformat()
            ), commit=True)
        except Exception as e:
            logger.debug(f"记录验证历史失败: {e}")

    def add_category_keyword(self, category: str, keyword: str):
        """添加类别关键词映射"""
        db = DatabaseManager.get(self.db_path)
        db.execute(
            "INSERT OR IGNORE INTO category_mapping (category, keyword, created_at) VALUES (?, ?, ?)",
            (category, keyword, datetime.now().isoformat()),
            commit=True
        )
        logger.info(f"✅ 添加类别映射: {category} <- {keyword}")

    def add_entity_pattern(self, entity_type: str, pattern: str, confidence: float = 0.9):
        """添加实体模式"""
        db = DatabaseManager.get(self.db_path)
        db.execute(
            "INSERT INTO entity_mapping (entity_type, pattern, confidence, created_at) VALUES (?, ?, ?, ?)",
            (entity_type, pattern, confidence, datetime.now().isoformat()),
            commit=True
        )
        logger.info(f"✅ 添加实体模式: {entity_type} <- {pattern}")

    def learn_compatibility(self, type_a: str, type_b: str):
        """学习类型兼容性"""
        db = DatabaseManager.get(self.db_path)
        row = db.query_one(
            "SELECT id, occurrences FROM type_compatibility WHERE type_a = ? AND type_b = ?",
            (type_a, type_b)
        )

        if row:
            db.execute('''
                UPDATE type_compatibility
                SET occurrences = occurrences + 1,
                    confidence = ?,
                    updated_at = ?
                WHERE id = ?
            ''', (min(1.0, (row['occurrences'] + 1) / 10), datetime.now().isoformat(), row['id']))
        else:
            db.execute('''
                INSERT INTO type_compatibility
                (type_a, type_b, confidence, occurrences, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (type_a, type_b, 0.5, 1, datetime.now().isoformat(), datetime.now().isoformat()))

        db.execute("SELECT 1", commit=True)
        logger.info(f"📚 学习类型兼容性: {type_a} ↔ {type_b}")


knowledge_validator = KnowledgeBasedValidator()
