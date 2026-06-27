"""
内省命令处理器
提供 :why 和 :reflect 命令，让系统透明化
"""
from typing import Dict, Optional
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from core.decision_chain import decision_chain_manager
from core.learning_reflector import learning_reflector


class IntrospectionCommands:
    """
    内省命令处理器
    
    提供命令：
    - :why - 显示上次决策的完整推理路径
    - :reflect - 让系统对自己最近的行为进行反思总结
    - :stats - 显示决策链统计
    - :history - 显示决策链历史
    """
    
    def __init__(self):
        self.command_handlers = {
            ':why': self.handle_why,
            ':reflect': self.handle_reflect,
            ':stats': self.handle_stats,
            ':history': self.handle_history,
            ':help': self.handle_help
        }
    
    def is_introspection_command(self, user_input: str) -> bool:
        """判断是否是内省命令"""
        command = user_input.strip().lower()
        return any(command.startswith(cmd) for cmd in self.command_handlers.keys())
    
    def handle_command(self, user_input: str) -> str:
        """处理内省命令"""
        command = user_input.strip().lower()
        
        for cmd_prefix, handler in self.command_handlers.items():
            if command.startswith(cmd_prefix):
                args = command[len(cmd_prefix):].strip()
                return handler(args)
        
        return f"未知命令: {command}\n输入 :help 查看可用命令"
    
    def handle_why(self, args: str = "") -> str:
        """
        :why - 显示上次决策的完整推理路径
        
        用法：
            :why          - 显示最近一次决策链
            :why detailed - 显示详细信息
            :why <id>     - 显示指定ID的决策链
        """
        detailed = "detailed" in args.lower()
        
        # 尝试获取指定ID的决策链
        chain_id = None
        for word in args.split():
            if word.startswith("20") and "_" in word:  # 格式如 20260623_010203
                chain_id = word
                break
        
        if chain_id:
            chain = decision_chain_manager.get_chain_by_id(chain_id)
            if not chain:
                return f"❌ 未找到决策链: {chain_id}"
        else:
            chain = decision_chain_manager.get_last_chain()
            if not chain:
                return "❌ 暂无决策记录\n\n提示: 进行一次对话后，使用 :why 查看决策过程"
        
        return chain.visualize(detailed=detailed)
    
    def handle_reflect(self, args: str = "") -> str:
        """
        :reflect - 让系统对自己最近的行为进行反思总结
        
        用法：
            :reflect        - 反思最近一周
            :reflect day    - 反思最近一天
            :reflect week   - 反思最近一周
            :reflect month  - 反思最近一月
        """
        period = "week"
        
        if "day" in args.lower():
            period = "day"
        elif "month" in args.lower():
            period = "month"
        elif "week" in args.lower():
            period = "week"
        
        result = learning_reflector.generate_learning_report(period=period)
        return learning_reflector.format_report(result)
    
    def handle_stats(self, args: str = "") -> str:
        """
        :stats - 显示决策链统计
        """
        stats = decision_chain_manager.get_statistics()
        
        lines = []
        lines.append("=" * 70)
        lines.append("  决策链统计")
        lines.append("=" * 70)
        lines.append(f"\n总决策链数: {stats['total_chains']}")
        lines.append(f"总决策步骤: {stats.get('total_steps', 0)}")
        lines.append(f"平均步骤数: {stats['avg_steps']:.1f}")
        lines.append(f"平均置信度: {stats['avg_confidence']:.2f}")
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)
    
    def handle_history(self, args: str = "") -> str:
        """
        :history - 显示决策链历史
        """
        chains = decision_chain_manager.history[-10:]  # 最近10条
        
        if not chains:
            return "❌ 暂无决策历史"
        
        lines = []
        lines.append("=" * 70)
        lines.append("  决策链历史 (最近10条)")
        lines.append("=" * 70)
        
        for i, chain in enumerate(reversed(chains), 1):
            steps_count = len(chain.steps)
            confidence = chain.final_confidence
            output_preview = (chain.final_output or "")[:50]
            
            lines.append(f"\n{i}. #{chain.chain_id}")
            lines.append(f"   步骤: {steps_count}, 置信度: {confidence:.2f}")
            lines.append(f"   输出: {output_preview}...")
        
        lines.append("\n" + "=" * 70)
        lines.append("\n提示: 使用 :why <id> 查看详细决策链")
        
        return "\n".join(lines)
    
    def handle_help(self, args: str = "") -> str:
        """
        :help - 显示帮助信息
        """
        lines = []
        lines.append("=" * 70)
        lines.append("  内省命令帮助")
        lines.append("=" * 70)
        
        lines.append("\n【决策透明化】")
        lines.append("  :why              - 显示上次决策的完整推理路径")
        lines.append("  :why detailed     - 显示详细信息")
        lines.append("  :why <id>         - 显示指定ID的决策链")
        lines.append("  :stats            - 显示决策链统计")
        lines.append("  :history          - 显示决策链历史")
        
        lines.append("\n【学习反思】")
        lines.append("  :reflect          - 反思最近一周的学习")
        lines.append("  :reflect day      - 反思最近一天")
        lines.append("  :reflect month    - 反思最近一月")
        
        lines.append("\n【说明】")
        lines.append("  这些命令让系统从'黑盒'变成'透明盒子'")
        lines.append("  你可以清楚地看到系统是如何得出结论的")
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)


introspection_commands = IntrospectionCommands()


def process_introspection_command(user_input: str) -> Optional[str]:
    """
    处理内省命令的便捷函数
    
    Args:
        user_input: 用户输入
    
    Returns:
        如果是内省命令，返回处理结果；否则返回None
    """
    if introspection_commands.is_introspection_command(user_input):
        return introspection_commands.handle_command(user_input)
    return None