import os
from datetime import datetime
from pathlib import Path

class CampfireLogger:
    def __init__(self, log_file: str = "campfire_log.txt"):
        self.log_file = Path(log_file)
        # 如果文件不存在，创建并写入 header
        if not self.log_file.exists():
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(f"# 营火日志 - 创建于 {datetime.now()}\n")
                f.write("# 格式: [时间] 角色: 内容\n\n")

    def log_user(self, message: str):
        """记录用户消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] 用户: {message}\n")

    def log_assistant(self, message: str):
        """记录助手消息"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] 拓荒者: {message}\n")

    def get_recent_context(self, lines: int = 10) -> str:
        """获取最近的对话上下文（用于后续实现记忆注入）"""
        if not self.log_file.exists():
            return ""
        with open(self.log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        # 跳过前面的注释行，取最后 N 条对话（每条以 [时间] 开头）
        recent = []
        for line in reversed(all_lines):
            if line.startswith("[") and ("用户:" in line or "拓荒者:" in line):
                recent.insert(0, line.strip())
                if len(recent) >= lines:
                    break
        return "\n".join(recent)
