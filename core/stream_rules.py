"""
Time-Traveling Stream Rules - 从oh-my-pi移植
实时监控流，触发规则时中断、注入、重试
"""
import asyncio
from typing import Callable, Any, AsyncGenerator, List
from dataclasses import dataclass
from loguru import logger

@dataclass
class StreamRule:
    """流式规则"""
    name: str
    condition: Callable[[Any], bool]  # 触发条件
    action: Callable[[Any], str]      # 修正动作（返回注入内容）
    max_retries: int = 3              # 最大重试次数
    
    def __str__(self):
        return f"Rule({self.name})"


class StreamInterrupter:
    """
    流中断器
    实现omp的Time-Traveling Stream Rules机制
    """
    
    def __init__(self, rules: List[StreamRule] = None):
        self.rules = rules or []
        self.retry_count = {}
        self.checkpoints = []
    
    def add_rule(self, rule: StreamRule):
        """添加规则"""
        self.rules.append(rule)
        logger.info(f"添加流规则: {rule.name}")
    
    async def apply(
        self, 
        stream: AsyncGenerator,
        checkpoint_data: Any = None
    ) -> AsyncGenerator:
        """
        应用规则到流
        
        Args:
            stream: 输入流
            checkpoint_data: 检查点数据（用于重试）
            
        Yields:
            处理后的流内容
        """
        buffer = []
        
        async for chunk in stream:
            buffer.append(chunk)
            
            # 检查所有规则
            for rule in self.rules:
                if rule.condition(chunk):
                    logger.warning(f"触发规则: {rule.name}")
                    
                    # 检查重试次数
                    rule_key = rule.name
                    self.retry_count[rule_key] = self.retry_count.get(rule_key, 0) + 1
                    
                    if self.retry_count[rule_key] > rule.max_retries:
                        logger.error(f"规则 {rule.name} 重试次数超限")
                        yield chunk
                        continue
                    
                    # 生成注入内容
                    injection = rule.action(chunk)
                    logger.info(f"注入修正: {injection[:50]}...")
                    
                    # 保存检查点
                    self.checkpoints.append({
                        "rule": rule.name,
                        "buffer": buffer.copy(),
                        "checkpoint_data": checkpoint_data
                    })
                    
                    # 发送注入内容
                    yield f"\n[系统修正]: {injection}\n"
                    
                    # 重试（这里简化处理，实际应该从检查点重新开始流）
                    break
            else:
                # 没有触发规则，正常输出
                yield chunk


class RuleBuilder:
    """规则构建器"""
    
    @staticmethod
    def prevent_hallucination() -> StreamRule:
        """防止幻觉规则"""
        def condition(chunk):
            # 检测常见的幻觉模式
            hallucination_patterns = [
                "我确定",
                "肯定是",
                "毫无疑问",
                "100%确定"
            ]
            if isinstance(chunk, str):
                return any(pattern in chunk for pattern in hallucination_patterns)
            return False
        
        def action(chunk):
            return "请谨慎表达，避免绝对化陈述。使用'可能'、'或许'等词汇。"
        
        return StreamRule(
            name="prevent_hallucination",
            condition=condition,
            action=action
        )
    
    @staticmethod
    def prevent_code_injection() -> StreamRule:
        """防止代码注入规则"""
        def condition(chunk):
            # 检测可疑的代码模式
            suspicious_patterns = [
                "exec(",
                "eval(",
                "__import__",
                "os.system",
                "subprocess.call"
            ]
            if isinstance(chunk, str):
                return any(pattern in chunk for pattern in suspicious_patterns)
            return False
        
        def action(chunk):
            return "检测到潜在危险的代码模式，请使用更安全的方式实现。"
        
        return StreamRule(
            name="prevent_code_injection",
            condition=condition,
            action=action
        )
    
    @staticmethod
    def enforce_type_safety() -> StreamRule:
        """强制类型安全规则"""
        def condition(chunk):
            # 检测类型不安全的模式
            unsafe_patterns = [
                "any",
                ": Any",
                "# type: ignore"
            ]
            if isinstance(chunk, str):
                return any(pattern in chunk for pattern in unsafe_patterns)
            return False
        
        def action(chunk):
            return "建议使用具体的类型注解，避免使用Any。"
        
        return StreamRule(
            name="enforce_type_safety",
            condition=condition,
            action=action
        )
    
    @staticmethod
    def prevent_long_output(max_length: int = 1000) -> StreamRule:
        """防止输出过长规则"""
        accumulated_length = [0]  # 使用列表以便在闭包中修改
        
        def condition(chunk):
            if isinstance(chunk, str):
                accumulated_length[0] += len(chunk)
                return accumulated_length[0] > max_length
            return False
        
        def action(chunk):
            return "输出过长，建议分段处理或提供摘要。"
        
        return StreamRule(
            name="prevent_long_output",
            condition=condition,
            action=action
        )


async def demo_stream_rules():
    """演示流规则"""
    
    # 创建规则集
    rules = [
        RuleBuilder.prevent_hallucination(),
        RuleBuilder.prevent_code_injection(),
        RuleBuilder.enforce_type_safety(),
    ]
    
    interrupter = StreamInterrupter(rules)
    
    # 模拟流
    async def mock_stream():
        texts = [
            "这是一个正常的输出。",
            "我确定这个方案是正确的。",  # 触发幻觉规则
            "使用exec('code')来执行。",   # 触发代码注入规则
            "def foo(x: Any): pass",      # 触发类型安全规则
            "最后一段正常输出。"
        ]
        for text in texts:
            yield text
            await asyncio.sleep(0.1)
    
    # 应用规则
    print("\n=== 流规则演示 ===\n")
    async for chunk in interrupter.apply(mock_stream()):
        print(chunk)


if __name__ == "__main__":
    asyncio.run(demo_stream_rules())