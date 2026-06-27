"""
对话认知引擎 - 从"单轮处理"到"场景理解"

核心理念：
- 每一轮用户输入，系统都会判断它"在这一段对话中是做什么的"
- 从"听见"到"听懂"再到"理解到位"

三层架构：
1. 感知层预处理（L1）：判断输入角色
2. 认知层深层理解（L3/L4）：推断真实意图
3. 自问自答验证（元认知层）：验证理解
"""

from .scene_perceiver import (
    ScenePerceiver,
    SceneRole,
    SceneHint
)

from .dialogue_understander import (
    DialogueUnderstander,
    UnderstandingHypothesis,
    UnderstandingCandidate,
    DialogueUnderstanding
)

from .self_verifier import (
    SelfVerifier,
    SelfVerificationResult
)

from .dialogue_cognitive_engine import (
    DialogueCognitiveEngine,
    process_dialogue,
    get_dialogue_engine
)

__all__ = [
    'ScenePerceiver',
    'SceneRole',
    'SceneHint',
    'DialogueUnderstander',
    'UnderstandingHypothesis',
    'UnderstandingCandidate',
    'DialogueUnderstanding',
    'SelfVerifier',
    'SelfVerificationResult',
    'DialogueCognitiveEngine',
    'process_dialogue',
    'get_dialogue_engine',
]