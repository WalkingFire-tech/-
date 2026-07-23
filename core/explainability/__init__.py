"""
可解释性模块 — 让系统的决策过程可被人类理解

核心设计：
- 非侵入式：解释能力不改变现有决策逻辑，只附加解释层
- 可追溯：每个解释必须能追溯到具体的代码路径和数据
- 分层解释：简要解释(用户级) + 详细解释(开发者级)
- 渐进实现：先L5自修改解释，再扩展到其他决策点

解释覆盖5大决策域：
1. L5自修改：补丁选择、安全验证、自动审批、部署阶段
2. 路径选择：路由决策、资源保护、紧迫度覆盖
3. 真谛升级：四道筛子通过/拒绝原因
4. 资源分配：模式切换、路径削减、约束优化
5. 好奇心探索：缺口排序、提问选择

使用方式：
    from core.explainability import explain, Explanation, DecisionExplainer
    
    # 在决策点生成解释
    explanation = explain(
        domain="l5_modification",
        decision="auto_approve",
        outcome=True,
        inputs={"confidence": 0.95, "category": "exception_handling"},
        reasoning="置信度0.95超过阈值0.9，且类别在自动批准白名单中"
    )
    
    # 获取人类可读摘要
    print(explanation.summary())      # "自动批准：置信度0.95≥阈值0.9，类别exception_handling在白名单中"
    print(explanation.details())      # 完整决策链路
"""

from core.explainability.explanation_types import (
    Explanation,
    ExplanationLevel,
    DecisionDomain,
)
from core.explainability.decision_explainer import (
    DecisionExplainer,
    explain,
    get_explanation,
    get_recent_explanations,
)

__all__ = [
    "Explanation",
    "ExplanationLevel",
    "DecisionDomain",
    "DecisionExplainer",
    "explain",
    "get_explanation",
    "get_recent_explanations",
]