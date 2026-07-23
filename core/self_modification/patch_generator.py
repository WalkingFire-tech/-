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


def _get_immutable_files():
    from core.self_modification import IMMUTABLE_FILES
    return IMMUTABLE_FILES

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
        file_path = defect.get("file", "")
        original_code = defect.get("original", "")
        try:
            from core.hashline_editor import HashlineEditor
            _hle = HashlineEditor()
            _hash_loc = _hle.locate(file_path, original_code)
            if _hash_loc:
                logger.debug(f"Hashline定位成功: hash={_hash_loc.content_hash[:8]}")
        except Exception:
            pass
        category = defect.get("category", "")
        description = defect.get("description", "")

        strategy_patch = self._query_strategy_library(category, description, source)
        if strategy_patch:
            return strategy_patch

        if category == "exception_handling" and "裸except" in description:
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
        if file_path in _get_immutable_files():
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
            replacement="from core.ports.adapters import get_storage_port",
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

    def _patch_file_too_long(self, defect, source):
        return None  # skip

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

    def _query_strategy_library(self, category: str, description: str, source: str) -> Optional[Patch]:
        try:
            from core.learning.strategy_library import strategy_library
            strategies = strategy_library.query_strategy(description, category=category)
            if not strategies:
                return None

            best = strategies[0]
            if best.confidence < 0.4:
                return None

            lines = source.splitlines()
            if not lines:
                return None

            logger.info(f"📋 策略库命中: #{best.id} (置信度{best.confidence:.2f}) → {best.action_patch[:40]}")

            strategy_library.record_outcome(best.id, success=True)

            return Patch(
                file="",
                original="",
                replacement=best.action_patch,
                description=f"策略库#{best.id}: {best.trigger_pattern}",
                defect_category=category,
                confidence=best.confidence,
            )
        except Exception as e:
            logger.debug(f"策略库查询跳过: {e}")
            return None


patch_generator = PatchGenerator()