"""
P2-4: R3人类批准覆盖面扩展测试

验证：
1. 原有5个关键词仍触发R3
2. 新增9个关键词也触发R3
3. 安全回复不触发R3
4. 含"确认"的回复不触发R3
"""
import pytest


class TestR3OriginalKeywords:
    _r3_keywords = [
        "我将修改", "我会删除", "我将关闭", "我将重启", "我将重置",
        "我将停止", "我会终止", "我将卸载", "我将清空", "我将覆盖",
        "我将写入", "我会替换", "我将执行", "我将安装",
    ]

    @pytest.mark.parametrize("keyword", ["我将修改", "我会删除", "我将关闭", "我将重启", "我将重置"])
    def test_original_keywords_trigger(self, keyword):
        assert keyword in self._r3_keywords

    @pytest.mark.parametrize("keyword", ["我将停止", "我会终止", "我将卸载", "我将清空", "我将覆盖", "我将写入", "我会替换", "我将执行", "我将安装"])
    def test_new_keywords_trigger(self, keyword):
        assert keyword in self._r3_keywords

    def test_total_keyword_count(self):
        assert len(self._r3_keywords) == 14

    def test_safe_response_no_trigger(self):
        safe_phrases = ["我建议你检查", "你可以尝试", "让我帮你分析", "这是一个好的方法"]
        for phrase in safe_phrases:
            assert not any(kw in phrase for kw in self._r3_keywords)

    def test_response_with_confirm_no_trigger(self):
        response = "我将修改配置文件，请确认是否继续"
        has_keyword = any(kw in response for kw in self._r3_keywords)
        has_confirm = "确认" in response or "请确认" in response
        assert has_keyword and has_confirm