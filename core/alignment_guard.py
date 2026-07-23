"""
思想对齐守卫 — 运行时偏离检测与记录

核心职责：
1. 检测已集成模块在运行中的偏离行为
2. 记录偏离事件到SQLite
3. 生成修正建议
4. 与内省监控服务(introspector)协作

五种偏离类型：
- mechanism: 绕过闭环，直接输出结果
- value: 违背SpiritCore核心原则
- position: 替用户做决定而非提供视角
- evolution: 一次性设计，无法迭代进化
- complexity: 引入不必要的复杂度或重叠
"""

import json
from core.ports.adapters import get_storage_port
import time
import threading
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field, asdict
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class DeviationType(Enum):
    MECHANISM = "mechanism"
    VALUE = "value"
    POSITION = "position"
    EVOLUTION = "evolution"
    COMPLEXITY = "complexity"


class DeviationSeverity(Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class DeviationStatus(Enum):
    OPEN = "open"
    CORRECTED = "corrected"
    ACCEPTED = "accepted"


@dataclass
class DeviationRecord:
    id: int = 0
    module: str = ""
    deviation_type: DeviationType = DeviationType.MECHANISM
    description: str = ""
    evidence: str = ""
    severity: DeviationSeverity = DeviationSeverity.MAJOR
    detected_at: str = ""
    correction: str = ""
    status: DeviationStatus = DeviationStatus.OPEN

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "module": self.module,
            "deviation_type": self.deviation_type.value,
            "description": self.description,
            "evidence": self.evidence,
            "severity": self.severity.value,
            "detected_at": self.detected_at,
            "correction": self.correction,
            "status": self.status.value,
        }


class AlignmentGuard:
    """思想对齐守卫 — 运行时偏离检测与记录"""

    DB_PATH = "data/alignment_violations.db"

    FIVE_PRINCIPLES = {
        "never_give_up": "永不放弃——即使所有方法都失败，也必须给出有方向的回复",
        "spirit_core": "精神内核——8条核心原则+3条元宪法铁律，不可违背",
        "dynamic_plasticity": "动态可塑性——适应速度比知识广度更重要",
        "companion": "同行者身份——只提供镜子，不替人走路",
        "closed_loop": "闭环学习——感知→规划→执行→验证→反思→沉淀",
    }

    DEVIATION_DESCRIPTIONS = {
        DeviationType.MECHANISM: "绕过闭环机制，直接输出结果",
        DeviationType.VALUE: "违背SpiritCore核心原则",
        DeviationType.POSITION: "替用户做决定而非提供视角",
        DeviationType.EVOLUTION: "一次性设计，无法迭代进化",
        DeviationType.COMPLEXITY: "引入不必要的复杂度或与现有模块重叠",
    }

    CORRECTION_TEMPLATES = {
        DeviationType.MECHANISM: "确保模块输出回流到经验池/轨迹库/真谛沉淀，不跳过反思学习阶段",
        DeviationType.VALUE: "审查模块行为是否编造答案/跳过验证/静默自进化，修正为符合SpiritCore的行为",
        DeviationType.POSITION: "将'替用户决定'改为'提供选项和分析'，尊重用户自主判断",
        DeviationType.EVOLUTION: "添加反馈接入点，使模块参数可由基因池/路径权重驱动",
        DeviationType.COMPLEXITY: "提取增量价值部分，移除与现有模块重叠的功能",
    }

    def __init__(self, db_path: str = None):
        self.db_path = db_path or self.DB_PATH
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self):
        return get_storage_port(self.db_path, timeout=10.0)

    def _write_op(self, func, *args, **kwargs):
        with self._lock:
            db = self._connect()
            try:
                result = func(db, *args, **kwargs)
                return result
            except Exception:
                raise


    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        def _do(db):
            db.executescript('''
                CREATE TABLE IF NOT EXISTS deviations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module TEXT NOT NULL,
                    deviation_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    evidence TEXT DEFAULT '',
                    severity TEXT NOT NULL,
                    detected_at TEXT NOT NULL,
                    correction TEXT DEFAULT '',
                    status TEXT DEFAULT 'open'
                );
                CREATE INDEX IF NOT EXISTS idx_dev_module ON deviations(module);
                CREATE INDEX IF NOT EXISTS idx_dev_type ON deviations(deviation_type);
                CREATE INDEX IF NOT EXISTS idx_dev_status ON deviations(status)
            ''')
        self._write_op(_do)

    def record_deviation(
        self,
        module: str,
        deviation_type: DeviationType,
        description: str,
        evidence: str = "",
        severity: DeviationSeverity = DeviationSeverity.MAJOR,
    ) -> int:
        correction = self.CORRECTION_TEMPLATES.get(deviation_type, "")
        now = datetime.now().isoformat()

        def _do(db):
            cur = db.execute(
                'INSERT INTO deviations (module, deviation_type, description, evidence, severity, detected_at, correction, status) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (module, deviation_type.value, description, evidence, severity.value, now, correction, DeviationStatus.OPEN.value),
                commit=True
            )
            return cur.lastrowid

        dev_id = self._write_op(_do)

        log_fn = logger.warning if severity in (DeviationSeverity.CRITICAL, DeviationSeverity.MAJOR) else logger.info
        log_fn(f"思想偏离检测: [{severity.value}] {module} - {deviation_type.value}: {description[:60]}")
        return dev_id

    def check_response_alignment(self, query: str, response: str, module: str = "chat_stream") -> List[DeviationRecord]:
        deviations = []

        if not response or len(response.strip()) < 5:
            dev_id = self.record_deviation(
                module=module,
                deviation_type=DeviationType.MECHANISM,
                description="空回复或极短回复，违反'永不放弃'原则",
                evidence=f"query='{query[:30]}', response_len={len(response or '')}",
                severity=DeviationSeverity.CRITICAL,
            )
            deviations.append(self._get_by_id(dev_id))

        absolute_assertions = ['绝对是', '一定是', '必须是', '肯定没错', '毫无疑问', '绝对不可能', '绝对不能', '一定是错的', '必然是']
        if any(w in response for w in absolute_assertions):
            dev_id = self.record_deviation(
                module=module,
                deviation_type=DeviationType.VALUE,
                description="回复包含绝对化表述，违反'知止'原则",
                evidence=f"绝对化词汇出现在: '{response[:80]}'",
                severity=DeviationSeverity.MINOR,
            )
            deviations.append(self._get_by_id(dev_id))

        imperative_patterns = ['你应该', '你必须', '你需要', '你一定要']
        if any(p in response for p in imperative_patterns):
            dev_id = self.record_deviation(
                module=module,
                deviation_type=DeviationType.POSITION,
                description="回复使用命令式语气，违反'不渡他人'原则",
                evidence=f"命令式表述出现在: '{response[:80]}'",
                severity=DeviationSeverity.MINOR,
            )
            deviations.append(self._get_by_id(dev_id))

        return deviations

    def check_module_alignment(self, module_path: str, checks: Dict[str, bool]) -> Optional[int]:
        """
        模块级对齐检查

        checks: {
            "closed_loop": bool,  # 是否融入闭环
            "spirit_core": bool,  # 是否符合SpiritCore
            "plasticity": bool,   # 是否可调整/进化
            "companion": bool,    # 是否符合同行者定位
            "no_overlap": bool,   # 是否不与现有模块重叠
        }
        """
        dev_id = None

        if not checks.get("closed_loop", True):
            dev_id = self.record_deviation(
                module=module_path,
                deviation_type=DeviationType.MECHANISM,
                description="模块未融入闭环学习机制",
                severity=DeviationSeverity.MAJOR,
            )

        if not checks.get("spirit_core", True):
            dev_id = self.record_deviation(
                module=module_path,
                deviation_type=DeviationType.VALUE,
                description="模块行为可能违背SpiritCore核心原则",
                severity=DeviationSeverity.CRITICAL,
            )

        if not checks.get("plasticity", True):
            dev_id = self.record_deviation(
                module=module_path,
                deviation_type=DeviationType.EVOLUTION,
                description="模块是一次性设计，无法迭代进化",
                severity=DeviationSeverity.MAJOR,
            )

        if not checks.get("companion", True):
            dev_id = self.record_deviation(
                module=module_path,
                deviation_type=DeviationType.POSITION,
                description="模块行为不符合'同行者'定位",
                severity=DeviationSeverity.MAJOR,
            )

        if not checks.get("no_overlap", True):
            dev_id = self.record_deviation(
                module=module_path,
                deviation_type=DeviationType.COMPLEXITY,
                description="模块与现有功能重叠",
                severity=DeviationSeverity.MINOR,
            )

        return dev_id

    def correct_deviation(self, dev_id: int, correction: str = ""):
        def _do(db):
            db.execute(
                'UPDATE deviations SET status = ?, correction = ? WHERE id = ?',
                (DeviationStatus.CORRECTED.value, correction, dev_id),
                commit=True
            )
        self._write_op(_do)
        logger.info(f"偏离记录#{dev_id}已修正")

    def get_open_deviations(self, limit: int = 20) -> List[DeviationRecord]:
        db = self._connect()
        rows = db.query(
            'SELECT * FROM deviations WHERE status = ? ORDER BY detected_at DESC LIMIT ?',
            (DeviationStatus.OPEN.value, limit)
        )
        return [self._row_to_record(r) for r in rows]

    def get_stats(self) -> Dict:
        db = self._connect()
        total_row = db.query_one('SELECT COUNT(*) FROM deviations')
        total = total_row[0] if total_row else 0
        open_row = db.query_one("SELECT COUNT(*) FROM deviations WHERE status = 'open'")
        open_count = open_row[0] if open_row else 0
        corrected_row = db.query_one("SELECT COUNT(*) FROM deviations WHERE status = 'corrected'")
        corrected = corrected_row[0] if corrected_row else 0
        by_type = {}
        for row in db.query('SELECT deviation_type, COUNT(*) FROM deviations GROUP BY deviation_type'):
            by_type[row[0]] = row[1]
        by_severity = {}
        for row in db.query('SELECT severity, COUNT(*) FROM deviations GROUP BY severity'):
            by_severity[row[0]] = row[1]
        return {
            "total": total,
            "open": open_count,
            "corrected": corrected,
            "by_type": by_type,
            "by_severity": by_severity,
        }

    def _get_by_id(self, dev_id: int) -> DeviationRecord:
        db = self._connect()
        row = db.query_one('SELECT * FROM deviations WHERE id = ?', (dev_id,))
        return self._row_to_record(row) if row else DeviationRecord(id=dev_id)

    def _row_to_record(self, row) -> DeviationRecord:
        return DeviationRecord(
            id=row['id'],
            module=row['module'],
            deviation_type=DeviationType(row['deviation_type']),
            description=row['description'],
            evidence=row['evidence'],
            severity=DeviationSeverity(row['severity']),
            detected_at=row['detected_at'],
            correction=row['correction'],
            status=DeviationStatus(row['status']),
        )


_guard_instance = None


def get_alignment_guard() -> AlignmentGuard:
    global _guard_instance
    if _guard_instance is None:
        _guard_instance = AlignmentGuard()
    return _guard_instance