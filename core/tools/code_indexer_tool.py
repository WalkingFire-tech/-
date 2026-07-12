import os
import ast
import asyncio
from typing import Dict, List, Optional
from core.tool_registry import ToolInterface, ToolResult, run_tool_async


class CodeIndexerTool(ToolInterface):
    @property
    def name(self) -> str:
        return "code_indexer"

    @property
    def description(self) -> str:
        return "代码语义索引：AST解析Python文件，提取类/函数/导入，支持符号查询"

    @property
    def parameters(self) -> Dict:
        return {
            "query": {"type": "string", "description": "查询：路径或符号名", "required": True},
            "mode": {"type": "string", "description": "模式(index文件路径 / search符号名 / overview概览)", "default": "auto"},
            "max_files": {"type": "integer", "description": "最大索引文件数", "default": 100},
        }

    @property
    def timeout(self) -> float:
        return 15.0

    @property
    def category(self) -> str:
        return "analysis"

    @property
    def priority(self) -> int:
        return 73

    def can_handle(self, query: str, intent_type: str = "") -> bool:
        if intent_type == "code":
            return True
        indicators = [
            "在哪定义", "哪个文件", "函数在哪", "类在哪", "符号", "代码索引", "AST",
            "代码结构", "有哪些类", "有哪些函数", "代码概览",
            "where defined", "which file", "function where", "class where",
            "symbol", "code index", "code structure",
        ]
        return any(ind in query.lower() for ind in indicators)

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        mode = kwargs.get("mode", "auto")
        max_files = kwargs.get("max_files", 100)

        if not query:
            return ToolResult(success=False, error="查询不能为空", source=self.name)

        try:
            def _run():
                if mode == "auto":
                    if os.path.isdir(query):
                        mode_resolved = "overview"
                    elif os.path.isfile(query):
                        mode_resolved = "index"
                    else:
                        mode_resolved = "search"
                else:
                    mode_resolved = mode

                if mode_resolved == "overview":
                    return self._index_directory(query, max_files)
                elif mode_resolved == "index":
                    return self._index_file(query)
                else:
                    return self._search_symbol(query)
            result = await run_tool_async(_run, timeout=14)
        except Exception as e:
            return ToolResult(success=False, error=f"索引失败: {e}", source=self.name)

        if result:
            return ToolResult(
                success=True, data=result,
                source=self.name, quality=85,
                metadata={"query": query, "mode": mode},
            )
        return ToolResult(success=False, error="索引结果为空", source=self.name)

    def _index_file(self, filepath: str) -> str:
        if not os.path.isfile(filepath):
            return f"文件不存在: {filepath}"
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                source = f.read()
            tree = ast.parse(source, filename=filepath)
        except SyntaxError as e:
            return f"语法错误: {e}"
        except Exception as e:
            return f"解析失败: {e}"

        lines = []
        lines.append(f"## 文件索引: {os.path.basename(filepath)}")
        lines.append(f"路径: {filepath}")
        lines.append(f"行数: {len(source.splitlines())}")
        lines.append("")

        imports = []
        classes = []
        functions = []
        globals_vars = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.asname or alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    imports.append((f"{module}.{alias.asname or alias.name}", node.lineno))
            elif isinstance(node, ast.ClassDef):
                bases = [self._get_name(b) for b in node.bases]
                methods = [(n.name, n.lineno) for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                classes.append((node.name, node.lineno, bases, methods))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in node.args.args if a.arg != 'self']
                functions.append((node.name, node.lineno, args, isinstance(node, ast.AsyncFunctionDef)))
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        globals_vars.append((target.id, node.lineno))

        if imports:
            lines.append("### 导入")
            for name, lineno in imports:
                lines.append(f"  L{lineno}: {name}")
            lines.append("")

        if classes:
            lines.append("### 类")
            for name, lineno, bases, methods in classes:
                base_str = f"({', '.join(bases)})" if bases else ""
                lines.append(f"  L{lineno}: class {name}{base_str}")
                for mname, mlineno in methods:
                    lines.append(f"    L{lineno}: def {mname}()")
            lines.append("")

        if functions:
            lines.append("### 函数")
            for name, lineno, args, is_async in functions:
                prefix = "async " if is_async else ""
                args_str = ", ".join(args)
                lines.append(f"  L{lineno}: {prefix}def {name}({args_str})")
            lines.append("")

        if globals_vars:
            lines.append("### 全局变量")
            for name, lineno in globals_vars[:20]:
                lines.append(f"  L{lineno}: {name}")
            lines.append("")

        return '\n'.join(lines)

    def _index_directory(self, dirpath: str, max_files: int) -> str:
        if not os.path.isdir(dirpath):
            return f"目录不存在: {dirpath}"

        py_files = []
        for root, dirs, files in os.walk(dirpath):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', 'venv', '.venv'}]
            for f in files:
                if f.endswith('.py'):
                    py_files.append(os.path.join(root, f))
            if len(py_files) >= max_files:
                break

        all_symbols = []
        total_lines = 0
        total_classes = 0
        total_functions = 0
        errors = 0

        for fpath in py_files[:max_files]:
            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                    source = f.read()
                tree = ast.parse(source, filename=fpath)
                line_count = len(source.splitlines())
                total_lines += line_count
                rel = os.path.relpath(fpath, dirpath)

                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, ast.ClassDef):
                        total_classes += 1
                        all_symbols.append(("class", node.name, rel, node.lineno))
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        total_functions += 1
                        all_symbols.append(("function", node.name, rel, node.lineno))
            except Exception:
                errors += 1

        lines = []
        lines.append(f"## 项目代码索引: {os.path.basename(dirpath)}")
        lines.append(f"- Python文件: {len(py_files)}")
        lines.append(f"- 总行数: {total_lines}")
        lines.append(f"- 类: {total_classes}")
        lines.append(f"- 函数: {total_functions}")
        if errors:
            lines.append(f"- 解析错误: {errors}")
        lines.append("")

        lines.append("### 类索引")
        for kind, name, path, lineno in all_symbols:
            if kind == "class":
                lines.append(f"  {name:30s} → {path}:{lineno}")
        lines.append("")

        lines.append("### 函数索引（前50）")
        func_symbols = [s for s in all_symbols if s[0] == "function"]
        for kind, name, path, lineno in func_symbols[:50]:
            lines.append(f"  {name:30s} → {path}:{lineno}")
        if len(func_symbols) > 50:
            lines.append(f"  ... 还有 {len(func_symbols) - 50} 个函数")

        return '\n'.join(lines)

    def _search_symbol(self, symbol: str) -> str:
        search_dir = os.getcwd()
        results = []
        py_files = []

        for root, dirs, files in os.walk(search_dir):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', 'venv', '.venv', 'archives', 'tests'}]
            for f in files:
                if f.endswith('.py'):
                    py_files.append(os.path.join(root, f))

        for fpath in py_files[:200]:
            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                    source = f.read()
                tree = ast.parse(source, filename=fpath)
                rel = os.path.relpath(fpath, search_dir)

                for node in ast.walk(tree):
                    name = None
                    kind = None
                    if isinstance(node, ast.ClassDef) and symbol.lower() in node.name.lower():
                        name, kind = node.name, "class"
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and symbol.lower() in node.name.lower():
                        name, kind = node.name, "function"
                    if name:
                        results.append((kind, name, rel, node.lineno))
            except Exception:
                logger.warning("操作降级跳过")

        if not results:
            return f"未找到符号: {symbol}"

        lines = [f"## 符号搜索: {symbol}", f"找到 {len(results)} 个匹配:", ""]
        for kind, name, path, lineno in results[:30]:
            lines.append(f"  [{kind}] {name:30s} → {path}:{lineno}")
        if len(results) > 30:
            lines.append(f"  ... 还有 {len(results) - 30} 个匹配")
        return '\n'.join(lines)

    @staticmethod
    def _get_name(node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{CodeIndexerTool._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return "..."