from core.ports.llm_port import LLMPort
import random

class MockAdapter(LLMPort):
    @property
    def model_name(self) -> str:
        return "Mock/回声"
    
    def generate(self, prompt: str, **kwargs) -> str:
        # 模拟回复：回显前50字 + 一些随机风趣
        short = prompt[:100]
        responses = [
            f"🔥 拓荒者听到你说：{short}…… 这很有趣。我们继续探索。",
            f"💡 关于「{short}」，我想和你多聊聊。不过现在我只是模拟模式，等配置好真实模型，我会更有用。",
            f"📡 信号已收到。你说的 '{short}' 让我想起宇宙中的一片星云。"
        ]
        return random.choice(responses)
