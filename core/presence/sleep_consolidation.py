"""
睡眠整合模块 - 在系统空闲时执行深度的记忆整合和结构重组

这是存在层的核心能力之一：
- 像生物体的睡眠一样，在空闲时整合记忆、重组结构
- 将短期经验转化为长期技能
- 清理无用信息，优化知识结构
- 在"沉睡"中完成深度的自我更新

核心理念：
- 睡眠不是"停止"，而是"另一种形式的存在"
- 在睡眠中，系统完成清醒时无法完成的深度处理
- 每一次睡眠，系统都比醒来时更加完整

修复记录：
- P1: 真实数据读写（从立体记忆、间隙生长引擎读取）
- P2: 与间隙生长引擎协同（明确分工）
- P3: 基于工作量决定睡眠深度
- P4: 唤醒机制
- P5: 历史增长限制
"""

import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import Counter

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from core.ports.adapters import get_storage_port


class SleepStage(Enum):
    LIGHT = "light"
    DEEP = "deep"
    REM = "rem"


@dataclass
class ConsolidationResult:
    timestamp: str
    stage: SleepStage
    consolidated_memories: int
    solidified_skills: int
    reorganized_knowledge: int
    forgotten_items: int
    extracted_patterns: int
    overall_impact: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryPattern:
    topic: str
    count: int
    recent_access: datetime
    importance: float


class SleepConsolidationEngine:
    """
    睡眠整合引擎
    
    与间隙生长引擎的协同：
    - 间隙生长：即时处理（秒级），快速反应
    - 睡眠整合：深度处理（分钟级），技能固化
    """

    def __init__(self, config: Optional[Dict] = None):
        self._sleep_stage = SleepStage.LIGHT
        self._is_sleeping = False
        self._sleep_start_time: Optional[datetime] = None
        self._last_consolidation_time: Optional[datetime] = None
        self._consolidation_history: List[ConsolidationResult] = []
        self._sleep_cycles = 0
        self._total_sleep_time = 0.0
        self._max_history_size = 100

        self._stats = {
            "total_consolidations": 0,
            "total_memories_consolidated": 0,
            "total_skills_solidified": 0,
            "total_knowledge_reorganized": 0,
            "total_items_forgotten": 0,
            "total_patterns_extracted": 0,
            "avg_impact": 0.0,
            "wake_ups": 0,
        }

        self._running = False
        self._thread = None

        self._config = config or {
            "light_sleep_interval": 300,
            "deep_sleep_interval": 1800,
            "rem_sleep_interval": 7200,
            "max_sleep_duration": 3600,
            "min_sleep_duration": 60,
            "wake_threshold_seconds": 60,
            "min_workload_for_light": 1,
            "min_workload_for_deep": 10,
            "min_workload_for_rem": 20,
        }

        self._last_user_interaction: Optional[datetime] = None
        self._idle_detection_interval = 60
        
        self._db_path = Path("data/sleep_consolidation.db")
        self._init_database()

        logger.info("💤 睡眠整合引擎已创建")

    def _init_database(self):
        """初始化持久化数据库"""
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            
            db = get_storage_port(str(self._db_path))
            db.executescript('''
                CREATE TABLE IF NOT EXISTS consolidation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    stage TEXT,
                    consolidated_memories INTEGER,
                    solidified_skills INTEGER,
                    reorganized_knowledge INTEGER,
                    forgotten_items INTEGER,
                    extracted_patterns INTEGER,
                    overall_impact REAL,
                    details TEXT
                );
                CREATE TABLE IF NOT EXISTS solidified_skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_name TEXT UNIQUE,
                    topic TEXT,
                    occurrence_count INTEGER,
                    first_seen TEXT,
                    last_updated TEXT,
                    importance REAL
                );
            ''')
            logger.debug("睡眠整合数据库初始化成功")
        except Exception as e:
            logger.warning(f"睡眠整合数据库初始化失败: {e}")

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._sleep_loop, daemon=True)
        self._thread.start()
        logger.info("💤 睡眠整合引擎已启动")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("💤 睡眠整合引擎已停止")

    def notify_interaction(self) -> None:
        """通知用户交互"""
        self._last_user_interaction = datetime.now()
        
        if self._is_sleeping:
            logger.info("☀️ 用户交互，准备唤醒")

    def _sleep_loop(self) -> None:
        """睡眠循环 - 修复P4: 添加唤醒检查"""
        while self._running:
            try:
                try:
                    from core.resource_awareness.background_controller import get_background_controller
                    if not get_background_controller().should_run("sleep_consolidation"):
                        time.sleep(self._idle_detection_interval)
                        continue
                except ImportError:
                    pass

                if self._is_sleeping:
                    if self._should_wake():
                        self._wake_up()
                else:
                    sleep_decision = self._should_sleep()
                    if sleep_decision["should_sleep"]:
                        self._execute_sleep(sleep_decision["stage"])
                
                time.sleep(self._idle_detection_interval)
            except Exception as e:
                logger.error(f"睡眠整合异常: {e}")
                time.sleep(60)

    def _should_wake(self) -> bool:
        """
        检查是否应该唤醒
        
        修复P4: 唤醒机制
        """
        if not self._is_sleeping:
            return False
        
        if self._last_user_interaction is None:
            return False
        
        wake_threshold = self._config.get("wake_threshold_seconds", 60)
        time_since_interaction = (datetime.now() - self._last_user_interaction).total_seconds()
        
        return time_since_interaction < wake_threshold

    def _wake_up(self) -> None:
        """唤醒系统"""
        if self._is_sleeping:
            self._is_sleeping = False
            self._stats["wake_ups"] += 1
            logger.info(f"☀️ 系统唤醒 (第{self._stats['wake_ups']}次)")

    def _should_sleep(self) -> Dict:
        """
        决定是否应该睡眠
        
        修复P3: 基于工作量和空闲时间综合决策
        """
        if self._is_sleeping:
            return {"should_sleep": False}
        
        if self._last_user_interaction is None:
            return {"should_sleep": False}

        idle_time = (datetime.now() - self._last_user_interaction).total_seconds()
        pending_work = self._get_pending_workload()

        min_work_rem = self._config.get("min_workload_for_rem", 20)
        min_work_deep = self._config.get("min_workload_for_deep", 10)
        min_work_light = self._config.get("min_workload_for_light", 1)

        if pending_work >= min_work_rem and idle_time >= self._config["rem_sleep_interval"]:
            return {"should_sleep": True, "stage": SleepStage.REM, "workload": pending_work}
        elif pending_work >= min_work_deep and idle_time >= self._config["deep_sleep_interval"]:
            return {"should_sleep": True, "stage": SleepStage.DEEP, "workload": pending_work}
        elif pending_work >= min_work_light and idle_time >= self._config["light_sleep_interval"]:
            return {"should_sleep": True, "stage": SleepStage.LIGHT, "workload": pending_work}
        
        if idle_time >= self._config["rem_sleep_interval"]:
            return {"should_sleep": True, "stage": SleepStage.REM, "workload": pending_work}

        return {"should_sleep": False}

    def _get_pending_workload(self) -> int:
        """
        获取待处理的工作量
        
        修复P2: 从间隙生长引擎获取待处理信号
        """
        workload = 0
        
        try:
            from core.presence.gap_growth import get_gap_growth_engine
            gap_engine = get_gap_growth_engine()
            status = gap_engine.get_queue_status()
            workload += status.get('queue_size', 0)
        except Exception:
            logger.warning("操作降级跳过")
        
        try:
            from core.memory.stereo_memory import get_stereo_memory
            store = get_stereo_memory()
            recent = store.get_recent(limit=100)
            unprocessed = sum(1 for m in recent if not m.get('consolidated', False))
            workload += unprocessed
        except Exception:
            logger.warning("操作降级跳过")
        
        return workload

    def consolidate(self, stage: SleepStage = SleepStage.LIGHT) -> Dict:
        """公共接口：执行一次睡眠整合，返回结果dict"""
        self._execute_sleep(stage)
        if self._consolidation_history:
            r = self._consolidation_history[-1]
            return {
                "consolidated": r.consolidated_memories,
                "solidified": r.solidified_skills,
                "impact": r.overall_impact,
                "stage": r.stage.value,
            }
        return {"consolidated": 0, "solidified": 0, "impact": 0.0, "stage": stage.value}

    def _execute_sleep(self, stage: SleepStage) -> None:
        """执行睡眠整合"""
        self._is_sleeping = True
        self._sleep_start_time = datetime.now()
        self._sleep_stage = stage
        self._sleep_cycles += 1

        try:
            from core.learning.rhythm_controller import CognitiveRhythmController
            crc = CognitiveRhythmController()
            snapshot = crc.tick()
            recommended = crc.get_recommended_actions()
            if recommended:
                logger.info(f"🎵 认知节奏: phase={snapshot.phase.value}, energy={snapshot.energy_level:.2f}, 推荐={recommended[:3]}")
        except Exception as e:
            logger.warning(f"认知节奏控制器跳过: {e}")

        logger.info(f"💤 进入睡眠: {stage.value}")

        start_time = time.time()

        if stage == SleepStage.LIGHT:
            result = self._light_sleep_consolidation()
        elif stage == SleepStage.DEEP:
            result = self._deep_sleep_consolidation()
        else:
            result = self._rem_sleep_consolidation()

        self._consolidation_history.append(result)
        self._save_consolidation_result(result)
        
        if len(self._consolidation_history) > self._max_history_size:
            self._consolidation_history = self._consolidation_history[-self._max_history_size:]

        self._update_stats(result)

        sleep_duration = time.time() - start_time
        self._total_sleep_time += sleep_duration
        self._last_consolidation_time = datetime.now()

        logger.info(
            f"💤 睡眠完成 ({stage.value}): "
            f"记忆={result.consolidated_memories}, "
            f"技能={result.solidified_skills}, "
            f"影响={result.overall_impact:.2f}"
        )

        self._is_sleeping = False

    def _light_sleep_consolidation(self) -> ConsolidationResult:
        """
        浅睡整合：处理高频信号，轻量级整合
        
        修复P1: 真实数据读写
        """
        consolidated = 0
        solidified = 0
        forgotten = 0
        details = {}
        
        try:
            from core.presence.gap_growth import get_gap_growth_engine
            gap_engine = get_gap_growth_engine()
            queue_status = gap_engine.get_queue_status()
            signals_to_process = min(queue_status.get('queue_size', 0), 10)
            consolidated = signals_to_process
            details['gap_signals'] = signals_to_process
        except Exception as e:
            logger.error(f"读取间隙生长队列失败: {e}")
        
        try:
            from core.memory.stereo_memory import get_stereo_memory
            store = get_stereo_memory()
            recent = store.get_recent(limit=30)
            
            topic_counts = Counter()
            for mem in recent:
                if isinstance(mem, dict):
                    topic = mem.get('topic', 'general')
                else:
                    topic = getattr(mem, 'content', None)
                    if topic and isinstance(topic, dict):
                        topic = topic.get('topic', 'general')
                    elif topic and isinstance(topic, str):
                        topic = topic[:50] if len(topic) > 50 else topic
                    else:
                        topic = 'general'
                if topic and topic != 'general':
                    topic_counts[topic] += 1
            
            for topic, count in topic_counts.most_common(3):
                if count >= 2:
                    solidified += self._record_skill_candidate(topic, count)
            
            details['memory_topics'] = len(topic_counts)
        except Exception as e:
            logger.error(f"读取立体记忆失败: {e}")
        
        try:
            from core.cognition.audit_logger import AuditLogger
            from core.cognition.failure_classifier import FailureClassifier
            audit_failures = AuditLogger.get_recent_failures(limit=10)
            if audit_failures:
                consumed = 0
                for af in audit_failures:
                    try:
                        intent = af.get("detected_intent", "unknown")
                        reason = af.get("reflection_reason", "")
                        lesson_type = f"audit_{intent}"
                        lesson_text = f"审计发现: {reason}"
                        db = get_storage_port("data/spirit_lessons.db")
                        existing = db.query_one(
                            'SELECT id FROM spirit_lessons WHERE lesson_type = ? AND lesson_text = ? LIMIT 1',
                            (lesson_type, lesson_text)
                        )
                        if existing:
                            continue
                        db.execute(
                            'INSERT INTO spirit_lessons (lesson_type, lesson_text, severity, context) VALUES (?, ?, ?, ?)',
                            (lesson_type, lesson_text, "medium", json.dumps(af, ensure_ascii=False, default=str)[:500]),
                            commit=True
                        )
                        consumed += 1
                    except Exception as e:
                        logger.warning(f"精神教训DB写入失败: {e}")
                details['audit_failures_consumed'] = consumed
                logger.info(f"📋 睡眠整合消费审计日志: {len(audit_failures)}条")
        except Exception as e:
            logger.warning(f"审计日志消费跳过: {e}")
        
        try:
            from core.learning.incremental_perception import IncrementalPerception, Signal, SignalType
            ip = IncrementalPerception()
            from core.memory.stereo_memory import get_stereo_memory
            store = get_stereo_memory()
            recent = store.get_recent(limit=20)
            for mem in recent:
                try:
                    sig = Signal(
                        type=SignalType.USER_FEEDBACK if mem.get('feedback') else SignalType.INTERACTION,
                        content=str(mem.get('content', ''))[:200],
                        source="sleep_consolidation",
                        timestamp=mem.get('timestamp', datetime.now().isoformat()),
                    )
                    result = ip.perceive(sig)
                    if result.patterns_detected:
                        details.setdefault('perception_patterns', []).extend(result.patterns_detected)
                except Exception:
                    pass
            logger.info(f"🔍 增量感知: 处理{len(recent)}条记忆信号")
        except Exception as e:
            logger.warning(f"增量感知挂接跳过: {e}")
        
        impact = 0.2 + consolidated * 0.02 + solidified * 0.05
        
        return ConsolidationResult(
            timestamp=datetime.now().isoformat(),
            stage=SleepStage.LIGHT,
            consolidated_memories=consolidated,
            solidified_skills=solidified,
            reorganized_knowledge=0,
            forgotten_items=forgotten,
            extracted_patterns=0,
            overall_impact=min(0.5, impact),
            details=details
        )

    def _deep_sleep_consolidation(self) -> ConsolidationResult:
        """
        深睡整合：记忆巩固，技能固化
        
        修复P1: 真实数据读写
        """
        consolidated = 0
        solidified = 0
        reorganized = 0
        forgotten = 0
        patterns = 0
        details = {}
        
        try:
            from core.memory.stereo_memory import get_stereo_memory
            store = get_stereo_memory()
            recent = store.get_recent(limit=100)
            
            topic_counts = Counter()
            intent_counts = Counter()
            
            for mem in recent:
                topic = mem.get('topic', 'general')
                intent = mem.get('intent', 'unknown')
                if topic and topic != 'general':
                    topic_counts[topic] += 1
                if intent and intent != 'unknown':
                    intent_counts[intent] += 1
            
            for topic, count in topic_counts.most_common(10):
                if count >= 3:
                    solidified += self._solidify_skill(topic, count)
            
            patterns = len([t for t, c in topic_counts.items() if c >= 3])
            reorganized = len(topic_counts)
            
            details['topics'] = len(topic_counts)
            details['intents'] = len(intent_counts)
            details['patterns_found'] = patterns
            
            consolidated = len(recent)
        except Exception as e:
            logger.error(f"深睡整合失败: {e}")
        
        try:
            forgotten = self._cleanup_old_memories()
            details['forgotten'] = forgotten
        except Exception as e:
            logger.error(f"记忆清理失败: {e}")
        
        try:
            from core.learning.feedback_loop import LearningFeedbackLoop, Feedback, FeedbackType
            fbl = LearningFeedbackLoop()
            db = get_storage_port(str(self._db_path))
            rows = db.query("SELECT skill_name, occurrence_count, importance FROM solidified_skills WHERE importance >= 0.5 LIMIT 20")
            validated_count = 0
            for row in (rows or []):
                try:
                    kid = row[0] if isinstance(row, (list, tuple)) else row.get('skill_name', '')
                    occ = row[1] if isinstance(row, (list, tuple)) else row.get('occurrence_count', 0)
                    fb = Feedback(
                        knowledge_id=str(kid),
                        feedback_type=FeedbackType.POSITIVE if occ >= 3 else FeedbackType.NEUTRAL,
                        content=f"深睡验证: 出现{occ}次",
                        confidence=min(1.0, occ / 10.0),
                    )
                    result = fbl.validate(fb)
                    if result.validated:
                        validated_count += 1
                except Exception:
                    pass
            details['feedback_validated'] = validated_count
            logger.info(f"🔄 反馈回路验证: {validated_count}条知识")
        except Exception as e:
            logger.warning(f"反馈回路挂接跳过: {e}")
        
        impact = 0.4 + consolidated * 0.01 + solidified * 0.05 + patterns * 0.03
        
        return ConsolidationResult(
            timestamp=datetime.now().isoformat(),
            stage=SleepStage.DEEP,
            consolidated_memories=consolidated,
            solidified_skills=solidified,
            reorganized_knowledge=reorganized,
            forgotten_items=forgotten,
            extracted_patterns=patterns,
            overall_impact=min(0.75, impact),
            details=details
        )

    def _rem_sleep_consolidation(self) -> ConsolidationResult:
        """
        REM睡眠：深度模式提取，知识重组
        
        修复P1: 真实数据读写
        """
        consolidated = 0
        solidified = 0
        reorganized = 0
        forgotten = 0
        patterns = 0
        details = {}
        
        try:
            from core.memory.stereo_memory import get_stereo_memory
            store = get_stereo_memory()
            recent = store.get_recent(limit=200)
            
            topic_patterns = Counter()
            intent_patterns = Counter()
            topic_intent_pairs = Counter()
            
            for mem in recent:
                topic = mem.get('topic', 'general')
                intent = mem.get('intent', 'unknown')
                
                if topic and topic != 'general':
                    topic_patterns[topic] += 1
                if intent and intent != 'unknown':
                    intent_patterns[intent] += 1
                if topic and intent:
                    pair = f"{topic}:{intent}"
                    topic_intent_pairs[pair] += 1
            
            for topic, count in topic_patterns.most_common(15):
                if count >= 5:
                    solidified += self._solidify_skill(topic, count, importance=0.8)
            
            patterns = len([p for p, c in topic_intent_pairs.items() if c >= 3])
            reorganized = len(topic_patterns) + len(intent_patterns)
            
            details['topic_patterns'] = len(topic_patterns)
            details['intent_patterns'] = len(intent_patterns)
            details['pair_patterns'] = len(topic_intent_pairs)
            details['strong_patterns'] = patterns
            
            consolidated = len(recent)
        except Exception as e:
            logger.error(f"REM整合失败: {e}")
        
        try:
            forgotten = self._cleanup_old_memories(aggressive=True)
            details['forgotten'] = forgotten
        except Exception as e:
            logger.error(f"记忆清理失败: {e}")
        
        try:
            reorganized += self._reorganize_from_db()
        except Exception as e:
            logger.error(f"知识结构更新失败: {e}")
        
        try:
            from core.learning.knowledge_weaver import KnowledgeWeaver, NodeType, ConnectionType
            kw = KnowledgeWeaver()
            from core.memory.stereo_memory import get_stereo_memory
            store = get_stereo_memory()
            recent = store.get_recent(limit=50)
            nodes_to_weave = []
            for mem in recent:
                topic = mem.get('topic', '')
                if topic and topic != 'general':
                    nodes_to_weave.append((topic, NodeType.CONCEPT))
            if nodes_to_weave:
                weave_result = kw.weave(nodes_to_weave)
                reorganized += weave_result.nodes_added
                patterns += weave_result.clusters_updated
                details['weaver_nodes'] = weave_result.nodes_added
                details['weaver_connections'] = weave_result.connections_added
                details['weaver_clusters'] = weave_result.clusters_updated
                logger.info(f"🕸️ 知识编织: {weave_result.nodes_added}节点, {weave_result.connections_added}连接, {weave_result.clusters_updated}聚类")
        except Exception as e:
            logger.warning(f"知识编织挂接跳过: {e}")
        
        impact = 0.6 + consolidated * 0.005 + solidified * 0.03 + patterns * 0.05
        
        return ConsolidationResult(
            timestamp=datetime.now().isoformat(),
            stage=SleepStage.REM,
            consolidated_memories=consolidated,
            solidified_skills=solidified,
            reorganized_knowledge=reorganized,
            forgotten_items=forgotten,
            extracted_patterns=patterns,
            overall_impact=min(0.95, impact),
            details=details
        )

    def _record_skill_candidate(self, topic: str, count: int) -> int:
        """记录技能候选"""
        try:
            db = get_storage_port(str(self._db_path))
            row = db.query_one(
                'SELECT occurrence_count FROM solidified_skills WHERE skill_name = ?',
                (topic,)
            )
            
            if row:
                new_count = row[0] + count
                db.execute('''
                    UPDATE solidified_skills 
                    SET occurrence_count = ?, last_updated = ?
                    WHERE skill_name = ?
                ''', (new_count, datetime.now().isoformat(), topic), commit=True)
            else:
                db.execute('''
                    INSERT INTO solidified_skills 
                    (skill_name, topic, occurrence_count, first_seen, last_updated, importance)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (topic, topic, count, datetime.now().isoformat(), 
                     datetime.now().isoformat(), 0.5), commit=True)
            return 0
        except Exception as e:
            logger.error(f"记录技能候选失败: {e}")
            return 0

    def _solidify_skill(self, topic: str, count: int, importance: float = 0.7) -> int:
        """固化技能"""
        try:
            db = get_storage_port(str(self._db_path))
            row = db.query_one(
                'SELECT occurrence_count, importance FROM solidified_skills WHERE skill_name = ?',
                (topic,)
            )
            
            if row:
                new_count = row[0] + count
                new_importance = min(1.0, row[1] + 0.1)
                db.execute('''
                    UPDATE solidified_skills 
                    SET occurrence_count = ?, importance = ?, last_updated = ?
                    WHERE skill_name = ?
                ''', (new_count, new_importance, datetime.now().isoformat(), topic), commit=True)
                return 1
            else:
                db.execute('''
                    INSERT INTO solidified_skills 
                    (skill_name, topic, occurrence_count, first_seen, last_updated, importance)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (topic, topic, count, datetime.now().isoformat(), 
                     datetime.now().isoformat(), importance), commit=True)
                return 1
        except Exception as e:
            logger.error(f"固化技能失败: {e}")
            return 0

    def _cleanup_old_memories(self, aggressive: bool = False) -> int:
        """清理旧记忆"""
        forgotten = 0
        
        try:
            from core.memory.stereo_memory import get_stereo_memory
            store = get_stereo_memory()
            
            threshold_days = 7 if aggressive else 30
            cutoff = datetime.now() - timedelta(days=threshold_days)
            
            forgotten = store.cleanup_before(cutoff)
        except Exception as e:
            logger.error(f"记忆清理失败: {e}")
        
        return forgotten

    def _reorganize_from_db(self) -> int:
        """从数据库重组知识结构（纯SQL，不调Ollama）"""
        reorganized = 0
        try:
            db = get_storage_port(str(self._db_path))
            rows = db.query('''
                SELECT skill_name, occurrence_count, importance
                FROM solidified_skills
                WHERE importance < 0.5 AND occurrence_count >= 5
            ''')
            for row in rows:
                db.execute('''
                    UPDATE solidified_skills
                    SET importance = importance + 0.1, last_updated = ?
                    WHERE skill_name = ?
                ''', (datetime.now().isoformat(), row[0]), commit=True)
                reorganized += 1
        except Exception as e:
            logger.error(f"知识结构重组失败: {e}")
        return reorganized

    def _save_consolidation_result(self, result: ConsolidationResult) -> None:
        """保存整合结果"""
        try:
            db = get_storage_port(str(self._db_path))
            db.execute('''
                INSERT INTO consolidation_history
                (timestamp, stage, consolidated_memories, solidified_skills,
                 reorganized_knowledge, forgotten_items, extracted_patterns,
                 overall_impact, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.timestamp,
                result.stage.value,
                result.consolidated_memories,
                result.solidified_skills,
                result.reorganized_knowledge,
                result.forgotten_items,
                result.extracted_patterns,
                result.overall_impact,
                json.dumps(result.details)
            ), commit=True)
        except Exception as e:
            logger.error(f"保存整合结果失败: {e}")

    def _update_stats(self, result: ConsolidationResult) -> None:
        """更新统计"""
        self._stats["total_consolidations"] += 1
        self._stats["total_memories_consolidated"] += result.consolidated_memories
        self._stats["total_skills_solidified"] += result.solidified_skills
        self._stats["total_knowledge_reorganized"] += result.reorganized_knowledge
        self._stats["total_items_forgotten"] += result.forgotten_items
        self._stats["total_patterns_extracted"] += result.extracted_patterns
        
        total = self._stats["total_consolidations"]
        old_avg = self._stats["avg_impact"]
        self._stats["avg_impact"] = (old_avg * (total - 1) + result.overall_impact) / total

    def get_sleep_status(self) -> Dict:
        return {
            "is_sleeping": self._is_sleeping,
            "sleep_stage": self._sleep_stage.value,
            "sleep_cycles": self._sleep_cycles,
            "total_sleep_time": self._total_sleep_time,
            "pending_workload": self._get_pending_workload() if not self._is_sleeping else 0,
        }

    def get_consolidation_summary(self) -> Dict:
        return {
            "stats": self._stats,
            "recent_consolidations": [
                {
                    "timestamp": r.timestamp,
                    "stage": r.stage.value,
                    "impact": r.overall_impact,
                    "memories": r.consolidated_memories,
                    "skills": r.solidified_skills,
                }
                for r in self._consolidation_history[-10:]
            ],
        }

    def get_solidified_skills(self) -> List[Dict]:
        """获取已固化的技能"""
        try:
            db = get_storage_port(str(self._db_path))
            rows = db.query('''
                SELECT skill_name, topic, occurrence_count, importance, last_updated
                FROM solidified_skills
                ORDER BY importance DESC, occurrence_count DESC
                LIMIT 20
            ''')
            return [
                {
                    "skill": row[0],
                    "topic": row[1],
                    "count": row[2],
                    "importance": row[3],
                    "last_updated": row[4],
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"获取固化技能失败: {e}")
            return []

    def is_running(self) -> bool:
        return self._running and self._thread and self._thread.is_alive()


_sleep_engine: Optional[SleepConsolidationEngine] = None


def get_sleep_engine(config: Optional[Dict] = None) -> SleepConsolidationEngine:
    global _sleep_engine
    if _sleep_engine is None:
        _sleep_engine = SleepConsolidationEngine(config)
    return _sleep_engine


def start_sleep_engine() -> None:
    engine = get_sleep_engine()
    if not engine.is_running():
        engine.start()


def stop_sleep_engine() -> None:
    engine = get_sleep_engine()
    if engine.is_running():
        engine.stop()
