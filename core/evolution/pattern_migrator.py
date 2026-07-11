import re
from typing import Dict, List, Optional
from collections import defaultdict
from loguru import logger
from infrastructure.database_manager import DatabaseManager


class PatternMigrator:
    """
    认知模式迁移器——举一反三。
    学会"串口N"→"COMN"后，能迁移到"ttyUSB0"等新场景。
    持久化到数据库，重启不丢失。
    """

    @classmethod
    def _ensure_table(cls):
        db = DatabaseManager.get("data/pattern_migrations.db")
        db.execute('''CREATE TABLE IF NOT EXISTS learned_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias_prefix TEXT, standard_prefix TEXT, source TEXT,
            hit_count INTEGER DEFAULT 0, created_at TEXT
        )''', commit=True)

    @classmethod
    def learn_from_correction(cls, user_prefix: str, corrected_entity: str, source: str = "audit"):
        cls._ensure_table()
        standard_pre = re.sub(r'\d+$', '', corrected_entity)
        if not standard_pre or not user_prefix:
            return
        db = DatabaseManager.get("data/pattern_migrations.db")
        existing = db.query_one(
            'SELECT id FROM learned_patterns WHERE alias_prefix=? AND standard_prefix=?',
            (user_prefix, standard_pre)
        )
        if existing:
            db.execute(
                'UPDATE learned_patterns SET hit_count=hit_count+1 WHERE alias_prefix=? AND standard_prefix=?',
                (user_prefix, standard_pre), commit=True
            )
        else:
            from datetime import datetime
            db.execute(
                'INSERT INTO learned_patterns (alias_prefix, standard_prefix, source, hit_count, created_at) VALUES (?, ?, ?, 1, ?)',
                (user_prefix, standard_pre, source, datetime.now().isoformat()), commit=True
            )
            logger.info(f"🧬 认知进化: 学习到新映射 '{user_prefix}N' → '{standard_pre}N'")

    @classmethod
    def apply_migration(cls, user_input: str) -> str:
        cls._ensure_table()
        db = DatabaseManager.get("data/pattern_migrations.db")
        rows = db.query(
            'SELECT alias_prefix, standard_prefix FROM learned_patterns ORDER BY hit_count DESC'
        )
        for row in rows:
            alias_pre, standard_pre = row[0], row[1]
            pattern = rf'{re.escape(alias_pre)}(\d+)'
            if re.search(pattern, user_input):
                normalized = re.sub(pattern, rf'{standard_pre}\1', user_input)
                db.execute(
                    'UPDATE learned_patterns SET hit_count=hit_count+1 WHERE alias_prefix=? AND standard_prefix=?',
                    (alias_pre, standard_pre), commit=True
                )
                return normalized
        return user_input

    @classmethod
    def bootstrap(cls):
        base_mappings = {
            "串口": "COM", "com口": "COM", "ttyUSB": "COM",
            "ttyACM": "COM", "ttyS": "COM",
        }
        cls._ensure_table()
        db = DatabaseManager.get("data/pattern_migrations.db")
        for alias, standard in base_mappings.items():
            existing = db.query_one(
                'SELECT id FROM learned_patterns WHERE alias_prefix=? AND standard_prefix=?',
                (alias, standard)
            )
            if not existing:
                from datetime import datetime
                db.execute(
                    'INSERT INTO learned_patterns (alias_prefix, standard_prefix, source, hit_count, created_at) VALUES (?, ?, ?, 0, ?)',
                    (alias, standard, "bootstrap", datetime.now().isoformat()), commit=True
                )
        logger.info("✅ 认知引导: 已加载基础物理实体映射(串口→COM等)")