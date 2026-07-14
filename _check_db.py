from infrastructure.database_manager import DatabaseManager
db = DatabaseManager.get("data/knowledge_items.db")
tables = db.query("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", [dict(r) for r in tables])