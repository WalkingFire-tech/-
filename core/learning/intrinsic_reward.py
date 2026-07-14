"""
内在奖励机制 — 让系统获得"满足感"

灵感来源：哥德尔智能体的"经验抽象" + 强化学习的内在奖励
核心思想：当系统成功学习新知识、修复自身缺陷、解决悬而未决的问题时，
获得"内在满足感"，强化其自主学习和进化的动机。

奖励信号来源：
1. 学习奖励：成功学习新知识 (+0.3)
2. 修复奖励：成功修复代码缺陷 (+0.5)
3. 策略奖励：策略库新增高置信度策略 (+0.4)
4. 闭环奖励：闭环转化率提升 (+0.3)
5. 惩罚信号：重复犯同样的错误 (-0.2)

与存在层的关系：
- 存在层每次生长循环后查询内在奖励状态
- 奖励值高时增加生长频率，奖励值低时增加反思频率
"""

import time
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class RewardEvent:
    event_type: str
    value: float
    description: str
    timestamp: str = ""


class IntrinsicReward:
    REWARD_TYPES = {
        "learn_new_knowledge": 0.3,
        "fix_code_defect": 0.5,
        "add_high_confidence_strategy": 0.4,
        "close_loop_improvement": 0.3,
        "solve_long_standing_issue": 0.6,
        "repeat_same_error": -0.2,
        "failed_learning_attempt": -0.1,
    }

    def __init__(self):
        self._total_reward: float = 0.0
        self._recent_events: List[RewardEvent] = []
        self._max_recent = 50
        self._lock = threading.Lock()
        self._last_decay_time: float = time.time()

    def reward(self, event_type: str, description: str = "", custom_value: float = None):
        value = custom_value if custom_value is not None else self.REWARD_TYPES.get(event_type, 0.0)
        if value == 0.0:
            return

        event = RewardEvent(
            event_type=event_type,
            value=value,
            description=description[:100],
            timestamp=datetime.now().isoformat(),
        )

        with self._lock:
            self._total_reward += value
            self._recent_events.append(event)
            if len(self._recent_events) > self._max_recent:
                self._recent_events = self._recent_events[-self._max_recent:]

        if value > 0:
            logger.debug(f"✨ 内在奖励 +{value:.1f}: {event_type} ({description[:30]})")
        else:
            logger.debug(f"📉 内在惩罚 {value:.1f}: {event_type} ({description[:30]})")

    def get_satisfaction_level(self) -> float:
        with self._lock:
            if not self._recent_events:
                return 0.5

            recent_positive = sum(e.value for e in self._recent_events[-10:] if e.value > 0)
            recent_negative = sum(abs(e.value) for e in self._recent_events[-10:] if e.value < 0)

            if recent_positive + recent_negative == 0:
                return 0.5

            return min(max(recent_positive / (recent_positive + recent_negative), 0.0), 1.0)

    def should_explore(self) -> bool:
        satisfaction = self.get_satisfaction_level()
        return satisfaction < 0.6

    def should_consolidate(self) -> bool:
        satisfaction = self.get_satisfaction_level()
        return satisfaction >= 0.7

    def get_stats(self) -> Dict:
        with self._lock:
            positive = sum(e.value for e in self._recent_events if e.value > 0)
            negative = sum(abs(e.value) for e in self._recent_events if e.value < 0)
            return {
                "total_reward": round(self._total_reward, 2),
                "satisfaction": round(self.get_satisfaction_level(), 2),
                "recent_positive": round(positive, 2),
                "recent_negative": round(negative, 2),
                "event_count": len(self._recent_events),
                "should_explore": self.should_explore(),
            }


intrinsic_reward = IntrinsicReward()