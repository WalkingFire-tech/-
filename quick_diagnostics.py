"""
轻量级系统诊断 - 不使用psutil等重依赖
"""
import sys
import os
import sqlite3
from pathlib import Path
from datetime import datetime
import json

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

issues = []
warnings = []
passed = []

print("\n" + "="*60)
print("系统深度诊断")
print("="*60)

# ========== 1. 数据库完整性 ==========
print("\n【1. 数据库完整性检查】")
db_files = list(Path("data").glob("*.db"))
for db_file in db_files:
    try:
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        
        if result == "ok":
            print(f"  ✓ {db_file.name}: 完整性OK")
            passed.append(f"数据库.{db_file.name}")
        else:
            print(f"  ✗ {db_file.name}: 完整性失败")
            issues.append(f"数据库.{db_file.name}: 完整性失败")
        
        # 检查knowledge表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        if db_file.name == "knowledge_store.db" and "knowledge" not in tables:
            print(f"  ✗ knowledge表不存在")
            issues.append("数据库: knowledge表不存在")
            
            # 创建表
            print(f"  → 创建knowledge表...")
            cursor.execute('''
                CREATE TABLE knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT,
                    source TEXT,
                    type TEXT,
                    quality REAL,
                    created_at TEXT,
                    salience REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    metadata TEXT
                )
            ''')
            conn.commit()
            print(f"  ✓ knowledge表已创建")
            passed.append("数据库: knowledge表已创建")
        
        conn.close()
    except Exception as e:
        print(f"  ✗ {db_file.name}: {e}")
        issues.append(f"数据库.{db_file.name}: {e}")

# ========== 2. 核心模块导入 ==========
print("\n【2. 核心模块导入检查】")
modules = [
    "core.services.planner",
    "core.learning_engine",
    "core.vector_retriever",
    "adapters.llm.ollama_adapter",
]
for module in modules:
    try:
        __import__(module)
        print(f"  ✓ {module}")
        passed.append(f"模块.{module}")
    except Exception as e:
        print(f"  ✗ {module}: {e}")
        issues.append(f"模块.{module}: {e}")

# ========== 3. 异常处理检查 ==========
print("\n【3. 异常处理检查】")
critical_files = [
    "backend/main.py",
    "core/services/planner.py",
]
for file_path in critical_files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        bare_except = content.count("except:")
        if bare_except > 0:
            print(f"  ⚠ {file_path}: {bare_except}个裸except")
            warnings.append(f"异常处理.{file_path}: {bare_except}个裸except")
        else:
            print(f"  ✓ {file_path}: 无裸except")
            passed.append(f"异常处理.{file_path}")
    except Exception as e:
        print(f"  ⚠ 无法检查 {file_path}: {e}")

# ========== 4. 安全检查 ==========
print("\n【4. 安全检查】")
# 检查SQL注入风险
for file_path in Path(".").rglob("*.py"):
    if "test_" in str(file_path) or "__pycache__" in str(file_path):
        continue
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # 检查字符串拼接SQL
        if "execute(" in content and ("f\"" in content or "f'" in content):
            if "SELECT" in content or "INSERT" in content:
                print(f"  ⚠ {file_path}: 可能SQL注入风险")
                warnings.append(f"安全.{file_path}: SQL注入风险")
    except:
        pass

print("  ✓ 安全检查完成")
passed.append("安全检查")

# ========== 5. 配置检查 ==========
print("\n【5. 配置检查】")
config_file = Path("config/settings.yaml")
if config_file.exists():
    try:
        import yaml
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print("  ✓ 配置文件正常")
        passed.append("配置文件")
    except Exception as e:
        print(f"  ✗ 配置解析失败: {e}")
        issues.append(f"配置: {e}")
else:
    print("  ✗ 配置文件不存在")
    issues.append("配置: 文件不存在")

# ========== 6. API端点检查 ==========
print("\n【6. API端点检查】")
try:
    import requests
    
    endpoints = [
        ("/api/health", "健康检查"),
        ("/api/stats", "统计信息"),
        ("/api/models", "模型列表"),
    ]
    
    for endpoint, desc in endpoints:
        try:
            response = requests.get(f"http://localhost:8000{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"  ✓ {endpoint}: {desc}")
                passed.append(f"API.{endpoint}")
            else:
                print(f"  ⚠ {endpoint}: {response.status_code}")
                warnings.append(f"API.{endpoint}: {response.status_code}")
        except Exception as e:
            print(f"  ⚠ {endpoint}: {e}")
            warnings.append(f"API.{endpoint}: {e}")
except ImportError:
    print("  ⚠ requests库未安装")

# ========== 7. 依赖检查 ==========
print("\n【7. 依赖检查】")
required = ["fastapi", "uvicorn", "loguru", "requests", "yaml", "fitz", "numpy"]
for package in required:
    try:
        __import__(package)
        print(f"  ✓ {package}")
        passed.append(f"依赖.{package}")
    except ImportError:
        print(f"  ⚠ {package}: 未安装")
        warnings.append(f"依赖.{package}: 未安装")

# ========== 生成报告 ==========
print("\n" + "="*60)
print("诊断报告")
print("="*60)
print(f"✅ 通过: {len(passed)}")
print(f"⚠️  警告: {len(warnings)}")
print(f"❌ 问题: {len(issues)}")

if issues:
    print("\n【严重问题】")
    for issue in issues:
        print(f"  ✗ {issue}")

if warnings:
    print("\n【警告】")
    for warning in warnings[:10]:
        print(f"  ⚠ {warning}")

# 保存报告
report = {
    "timestamp": datetime.now().isoformat(),
    "summary": {
        "passed": len(passed),
        "warnings": len(warnings),
        "issues": len(issues)
    },
    "issues": issues,
    "warnings": warnings,
    "passed": passed
}

with open("diagnostic_report.json", 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"\n📄 报告已保存: diagnostic_report.json")

if issues:
    print("\n⚠️  发现严重问题，请修复后再使用")
    sys.exit(1)
else:
    print("\n✅ 系统诊断完成：无严重问题")
    sys.exit(0)