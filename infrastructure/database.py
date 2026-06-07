"""
数据库初始化 - 创建所有必需的表
"""
import sqlite3
from pathlib import Path
from loguru import logger


def init_learning_rules_db(db_path: str = "learning_rules.db"):
    """初始化学习规则数据库"""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(db_path) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS learning_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                condition TEXT NOT NULL,
                action TEXT NOT NULL,
                priority INTEGER DEFAULT 3,
                confidence REAL DEFAULT 0.5,
                status TEXT DEFAULT 'pending',
                source TEXT,
                created_at TEXT,
                last_applied TEXT,
                apply_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                metadata TEXT
            )
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_learning_rules_status 
            ON learning_rules(status)
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_learning_rules_condition 
            ON learning_rules(condition)
        ''')
        
        conn.commit()
    
    logger.info(f"学习规则数据库初始化完成: {db_path}")


def init_all_databases():
    """初始化所有数据库"""
    init_learning_rules_db()
    
    try:
        from infrastructure.experience_pool import ExperiencePool
        pool = ExperiencePool()
        logger.info("经验池数据库初始化完成")
    except Exception as e:
        logger.warning(f"经验池初始化失败: {e}")
    
    try:
        from infrastructure.model_stats import ModelStats
        stats = ModelStats()
        logger.info("统计库数据库初始化完成")
    except Exception as e:
        logger.warning(f"统计库初始化失败: {e}")
    
    logger.info("所有数据库初始化完成")


if __name__ == "__main__":
    init_all_databases()