"""
记忆系统 - 优化版本
改进上下文提取,提升长期记忆效果
"""
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from loguru import logger
from infrastructure.config_manager import config


class MemoryEntry:
    """记忆条目"""
    def __init__(self, timestamp: str, role: str, content: str):
        self.timestamp = timestamp
        self.role = role
        self.content = content
    
    def to_dict(self) -> Dict[str, str]:
        return {
            "timestamp": self.timestamp,
            "role": self.role,
            "content": self.content
        }
    
    def __str__(self) -> str:
        return f"[{self.timestamp}] {self.role}: {self.content}"


class CampfireLogger:
    """营火记忆系统"""
    
    def __init__(self, log_file: str = None):
        self.log_file = Path(log_file or config.get("memory.short_term.file_path", "campfire_log.txt"))
        self.max_rounds = config.get("memory.short_term.max_rounds", 5)
        
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
    
    def _parse_all_entries(self) -> List[MemoryEntry]:
        """解析所有记忆条目"""
        entries = []
        if not self.log_file.exists():
            return entries
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                match = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] (用户|拓荒者|Pioneer|User): (.+)', line)
                if match:
                    timestamp, role, content = match.groups()
                    if role in ["User", "Pioneer"]:
                        role = "用户" if role == "User" else "拓荒者"
                    entries.append(MemoryEntry(timestamp, role, content))
        
        return entries
    
    def get_recent_context(self, rounds: int = None) -> str:
        """获取最近N轮对话上下文"""
        if rounds is None:
            rounds = self.max_rounds
        
        entries = self._parse_all_entries()
        if not entries:
            return ""
        
        recent_entries = entries[-(rounds * 2):] if len(entries) >= rounds * 2 else entries
        
        context_lines = []
        for entry in recent_entries:
            context_lines.append(f"{entry.role}: {entry.content}")
        
        return "\n".join(context_lines)
    
    def get_conversation_summary(self, rounds: int = 3) -> str:
        """获取对话摘要(用于记忆查询)"""
        entries = self._parse_all_entries()
        if not entries:
            return "我们还没有开始对话。"
        
        recent_entries = entries[-(rounds * 2):] if len(entries) >= rounds * 2 else entries
        
        summary_parts = []
        for i, entry in enumerate(recent_entries):
            if entry.role == "用户":
                summary_parts.append(f"用户问了: {entry.content[:50]}...")
            else:
                summary_parts.append(f"拓荒者回答了相关内容")
        
        if not summary_parts:
            return "我们还没有开始对话。"
        
        return "、".join(summary_parts[-3:])
    
    def search_memory(self, keyword: str, limit: int = 5) -> List[MemoryEntry]:
        """搜索记忆"""
        entries = self._parse_all_entries()
        results = []
        
        for entry in reversed(entries):
            if keyword.lower() in entry.content.lower():
                results.append(entry)
                if len(results) >= limit:
                    break
        
        return results
    
    def get_user_info(self) -> Dict[str, str]:
        """提取用户信息(如名字等)"""
        entries = self._parse_all_entries()
        user_info = {}
        
        for entry in entries:
            if entry.role == "用户":
                name_match = re.search(r'我[叫是](.+?)(?:[,.。!!\s]|$)', entry.content)
                if name_match:
                    user_info["name"] = name_match.group(1).strip()
                    break
        
        return user_info
    
    def get_last_user_message(self) -> Optional[str]:
        """获取用户最后一条消息"""
        entries = self._parse_all_entries()
        for entry in reversed(entries):
            if entry.role == "用户":
                return entry.content
        return None
    
    def get_last_assistant_message(self) -> Optional[str]:
        """获取助手最后一条消息"""
        entries = self._parse_all_entries()
        for entry in reversed(entries):
            if entry.role == "拓荒者":
                return entry.content
        return None
    
    def clear_old_memories(self, keep_rounds: int = 10):
        """清理旧记忆,保留最近N轮"""
        entries = self._parse_all_entries()
        if len(entries) <= keep_rounds * 2:
            return
        
        keep_entries = entries[-(keep_rounds * 2):]
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"# 营火日志 - 清理于 {datetime.now()}\n")
            f.write("# 格式: [时间] 角色: 内容\n\n")
            for entry in keep_entries:
                f.write(f"{entry}\n")
        
        logger.info(f"已清理旧记忆,保留最近{keep_rounds}轮对话")
