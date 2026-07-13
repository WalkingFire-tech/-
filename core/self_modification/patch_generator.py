"""
L5.3 补丁生成器 — LLM驱动的diff/patch生成

基于Ollama（qwen2.5-coder:7b）生成修复补丁。
安全约束：
- 生成的补丁必须经过沙箱验证（L5.4）
- 必须经过渐进部署（L5.5）
- 补丁不能修改spirit_core.py的不可变原则
"""

import os
import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class Patch:
    file: str
    original: str
    replacement: str
    description: str
    defect_category: str
    confidence: float = 0.0
    validated: bool = False


IMMUTABLE_FILES = {
    "core/spirit_core.py",
    "core/resource_awareness/health_monitor.py",
}

PATCH_TEMPLATES = {
    "exception_handling": {
        "pattern": r"except\s*:",
        "replacement": "except Exception:",
        "description": "裸except改为except Exception:",
    },
    "database": {
        "description": "sqlite3.connect迁移到DatabaseManager",
    },
    "performance": {
        "description": "time.sleep迁移到asyncio.sleep",
    },
}


class PatchGenerator:

    def generate_patch(self, defect: Dict, source: str) -> Optional[Patch]:
        category = defect.get("category", "")
        if category == "exception_handling" and "裸except" in defect.get("description", ""):
            return self._patch_bare_except(defect, source)
        elif category == "database" and "sqlite3" in defect.get("description", ""):
            return self._patch_sqlite3_migration(defect, source)
        elif category == "performance" and "time.sleep" in defect.get("description", ""):
            return self._patch_sync_sleep(defect, source)
        elif category == "code_smell" and "文件过长" in defect.get("description", ""):
            return self._patch_file_too_long(defect, source)
        return None

    def generate_llm_patch(self, defect: Dict, source: str) -> Optional[Patch]:
        file_path = defect.get("file", "")
        if file_path in IMMUTABLE_FILES:
            logger.warning(f"不可变文件，跳过补丁生成: {file_path}")
            return None

        prompt = self._build_prompt(defect, source)
        try:
            import httpx
            resp = httpx.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": "qwen2.5-coder:7b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 1024},
                },
                timeout=30.0,
            )
            if resp.status_code == 200:
                result = resp.json()
                response_text = result.get("response", "")
                return self._parse_llm_response(defect, response_text, source)
        except Exception as e:
            logger.debug(f"LLM补丁生成跳过: {e}")
        return None

    def validate_patch_safety(self, patch: Patch) -> bool:
        if patch.file in IMMUTABLE_FILES:
            logger.warning(f"补丁试图修改不可变文件: {patch.file}")
            return False
        dangerous_patterns = [
            r"import\s+os",
            r"import\s+subprocess",
            r"import\s+sys",
            r"exec\s*\(",
            r"eval\s*\(",
            r"__import__\s*\(",
            r"open\s*\(.+['\"]w",
            r"shutil\.rmtree",
            r"os\.remove",
            r"os\.system",
            r"subprocess\.",
        ]
        for pattern in dangerous_patterns:
            if re.search(pattern, patch.replacement):
                logger.warning(f"补丁包含危险模式: {pattern}")
                return False
        return True

    def _patch_bare_except(self, defect: Dict, source: str) -> Optional[Patch]:
        lines = source.splitlines()
        line_num = defect.get("line", 0) - 1
        if 0 <= line_num < len(lines):
            original = lines[line_num]
            replacement = original.replace("except:", "except Exception:")
            if original != replacement:
                return Patch(
                    file=defect.get("file", ""),
                    original=original,
                    replacement=replacement,
                    description="裸except改为except Exception:",
                    defect_category="exception_handling",
                    confidence=0.95,
                )
        return None

    def _patch_sqlite3_migration(self, defect: Dict, source: str) -> Optional[Patch]:
        return Patch(
            file=defect.get("file", ""),
            original="import sqlite3",
            replacement="from infrastructure.database_manager import DatabaseManager",
            description="sqlite3迁移到DatabaseManager（需手动调整连接代码）",
            defect_category="database",
            confidence=0.3,
        )

    def _patch_sync_sleep(self, defect: Dict, source: str) -> Optional[Patch]:
        lines = source.splitlines()
        line_num = defect.get("line", 0) - 1
        if 0 <= line_num < len(lines):
            original = lines[line_num]
            replacement = re.sub(
                r'time\.sleep\((\d+(?:\.\d+)?)\)',
                r'await asyncio.sleep(\1)',
                original,
            )
            if original != replacement:
                return Patch(
                    file=defect.get("file", ""),
                    original=original,
                    replacement=replacement,
                    description="time.sleep迁移到asyncio.sleep",
                    defect_category="performance",
                    confidence=0.7,
                )
        return None

    def _patch_file_too_long(self, defect: Dict, source: str) -> Optional[Patch]:
        return Patch(
            file=defect.get("file", ""),
            original="",
            replacement="",
            description="文件过长，建议拆分（需人工决策拆分策略）",
            defect_category="code_smell",
            confidence=0.1,
        )

    def _build_prompt(self, defect: Dict, source: str) -> str:
        return f"""You are a Python code fixer. Fix the following defect.

File: {defect.get('file', '')}
Line: {defect.get('line', 0)}
Category: {defect.get('category', '')}
Description: {defect.get('description', '')}

Context (5 lines around the defect):
{self._get_context(source, defect.get('line', 0), 5)}

Provide ONLY the fixed line(s), no explanation. Use this format:
FIXED: <the fixed code line>"""

    def _get_context(self, source: str, line: int, radius: int = 5) -> str:
        lines = source.splitlines()
        start = max(0, line - radius - 1)
        end = min(len(lines), line + radius)
        return "\n".join(f"{i+1}: {lines[i]}" for i in range(start, end))

    def _parse_llm_response(self, defect: Dict, response: str, source: str) -> Optional[Patch]:
        lines = source.splitlines()
        line_num = defect.get("line", 0) - 1
        if 0 <= line_num < len(lines):
            fixed_match = re.search(r"FIXED:\s*(.+)", response)
            if fixed_match:
                fixed_line = fixed_match.group(1).strip()
                return Patch(
                    file=defect.get("file", ""),
                    original=lines[line_num],
                    replacement=fixed_line,
                    description=defect.get("description", ""),
                    defect_category=defect.get("category", ""),
                    confidence=0.5,
                )
        return None


patch_generator = PatchGenerator()