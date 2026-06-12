"""
会话压缩模块 (Session Compressor)
参考Claude 5的微压缩机制，保留骨架，丢弃噪音
"""
import json
from typing import List, Dict, Any
from datetime import datetime
from loguru import logger


class SessionCompressor:
    """会话压缩器 - 当对话过长时生成结构化摘要"""
    
    def __init__(self, llm_adapter=None, max_context_length: int = 50):
        self.llm_adapter = llm_adapter
        self.max_context_length = max_context_length
        self.compression_threshold = 40  # 超过40轮触发压缩
        
    def should_compress(self, context_length: int) -> bool:
        """判断是否需要压缩"""
        return context_length > self.compression_threshold
    
    def compress(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        压缩会话历史
        
        Args:
            messages: 消息列表 [{"role": "user/assistant", "content": "..."}]
        
        Returns:
            压缩结果 {"summary": "...", "key_points": [...], "compressed": True}
        """
        if not self.should_compress(len(messages)):
            return {"messages": messages, "compressed": False}
        
        logger.info(f"触发会话压缩: {len(messages)}轮对话")
        
        # 提取关键信息
        key_points = self._extract_key_points(messages)
        
        # 生成摘要
        if self.llm_adapter:
            summary = self._generate_summary_with_llm(messages, key_points)
        else:
            summary = self._generate_simple_summary(messages, key_points)
        
        # 构建压缩结果
        compressed = {
            "summary": summary,
            "key_points": key_points,
            "original_length": len(messages),
            "compressed_at": datetime.now().isoformat(),
            "compressed": True
        }
        
        logger.info(f"会话压缩完成: {len(messages)}轮 → 摘要({len(summary)}字符)")
        
        return compressed
    
    def _extract_key_points(self, messages: List[Dict]) -> List[str]:
        """提取关键点"""
        key_points = []
        
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            
            # 提取用户的主要问题
            if role == "user" and len(content) > 10:
                # 简单提取：取前100字符作为关键点
                point = content[:100] + "..." if len(content) > 100 else content
                key_points.append(f"[用户] {point}")
            
            # 提取助手的关键结论
            elif role == "assistant":
                # 查找结论性语句
                if any(keyword in content for keyword in ["结论", "结果", "答案", "完成", "成功"]):
                    # 提取包含关键词的句子
                    sentences = content.split("。")
                    for sentence in sentences:
                        if any(keyword in sentence for keyword in ["结论", "结果", "答案"]):
                            key_points.append(f"[结论] {sentence[:80]}")
                            break
        
        # 最多保留10个关键点
        return key_points[:10]
    
    def _generate_summary_with_llm(self, messages: List[Dict], key_points: List[str]) -> str:
        """使用LLM生成摘要"""
        try:
            # 构建压缩prompt
            prompt = f"""请将以下对话历史压缩为结构化摘要。

对话历史（共{len(messages)}轮）:
{self._format_messages_for_summary(messages[:20])}  # 只取前20轮避免过长

已提取的关键点:
{chr(10).join(key_points)}

请按以下格式生成摘要:
【用户目标】
【关键决策】
【未解决问题】
【重要结论】
"""
            
            response = self.llm_adapter.generate(prompt)
            return response
            
        except Exception as e:
            logger.error(f"LLM生成摘要失败: {e}")
            return self._generate_simple_summary(messages, key_points)
    
    def _generate_simple_summary(self, messages: List[Dict], key_points: List[str]) -> str:
        """简单摘要（无LLM时使用）"""
        user_msgs = [m for m in messages if m["role"] == "user"]
        assistant_msgs = [m for m in messages if m["role"] == "assistant"]
        
        summary = f"""【会话摘要】
时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}
对话轮次: {len(user_msgs)}轮用户提问, {len(assistant_msgs)}轮AI回答

【关键点】
{chr(10).join(key_points) if key_points else "无明确关键点"}

【统计】
- 用户消息: {len(user_msgs)}条
- AI回复: {len(assistant_msgs)}条
- 压缩比: {len(messages)} → 1
"""
        return summary
    
    def _format_messages_for_summary(self, messages: List[Dict]) -> str:
        """格式化消息用于摘要生成"""
        lines = []
        for i, msg in enumerate(messages, 1):
            role = "用户" if msg["role"] == "user" else "AI"
            content = msg["content"][:200]  # 限制长度
            lines.append(f"{i}. [{role}] {content}")
        return "\n".join(lines)
    
    def decompress_for_context(self, compressed: Dict[str, Any]) -> str:
        """
        将压缩结果转换为可用于上下文的文本
        
        Args:
            compressed: 压缩结果
        
        Returns:
            可插入prompt的文本
        """
        if not compressed.get("compressed"):
            return ""
        
        return f"""
[历史会话摘要]
{compressed['summary']}

[关键决策点]
{chr(10).join(compressed.get('key_points', []))}

[注: 原始对话{compressed.get('original_length', 0)}轮已压缩]
"""


# 集成到Planner的示例
def integrate_with_planner():
    """
    在core/services/planner.py中集成会话压缩
    
    添加位置: Planner.__init__方法
    """
    code = """
from infrastructure.session_compressor import SessionCompressor

class Planner:
    def __init__(self, adapters):
        # ... 现有初始化代码 ...
        
        # 添加会话压缩器
        code_model = adapters.get("code_light") or adapters.get("mindchat")
        self.session_compressor = SessionCompressor(
            llm_adapter=code_model,
            max_context_length=50
        )
        
        # 压缩后的会话摘要
        self.compressed_session = None
    
    def _manage_context_length(self):
        '''管理上下文长度，必要时压缩'''
        if len(self.context_buffer) > self.session_compressor.compression_threshold:
            # 压缩旧会话
            self.compressed_session = self.session_compressor.compress(
                self.context_buffer[:-10]  # 保留最近10轮
            )
            
            # 清空旧消息，保留最近10轮
            self.context_buffer = self.context_buffer[-10:]
            
            logger.info("会话已压缩，释放上下文空间")
    
    def _build_prompt(self, intent, context):
        '''构建prompt时考虑压缩摘要'''
        # ... 现有构建逻辑 ...
        
        # 如果有压缩摘要，插入到prompt开头
        if self.compressed_session:
            summary_text = self.session_compressor.decompress_for_context(
                self.compressed_session
            )
            prompt = summary_text + "\\n\\n" + prompt
        
        return prompt
"""
    return code


if __name__ == "__main__":
    # 测试会话压缩
    print("=" * 60)
    print("会话压缩模块测试")
    print("=" * 60)
    
    # 创建测试数据
    test_messages = [
        {"role": "user", "content": "如何实现一个快速排序算法？"},
        {"role": "assistant", "content": "快速排序的基本思路是选择一个基准元素...结论：时间复杂度O(n log n)"},
        {"role": "user", "content": "能给出Python实现吗？"},
        {"role": "assistant", "content": "当然，这是Python实现...完成，已测试通过"},
    ] * 15  # 60轮对话
    
    # 创建压缩器
    compressor = SessionCompressor(max_context_length=50)
    
    # 测试压缩
    print(f"\n测试数据: {len(test_messages)}轮对话")
    print(f"压缩阈值: {compressor.compression_threshold}轮")
    print(f"需要压缩: {compressor.should_compress(len(test_messages))}")
    
    # 执行压缩
    result = compressor.compress(test_messages)
    
    print("\n压缩结果:")
    print(f"  压缩状态: {result['compressed']}")
    print(f"  原始长度: {result.get('original_length', 0)}轮")
    print(f"  摘要长度: {len(result['summary'])}字符")
    print(f"\n摘要内容:")
    print(result['summary'])
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)