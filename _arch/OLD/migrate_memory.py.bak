"""
数据库迁移 - 添加情感权重和环境关联
"""
from pathlib import Path
from infrastructure.database_manager import DatabaseManager
from loguru import logger

def migrate_database(db_path: str = "data/knowledge_store.db"):
    """迁移数据库，添加情感权重和环境关联字段"""
    
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    db = DatabaseManager.get(db_path)
    columns = [row[1] for row in db.query("PRAGMA table_info(knowledge_items)")]
    
    migrations = []
    
    if 'emotional_valence' not in columns:
        migrations.append('ALTER TABLE knowledge_items ADD COLUMN emotional_valence REAL DEFAULT 0.0')
    
    if 'environmental_triggers' not in columns:
        migrations.append('ALTER TABLE knowledge_items ADD COLUMN environmental_triggers TEXT')
    
    if 'salience' not in columns:
        migrations.append('ALTER TABLE knowledge_items ADD COLUMN salience REAL DEFAULT 0.5')
    
    if 'memory_layer' not in columns:
        migrations.append('ALTER TABLE knowledge_items ADD COLUMN memory_layer INTEGER DEFAULT 2')
    
    if 'context_snapshot' not in columns:
        migrations.append('ALTER TABLE knowledge_items ADD COLUMN context_snapshot TEXT')
    
    for migration in migrations:
        try:
            db.execute(migration, commit=True)
            logger.info(f"执行迁移: {migration}")
        except Exception as e:
            logger.warning(f"迁移失败（可能已存在）: {e}")
    
    try:
        db.executescript('''
            CREATE INDEX IF NOT EXISTS idx_salience ON knowledge_items(salience);
            CREATE INDEX IF NOT EXISTS idx_layer ON knowledge_items(memory_layer);
            CREATE INDEX IF NOT EXISTS idx_emotion ON knowledge_items(emotional_valence)
        ''')
    except Exception:
        logger.warning("操作降级跳过")
    
    logger.info("数据库迁移完成")

if __name__ == "__main__":
    migrate_database()
    print("✅ 数据库迁移完成")