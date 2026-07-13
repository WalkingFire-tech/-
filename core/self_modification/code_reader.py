"""
L5.1 代码阅读器 — 读取自身源代码

基于已有的file_reader_tool，提供结构化的代码阅读能力。
支持：读取文件、搜索符号、提取函数/类定义、获取导入关系。
"""

import ast
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class CodeReader:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def read_file(self, relative_path: str) -> Optional[str]:
        full_path = os.path.join(self.PROJECT_ROOT, relative_path.replace("/", os.sep))
        if not os.path.exists(full_path):
            logger.warning(f"文件不存在: {full_path}")
            return None
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return None

    def list_files(self, directory: str = "", pattern: str = "*.py") -> List[str]:
        search_dir = os.path.join(self.PROJECT_ROOT, directory.replace("/", os.sep)) if directory else self.PROJECT_ROOT
        if not os.path.isdir(search_dir):
            return []
        result = []
        for root, dirs, files in os.walk(search_dir):
            skip_dirs = {".venv", "venv", "__pycache__", ".git", "node_modules", ".codeartsdoer", ".arts"}
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for f in files:
                if f.endswith(pattern.lstrip("*")):
                    rel = os.path.relpath(os.path.join(root, f), self.PROJECT_ROOT)
                    result.append(rel.replace(os.sep, "/"))
        return sorted(result)

    def extract_symbols(self, relative_path: str) -> Dict[str, Any]:
        source = self.read_file(relative_path)
        if not source:
            return {"error": f"无法读取: {relative_path}"}
        try:
            tree = ast.parse(source, filename=relative_path)
        except SyntaxError as e:
            return {"error": f"语法错误: {e}", "line": e.lineno}

        classes = []
        functions = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "end_line": node.end_lineno,
                    "bases": [ast.dump(b) for b in node.bases],
                    "methods": methods,
                })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not isinstance(getattr(node, "_parent", None), ast.ClassDef):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "end_line": node.end_lineno,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "args": [a.arg for a in node.args.args if a.arg != "self"],
                    })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({"module": alias.name, "alias": alias.asname, "line": node.lineno})
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append({"module": f"{module}.{alias.name}", "alias": alias.asname, "line": node.lineno})

        return {
            "file": relative_path,
            "lines": len(source.splitlines()),
            "classes": classes,
            "functions": functions,
            "imports": imports,
        }

    def find_symbol_definition(self, symbol_name: str, search_dirs: List[str] = None) -> List[Dict]:
        search_dirs = search_dirs or ["core", "backend", "infrastructure"]
        results = []
        seen = set()
        for d in search_dirs:
            for f in self.list_files(d):
                if f in seen:
                    continue
                seen.add(f)
                symbols = self.extract_symbols(f)
                if "error" in symbols:
                    continue
                for cls in symbols.get("classes", []):
                    if cls["name"] == symbol_name:
                        results.append({"file": f, "type": "class", **cls})
                    for m in cls.get("methods", []):
                        if m == symbol_name:
                            results.append({"file": f, "type": "method", "class": cls["name"], **cls})
                for func in symbols.get("functions", []):
                    if func["name"] == symbol_name:
                        results.append({"file": f, "type": "function", **func})
        return results

    def get_import_graph(self, relative_path: str) -> Dict[str, List[str]]:
        symbols = self.extract_symbols(relative_path)
        if "error" in symbols:
            return {}
        graph = {"imports_from": [], "imported_by": []}
        for imp in symbols.get("imports", []):
            module = imp["module"]
            parts = module.split(".")
            if parts[0] in ("core", "backend", "infrastructure"):
                candidate = "/".join(parts) + ".py"
                if os.path.exists(os.path.join(self.PROJECT_ROOT, candidate)):
                    graph["imports_from"].append(candidate)
        return graph


code_reader = CodeReader()