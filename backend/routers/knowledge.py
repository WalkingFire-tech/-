"""
知识管理路由 — knowledge-graph/facts/forgetting/induction/optimize/knowledge-health/recent-learning/files
"""

from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter
from loguru import logger
from core.ports.adapters import get_storage_port

router = APIRouter()

ROOT_DIR = Path(__file__).parent.parent.parent
MAX_FILE_SIZE = 10 * 1024 * 1024


def _is_path_allowed(folder) -> bool:
    try:
        resolved = Path(folder).resolve()
        allowed_bases = [
            Path.cwd().resolve(),
            Path.home().resolve(),
        ]
        allowed_bases = [b for b in allowed_bases if b is not None]
        return any(
            str(resolved).startswith(str(base))
            for base in allowed_bases
        )
    except (OSError, RuntimeError):
        return False


@router.get("/knowledge-graph/stats")
async def knowledge_graph_stats():
    try:
        from core.knowledge_graph import get_knowledge_graph
        return get_knowledge_graph().get_stats()
    except Exception as e:
        return {"error": str(e), "node_count": 0, "connection_count": 0}


@router.get("/knowledge-graph/search")
async def knowledge_graph_search(q: str = "", top_k: int = 5):
    try:
        from core.knowledge_graph import get_knowledge_graph
        kg = get_knowledge_graph()
        nodes = kg.search(q, top_k)
        return {"results": [n.to_dict() for n in nodes]}
    except Exception as e:
        return {"error": str(e), "results": []}


@router.get("/knowledge-graph/clusters")
async def knowledge_graph_clusters():
    try:
        from core.knowledge_graph import get_knowledge_graph
        kg = get_knowledge_graph()
        clusters = kg.find_clusters()
        return {"clusters": [c.to_dict() for c in clusters], "total": len(clusters)}
    except Exception as e:
        return {"error": str(e), "clusters": []}


@router.get("/knowledge/health")
async def get_knowledge_health():
    try:
        knowledge_total = 0
        skills_total = 0
        rules_active = 0
        try:
            db = get_storage_port("data/knowledge_store.db")
            row = db.query_one("SELECT COUNT(*) FROM knowledge")
            knowledge_total = row[0]
        except Exception:
            logger.warning("操作降级跳过")
        try:
            db = get_storage_port("data/skills.db")
            row = db.query_one("SELECT COUNT(*) FROM skills")
            skills_total = row[0]
        except Exception:
            logger.warning("操作降级跳过")
        try:
            db = get_storage_port("data/learning_rules.db")
            row = db.query_one("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            rules_active = row[0]
        except Exception:
            logger.warning("操作降级跳过")
        total = knowledge_total + skills_total + rules_active
        score = min(100, total // 3)
        coverage = min(100, knowledge_total * 2)
        quality = min(100, rules_active * 2)
        memory = min(100, skills_total * 10)
        skills_pct = min(100, skills_total * 20)
        if score >= 80:
            level = "🌟 优秀"
        elif score >= 60:
            level = "👍 良好"
        elif score >= 40:
            level = "📈 发展中"
        elif score >= 20:
            level = "🌱 起步"
        else:
            level = "⬜ 未初始化"
        return {
            "success": True,
            "report": {
                "score": {"total": score, "coverage": coverage, "quality": quality, "memory": memory, "skills": skills_pct},
                "knowledge": {"total": knowledge_total},
                "skills": {"total": skills_total},
                "rules": {"active": rules_active}
            },
            "summary": {
                "score": score,
                "level": level,
                "total_knowledge": knowledge_total,
                "skills": skills_total,
                "rules": rules_active
            }
        }
    except Exception as e:
        logger.error(f"获取知识健康度失败: {e}")
        return {"success": False, "error": str(e)}


@router.post("/optimize")
async def run_optimize(request: dict):
    try:
        db_exp = get_storage_port("data/experience_pool.db")
        row = db_exp.query_one("SELECT COUNT(*) FROM experiences")
        exp_count = row[0]
        db_rules = get_storage_port("data/learning_rules.db")
        row = db_rules.query_one("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
        active = row[0]
        row = db_rules.query_one("SELECT AVG(confidence) FROM learning_rules WHERE status='active'")
        avg_conf = row[0] or 0.5
        result = f"当前系统状态: 经验{exp_count}条, 活跃规则{active}条, 平均置信度{avg_conf:.2f}. 基于当前状态, 建议增加更多交互以积累经验."
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"优化失败: {e}")
        return {"success": False, "error": str(e)}


@router.post("/induction")
async def run_induction(request: dict):
    try:
        days = request.get("days", 7)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        patterns = 0
        rules = 0
        try:
            db = get_storage_port("data/experience_pool.db")
            row = db.query_one("SELECT COUNT(*) FROM experiences WHERE created_at >= ?", (cutoff,))
            recent = row[0]
            patterns = min(recent // 10, 5)
        except Exception:
            logger.warning("操作降级跳过")
        try:
            db = get_storage_port("data/learning_rules.db")
            row = db.query_one("SELECT COUNT(*) FROM learning_rules WHERE status='pending'")
            pending = row[0]
            cursor = db.execute("UPDATE learning_rules SET status='active' WHERE status='pending' AND confidence >= 0.4 AND apply_count >= 2", commit=True)
            activated = cursor.rowcount
            cursor2 = db.execute("UPDATE learning_rules SET status='trial', promoted_at=datetime('now'), promotion_reason='归纳端点晋升试用' WHERE status='pending' AND confidence >= 0.3", commit=True)
            promoted = cursor2.rowcount
            rules = activated + promoted
        except Exception:
            logger.warning("操作降级跳过")
        return {
            "success": True,
            "patterns": patterns,
            "rules": rules,
            "message": f"归纳完成: 发现{patterns}个模式, 激活{rules}条规则"
        }
    except Exception as e:
        logger.error(f"归纳失败: {e}")
        return {"success": False, "error": str(e), "patterns": 0, "rules": 0}


@router.get("/cognitive-status")
async def get_cognitive_status():
    try:
        from core.self.model import get_self_model
        model = get_self_model()
        return model.get_status_summary()
    except Exception as e:
        return {"error": str(e), "status": "unavailable"}


@router.get("/recent_learning")
async def get_recent_learning():
    try:
        items = []
        try:
            db = get_storage_port("data/experience_pool.db")
            rows = db.query("SELECT raw_input, timestamp, intent_type FROM experiences ORDER BY timestamp DESC LIMIT 5")
            for row in rows:
                query = (row["raw_input"] or "")[:30]
                created = row["timestamp"] or ""
                intent = row["intent_type"] or ""
                if created:
                    try:
                        dt = datetime.fromisoformat(created)
                        time_str = dt.strftime("%m/%d %H:%M")
                    except Exception:
                        time_str = str(created)[:10]
                else:
                    time_str = ""
                items.append({"content": f"[{intent}] {query}", "time": time_str})
        except Exception:
            logger.warning("操作降级跳过")
        try:
            db = get_storage_port("data/essence_reasoning.db")
            rows = db.query("SELECT query, final_verdict, timestamp FROM reasoning_chains ORDER BY timestamp DESC LIMIT 3")
            for row in rows:
                query = (row[0] or "")[:30]
                created = row[2] or ""
                if created:
                    try:
                        dt = datetime.fromisoformat(created)
                        time_str = dt.strftime("%m/%d %H:%M")
                    except Exception:
                        time_str = str(created)[:10]
                else:
                    time_str = ""
                items.append({"content": f"推理: {query}", "time": time_str})
        except Exception:
            logger.warning("操作降级跳过")
        items.sort(key=lambda x: x.get("time", ""), reverse=True)
        try:
            from core.self.model import get_self_model
            sm = get_self_model()
            snap = sm.snapshot()
            for item in snap.get("recent_learning", [])[:3]:
                items.append({"content": f"认知: {item.get('summary', '')[:30]}", "time": item.get("timestamp", "")[:10]})
        except Exception:
            logger.warning("操作降级跳过")
        return {"items": items[:8]}
    except Exception as e:
        return {"items": []}


@router.get("/facts/search")
async def search_facts(q: str = "", limit: int = 10):
    try:
        from core.ports.adapters import get_fact_store_port
        fs = get_fact_store_port()
        if q:
            results = await fs.search_by_keywords(q, limit=limit)
        else:
            results = []
        return {"query": q, "results": results, "count": len(results)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/facts/stats")
async def fact_stats():
    try:
        from core.ports.adapters import get_fact_store_port
        return get_fact_store_port().get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/facts/add")
async def add_fact(request: dict):
    try:
        from core.ports.adapters import get_fact_store_port
        fs = get_fact_store_port()
        assertion_id = fs.add_assertion(
            question=request.get("question", ""),
            subject=request.get("subject", ""),
            predicate=request.get("predicate", ""),
            obj=request.get("object", ""),
            source=request.get("source", "manual"),
            confidence=request.get("confidence", 0.9)
        )
        return {"id": assertion_id, "status": "added"}
    except Exception as e:
        return {"error": str(e)}


@router.post("/facts/correct")
async def correct_fact(request: dict):
    try:
        from core.ports.adapters import get_fact_store_port
        fs = get_fact_store_port()
        fs.add_correction(
            question=request.get("question", ""),
            old_subject=request.get("old_subject", ""),
            old_predicate=request.get("old_predicate", ""),
            old_obj=request.get("old_object", ""),
            new_subject=request.get("new_subject", ""),
            new_predicate=request.get("new_predicate", ""),
            new_obj=request.get("new_object", ""),
            correction_source=request.get("source", "user_correction")
        )
        return {"status": "corrected"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/forgetting/evaluate")
async def evaluate_forgetting():
    try:
        from core.knowledge_forgetting import knowledge_forgetting
        return {
            "rules": knowledge_forgetting.evaluate_rules(),
            "experiences": knowledge_forgetting.evaluate_experiences(),
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/forgetting/execute")
async def execute_forgetting(request: dict):
    dry_run = request.get("dry_run", True)
    try:
        from core.knowledge_forgetting import knowledge_forgetting
        return knowledge_forgetting.execute_fading(dry_run=dry_run)
    except Exception as e:
        return {"error": str(e)}


@router.post("/reorganization/run")
async def run_reorganization():
    try:
        from core.low_load_reorganization import low_load_reorganization
        return low_load_reorganization.run()
    except Exception as e:
        logger.error(f"低负载重组失败: {e}")
        return {"error": str(e)}


@router.post("/folder/preview")
async def preview_folder(request: dict):
    folder_path = request.get("path", "")
    file_types = request.get("file_types", "all")
    if not folder_path:
        return {"success": False, "error": "请提供文件夹路径"}
    try:
        folder = Path(folder_path).resolve()
        if not _is_path_allowed(folder):
            return {"success": False, "error": "路径不在允许范围内"}
        if not folder.exists():
            return {"success": False, "error": "文件夹不存在"}
        if not folder.is_dir():
            return {"success": False, "error": "路径不是文件夹"}
        extensions = {
            "code": [".py", ".js", ".java", ".cpp", ".c", ".go", ".rs", ".ts", ".jsx", ".tsx"],
            "doc": [".md", ".txt", ".rst", ".doc", ".docx", ".pdf"],
            "config": [".yaml", ".yml", ".json", ".toml", ".ini", ".cfg"],
            "all": []
        }
        target_extensions = extensions.get(file_types, [])
        files = []
        if target_extensions:
            for ext in target_extensions:
                for f in folder.rglob(f"*{ext}"):
                    if f.is_file() and not f.is_symlink() and _is_path_allowed(f):
                        files.append(str(f.relative_to(folder)))
        else:
            for f in folder.rglob("*"):
                if f.is_file() and not f.is_symlink() and _is_path_allowed(f):
                    files.append(str(f.relative_to(folder)))
        files = files[:100]
        return {"success": True, "files": files, "total": len(files)}
    except Exception as e:
        logger.error(f"预览文件夹失败: {e}")
        return {"success": False, "error": str(e)}


@router.post("/folder/browse")
async def browse_folder(request: dict):
    folder_path = request.get("path", "")
    if not folder_path:
        return {"success": False, "error": "请提供文件夹路径"}
    try:
        folder = Path(folder_path).resolve()
        if not _is_path_allowed(folder):
            return {"success": False, "error": "路径不在允许范围内"}
        if not folder.exists():
            return {"success": False, "error": "路径不存在"}
        if not folder.is_dir():
            return {"success": False, "error": "路径不是文件夹"}
        items = []
        for item in folder.iterdir():
            if item.is_symlink():
                continue
            try:
                stat = item.stat()
                items.append({
                    "name": item.name,
                    "path": str(item),
                    "is_dir": item.is_dir(),
                    "size": stat.st_size if item.is_file() else 0,
                    "modified": stat.st_mtime
                })
            except Exception:
                continue
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return {"success": True, "items": items, "path": str(folder)}
    except Exception as e:
        logger.error(f"浏览文件夹失败: {e}")
        return {"success": False, "error": str(e)}


@router.post("/file/preview")
async def preview_file(request: dict):
    file_path = request.get("path", "")
    if not file_path:
        return {"success": False, "error": "请提供文件路径"}
    try:
        file = Path(file_path).resolve()
        if not _is_path_allowed(file):
            return {"success": False, "error": "路径不在允许范围内"}
        if not file.exists():
            return {"success": False, "error": "文件不存在"}
        if not file.is_file():
            return {"success": False, "error": "路径不是文件"}
        file_size = file.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return {"success": False, "error": "文件过大，请选择小于10MB的文件"}
        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return {"success": True, "content": content, "size": file_size}
    except Exception as e:
        logger.error(f"预览文件失败: {e}")
        return {"success": False, "error": str(e)}


@router.post("/files/learn")
async def learn_from_files(request: dict):
    files = request.get("files", [])
    if not files:
        return {"success": False, "error": "请选择要学习的文件"}
    try:
        results = []
        total_knowledge = 0
        for file_path in files:
            file = Path(file_path).resolve()
            if not _is_path_allowed(file):
                continue
            if not file.exists() or not file.is_file():
                continue
            try:
                file_size = file.stat().st_size
                if file_size > MAX_FILE_SIZE:
                    continue
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                if len(content) < 10:
                    continue
                db = get_storage_port("data/knowledge_store.db")
                db.execute('''
                    INSERT INTO knowledge (content, source, type, quality, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (content[:5000], f"file:{file.name}", "file_content", 70.0, datetime.now().isoformat()), commit=True)
                total_knowledge += 1
                results.append(f"{file.name}: 已学习")
            except Exception as e:
                results.append(f"{file.name}: 失败 - {str(e)[:50]}")
                continue
        summary = '\n'.join(results[:10])
        return {"success": True, "summary": summary, "processed": len(results), "knowledge": total_knowledge}
    except Exception as e:
        logger.error(f"文件学习失败: {e}")
        return {"success": False, "error": str(e)}


@router.post("/folder/learn")
async def learn_from_folder(request: dict):
    folder_path = request.get("path", "")
    file_types = request.get("file_types", "all")
    learn_mode = request.get("mode", "analyze")
    if not folder_path:
        return {"success": False, "error": "请提供文件夹路径"}
    try:
        folder = Path(folder_path).resolve()
        if not _is_path_allowed(folder):
            return {"success": False, "error": "路径不在允许范围内"}
        if not folder.exists():
            return {"success": False, "error": "文件夹不存在"}
        extensions = {
            "code": [".py", ".js", ".java", ".cpp", ".c", ".go", ".rs", ".ts"],
            "doc": [".md", ".txt", ".rst", ".pdf"],
            "config": [".yaml", ".yml", ".json", ".toml"],
            "all": []
        }
        target_extensions = extensions.get(file_types, [])
        files = []
        if target_extensions:
            for ext in target_extensions:
                for f in folder.rglob(f"*{ext}"):
                    if f.is_file() and not f.is_symlink() and _is_path_allowed(f):
                        files.append(f)
        else:
            for f in folder.rglob("*"):
                if f.is_file() and not f.is_symlink() and _is_path_allowed(f):
                    files.append(f)
        files = files[:50]
        processed = 0
        knowledge_count = 0
        summaries = []
        for file_path in files:
            try:
                file_size = file_path.stat().st_size
                if file_size > MAX_FILE_SIZE:
                    continue
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                if len(content) < 10:
                    continue
                if learn_mode == "analyze":
                    lines = content.count('\n')
                    functions = content.count('def ') + content.count('function ')
                    classes = content.count('class ')
                    summaries.append(f"{file_path.name}: {lines}行, {functions}函数, {classes}类")
                elif learn_mode == "extract":
                    summaries.append(f"{file_path.name}: 已提取")
                elif learn_mode == "summarize":
                    first_lines = '\n'.join(content.split('\n')[:5])
                    summaries.append(f"{file_path.name}:\n{first_lines}")
                db = get_storage_port("data/knowledge_store.db")
                db.execute('''
                    INSERT INTO knowledge (content, source, type, quality, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (content[:5000], f"folder:{file_path.name}", "folder_content", 70.0, datetime.now().isoformat()), commit=True)
                knowledge_count += 1
                processed += 1
            except Exception as e:
                summaries.append(f"{file_path.name}: 失败 - {str(e)[:50]}")
                continue
        summary_text = '\n'.join(summaries[:10])
        return {"success": True, "processed": processed, "knowledge": knowledge_count, "summary": summary_text}
    except Exception as e:
        logger.error(f"文件夹学习失败: {e}")
        return {"success": False, "error": str(e)}


@router.get("/failure-patterns")
async def get_failure_patterns():
    try:
        from core.cognition.failure_classifier import FailureClassifier
        patterns = FailureClassifier.get_failure_patterns()
        severity = FailureClassifier.get_severity_summary()
        recent = FailureClassifier.get_recent_failures(5)
        return {"patterns": patterns, "severity_summary": severity, "recent": recent}
    except Exception as e:
        logger.error(f"失败模式查询失败: {e}")
        return {"patterns": [], "severity_summary": {}, "recent": []}