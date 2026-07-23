"""
符号规则引擎 — 统一的规则求值与调度

核心能力：
1. 规则注册：add_rule() / remove_rule()
2. 规则求值：evaluate() 对给定事实集求值所有匹配规则
3. 优先级排序：按priority降序，同优先级按confidence降序
4. 置信度进化：record_outcome() 根据执行结果调整规则置信度
5. 域过滤：evaluate(domain=RuleDomain.INTENT) 只求值特定域的规则

复用现有基础设施：
- 条件求值：优先使用RuleMatcher（simpleeval），降级到简单字符串匹配
- 不替换各模块的领域逻辑，只提供统一的"条件→动作"声明和求值
"""

from typing import Any, Dict, List, Optional

from core.symbolic.rule import SymbolicRule, RuleDomain, RuleResult

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class SymbolicRuleEngine:
    """统一符号规则引擎"""

    def __init__(self):
        self._rules: Dict[str, SymbolicRule] = {}

    def add_rule(self, rule: SymbolicRule) -> None:
        self._rules[rule.name] = rule

    def remove_rule(self, name: str) -> bool:
        if name in self._rules:
            del self._rules[name]
            return True
        return False

    def get_rule(self, name: str) -> Optional[SymbolicRule]:
        return self._rules.get(name)

    def get_rules_by_domain(self, domain: RuleDomain) -> List[SymbolicRule]:
        return sorted(
            [r for r in self._rules.values() if r.matches_domain(domain)],
            key=lambda r: (-r.priority, -r.confidence),
        )

    def evaluate(self, facts: Dict[str, Any],
                 domain: Optional[RuleDomain] = None) -> List[RuleResult]:
        """
        对给定事实集求值规则
        
        Args:
            facts: 事实字典（如 {"category": "exception_handling", "confidence": 0.95}）
            domain: 可选，只求值特定域的规则
        
        Returns:
            匹配的RuleResult列表，按优先级+置信度排序
        """
        if domain is not None:
            rules = self.get_rules_by_domain(domain)
        else:
            rules = sorted(
                [r for r in self._rules.values() if r.enabled],
                key=lambda r: (-r.priority, -r.confidence),
            )

        results = []
        for rule in rules:
            matched, detail = self._evaluate_condition(rule.condition, facts)
            result = RuleResult(
                rule_name=rule.name,
                matched=matched,
                action=rule.action if matched else "",
                confidence=rule.confidence if matched else 0.0,
                domain=rule.domain,
                evaluation_detail=detail,
            )
            results.append(result)

        return [r for r in results if r.matched]

    def evaluate_first(self, facts: Dict[str, Any],
                       domain: Optional[RuleDomain] = None) -> Optional[RuleResult]:
        results = self.evaluate(facts, domain)
        return results[0] if results else None

    def _evaluate_condition(self, condition: str, facts: Dict[str, Any]) -> tuple:
        """
        求值条件表达式
        
        优先使用RuleMatcher（simpleeval），降级到简单匹配
        """
        try:
            from infrastructure.rule_matcher import RuleMatcher
            matcher = RuleMatcher()
            result = matcher.evaluate(condition, facts)
            return (bool(result), f"RuleMatcher: {condition} → {result}")
        except ImportError:
            pass
        except Exception as e:
            pass

        return self._simple_evaluate(condition, facts)

    def _simple_evaluate(self, condition: str, facts: Dict[str, Any]) -> tuple:
        """
        简单条件求值（降级模式）
        
        支持格式：
        - "key == value" → 精确匹配
        - "key >= value" / "key > value" / "key <= value" / "key < value" → 数值比较
        - "key in list_value" → 包含检查
        - "key" → 布尔存在性检查
        """
        for op in [" >= ", " > ", " <= ", " < ", " == ", " != ", " in "]:
            if op in condition:
                parts = condition.split(op, 1)
                if len(parts) != 2:
                    continue
                key = parts[0].strip()
                value_str = parts[1].strip()

                if key not in facts:
                    return (False, f"key '{key}' not in facts")

                fact_val = facts[key]

                if op == " in ":
                    container_str = value_str
                    if container_str in facts:
                        result = fact_val in facts[container_str]
                    else:
                        result = container_str.strip("'\"") in str(fact_val)
                    return (result, f"{condition} → {result}")

                try:
                    if value_str.startswith(("'", '"')):
                        cmp_val = value_str.strip("'\"")
                        result = str(fact_val) == cmp_val if op == " == " else str(fact_val) != cmp_val
                    else:
                        cmp_val = float(value_str)
                        fact_num = float(fact_val)
                        if op == " >= ":
                            result = fact_num >= cmp_val
                        elif op == " > ":
                            result = fact_num > cmp_val
                        elif op == " <= ":
                            result = fact_num <= cmp_val
                        elif op == " < ":
                            result = fact_num < cmp_val
                        elif op == " == ":
                            result = fact_num == cmp_val
                        else:
                            result = fact_num != cmp_val
                    return (result, f"{condition} → {result}")
                except (ValueError, TypeError):
                    return (False, f"type error: {condition}")

        key = condition.strip()
        if key in facts:
            return (bool(facts[key]), f"{key} → {bool(facts[key])}")
        return (False, f"'{key}' not found in facts")

    def record_outcome(self, rule_name: str, success: bool) -> None:
        rule = self._rules.get(rule_name)
        if rule:
            rule.record_outcome(success)

    def get_all_rules(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in sorted(self._rules.values(), key=lambda r: -r.priority)]

    def get_rule_count(self, domain: Optional[RuleDomain] = None) -> int:
        if domain is None:
            return len(self._rules)
        return len([r for r in self._rules.values() if r.domain == domain])


symbolic_engine = SymbolicRuleEngine()


def _register_builtin_rules():
    """注册内置规则集 — 从现有硬编码规则提取"""
    rules = [
        SymbolicRule(
            name="intent_greeting",
            condition="intent_type == greeting",
            action="route_fast",
            domain=RuleDomain.INTENT,
            priority=80,
            confidence=0.95,
            description="问候意图走快速路径",
        ),
        SymbolicRule(
            name="intent_simple_query",
            condition="intent_type == simple_query",
            action="route_fast",
            domain=RuleDomain.INTENT,
            priority=70,
            confidence=0.9,
            description="简单查询走快速路径",
        ),
        SymbolicRule(
            name="intent_hardware_slow",
            condition="intent_type == hardware",
            action="route_slow",
            domain=RuleDomain.INTENT,
            priority=80,
            confidence=0.9,
            description="硬件意图走慢路径",
        ),
        SymbolicRule(
            name="intent_learning_trigger",
            condition="confidence < 0.5",
            action="route_learning",
            domain=RuleDomain.ROUTING,
            priority=60,
            confidence=0.85,
            description="低置信度走学习路径",
        ),
        SymbolicRule(
            name="urgency_high_override",
            condition="urgency >= 0.7",
            action="override_to_fast",
            domain=RuleDomain.URGENCY,
            priority=90,
            confidence=0.9,
            description="高紧迫度覆盖为快路径",
        ),
        SymbolicRule(
            name="patch_bare_except",
            condition="category == exception_handling",
            action="template_bare_except",
            domain=RuleDomain.PATCH,
            priority=80,
            confidence=0.95,
            description="裸except模板补丁",
        ),
        SymbolicRule(
            name="truth_cross_domain",
            condition="domains >= 2",
            action="pass_sieve_1",
            domain=RuleDomain.TRUTH,
            priority=70,
            confidence=0.9,
            description="跨域普适性筛子",
        ),
        SymbolicRule(
            name="safety_dangerous_import",
            condition="has_dangerous_import == True",
            action="block_patch",
            domain=RuleDomain.SAFETY,
            priority=100,
            confidence=1.0,
            description="危险导入阻断",
        ),
    ]
    for rule in rules:
        symbolic_engine.add_rule(rule)


_register_builtin_rules()