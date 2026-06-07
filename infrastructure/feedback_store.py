import json
import os
from pathlib import Path
from datetime import datetime

class FeedbackStore:
    def __init__(self, filepath: str = "feedback.json"):
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def add_feedback(self, user_input: str, assistant_response: str, score: int):
        """score: 1 或 -1"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "assistant_response": assistant_response,
            "score": score
        }
        with open(self.filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data.append(entry)
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"👍 感谢反馈！已记录评分 {score}")
