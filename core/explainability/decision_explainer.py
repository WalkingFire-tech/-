"""
决策解释器 — 可解释性模块的核心引擎

提供：
- explain(): 在决策点生成解释（非侵入式，不改变决策逻辑）
- get_explanation(): 按ID查询历史解释
- get_recent_explanations(): 按域查询最近解释
- DecisionExplainer: 可扩展的领域解释器基类

设计原则：
- 解释生成是纯附加操作，不影响决策结果
- 解释存储在内存环形缓冲区中（最近1000条）
- 支持按域/按时间范围查询
"""

import uuid
from collections import deque
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional

from core.explainability.explanation_types import (
    DecisionDomain,
    Explanation,
)

_MAX_STORED = 1000


class DecisionExplainer:
    """
    领域解释器基类
    
    子类实现 explain_*() 方法，为特定决策域生成解释。
    """

    domain: DecisionDomain = DecisionDomain.L5_MODIFICATION

    def explain_decision(self, decision: str, outcome: Any,
                         inputs: Dict[str, Any], **kwargs) -> Explanation:
        raise NotImplementedError


_explanation_store: deque = deque(maxlen=_MAX_STORED)
_store_lock = Lock()
_explainers: Dict[DecisionDomain, DecisionExplainer] = {}


def register_explainer(explainer: DecisionExplainer) -> None:
    _explainers[explainer.domain] = explainer


def explain(domain: DecisionDomain, decision: str, outcome: Any,
            reasoning: str = "", inputs: Dict[str, Any] = None,
            context: Dict[str, Any] = None, alternatives: List[str] = None,
            trace: List[Dict[str, Any]] = None) -> Explanation:
    """
    在决策点生成解释
    
    Args:
        domain: 决策域
        decision: 决策名称（如 "auto_approve", "route_fast"）
        outcome: 决策结果
        reasoning: 人类可读的决策原因
        inputs: 决策输入数据
        context: 决策上下文
        alternatives: 被排除的备选方案
        trace: 决策链路（多步骤决策的中间步骤）
    
    Returns:
        Explanation对象
    """
    exp = Explanation(
        domain=domain,
        decision=decision,
        outcome=outcome,
        reasoning=reasoning,
        inputs=inputs or {},
        context=context or {},
        alternatives=alternatives or [],
        trace=trace or [],
    )
    exp._id = str(uuid.uuid4())[:8]

    with _store_lock:
        _explanation_store.append(exp)

    return exp


def get_explanation(explanation_id: str) -> Optional[Explanation]:
    with _store_lock:
        for exp in _explanation_store:
            if exp._id == explanation_id:
                return exp
    return None


def get_recent_explanations(domain: Optional[DecisionDomain] = None,
                            limit: int = 20) -> List[Explanation]:
    with _store_lock:
        results = list(_explanation_store)
    if domain is not None:
        results = [e for e in results if e.domain == domain]
    results.reverse()
    return results[:limit]


def clear_store() -> int:
    with _store_lock:
        count = len(_explanation_store)
        _explanation_store.clear()
    return count