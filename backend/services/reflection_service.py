import time
from loguru import logger
from infrastructure.database_manager import DatabaseManager


def reflect_and_learn(query: str, response: str, attempts: list, start_time: float, comparison: list) -> str:
    elapsed = time.time() - start_time
    successful = [a for a in attempts if a[1]]
    failed = [a for a in attempts if not a[1]]
    lessons = []

    if successful:
        lessons.append(f"成功: {', '.join([a[0] for a in successful])}")
    if failed:
        lessons.append(f"失败: {', '.join([a[0] for a in failed])}")
    if elapsed > 30:
        lessons.append("响应较慢，需优化路径")
    if len(successful) == 1 and successful[0][0] == "规则推理":
        lessons.append("仅靠规则匹配，知识储备不足")
    if comparison and len(comparison) > 1:
        best_src = comparison[0]["source"]
        best_score = comparison[0]["score"]
        lessons.append(f"最优来源={best_src}(评分{best_score:.0f})，共{len(comparison)}路对比")

    try:
        from datetime import datetime
        db = DatabaseManager.get("data/spirit_lessons.db")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT, response TEXT, attempts TEXT,
                lessons TEXT, elapsed REAL, timestamp TEXT
            )
        """)
        db.execute(
            "INSERT INTO reflections (query, response, attempts, lessons, elapsed, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (query[:200], response[:200], str([(a[0], a[1]) for a in attempts]), "; ".join(lessons), elapsed, datetime.now().isoformat()),
            commit=True
        )
    except Exception:
        logger.warning("操作降级跳过")

    if successful:
        try:
            from datetime import datetime as dt
            success_path = [a[0] for a in successful]
            pattern_type = "unknown"
            if any("代码" in a[0].lower() or "编程" in a[0].lower() for a in successful):
                pattern_type = "code_generation"
            elif any("本质" in a[0] for a in successful):
                pattern_type = "essence_reasoning"
            elif any("多源" in a[0] for a in successful):
                pattern_type = "multi_source_verify"
            elif any("规则" in a[0] for a in successful):
                pattern_type = "rule_based"

            if pattern_type != "unknown":
                db = DatabaseManager.get("data/experience_pool.db")
                db.execute(
                    "INSERT INTO experiences (raw_input, response, timestamp, intent_type, quality_score, success, duration) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (f"[模式]{pattern_type}:{query[:50]}", f"解决路径:{'→'.join(success_path)}", dt.now().isoformat(), f"pattern_{pattern_type}", 85, 1, 0.0),
                    commit=True
                )
        except Exception:
            logger.warning("操作降级跳过")

        try:
            from core.skill_emergence import skill_emergence
            skill_name = skill_emergence.analyze_and_learn(query, attempts, response, elapsed)
            if skill_name:
                lessons.append(f"✨ 技能涌现: {skill_name}")
        except Exception:
            logger.warning("操作降级跳过")

        try:
            from core.truth_accumulator import truth_accumulator
            truth_name = truth_accumulator.accumulate(query, attempts, response)
            if truth_name:
                lessons.append(f"💎 真谛沉淀: {truth_name}")
        except Exception:
            logger.warning("操作降级跳过")

    return "; ".join(lessons) if lessons else "交互正常"


def try_solidify_to_gene_pool(query: str, response: str, attempts: list, comparison: list) -> str:
    if not response or len(response) < 100:
        return ""

    ollama_sources = [a for a in attempts if a[0].startswith("Ollama") and a[1]]
    if not ollama_sources:
        return ""

    best_score = 0
    if comparison:
        best_score = comparison[0].get("score", 0)
    if best_score < 80:
        return ""

    try:
        db = DatabaseManager.get("data/experience_pool.db")
        row = db.query_one("SELECT COUNT(*) FROM experiences WHERE raw_input LIKE ? AND quality_score >= 80", (f"%{query[:20]}%",))
        count = row[0] if row else 0
    except Exception:
        count = 0

    should_solidify = (count >= 1) or (best_score >= 100)

    if not should_solidify:
        return ""

    solidified = []

    try:
        from datetime import datetime
        db = DatabaseManager.get("data/knowledge_store.db")
        db.execute(
            "INSERT INTO knowledge (content, source, type, quality, created_at) VALUES (?, ?, ?, ?, ?)",
            (response, "gene_pool_solidification", "solidified", int(best_score), datetime.now().isoformat()),
            commit=True
        )
        solidified.append("知识库")
    except Exception as e:
        logger.error(f"基因库固化-知识库写入失败: {e}")

    try:
        db = DatabaseManager.get("data/experience_pool.db")
        db.execute(
            "UPDATE experiences SET quality_score = ? WHERE raw_input LIKE ? AND quality_score < ?",
            (95, f"%{query[:20]}%", 95),
            commit=True
        )
        solidified.append("经验池升级")
    except Exception as e:
        logger.error(f"基因库固化-经验池升级失败: {e}")

    try:
        from core.delta_knowledge_updater import delta_knowledge_updater
        new_knowledge = {"response": response[:2000], "score": best_score, "source": "gene_pool_solidification"}
        delta_result = delta_knowledge_updater.update(new_knowledge, topic=query[:100])
        if delta_result.get("updated"):
            solidified.append(f"增量知识(v{delta_result['version']}, 压缩{delta_result['compression_ratio']:.2f})")
    except Exception as e:
        logger.warning(f"增量知识更新跳过: {e}")

    try:
        from datetime import datetime
        db = DatabaseManager.get("data/spirit_lessons.db")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS gene_pool (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT, response TEXT, score REAL,
                source TEXT, solidified_to TEXT, timestamp TEXT
            )
        """)
        db.execute(
            "INSERT INTO gene_pool (query, response, score, source, solidified_to, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (query[:200], response[:500], best_score, "auto", ", ".join(solidified), datetime.now().isoformat()),
            commit=True
        )
    except Exception as e:
        logger.error(f"基因库固化-日志写入失败: {e}")

    if solidified:
        logger.info(f"🧬 基因库固化: {query[:30]} → {', '.join(solidified)} (评分{best_score:.0f})")
        return f"🧬 基因库固化: {', '.join(solidified)} (评分{best_score:.0f})"

    return ""