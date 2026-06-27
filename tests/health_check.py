#!/usr/bin/env python3
"""
联盟拓荒者 - 全组件健康检查脚本
用法: python health_check.py
"""

import os
import sys
import json
import sqlite3
import socket
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple

# 尝试导入请求库（用于网络探测）
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

# ==================== 配置区域 ====================
OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
PROJECT_ROOT = Path(__file__).parent.absolute()
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
DB_PATH = DATA_DIR / "knowledge_store.db"

# 核心依赖列表
CORE_DEPENDENCIES = [
    "fastapi", "uvicorn", "pydantic",
    "sqlalchemy", "aiofiles"
]

OPTIONAL_DEPENDENCIES = {
    "chromadb": "向量检索（缺失会降级为内存检索）",
    "numexpr": "数学计算加速（缺失会降级为eval）",
    "ddgs": "DuckDuckGo搜索（缺失则无法网络搜索）",
    "pypdf": "PDF解析",
    "python-docx": "Word解析",
    "fitz": "高级PDF渲染",
}

# ==================== 颜色输出 ====================
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def ok(msg): return f"{Colors.GREEN}✅ {msg}{Colors.END}"
def fail(msg): return f"{Colors.RED}❌ {msg}{Colors.END}"
def warn(msg): return f"{Colors.YELLOW}⚠️  {msg}{Colors.END}"
def info(msg): return f"{Colors.BLUE}🔍 {msg}{Colors.END}"
def title(msg): return f"\n{Colors.BOLD}=== {msg} ==={Colors.END}"

# ==================== 核心检查器 ====================

def check_ollama() -> Dict[str, Any]:
    """检查 Ollama 服务状态和可用模型"""
    result = {"status": "unknown", "models": [], "message": ""}
    if not REQUESTS_AVAILABLE:
        result["status"] = "skipped"
        result["message"] = "requests库未安装，跳过Ollama检查"
        return result
    
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            result["status"] = "healthy" if models else "warning"
            result["models"] = models
            result["message"] = f"发现 {len(models)} 个模型: {', '.join(models[:5])}"
        else:
            result["status"] = "unhealthy"
            result["message"] = f"Ollama服务响应异常，HTTP {resp.status_code}"
    except requests.exceptions.ConnectionError:
        result["status"] = "dead"
        result["message"] = "无法连接到Ollama服务，请确保已启动 (ollama serve)"
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)
    return result

def check_network() -> Dict[str, Any]:
    """检查网络连通性（外网/搜索引擎）"""
    result = {"status": "unknown", "internet": False, "dns": False, "message": ""}
    try:
        socket.gethostbyname("www.baidu.com")
        result["dns"] = True
    except:
        pass
    
    if not REQUESTS_AVAILABLE:
        result["status"] = "skipped"
        result["message"] = "requests库未安装，跳过网络检查"
        return result
    
    try:
        r = requests.get("https://www.bing.com", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            result["internet"] = True
            result["status"] = "healthy"
            result["message"] = "外网连通，搜索引擎可访问"
        else:
            result["internet"] = False
            result["status"] = "warning"
            result["message"] = f"Bing返回 {r.status_code}，搜索可能受限"
    except requests.exceptions.Timeout:
        result["status"] = "warning"
        result["message"] = "外网访问超时（可能需代理）"
    except Exception as e:
        result["status"] = "error"
        result["message"] = str(e)
    
    if not result["internet"] and result["dns"]:
        result["message"] += " (DNS解析正常，但HTTP不通)"
    return result

def check_database() -> Dict[str, Any]:
    """检查 SQLite 数据库和表结构"""
    result = {"status": "unknown", "tables": [], "message": ""}
    db_file = DB_PATH
    
    if not db_file.parent.exists():
        db_file.parent.mkdir(parents=True, exist_ok=True)
    
    if not db_file.exists():
        result["status"] = "missing"
        result["message"] = f"数据库文件不存在: {db_file} (系统将自动创建)"
        return result
    
    try:
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        result["tables"] = tables
        
        if "knowledge_items" in tables:
            result["status"] = "healthy"
            result["message"] = f"数据库存在，包含 {len(tables)} 个表，关键表 'knowledge_items' 正常"
        else:
            result["status"] = "warning"
            result["message"] = f"数据库存在，但缺少 'knowledge_items' 表 (现有表: {', '.join(tables[:5])})"
        conn.close()
    except Exception as e:
        result["status"] = "error"
        result["message"] = f"数据库读取失败: {e}"
    return result

def check_dependencies() -> Dict[str, Any]:
    """检查 Python 依赖包"""
    result = {
        "status": "healthy",
        "installed_core": [],
        "missing_core": [],
        "optional_status": {},
        "message": ""
    }
    
    for pkg in CORE_DEPENDENCIES:
        spec = importlib.util.find_spec(pkg)
        if spec:
            result["installed_core"].append(pkg)
        else:
            result["missing_core"].append(pkg)
    
    for pkg, desc in OPTIONAL_DEPENDENCIES.items():
        spec = importlib.util.find_spec(pkg.replace("-", "_"))
        if spec:
            result["optional_status"][pkg] = {"installed": True, "desc": desc}
        else:
            result["optional_status"][pkg] = {"installed": False, "desc": desc}
    
    if result["missing_core"]:
        result["status"] = "critical"
        result["message"] = f"缺少核心依赖: {', '.join(result['missing_core'])}"
    else:
        result["message"] = f"核心依赖完整 ({len(result['installed_core'])} 个)"
    
    return result

def check_directories() -> Dict[str, Any]:
    """检查关键目录权限"""
    result = {"status": "healthy", "writable": [], "missing": [], "message": ""}
    dirs_to_check = [
        (DATA_DIR, "数据目录"),
        (LOGS_DIR, "日志目录"),
        (CONFIG_DIR, "配置目录"),
    ]
    
    for path, name in dirs_to_check:
        if not path.exists():
            result["missing"].append(name)
            try:
                path.mkdir(parents=True, exist_ok=True)
                result["writable"].append(name)
            except:
                pass
            continue
        
        test_file = path / ".write_test"
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            test_file.unlink()
            result["writable"].append(name)
        except:
            result["status"] = "warning"
            result["message"] += f"{name}不可写; "
    
    if not result["message"]:
        result["message"] = f"所有目录可写 ({len(result['writable'])} 个)"
    return result

def check_environment() -> Dict[str, Any]:
    """检查关键环境变量"""
    result = {"status": "healthy", "variables": {}, "message": ""}
    keys_to_check = [
        "DEEPSEEK_API_KEY",
        "OPENAI_API_KEY",
        "OLLAMA_HOST",
        "PYTHONPATH"
    ]
    
    for key in keys_to_check:
        value = os.getenv(key)
        if value:
            if "KEY" in key or "SECRET" in key:
                display = value[:4] + "****" + value[-4:] if len(value) > 8 else "****"
            else:
                display = value
            result["variables"][key] = {"set": True, "value": display}
        else:
            result["variables"][key] = {"set": False}
    
    if not result["variables"].get("DEEPSEEK_API_KEY", {}).get("set", False):
        result["status"] = "warning"
        result["message"] = "DEEPSEEK_API_KEY 未设置（远程外脑将不可用）"
    else:
        result["message"] = "关键环境变量已配置"
    
    return result

def check_config_files() -> Dict[str, Any]:
    """检查核心配置文件是否存在且可读"""
    result = {"status": "healthy", "files": [], "missing": [], "message": ""}
    config_files = [
        CONFIG_DIR / "learning_targets.yaml",
        CONFIG_DIR / "settings.yaml",
    ]
    
    for f in config_files:
        if f.exists():
            result["files"].append(f.name)
        else:
            result["missing"].append(f.name)
    
    if result["missing"]:
        result["status"] = "warning"
        result["message"] = f"缺失配置文件: {', '.join(result['missing'])} (系统会使用默认值)"
    else:
        result["message"] = "所有配置文件存在"
    return result

# ==================== 主报告引擎 ====================

def run_full_health_check() -> Dict[str, Any]:
    """执行所有检查并生成综合报告"""
    print(title("🏥 联盟拓荒者 - 全组件健康诊断"))
    print(f"📅 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 项目根目录: {PROJECT_ROOT}")
    print(f"🐍 Python版本: {sys.version.split()[0]}")
    print("-" * 50)
    
    results = {}
    
    # 1. 环境变量
    print(info("检查环境变量..."))
    results["environment"] = check_environment()
    print(f"  → {results['environment']['message']}")
    
    # 2. 依赖包
    print(info("检查Python依赖..."))
    results["dependencies"] = check_dependencies()
    if results["dependencies"]["status"] == "healthy":
        print(f"  → {ok(results['dependencies']['message'])}")
    else:
        print(f"  → {fail(results['dependencies']['message'])}")
    for pkg, stat in results["dependencies"]["optional_status"].items():
        if stat["installed"]:
            print(f"     {ok(pkg + ': ' + stat['desc'])}")
        else:
            print(f"     {warn(pkg + ': ' + stat['desc'])}")
    
    # 3. 目录权限
    print(info("检查目录权限..."))
    results["directories"] = check_directories()
    print(f"  → {ok(results['directories']['message'])}")
    
    # 4. 配置文件
    print(info("检查配置文件..."))
    results["config_files"] = check_config_files()
    msg = results['config_files']['message']
    if results['config_files']['status'] == 'healthy':
        print(f"  → {ok(msg)}")
    else:
        print(f"  → {warn(msg)}")
    
    # 5. Ollama 服务
    print(info("检查Ollama服务..."))
    results["ollama"] = check_ollama()
    if results["ollama"]["status"] == "healthy":
        print(f"  → {ok(results['ollama']['message'])}")
        if results["ollama"]["models"]:
            print(f"     📋 模型列表: {', '.join(results['ollama']['models'])}")
    elif results["ollama"]["status"] == "warning":
        print(f"  → {warn(results['ollama']['message'])}")
    elif results["ollama"]["status"] == "dead":
        print(f"  → {fail('Ollama未启动! 请运行: ollama serve')}")
    else:
        print(f"  → {fail(results['ollama']['message'])}")
    
    # 6. 网络连通性
    print(info("检查网络/搜索引擎..."))
    results["network"] = check_network()
    if results["network"]["status"] == "healthy":
        print(f"  → {ok(results['network']['message'])}")
    else:
        print(f"  → {warn(results['network']['message'])} (外部搜索将不可用)")
    
    # 7. 数据库
    print(info("检查知识库数据库..."))
    results["database"] = check_database()
    if results["database"]["status"] == "healthy":
        print(f"  → {ok(results['database']['message'])}")
    elif results["database"]["status"] == "missing":
        print(f"  → {warn(results['database']['message'])} (首次启动会自动创建)")
    else:
        print(f"  → {fail(results['database']['message'])}")
    
    # ==================== 综合评分 ====================
    print(title("📊 综合评估"))
    
    critical_failures = []
    warnings = []
    
    if results["ollama"]["status"] in ["dead", "unhealthy"]:
        critical_failures.append("Ollama服务不可用 (所有本地推理将失败)")
    if results["dependencies"]["status"] == "critical":
        critical_failures.append(f"缺少核心依赖: {', '.join(results['dependencies']['missing_core'])}")
    if results["network"]["status"] == "error":
        critical_failures.append("网络严重异常")
    
    if results["environment"]["status"] == "warning":
        warnings.append("远程API Key未配置 (外脑协作降级)")
    if results["database"]["status"] in ["warning", "missing"]:
        warnings.append("数据库表缺失 (知识持久化降级)")
    if not results["network"]["internet"] and results["network"]["status"] != "skipped":
        warnings.append("外网不通 (实时搜索不可用)")
    
    missing_opt = [pkg for pkg, stat in results["dependencies"]["optional_status"].items() if not stat["installed"]]
    if missing_opt:
        warnings.append(f"可选依赖缺失: {', '.join(missing_opt[:3])} (部分功能降级)")
    
    print(f"🔴 致命问题: {len(critical_failures)} 项")
    for item in critical_failures:
        print(f"   {fail(item)}")
    
    print(f"🟡 警告/降级: {len(warnings)} 项")
    for item in warnings:
        print(f"   {warn(item)}")
    
    if critical_failures:
        overall_status = "CRITICAL (系统无法正常运行)"
        status_color = Colors.RED
    elif warnings:
        overall_status = "DEGRADED (系统降级运行，核心功能可用)"
        status_color = Colors.YELLOW
    else:
        overall_status = "HEALTHY (所有组件正常运行)"
        status_color = Colors.GREEN
    
    print(f"\n{Colors.BOLD}🏁 最终状态: {status_color}{overall_status}{Colors.END}")
    print("=" * 50)
    
    if critical_failures:
        print("\n💡 紧急修复建议:")
        if "Ollama" in str(critical_failures):
            print("  1. 启动Ollama服务: ollama serve")
            print("  2. 拉取模型: ollama pull qwen2.5-coder:7b")
        if "核心依赖" in str(critical_failures):
            print("  3. 安装缺失依赖: pip install " + " ".join(results["dependencies"]["missing_core"]))
    elif warnings and "远程API" in str(warnings):
        print("\n💡 可选优化: 设置 DEEPSEEK_API_KEY 环境变量以启用外脑协作模式")
    
    return results

# ==================== 入口 ====================
if __name__ == "__main__":
    try:
        run_full_health_check()
    except KeyboardInterrupt:
        print("\n⏹️  检查已中断")
    except Exception as e:
        print(f"\n{Colors.RED}❌ 脚本执行异常: {e}{Colors.END}")
        import traceback
        traceback.print_exc()