"""
L2: 学习层 - 修复版

修复内容：
1. _learn_externally: 从模拟实现改为委托ExternalLearner真实搜索+LLM提取
2. _store_knowledge: 添加冲突检测和质量比较
3. 新增知识质量反馈接口 get_knowledge_for_l5()，供L5消费
4. 新增多维度质量评估 _assess_quality()
5. 新增冲突检测 _detect_conflict()

与原版的兼容：
- 保留 LayerReporter / HeartbeatManager 集成
- 保留 get_storage_port 接口
- LearningResult 扩展而非破坏性修改
"""

from typing import Dict, Optional, List, Any
from datetime import datetime
from dataclasses import dataclass, field
from core.ports.adapters import get_storage_port
import os
import hashlib
import json

try:
    from loguru import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

from core.introspection.layer_reporter import LayerReporter
from core.reporting.state_collector import get_state_collector
from core.introspection.heartbeat import get_heartbeat_manager
from core.state_report import LayerHealth


@dataclass
class LearningResult:
    success: bool
    knowledge_gained: int
    knowledge_ids: List[str]
    sources_used: List[str]
    confidence: float
    avg_knowledge_quality: float = 0.0
    knowledge_reuse_rate: float = 0.0
    real_search_performed: bool = False
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class L2LearningLayer:

    GENE_DIMENSION_MAP = {
        "检索阈值": "accuracy",
        "学习频率": "growth",
        "情感权重": "satisfaction",
        "探索倾向": "growth",
        "记忆衰减率": "stability",
        "抽象阈值": "knowledge_quality",
        "反思频率": "accuracy",
        "知识广度": "knowledge_quality",
        "技能固化阈值": "satisfaction",
        "环境敏感度": "stability",
    }

    def __init__(self):
        self.reporter = LayerReporter("L2")
        self.collector = get_state_collector()
        self.heartbeat = get_heartbeat_manager()

        self.reporter.report_idle()

        self.stats = {
            'total_learning_attempts': 0,
            'total_successful_learning': 0,
            'total_knowledge_gained': 0,
            'total_real_searches': 0,
            'total_search_failures': 0,
            'avg_knowledge_quality': 0.0,
            'knowledge_reuse_count': 0,
            'last_learning_time': None,
            'learning_sources': {},
        }

        self.pending_targets: List[Dict] = []
        self.search_threshold = 0.5

        self._init_knowledge_store()

        logger.info("📚 L2学习层已初始化（修复版 - 真实学习）")
        self.reporter.report_completed(
            metrics={"initialized": 1},
            confidence=1.0
        )

    def _init_knowledge_store(self):
        db_path = "data/knowledge_store.db"
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        db = get_storage_port(db_path)

        db.executescript('''
            CREATE TABLE IF NOT EXISTS knowledge_items (
                id TEXT PRIMARY KEY,
                question TEXT,
                answer TEXT,
                source TEXT,
                source_url TEXT,
                knowledge_type TEXT DEFAULT 'external',
                quality_score REAL DEFAULT 50.0,
                confidence REAL DEFAULT 0.5,
                keywords TEXT,
                created_at TEXT,
                updated_at TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                conflict_with TEXT,
                merged_from TEXT,
                status TEXT DEFAULT 'active'
            )
        ''')

        try:
            db.execute("CREATE INDEX IF NOT EXISTS idx_ki_question ON knowledge_items(question)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_ki_quality ON knowledge_items(quality_score DESC)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_ki_status ON knowledge_items(status)")
        except Exception:
            pass

        _migration_cols = {
            "source_url": "TEXT",
            "confidence": "REAL DEFAULT 0.5",
            "keywords": "TEXT",
            "updated_at": "TEXT",
            "conflict_with": "TEXT",
            "merged_from": "TEXT",
            "status": "TEXT DEFAULT 'active'",
        }
        try:
            existing_cols = {c[1] for c in db.query("PRAGMA table_info(knowledge_items)")}
            for col_name, col_type in _migration_cols.items():
                if col_name not in existing_cols:
                    db.execute(f"ALTER TABLE knowledge_items ADD COLUMN {col_name} {col_type}")
                    logger.info(f"L2迁移: knowledge_items添加列 {col_name}")
        except Exception as e:
            logger.debug(f"L2迁移跳过: {e}")

    def learn(self, target: Dict, context: Optional[Dict] = None) -> LearningResult:
        self.stats['total_learning_attempts'] += 1

        target_name = target.get('name', 'unknown')
        target_keywords = target.get('keywords', [])

        self.reporter.report_busy(
            operation=f"学习: {target_name[:50]}",
            active_tasks=[f"学习目标: {target_name}"]
        )

        reasoning = []
        issues = []
        warnings = []
        metrics = {}

        try:
            existing = self._retrieve_existing(target_keywords)
            reasoning.append(f"检索到 {len(existing)} 条相关知识")
            metrics['existing_knowledge_count'] = len(existing)

            if not self.heartbeat.is_layer_alive("L1"):
                warnings.append("L1不可用，可能影响学习上下文")

            search_results = self._perform_real_search(target_keywords)
            self.stats['total_real_searches'] += 1

            if not search_results:
                self.stats['total_search_failures'] += 1
                warnings.append("外部搜索无结果")
                metrics['knowledge_gained'] = 0
                reasoning.append("外部搜索无结果")

                self.reporter.report_completed(
                    metrics=metrics, confidence=0.2,
                    warnings=warnings if warnings else None,
                    issues=issues if issues else None
                )

                return LearningResult(
                    success=False, knowledge_gained=0, knowledge_ids=[],
                    sources_used=[], confidence=0.2,
                    real_search_performed=True, error="外部搜索无结果"
                )

            knowledge_items = self._extract_knowledge(search_results, target_name, target_keywords)

            if not knowledge_items:
                warnings.append("知识提取失败")
                metrics['knowledge_gained'] = 0
                reasoning.append("知识提取失败")

                self.reporter.report_completed(
                    metrics=metrics, confidence=0.3,
                    warnings=warnings if warnings else None
                )

                return LearningResult(
                    success=False, knowledge_gained=0, knowledge_ids=[],
                    sources_used=[r.get('source', 'unknown') for r in search_results],
                    confidence=0.3, real_search_performed=True, error="知识提取失败"
                )

            for item in knowledge_items:
                item['quality_score'] = self._assess_quality(item, existing)

            stored_ids = []
            sources_used = set()

            for item in knowledge_items:
                conflict = self._detect_conflict(item, existing)

                if conflict:
                    if item['quality_score'] > conflict.get('quality_score', 0) * 1.2:
                        logger.info(f"  更新知识: {item['question'][:50]}... "
                                    f"({conflict.get('quality_score', 0):.1f} -> {item['quality_score']:.1f})")
                        self._update_knowledge(item, conflict['id'])
                        stored_ids.append(item['id'])
                    else:
                        logger.debug(f"  跳过低质量知识: {item['question'][:50]}...")
                        self._record_conflict(item, conflict['id'])
                else:
                    self._insert_knowledge(item)
                    stored_ids.append(item['id'])

                sources_used.add(item.get('source', 'unknown'))

            knowledge_gained = len(stored_ids)
            self.stats['total_successful_learning'] += 1
            self.stats['total_knowledge_gained'] += knowledge_gained
            self.stats['last_learning_time'] = datetime.now().isoformat()

            for source in sources_used:
                self.stats['learning_sources'][source] = \
                    self.stats['learning_sources'].get(source, 0) + 1

            avg_quality = sum(k.get('quality_score', 50) for k in knowledge_items) / len(knowledge_items)
            self.stats['avg_knowledge_quality'] = (
                self.stats['avg_knowledge_quality'] * 0.9 + avg_quality * 0.1
            )

            reused = sum(1 for k in knowledge_items if k.get('access_count', 0) > 0)
            reuse_rate = reused / len(knowledge_items) if knowledge_items else 0

            metrics['knowledge_gained'] = knowledge_gained
            metrics['avg_quality'] = round(avg_quality, 1)
            reasoning.append(f"从 {len(sources_used)} 个来源获取 {knowledge_gained} 条新知识")

            confidence = min(1.0, avg_quality / 100 + 0.2)

            self.reporter.report_completed(
                metrics=metrics, confidence=confidence,
                warnings=warnings if warnings else None,
                issues=issues if issues else None
            )

            logger.info(f"📚 L2学习完成: {target_name} -> {knowledge_gained}条新知 "
                        f"(质量: {avg_quality:.1f}, 来源: {len(sources_used)}个)")

            return LearningResult(
                success=True, knowledge_gained=knowledge_gained,
                knowledge_ids=stored_ids, sources_used=list(sources_used),
                confidence=confidence,
                avg_knowledge_quality=avg_quality,
                knowledge_reuse_rate=reuse_rate,
                real_search_performed=True
            )

        except Exception as e:
            error_msg = f"L2学习异常: {str(e)}"
            logger.error(error_msg)

            self.reporter.report_error(issues=[error_msg], metrics=metrics)

            return LearningResult(
                success=False, knowledge_gained=0, knowledge_ids=[],
                sources_used=[], confidence=0.0,
                real_search_performed=False, error=error_msg
            )

    def _perform_real_search(self, keywords: List[str]) -> List[Dict]:
        query = " ".join(keywords[:5]) if keywords else "general knowledge"

        try:
            from core.external_learner import ExternalLearner
            learner = ExternalLearner()
            results = learner.search_web(query, num_results=3)

            parsed = []
            for i, r in enumerate(results):
                if isinstance(r, str) and len(r) > 20:
                    parsed.append({
                        'content': r,
                        'source': r[:20] if '[' in r else 'web_search',
                        'index': i,
                    })
            if parsed:
                return parsed
        except Exception as e:
            logger.warning(f"ExternalLearner搜索失败: {e}")

        try:
            from infrastructure.external_learners import composite_learner
            if composite_learner.is_available():
                results = composite_learner.learn(query, max_results=3)
                if results:
                    return [{'content': r.content, 'source': r.source} for r in results]
        except Exception as e:
            logger.debug(f"composite_learner搜索失败: {e}")

        try:
            from core.tools.builtin import WebSearchTool
            tool = WebSearchTool()
            result = tool.execute(query=query)
            if isinstance(result, dict) and result.get('results'):
                return result['results']
        except Exception as e:
            logger.debug(f"WebSearchTool搜索失败: {e}")

        logger.warning("所有搜索路径不可用")
        return []

    def _extract_knowledge(self, search_results: List[Dict],
                           target_name: str, keywords: List[str]) -> List[Dict]:
        items = []

        for result in search_results[:3]:
            content = result.get('content', '') or result.get('snippet', '')
            if not content or len(content) < 50:
                continue

            extracted = self._try_llm_extract(content, target_name)
            base_quality = 70.0

            if not extracted:
                extracted = self._heuristic_extract(content, target_name)
                base_quality = 50.0

            if extracted:
                item_id = f"learned_{hashlib.md5(content[:200].encode()).hexdigest()[:12]}"
                items.append({
                    'id': item_id,
                    'question': target_name,
                    'answer': extracted,
                    'source': result.get('source', 'web_search'),
                    'source_url': result.get('url'),
                    'keywords': keywords,
                    'quality_score': base_quality,
                    'confidence': 0.5,
                    'access_count': 0,
                })

        return items

    def _try_llm_extract(self, content: str, target_name: str) -> Optional[str]:
        try:
            from core.external_learner import ExternalLearner
            learner = ExternalLearner()

            if not hasattr(learner, 'ask_llm'):
                logger.debug("ExternalLearner无ask_llm方法，降级到启发式提取")
                return None

            prompt = (
                f"从以下搜索结果中，提取与\"{target_name}\"相关的核心知识。"
                f"只提取事实性内容，不添加推测。总长度不超过300字。\n\n"
                f"搜索结果：\n{content[:2000]}\n\n提取结果："
            )

            response = learner.ask_llm(prompt, system_prompt="你是知识助手，简洁准确地回答。")
            if response and len(response) > 30 and "无法" not in response[:20]:
                return response[:500]
        except Exception as e:
            logger.debug(f"LLM提取失败: {e}")

        return None

    def _heuristic_extract(self, content: str, target_name: str) -> Optional[str]:
        paragraphs = content.split('\n\n')

        for para in paragraphs:
            para = para.strip()
            if len(para) > 80:
                return para[:500]

        if content and len(content) > 80:
            return content[:500]

        return None

    def _assess_quality(self, item: Dict, existing: List[Dict]) -> float:
        scores = []

        content_len = len(item.get('answer', ''))
        if 200 <= content_len <= 800:
            scores.append(90)
        elif 100 <= content_len < 200:
            scores.append(70)
        elif content_len > 800:
            scores.append(60)
        else:
            scores.append(40)

        source = item.get('source', '')
        trusted = {'wikipedia', 'arxiv', 'github', 'edu', 'gov'}
        if any(t in source.lower() for t in trusted):
            scores.append(95)
        elif 'web_search' in source or 'stealth' in source:
            scores.append(65)
        else:
            scores.append(50)

        if existing:
            max_sim = max(self._text_similarity(item.get('answer', ''), ex.get('answer', ''))
                          for ex in existing)
            if max_sim > 0.8:
                scores.append(30)
            elif max_sim > 0.5:
                scores.append(60)
            else:
                scores.append(90)
        else:
            scores.append(85)

        answer = item.get('answer', '')
        has_structure = any(m in answer for m in ['- ', '1. ', '：', ': ', '•'])
        scores.append(80 if has_structure else 50)

        weights = [0.3, 0.25, 0.25, 0.2]
        final = sum(s * w for s, w in zip(scores, weights))
        return min(100, max(0, final))

    def _text_similarity(self, text1: str, text2: str) -> float:
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def _detect_conflict(self, item: Dict, existing: List[Dict]) -> Optional[Dict]:
        for ex in existing:
            q_sim = self._text_similarity(item.get('question', ''), ex.get('question', ''))
            a_sim = self._text_similarity(item.get('answer', ''), ex.get('answer', ''))

            if q_sim > 0.7 and a_sim < 0.8:
                return ex
            if item.get('question', '').lower().strip() == ex.get('question', '').lower().strip():
                return ex
        return None

    def _record_conflict(self, item: Dict, conflict_id: str):
        logger.debug(f"知识冲突: {item.get('id', '?')} vs {conflict_id}")

    def _retrieve_existing(self, target: Dict) -> List[Dict]:
        try:
            db_path = "data/knowledge_store.db"
            db = get_storage_port(db_path)

            keywords = target.get('keywords', []) if isinstance(target, dict) else []
            if not keywords:
                return []

            placeholders = ' OR '.join(['question LIKE ?' for _ in keywords[:5]])
            params = [f'%{kw}%' for kw in keywords[:5]]

            return [dict(row) for row in db.query(f'''
                SELECT id, question, answer, quality_score, source, access_count
                FROM knowledge_items
                WHERE {placeholders} AND status = 'active'
                ORDER BY quality_score DESC
                LIMIT 10
            ''', params)]
        except Exception as e:
            logger.warning(f"检索现有知识失败: {e}")
            return []

    def _insert_knowledge(self, item: Dict):
        try:
            db_path = "data/knowledge_store.db"
            db = get_storage_port(db_path)

            db.execute('''
                INSERT OR REPLACE INTO knowledge_items
                (id, question, answer, source, source_url, knowledge_type,
                 quality_score, confidence, keywords, created_at, updated_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item.get('id', f"auto_{datetime.now().timestamp()}"),
                item.get('question', ''),
                item.get('answer', ''),
                item.get('source', 'unknown'),
                item.get('source_url'),
                'external',
                item.get('quality_score', 50),
                item.get('confidence', 0.5),
                json.dumps(item.get('keywords', []), ensure_ascii=False),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                'active'
            ), commit=True)
        except Exception as e:
            logger.error(f"插入知识失败: {e}")

    def _update_knowledge(self, item: Dict, old_id: str):
        try:
            db_path = "data/knowledge_store.db"
            db = get_storage_port(db_path)

            db.execute('''
                UPDATE knowledge_items SET status = 'deprecated', merged_from = ?
                WHERE id = ?
            ''', (item.get('id', ''), old_id))

            self._insert_knowledge(item)
        except Exception as e:
            logger.error(f"更新知识失败: {e}")

    def get_knowledge_for_l5(self) -> Dict:
        try:
            db_path = "data/knowledge_store.db"
            db = get_storage_port(db_path)

            row = db.query_one('''
                SELECT COUNT(*) as total, AVG(quality_score) as avg_q, AVG(access_count) as avg_a
                FROM knowledge_items WHERE status = 'active'
            ''')
            total = row[0] if row else 0
            avg_quality = row[1] if row and row[1] else 0
            avg_access = row[2] if row and row[2] else 0

            recent = db.query_one('''
                SELECT COUNT(*), AVG(quality_score)
                FROM knowledge_items
                WHERE created_at > datetime('now', '-7 days') AND status = 'active'
            ''')
            recent_count = recent[0] if recent else 0
            recent_quality = recent[1] if recent and recent[1] else 0

            reused = db.query_one('''
                SELECT COUNT(*) FROM knowledge_items
                WHERE access_count > 0 AND status = 'active'
            ''')
            reused_count = reused[0] if reused else 0

            reuse_rate = reused_count / total if total > 0 else 0

            return {
                "total_knowledge": total,
                "avg_quality": avg_quality,
                "avg_access_count": avg_access,
                "recent_knowledge_count": recent_count,
                "recent_avg_quality": recent_quality,
                "knowledge_reuse_rate": reuse_rate,
            }
        except Exception as e:
            logger.warning(f"获取L5数据失败: {e}")
            return {
                "total_knowledge": 0, "avg_quality": 0,
                "avg_access_count": 0, "recent_knowledge_count": 0,
                "recent_avg_quality": 0, "knowledge_reuse_rate": 0,
            }

    def get_learning_status(self) -> Dict:
        neighbor_status = self.heartbeat.get_neighbor_status("L2")

        return {
            "layer": "L2",
            "stats": self.stats,
            "neighbor_status": {
                k: v.value for k, v in neighbor_status.items()
            },
            "pending_targets": len(self.pending_targets),
            "search_threshold": self.search_threshold,
        }


_l2_instance = None

def get_l2_learning() -> L2LearningLayer:
    global _l2_instance
    if _l2_instance is None:
        _l2_instance = L2LearningLayer()
    return _l2_instance
