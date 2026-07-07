import os
import asyncio
from typing import Dict, List
from core.tool_registry import ToolInterface, ToolResult, run_tool_async


class ProjectScannerTool(ToolInterface):
    @property
    def name(self) -> str:
        return "project_scanner"

    @property
    def description(self) -> str:
        return "项目结构扫描：扫描文件夹生成目录树、文件统计、技术栈识别"

    @property
    def parameters(self) -> Dict:
        return {
            "query": {"type": "string", "description": "项目根目录路径", "required": True},
            "max_depth": {"type": "integer", "description": "最大扫描深度", "default": 5},
            "detail": {"type": "string", "description": "输出详细度(summary/normal/full)", "default": "normal"},
        }

    @property
    def timeout(self) -> float:
        return 15.0

    @property
    def category(self) -> str:
        return "analysis"

    @property
    def priority(self) -> int:
        return 72

    def can_handle(self, query: str, intent_type: str = "") -> bool:
        if intent_type == "code":
            return True
        indicators = [
            "项目结构", "目录树", "文件统计", "技术栈", "扫描", "项目概览", "有哪些文件",
            "项目组成", "项目目录", "项目布局",
            "project structure", "directory tree", "file stats", "tech stack",
            "scan project", "project overview", "what files",
        ]
        return any(ind in query.lower() for ind in indicators)

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("query", "")
        max_depth = kwargs.get("max_depth", 5)
        detail = kwargs.get("detail", "normal")

        if not path or not os.path.isdir(path):
            return ToolResult(success=False, error=f"路径不存在或不是目录: {path}", source=self.name)

        try:
            def _scan():
                return self._scan_project(path, max_depth, detail)
            result = await run_tool_async(_scan, timeout=14)
        except Exception as e:
            return ToolResult(success=False, error=f"扫描失败: {e}", source=self.name)

        if result:
            return ToolResult(
                success=True, data=result,
                source=self.name, quality=80,
                metadata={"path": path, "max_depth": max_depth},
            )
        return ToolResult(success=False, error="扫描结果为空", source=self.name)

    def _scan_project(self, root: str, max_depth: int, detail: str) -> str:
        skip_dirs = {
            '__pycache__', '.git', 'node_modules', '.venv', 'venv', 'env',
            '.idea', '.vscode', 'dist', 'build', '.next', '.nuxt',
            'target', '.gradle', '.mvn', 'bin', 'obj', 'Debug', 'Release',
            '.tox', '.mypy_cache', '.pytest_cache', '.ruff_cache',
            'egg-info', '.eggs', 'htmlcov', '.coverage',
        }
        skip_ext = {'.pyc', '.pyo', '.so', '.dll', '.exe', '.o', '.a', '.lib', '.obj', '.pdb', '.idb'}

        tree_lines = []
        file_stats = {}
        tech_stack = set()
        total_files = 0
        total_dirs = 0
        total_size = 0

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith('.')]
            rel = os.path.relpath(dirpath, root)
            depth = rel.count(os.sep) if rel != '.' else 0
            if depth > max_depth:
                dirnames.clear()
                continue

            total_dirs += 1
            indent = '  ' * depth
            dirname = os.path.basename(dirpath) if rel != '.' else os.path.basename(root)
            tree_lines.append(f"{indent}{dirname}/")

            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in skip_ext:
                    continue
                total_files += 1
                fpath = os.path.join(dirpath, fname)
                try:
                    fsize = os.path.getsize(fpath)
                    total_size += fsize
                except OSError:
                    fsize = 0
                file_stats[ext] = file_stats.get(ext, 0) + 1
                if detail == "full":
                    tree_lines.append(f"{indent}  {fname} ({self._fmt_size(fsize)})")
                self._detect_tech(fname, ext, dirpath, tech_stack)

        lines = []
        lines.append(f"## 项目概览: {os.path.basename(root)}")
        lines.append(f"- 目录数: {total_dirs}")
        lines.append(f"- 文件数: {total_files}")
        lines.append(f"- 总大小: {self._fmt_size(total_size)}")
        lines.append("")

        if tech_stack:
            lines.append("## 技术栈")
            for t in sorted(tech_stack):
                lines.append(f"- {t}")
            lines.append("")

        sorted_stats = sorted(file_stats.items(), key=lambda x: -x[1])
        lines.append("## 文件类型分布")
        for ext, count in sorted_stats[:15]:
            pct = count / max(total_files, 1) * 100
            bar = '█' * int(pct / 2) + '░' * (50 - int(pct / 2))
            label = ext if ext else '(无扩展名)'
            lines.append(f"  {label:12s} {count:4d} ({pct:5.1f}%) {bar}")
        lines.append("")

        if detail != "summary":
            lines.append("## 目录结构")
            max_tree_lines = 200 if detail == "full" else 80
            for tl in tree_lines[:max_tree_lines]:
                lines.append(tl)
            if len(tree_lines) > max_tree_lines:
                lines.append(f"  ... 还有 {len(tree_lines) - max_tree_lines} 行省略")

        return '\n'.join(lines)

    def _detect_tech(self, fname: str, ext: str, dirpath: str, stack: set):
        tech_map = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.jsx': 'React', '.tsx': 'React+TypeScript',
            '.vue': 'Vue', '.svelte': 'Svelte',
            '.java': 'Java', '.kt': 'Kotlin', '.scala': 'Scala',
            '.go': 'Go', '.rs': 'Rust', '.cpp': 'C++', '.c': 'C',
            '.cs': 'C#', '.rb': 'Ruby', '.php': 'PHP',
            '.swift': 'Swift', '.dart': 'Dart',
            '.html': 'HTML', '.css': 'CSS', '.scss': 'SCSS',
            '.sql': 'SQL', '.sh': 'Shell', '.ps1': 'PowerShell',
            '.yaml': 'YAML', '.yml': 'YAML', '.json': 'JSON',
            '.toml': 'TOML', '.xml': 'XML',
            '.md': 'Markdown', '.rst': 'reStructuredText',
            '.dockerfile': 'Docker', '.tf': 'Terraform',
        }
        if ext in tech_map:
            stack.add(tech_map[ext])

        config_tech = {
            'package.json': 'Node.js/npm', 'tsconfig.json': 'TypeScript',
            'pyproject.toml': 'Python(Project)', 'requirements.txt': 'Python(pip)',
            'Pipfile': 'Python(pipenv)', 'Cargo.toml': 'Rust(Cargo)',
            'go.mod': 'Go Modules', 'pom.xml': 'Java(Maven)',
            'build.gradle': 'Java(Gradle)', 'Gemfile': 'Ruby(Bundler)',
            'composer.json': 'PHP(Composer)', 'pubspec.yaml': 'Dart/Flutter',
            'Dockerfile': 'Docker', 'docker-compose.yml': 'Docker Compose',
            '.github': 'GitHub CI/CD', 'Makefile': 'Make',
            'CMakeLists.txt': 'CMake', 'vite.config.ts': 'Vite',
            'webpack.config.js': 'Webpack', 'next.config.js': 'Next.js',
            'nuxt.config.ts': 'Nuxt', 'vue.config.js': 'Vue CLI',
        }
        if fname in config_tech:
            stack.add(config_tech[fname])

        fwk_dirs = {
            'django': 'Django', 'flask': 'Flask', 'fastapi': 'FastAPI',
            'spring': 'Spring', 'rails': 'Ruby on Rails',
            'express': 'Express', 'nestjs': 'NestJS',
            'react': 'React', 'vue': 'Vue',
        }
        dp = dirpath.lower().replace('\\', '/').replace('/', ' ')
        for kw, tech in fwk_dirs.items():
            if kw in dp:
                stack.add(tech)

    @staticmethod
    def _fmt_size(size: int) -> str:
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f}KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f}MB"
        return f"{size / (1024 * 1024 * 1024):.1f}GB"