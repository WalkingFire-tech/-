"""
意图解析器单元测试
"""
import pytest
from core.services.intent_parser import IntentParser, Intent


class TestIntentParser:
    """意图解析器测试套件"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.parser = IntentParser()
    
    def test_meta_intent_capability_boundary(self):
        """测试能力边界识别"""
        text = "你的能力边界在哪里？"
        intent = self.parser.parse(text)
        
        assert intent.type == "meta", f"期望meta，实际{intent.type}"
        assert intent.confidence > 0.6, f"置信度过低: {intent.confidence}"
    
    def test_meta_intent_self_assessment(self):
        """测试自我评估识别"""
        text = "你如何决策？"
        intent = self.parser.parse(text)
        
        assert intent.type == "meta", f"期望meta，实际{intent.type}"
    
    def test_meta_intent_dialog_review(self):
        """测试对话回顾识别"""
        text = "回顾对话历史"
        intent = self.parser.parse(text)
        
        assert intent.type == "meta", f"期望meta，实际{intent.type}"
    
    def test_meta_intent_evolution(self):
        """测试自我进化识别"""
        test_cases = [
            "你如何自我进化？",
            "你觉得自己哪里需要改进？",
            "如何让你变得更好？",
            "你如何理解我的需求？"
        ]
        
        for text in test_cases:
            intent = self.parser.parse(text)
            assert intent.type == "meta", f"'{text}' 期望meta，实际{intent.type}"
    
    def test_code_intent(self):
        """测试代码意图识别"""
        test_cases = [
            "写一个冒泡排序",
            "生成快速排序代码",
            "实现一个递归函数",
            "帮我写个Python类"
        ]
        
        for text in test_cases:
            intent = self.parser.parse(text)
            assert intent.type == "code", f"'{text}' 期望code，实际{intent.type}"
    
    def test_question_intent(self):
        """测试问题意图识别"""
        test_cases = [
            "什么是机器学习？",
            "为什么天是蓝的？",
            "如何学习Python？",
            "解释一下量子力学"
        ]
        
        for text in test_cases:
            intent = self.parser.parse(text)
            assert intent.type == "question", f"'{text}' 期望question，实际{intent.type}"
    
    def test_calculation_intent(self):
        """测试计算意图识别"""
        test_cases = [
            "计算圆周率前100位",
            "输出π的数值",
            "求圆周率的值"
        ]
        
        for text in test_cases:
            intent = self.parser.parse(text)
            assert intent.type == "calculation", f"'{text}' 期望calculation，实际{intent.type}"
    
    def test_memory_intent(self):
        """测试记忆意图识别"""
        test_cases = [
            "记住这个配置",
            "我们刚才聊了什么？",
            "之前讨论的内容"
        ]
        
        for text in test_cases:
            intent = self.parser.parse(text)
            assert intent.type == "memory", f"'{text}' 期望memory，实际{intent.type}"
    
    def test_feedback_intent(self):
        """测试反馈意图识别"""
        test_cases = ["+1", "-1", "点赞", "好评"]
        
        for text in test_cases:
            intent = self.parser.parse(text)
            assert intent.type == "feedback", f"'{text}' 期望feedback，实际{intent.type}"
    
    def test_chat_intent_fallback(self):
        """测试闲聊意图降级"""
        test_cases = [
            "你好",
            "早上好",
            "谢谢"
        ]
        
        for text in test_cases:
            intent = self.parser.parse(text)
            assert intent.type == "chat", f"'{text}' 期望chat，实际{intent.type}"
    
    def test_confidence_calculation(self):
        """测试置信度计算"""
        # 明确的代码意图应该有高置信度
        intent = self.parser.parse("写一个冒泡排序算法的代码")
        assert intent.confidence > 0.7, f"明确意图置信度过低: {intent.confidence}"
        
        # 模糊意图应该有较低置信度
        intent = self.parser.parse("嗯")
        assert intent.confidence <= 0.6, f"模糊意图置信度过高: {intent.confidence}"
    
    def test_entity_extraction(self):
        """测试实体提取"""
        text = "写一个Python函数"
        intent = self.parser.parse(text)
        
        assert isinstance(intent.entities, dict), "entities应该是字典"
    
    def test_raw_text_preserved(self):
        """测试原始文本保留"""
        text = "你的能力边界在哪里？"
        intent = self.parser.parse(text)
        
        assert intent.raw_text == text, "原始文本应该被保留"


class TestIntentDataclass:
    """Intent数据类测试"""
    
    def test_intent_creation(self):
        """测试Intent创建"""
        intent = Intent(
            type="code",
            raw_text="写代码",
            entities={},
            confidence=0.9
        )
        
        assert intent.type == "code"
        assert intent.raw_text == "写代码"
        assert intent.confidence == 0.9
    
    def test_intent_default_confidence(self):
        """测试默认置信度"""
        intent = Intent(
            type="chat",
            raw_text="你好",
            entities={}
        )
        
        assert intent.confidence == 1.0, "默认置信度应为1.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])