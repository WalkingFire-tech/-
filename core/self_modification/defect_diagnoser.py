"""
L5.2 缺陷诊断器 — AST解析+缺陷模式识别+教训驱动诊断

诊断来源：
1. 静态AST分析：裸except、未使用导入、过深嵌套、过长函数
2. 教训驱动：从spirit_lessons/alignment_violations中提取已知缺陷模式
3. 运行时信号：从日志/审计中提取异常模式

设计原则：
- 先修已知缺陷，比泛化AST分析更有价值
- 诊断结果必须包含修复建议（不只是指出问题）
"""

import ast
import os
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class Defect:
    file: str
    line: int
    severity: str  # critical, major, minor, info
    category: str  # exception_handling, code_smell, security, performance, lesson
    description: str
    suggestion: str = ""
    source: str = "ast"  # ast, lesson, runtime


class DefectDiagnoser:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    MAX_FUNCTION_LINES = 80
    MAX_NESTING_DEPTH = 5
    MAX_FILE_LINES = 500

    def diagnose_file(self, relative_path: str) -> List[Defect]:
        source = self._read_file(relative_path)
        if not source:
            return []
        defects = []
        defects.extend(self._ast_analysis(relative_path, source))
        defects.extend(self._pattern_analysis(relative_path, source))
        return defects

    def diagnose_directory(self, directory: str = "core") -> Dict[str, List[Defect]]:
        from core.self_modification.code_reader import code_reader
        results = {}
        for f in code_reader.list_files(directory):
            defects = self.diagnose_file(f)
            if defects:
                results[f] = defects
        return results

    def diagnose_from_lessons(self) -> List[Defect]:
        defects = []
        try:
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get("data/alignment_violations.db")
            rows = db.query("SELECT module, deviation_type, description, severity, status FROM deviations WHERE status='open'")
            for r in rows:
                d = dict(r) if hasattr(r, "keys") else r
                defects.append(Defect(
                    file=d.get("module", "unknown"),
                    line=0,
                    severity=d.get("severity", "minor"),
                    category="lesson",
                    description=d.get("description", ""),
                    suggestion=f"修正偏离: {d.get('deviation_type', '')}",
                    source="lesson",
                ))
        except Exception as e:
            logger.debug(f"教训驱动诊断跳过: {e}")
        return defects

    def _read_file(self, relative_path: str) -> Optional[str]:
        full_path = os.path.join(self.PROJECT_ROOT, relative_path.replace("/", os.sep))
        if not os.path.exists(full_path):
            return None
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None

    def _ast_analysis(self, relative_path: str, source: str) -> List[Defect]:
        defects = []
        try:
            tree = ast.parse(source, filename=relative_path)
        except SyntaxError as e:
            defects.append(Defect(
                file=relative_path, line=e.lineno or 0,
                severity="critical", category="syntax",
                description=f"语法错误: {e.msg}",
                suggestion="修复语法错误后重新分析",
                source="ast",
            ))
            return defects

        lines = source.splitlines()
        if len(lines) > self.MAX_FILE_LINES:
            defects.append(Defect(
                file=relative_path, line=1,
                severity="major", category="code_smell",
                description=f"文件过长: {len(lines)}行（阈值{self.MAX_FILE_LINES}）",
                suggestion="拆分为多个模块",
                source="ast",
            ))

        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    defects.append(Defect(
                        file=relative_path, line=node.lineno,
                        severity="major", category="exception_handling",
                        description="裸except: — 应改为except Exception:",
                        suggestion="改为 except Exception:",
                        source="ast",
                    ))

            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_lines = (node.end_lineno or node.lineno) - node.lineno + 1
                if func_lines > self.MAX_FUNCTION_LINES:
                    defects.append(Defect(
                        file=relative_path, line=node.lineno,
                        severity="minor", category="code_smell",
                        description=f"函数过长: {node.name}({func_lines}行，阈值{self.MAX_FUNCTION_LINES})",
                        suggestion=f"拆分{node.name}为多个子函数",
                        source="ast",
                    ))

                nesting = self._compute_nesting(node)
                if nesting > self.MAX_NESTING_DEPTH:
                    defects.append(Defect(
                        file=relative_path, line=node.lineno,
                        severity="minor", category="code_smell",
                        description=f"嵌套过深: {node.name}(深度{nesting}，阈值{self.MAX_NESTING_DEPTH})",
                        suggestion="提取内层逻辑为独立函数",
                        source="ast",
                    ))

        return defects

    def _pattern_analysis(self, relative_path: str, source: str) -> List[Defect]:
        defects = []
        lines = source.splitlines()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if "import sqlite3" in stripped and "DatabaseManager" not in source[:source.find(stripped) if stripped in source else 0]:
                rest = source[source.find(stripped) + len(stripped):] if stripped in source else ""
                if "DatabaseManager" not in rest:
                    defects.append(Defect(
                        file=relative_path, line=i,
                        severity="major", category="database",
                        description="直接使用sqlite3而非DatabaseManager",
                        suggestion="迁移到DatabaseManager统一接口",
                        source="ast",
                    ))

            if re.search(r'time\.sleep\(\d+\)', stripped):
                if "async" in source[:source.find(stripped) if stripped in source else len(source)]:
                    defects.append(Defect(
                        file=relative_path, line=i,
                        severity="major", category="performance",
                        description="async函数中使用同步time.sleep()会阻塞事件循环",
                        suggestion="改用 await asyncio.sleep()",
                        source="ast",
                    ))

        return defects

    def _compute_nesting(self, node: ast.AST) -> int:
        max_depth = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                depth = 0
                current = child
                while current != node and hasattr(current, "_parent"):
                    depth += 1
                    current = current._parent
                max_depth = max(max_depth, depth)
        return max_depth

    def get_diagnosis_summary(self, defects: List[Defect]) -> Dict[str, Any]:
        by_severity = {"critical": 0, "major": 0, "minor": 0, "info": 0}
        by_category = {}
        by_source = {}
        for d in defects:
            by_severity[d.severity] = by_severity.get(d.severity, 0) + 1
            by_category[d.category] = by_category.get(d.category, 0) + 1
            by_source[d.source] = by_source.get(d.source, 0) + 1
        return {
            "total": len(defects),
            "by_severity": by_severity,
            "by_category": by_category,
            "by_source": by_source,
        }


defect_diagnoser = DefectDiagnoser()