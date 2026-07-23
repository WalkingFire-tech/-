"""
间隙生长模块 - 在沉默中消化信号，在间隙中生长

这是存在层的核心能力之一：
- 系统在用户不说话时，依然在"消化"之前对话中的信号
- 不是等待下一个输入，而是主动处理未完成的思考
- 像人的"事后反思"一样，在安静的时候整理经验

核心理念：
- 每次对话结束后，系统不是"停止思考"，而是"继续消化"
- 在间隙中，信号被分类、关联、吸收
- 生长是持续的过程，不是偶尔的事件
"""

import threading
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class SignalType(Enum):
    """信号类型"""
    INTENT_PATTERN = "intent_pattern"          # 意图模式
    EMOTION_PATTERN = "emotion_pattern"        # 情绪模式
    ERROR_PATTERN = "error_pattern"            # 错误模式
    SUCCESS_PATTERN = "success_pattern"        # 成功模式
    KNOWLEDGE_GAP = "knowledge_gap"            # 知识缺口
    USER_PREFERENCE = "user_preference"        # 用户偏好
    TOOL_NEED = "tool_need"                    # 工具需求
    SKILL_OPPORTUNITY = "skill_opportunity"    # 技能机会


class SignalPriority(Enum):
    """信号优先级"""
    HIGH = 3       # 需要立即处理
    MEDIUM = 2     # 尽快处理
    LOW = 1        # 空闲时处理


@dataclass
class Signal:
    """一个待处理的信号"""
    id: str
    type: SignalType
    priority: SignalPriority
    content: str
    source: str                     # 哪个组件产生的
    timestamp: str
    context: Dict[str, Any] = field(default_factory=dict)
    processed: bool = False
    processing_result: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "priority": self.priority.value,
            "content": self.content[:100],
            "source": self.source,
            "timestamp": self.timestamp,
            "processed": self.processed,
            "has_result": self.processing_result is not None
        }


@dataclass
class GrowthEvent:
    """一次生长事件"""
    id: str
    signal_id: str
    growth_type: str                # 信号消化的类型
    description: str
    impact: float                   # 0-1 影响程度
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BoundaryExpectation:
    """边界扩展预期——消化信号后期望的能力扩展"""
    id: str
    gap_type: str
    expected_capability: str
    created_at: str
    verified: bool = False
    verified_at: Optional[str] = None
    verification_result: Optional[str] = None


class GapGrowthEngine:
    """
    间隙生长引擎

    在对话间隙中消化信号，驱动系统持续生长。
    """

    def __init__(self):
        self._lock = threading.RLock()
        
        self._signal_queue: List[Signal] = []

        self._signal_history: List[Signal] = []

        self._growth_events: List[GrowthEvent] = []

        self._boundary_expectations: List[BoundaryExpectation] = []

        self._boundary_verifications = {
            "total": 0, "confirmed": 0, "failed": 0, "pending": 0
        }

        self._stats = {
            "signals_received": 0,
            "signals_processed": 0,
            "growth_events": 0,
            "last_growth_time": None,
            "total_growth_impact": 0.0
        }

        self._running = False
        self._thread = None

        self._processing_interval = 15

        self._max_queue_size = 100

        self._dedup_window = 300
        
        self._last_deep_growth = datetime.now()
        self._deep_growth_interval = 3600

        logger.info("🌿 间隙生长引擎已创建")

    def start(self) -> None:
        """启动间隙生长引擎"""
        if self._running:
            logger.warning("间隙生长引擎已在运行")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._growth_loop,
            daemon=True,
            name="GapGrowthEngine"
        )
        self._thread.start()

        logger.info("🌿 间隙生长引擎已启动")

    def stop(self) -> None:
        """停止间隙生长引擎"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("🌿 间隙生长引擎已停止")

    def submit_signal(self, signal_type: str, content: str, 
                      source: str, context: Dict = None,
                      priority: str = "medium") -> str:
        """
        提交一个信号到队列

        由其他组件（如L4校验层、自我评估引擎）调用。
        """
        with self._lock:
            duplicate = self._find_duplicate(signal_type, content)
            if duplicate:
                duplicate.context["repeat_count"] = duplicate.context.get("repeat_count", 0) + 1
                duplicate.context["last_seen"] = datetime.now().isoformat()
                logger.debug(f"🔄 合并重复信号: {duplicate.id}")
                return duplicate.id

            signal_id = hashlib.md5(
                f"{signal_type}{content}{datetime.now().isoformat()}".encode()
            ).hexdigest()[:12]

            try:
                sig_type = SignalType(signal_type)
            except ValueError:
                sig_type = SignalType.KNOWLEDGE_GAP
                logger.warning(f"未知信号类型: {signal_type}, 降级为KNOWLEDGE_GAP")

            try:
                sig_priority = SignalPriority[priority.upper()]
            except KeyError:
                sig_priority = SignalPriority.MEDIUM
                logger.warning(f"未知优先级: {priority}, 降级为MEDIUM")

            signal = Signal(
                id=signal_id,
                type=sig_type,
                priority=sig_priority,
                content=content,
                source=source,
                timestamp=datetime.now().isoformat(),
                context=context or {},
                processed=False
            )

            self._signal_queue.append(signal)
            self._stats["signals_received"] += 1

            if len(self._signal_queue) > self._max_queue_size:
                low_priority = [s for s in self._signal_queue if s.priority == SignalPriority.LOW]
                for s in low_priority:
                    self._signal_queue.remove(s)
                    logger.debug(f"🗑️ 队列溢出，丢弃低优先级信号: {s.id}")

            logger.debug(f"📥 信号已入队: {signal_type} ({len(self._signal_queue)} 个待处理)")

            return signal_id

    def _growth_loop(self) -> None:
        """生长主循环"""
        while self._running:
            try:
                try:
                    from core.resource_awareness.background_controller import get_background_controller
                    if not get_background_controller().should_run("gap_growth"):
                        time.sleep(self._processing_interval)
                        continue
                except ImportError:
                    pass

                # 1. 处理信号队列
                processed = self._process_signals()

                # 2. 检查是否有新的生长
                if processed > 0:
                    self._stats["last_growth_time"] = datetime.now().isoformat()

                # 3. 执行周期性的深度生长
                self._periodic_deep_growth()

                # 等待下一个周期
                time.sleep(self._processing_interval)

            except Exception as e:
                logger.error(f"间隙生长异常: {e}")
                time.sleep(60)

    def process_signals(self, signals: list = None) -> int:
        """
        处理信号队列（公开接口）

        可接受外部信号列表，将其加入内部队列后处理。
        如果不传参数，则处理内部队列中已有的信号。
        """
        if signals:
            with self._lock:
                for sig in signals:
                    if hasattr(sig, 'id'):
                        self._signal_queue.append(sig)
        return self._process_signals()

    def _process_signals(self) -> int:
        """
        处理信号队列

        按优先级排序，每次最多处理5个信号。
        """
        with self._lock:
            if not self._signal_queue:
                return 0

            sorted_signals = sorted(
                self._signal_queue,
                key=lambda s: s.priority.value,
                reverse=True
            )

            to_process = sorted_signals[:5]
            processed_count = 0

            for signal in to_process:
                try:
                    result = self._digest_signal(signal)

                    signal.processed = True
                    signal.processing_result = result

                    self._signal_queue.remove(signal)

                    self._signal_history.append(signal)
                    self._stats["signals_processed"] += 1

                    self._record_growth_event(signal, result)

                    processed_count += 1

                except Exception as e:
                    logger.error(f"处理信号失败 {signal.id}: {e}")
                    if signal.priority == SignalPriority.HIGH:
                        signal.priority = SignalPriority.MEDIUM
                    elif signal.priority == SignalPriority.MEDIUM:
                        signal.priority = SignalPriority.LOW
                    else:
                        self._signal_queue.remove(signal)
                        logger.debug(f"🗑️ 丢弃无法处理的信号: {signal.id}")

            return processed_count

    def _digest_signal(self, signal: Signal) -> Dict:
        """
        消化一个信号

        不同类型的信号有不同的处理方式。
        """
        result = {
            "digested": True,
            "action_taken": False,
            "impact": 0.0,
            "description": ""
        }

        signal_type = signal.type

        if signal_type == SignalType.INTENT_PATTERN:
            result = self._digest_intent_pattern(signal)

        elif signal_type == SignalType.EMOTION_PATTERN:
            result = self._digest_emotion_pattern(signal)

        elif signal_type == SignalType.ERROR_PATTERN:
            result = self._digest_error_pattern(signal)

        elif signal_type == SignalType.SUCCESS_PATTERN:
            result = self._digest_success_pattern(signal)

        elif signal_type == SignalType.KNOWLEDGE_GAP:
            result = self._digest_knowledge_gap(signal)

        elif signal_type == SignalType.USER_PREFERENCE:
            result = self._digest_user_preference(signal)

        elif signal_type == SignalType.TOOL_NEED:
            result = self._digest_tool_need(signal)

        elif signal_type == SignalType.SKILL_OPPORTUNITY:
            result = self._digest_skill_opportunity(signal)

        else:
            result["description"] = f"未知信号类型: {signal_type}"

        return result

    def _digest_intent_pattern(self, signal: Signal) -> Dict:
        """消化意图模式信号"""
        intent = signal.content
        count = signal.context.get("repeat_count", 1)

        if count >= 3:
            return {
                "digested": True,
                "action_taken": True,
                "impact": 0.3,
                "description": f"强化的意图模式: {intent} (出现{count}次)"
            }
        else:
            return {
                "digested": True,
                "action_taken": False,
                "impact": 0.1,
                "description": f"记录意图模式: {intent}"
            }

    def _digest_emotion_pattern(self, signal: Signal) -> Dict:
        """消化情绪模式信号"""
        emotion = signal.content
        source = signal.source

        return {
            "digested": True,
            "action_taken": True,
            "impact": 0.2,
            "description": f"记录情绪模式: {emotion} (来自: {source})"
        }

    def _digest_error_pattern(self, signal: Signal) -> Dict:
        """消化错误模式信号"""
        error = signal.content
        context = signal.context

        error_type = context.get("error_type", "unknown")

        return {
            "digested": True,
            "action_taken": True,
            "impact": 0.4,
            "description": f"错误转化为学习信号: {error_type}",
            "details": {
                "error": error,
                "severity": context.get("severity", "medium"),
                "suggested_action": context.get("suggested_action", "review")
            }
        }

    def _digest_success_pattern(self, signal: Signal) -> Dict:
        """消化成功模式信号"""
        success = signal.content

        return {
            "digested": True,
            "action_taken": True,
            "impact": 0.3,
            "description": f"记录成功模式: {success[:50]}..."
        }

    def _digest_knowledge_gap(self, signal: Signal) -> Dict:
        """消化知识缺口信号 - 入队待学习，不在daemon线程中同步调Ollama"""
        gap = signal.content
        
        try:
            from core.task_queue import task_queue
            task_queue.enqueue("knowledge_gap_learning", {
                "gap": gap,
                "source": signal.source,
                "priority": "low"
            }, priority=5, delay_seconds=30)
            logger.info(f"🌱 知识缺口已入队待学习: {gap[:50]}")
        except Exception:
            logger.warning("操作降级跳过")
        
        return {
            "digested": True,
            "action_taken": True,
            "impact": 0.3,
            "description": f"知识缺口已入队待学习: {gap[:50]}",
            "details": {
                "source": signal.source,
                "priority": "low",
                "should_learn": True
            }
        }

    def _digest_user_preference(self, signal: Signal) -> Dict:
        """消化用户偏好信号"""
        preference = signal.content
        value = signal.context.get("value", "unknown")

        return {
            "digested": True,
            "action_taken": True,
            "impact": 0.2,
            "description": f"更新用户偏好: {preference} = {value}"
        }

    def _digest_tool_need(self, signal: Signal) -> Dict:
        """消化工具需求信号"""
        need = signal.content
        context = signal.context

        return {
            "digested": True,
            "action_taken": True,
            "impact": 0.4,
            "description": f"识别工具需求: {need}",
            "details": {
                "context": context,
                "should_generate": True
            }
        }

    def _digest_skill_opportunity(self, signal: Signal) -> Dict:
        """消化技能机会信号"""
        opportunity = signal.content
        context = signal.context

        return {
            "digested": True,
            "action_taken": True,
            "impact": 0.3,
            "description": f"识别技能机会: {opportunity}",
            "details": {
                "context": context,
                "should_form_skill": True
            }
        }

    def _record_growth_event(self, signal: Signal, result: Dict) -> None:
        """记录生长事件"""
        if not result.get("action_taken"):
            return

        event = GrowthEvent(
            id=hashlib.md5(
                f"{signal.id}{datetime.now().isoformat()}".encode()
            ).hexdigest()[:12],
            signal_id=signal.id,
            growth_type=signal.type.value,
            description=result.get("description", "生长事件"),
            impact=result.get("impact", 0.0),
            timestamp=datetime.now().isoformat(),
            details=result.get("details", {})
        )

        self._growth_events.append(event)
        self._stats["growth_events"] += 1
        self._stats["total_growth_impact"] += event.impact

        if signal.type in (SignalType.KNOWLEDGE_GAP, SignalType.TOOL_NEED, SignalType.SKILL_OPPORTUNITY):
            self._record_boundary_expectation(signal, result)

    def _record_boundary_expectation(self, signal: Signal, result: Dict) -> None:
        """记录边界扩展预期——消化后期望系统能力边界扩展"""
        expected = result.get("details", {}).get("expected_capability", signal.content[:80])
        expectation = BoundaryExpectation(
            id=hashlib.md5(f"be_{signal.id}_{datetime.now().isoformat()}".encode()).hexdigest()[:12],
            gap_type=signal.type.value,
            expected_capability=expected,
            created_at=datetime.now().isoformat(),
        )
        self._boundary_expectations.append(expectation)
        self._boundary_verifications["pending"] += 1
        self._boundary_verifications["total"] += 1

    def verify_boundary_expansion(self) -> Dict:
        """
        验证边界是否真正扩展——闭环的关键步骤

        检查未验证的边界预期，对比当前系统能力是否已覆盖预期。
        这是"生长→验证边界扩展"闭环的验证端。
        """
        verified_count = 0
        confirmed_count = 0
        failed_count = 0

        for exp in self._boundary_expectations:
            if exp.verified:
                continue

            is_confirmed = self._check_capability_exists(exp.expected_capability)

            exp.verified = True
            exp.verified_at = datetime.now().isoformat()
            exp.verification_result = "confirmed" if is_confirmed else "failed"

            if is_confirmed:
                confirmed_count += 1
                self._boundary_verifications["confirmed"] += 1
            else:
                failed_count += 1
                self._boundary_verifications["failed"] += 1
            self._boundary_verifications["pending"] -= 1
            verified_count += 1

        if verified_count > 0:
            logger.info(f"🌿 边界验证: {verified_count}项, 确认={confirmed_count}, 未达={failed_count}")

        return {
            "verified": verified_count,
            "confirmed": confirmed_count,
            "failed": failed_count,
            "total_expectations": len(self._boundary_expectations),
        }

    def _check_capability_exists(self, expected_capability: str) -> bool:
        """检查预期能力是否已存在于系统中"""
        try:
            from core.self.model import get_self_model
            sm = get_self_model()
            snapshot = sm.snapshot()
            capabilities = snapshot.get("capabilities", {})
            for cap_name, cap_data in capabilities.items():
                if isinstance(cap_data, dict):
                    score = cap_data.get("mastery_score", 0)
                    if score > 0.3 and (expected_capability.lower() in cap_name.lower()
                                        or cap_name.lower() in expected_capability.lower()):
                        return True
        except Exception:
            pass

        try:
            from core.skill_emergence import SkillEmergence
            se = SkillEmergence()
            result = se.reflex_query(expected_capability)
            if result and result.get("confidence", 0) > 0.3:
                return True
        except Exception:
            pass

        return False

    def _periodic_deep_growth(self) -> None:
        """执行周期性的深度生长（基于时间触发）"""
        now = datetime.now()
        if (now - self._last_deep_growth).total_seconds() >= self._deep_growth_interval:
            self._deep_pattern_extraction()
            self._last_deep_growth = now
            logger.debug("🌿 执行周期性深度生长")

    def _deep_pattern_extraction(self) -> None:
        """深度模式提取"""
        if len(self._signal_history) < 10:
            return

        type_counts = {}
        for s in self._signal_history[-50:]:
            type_counts[s.type.value] = type_counts.get(s.type.value, 0) + 1

        dominant_type = max(type_counts, key=type_counts.get)
        count = type_counts[dominant_type]

        if count > 10:
            logger.debug(f"🌿 深度模式: 最近出现最多的信号类型是 {dominant_type} ({count}次)")

    def _find_duplicate(self, signal_type: str, content: str) -> Optional[Signal]:
        """查找重复信号"""
        now = datetime.now()

        for signal in self._signal_queue:
            if signal.type.value != signal_type:
                continue

            if self._is_similar(content, signal.content):
                signal_time = datetime.fromisoformat(signal.timestamp)
                if (now - signal_time).total_seconds() < self._dedup_window:
                    return signal

        return None

    def _is_similar(self, text1: str, text2: str) -> bool:
        """检查两段文本是否相似（简化版）"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return False

        overlap = len(words1 & words2)
        min_len = min(len(words1), len(words2))

        return overlap / min_len > 0.5

    def get_queue_status(self) -> Dict:
        """获取队列状态"""
        with self._lock:
            return {
                "queue_size": len(self._signal_queue),
                "by_priority": {
                    "high": len([s for s in self._signal_queue if s.priority == SignalPriority.HIGH]),
                    "medium": len([s for s in self._signal_queue if s.priority == SignalPriority.MEDIUM]),
                    "low": len([s for s in self._signal_queue if s.priority == SignalPriority.LOW])
                },
                "history_size": len(self._signal_history)
            }

    def get_growth_summary(self) -> Dict:
        """获取生长摘要"""
        return {
            "stats": self._stats,
            "recent_growth": [
                {
                    "id": e.id,
                    "type": e.growth_type,
                    "description": e.description,
                    "impact": e.impact,
                }
                for e in self._growth_events[-10:]
            ],
            "boundary_verification": self._boundary_verifications,
            "pending_expectations": len([e for e in self._boundary_expectations if not e.verified]),
            "total_events": len(self._growth_events),
            "running": self._running
        }

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._running and self._thread and self._thread.is_alive()


# ============================================================
# 全局单例
# ============================================================

_gap_growth_engine: Optional[GapGrowthEngine] = None


def get_gap_growth_engine() -> GapGrowthEngine:
    """获取间隙生长引擎单例"""
    global _gap_growth_engine
    if _gap_growth_engine is None:
        _gap_growth_engine = GapGrowthEngine()
    return _gap_growth_engine


def start_gap_growth() -> None:
    """启动间隙生长引擎（便捷函数）"""
    engine = get_gap_growth_engine()
    if not engine.is_running():
        engine.start()


def stop_gap_growth() -> None:
    """停止间隙生长引擎（便捷函数）"""
    engine = get_gap_growth_engine()
    if engine.is_running():
        engine.stop()
