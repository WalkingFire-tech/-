import os
import ast
import asyncio
from collections import defaultdict
from typing import Dict, List, Set, Tuple
from core.tool_registry import ToolInterface, ToolResult, run_tool_async


class DependencyAnalyzerTool(ToolInterface):
    @property
    def name(self) -> str:
        return "dependency_analyzer"

    @property
    def description(self) -> str:
        return "架构依赖分析：模块依赖图、调用链追踪、影响范围分析"

    @property
    def parameters(self) -> Dict:
        return {
            "query": {"type": "string", "description": "项目路径或模块名", "required": True},
            "mode": {"type": "string", "description": "模式(graph依赖图/impact影响范围/callers调用者)", "default": "graph"},
            "depth": {"type": "integer", "description": "分析深度", "default": 2},
        }

    @property
    def timeout(self) -> float:
        return 20.0

    @property
    def category(self) -> str:
        return "analysis"

    @property
    def priority(self) -> int:
        return 71

    def can_handle(self, query: str, intent_type: str = "") -> bool:
        if intent_type == "code":
            return True
        indicators = [
            "依赖", "调用链", "影响范围", "模块关系", "谁调用了", "谁依赖",
            "模块依赖", "依赖图", "架构分析",
            "dependency", "call chain", "impact", "module relation",
            "who calls", "who depends", "dep graph",
        ]
        return any(ind in query.lower() for ind in indicators)

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        mode = kwargs.get("mode", "graph")
        depth = kwargs.get("depth", 2)

        if not query:
            return ToolResult(success=False, error="查询不能为空", source=self.name)

        try:
            def _run():
                project_dir = query if os.path.isdir(query) else os.getcwd()
                dep_graph = self._build_dependency_graph(project_dir)
                if mode == "graph":
                    return self._format_graph(dep_graph)
                elif mode == "impact":
                    return self._format_impact(dep_graph, query, depth)
                elif mode == "callers":
                    return self._format_callers(dep_graph, query)
                return self._format_graph(dep_graph)
            result = await run_tool_async(_run, timeout=18)
        except Exception as e:
            return ToolResult(success=False, error=f"分析失败: {e}", source=self.name)

        if result:
            return ToolResult(
                success=True, data=result,
                source=self.name, quality=85,
                metadata={"query": query, "mode": mode},
            )
        return ToolResult(success=False, error="分析结果为空", source=self.name)

    def _build_dependency_graph(self, project_dir: str) -> Dict:
        modules = {}
        py_files = []

        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if d not in {'__pycache__', '.git', 'node_modules', 'venv', '.venv', 'archives', 'tests'}]
            for f in files:
                if f.endswith('.py'):
                    py_files.append(os.path.join(root, f))

        for fpath in py_files[:150]:
            try:
                with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                    source = f.read()
                tree = ast.parse(source, filename=fpath)
                rel = os.path.relpath(fpath, project_dir)
                module_name = rel.replace(os.sep, '.').replace('.py', '')

                imports = set()
                calls = defaultdict(set)
                exports = set()

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.add(node.module.split('.')[0])
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        exports.add(node.name)
                        for child in ast.walk(node):
                            if isinstance(child, ast.Call):
                                called = self._get_call_name(child)
                                if called:
                                    calls[node.name].add(called)
                    elif isinstance(node, ast.ClassDef):
                        exports.add(node.name)

                modules[module_name] = {
                    "path": rel,
                    "imports": imports,
                    "calls": dict(calls),
                    "exports": exports,
                    "lines": len(source.splitlines()),
                }
            except Exception:
                pass

        return modules

    def _format_graph(self, modules: Dict) -> str:
        lines = ["## 模块依赖图", ""]

        internal_prefixes = set()
        for mod_name in modules:
            parts = mod_name.split('.')
            if len(parts) > 1:
                internal_prefixes.add(parts[0])

        dep_map = defaultdict(set)
        for mod_name, info in modules.items():
            for imp in info["imports"]:
                if imp in internal_prefixes:
                    top_level = mod_name.split('.')[0]
                    if imp != top_level:
                        dep_map[top_level].add(imp)

        top_modules = defaultdict(lambda: {"files": 0, "lines": 0, "exports": 0})
        for mod_name, info in modules.items():
            top = mod_name.split('.')[0]
            top_modules[top]["files"] += 1
            top_modules[top]["lines"] += info["lines"]
            top_modules[top]["exports"] += len(info["exports"])

        lines.append("### 顶层模块")
        for name in sorted(top_modules.keys()):
            info = top_modules[name]
            deps = dep_map.get(name, set())
            dep_str = f" → {', '.join(sorted(deps))}" if deps else ""
            lines.append(f"  {name:20s} ({info['files']}文件, {info['lines']}行, {info['exports']}导出){dep_str}")

        lines.append("")
        lines.append("### 依赖关系")
        for mod in sorted(dep_map.keys()):
            for dep in sorted(dep_map[mod]):
                lines.append(f"  {mod} → {dep}")

        cycles = self._find_cycles(dep_map)
        if cycles:
            lines.append("")
            lines.append("### ⚠️ 循环依赖")
            for cycle in cycles:
                lines.append(f"  {' → '.join(cycle)} → {cycle[0]}")

        return '\n'.join(lines)

    def _format_impact(self, modules: Dict, target: str, depth: int) -> str:
        target_prefix = target.split('.')[0] if '.' in target else target
        affected = set()
        current_level = {target_prefix}

        for _ in range(depth):
            next_level = set()
            for mod_name, info in modules.items():
                top = mod_name.split('.')[0]
                if top in current_level:
                    continue
                for imp in info["imports"]:
                    imp_top = imp.split('.')[0] if '.' in imp else imp
                    if imp_top in current_level:
                        next_level.add(top)
                        affected.add(top)
            current_level = next_level
            if not next_level:
                break

        lines = [f"## 影响范围分析: {target}", ""]
        if affected:
            lines.append(f"修改 `{target}` 可能影响以下 {len(affected)} 个模块:")
            for mod in sorted(affected):
                mod_info = [m for m in modules if m.split('.')[0] == mod]
                file_count = len(mod_info)
                line_count = sum(modules[m]["lines"] for m in mod_info)
                lines.append(f"  - {mod} ({file_count}文件, {line_count}行)")
        else:
            lines.append("未发现直接依赖模块")

        return '\n'.join(lines)

    def _format_callers(self, modules: Dict, symbol: str) -> str:
        callers = []
        symbol_lower = symbol.lower()

        for mod_name, info in modules.items():
            for func_name, called_list in info.get("calls", {}).items():
                for called in called_list:
                    if symbol_lower in called.lower():
                        callers.append((mod_name, func_name, called))

        lines = [f"## 调用者搜索: {symbol}", ""]
        if callers:
            lines.append(f"找到 {len(callers)} 处调用:")
            for mod, func, called in callers[:30]:
                lines.append(f"  {mod}.{func}() → {called}")
        else:
            lines.append("未找到调用者")

        return '\n'.join(lines)

    def _find_cycles(self, dep_map: Dict[str, set]) -> List[List[str]]:
        cycles = []
        visited = set()

        def _dfs(node, path, path_set):
            if node in path_set:
                cycle_start = path.index(node)
                cycle = path[cycle_start:]
                if len(cycle) > 1:
                    cycles.append(cycle)
                return
            if node in visited:
                return
            path.append(node)
            path_set.add(node)
            for dep in dep_map.get(node, set()):
                _dfs(dep, path, path_set)
            path.pop()
            path_set.discard(node)
            visited.add(node)

        for node in dep_map:
            _dfs(node, [], set())

        return cycles[:5]

    @staticmethod
    def _get_call_name(call_node: ast.Call) -> str:
        func = call_node.func
        if isinstance(func, ast.Name):
            return func.id
        elif isinstance(func, ast.Attribute):
            parts = []
            current = func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return '.'.join(reversed(parts))
        return ""