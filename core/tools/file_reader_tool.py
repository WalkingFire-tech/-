import os
import asyncio
from typing import Dict
from core.tool_registry import ToolInterface, ToolResult, run_tool_async


class FileReaderTool(ToolInterface):
    @property
    def name(self) -> str:
        return "file_reader"

    @property
    def description(self) -> str:
        return "文件读取：读取本地文件内容，支持文本/代码/配置等文件"

    @property
    def parameters(self) -> Dict:
        return {
            "query": {"type": "string", "description": "文件路径", "required": True},
            "max_lines": {"type": "integer", "description": "最大读取行数", "default": 500},
            "offset": {"type": "integer", "description": "起始行号(1-based)", "default": 1},
        }

    @property
    def timeout(self) -> float:
        return 8.0

    @property
    def category(self) -> str:
        return "knowledge"

    @property
    def priority(self) -> int:
        return 75

    def can_handle(self, query: str, intent_type: str = "") -> bool:
        if intent_type == "code":
            return True
        indicators = [
            "读取", "打开", "查看文件", "文件内容", "看看文件", "读一下",
            "readme", ".md", ".py", ".txt", ".json", ".yaml", ".yml",
            ".toml", ".cfg", ".ini", ".log", ".csv", ".html", ".css", ".js", ".ts",
            "read file", "open file", "show file", "file content", "view file",
            "cat ", "less ", "head ",
        ]
        ql = query.lower()
        if any(ind in ql for ind in indicators):
            return True
        import re
        if re.search(r'[\w/\\]+\.\w{1,6}', query):
            return True
        return False

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("query", "")
        max_lines = kwargs.get("max_lines", 500)
        offset = kwargs.get("offset", 1)

        if not path:
            return ToolResult(success=False, error="文件路径不能为空", source=self.name)

        path = path.strip().strip('"').strip("'")

        if not os.path.isfile(path):
            alt = os.path.join(os.getcwd(), path)
            if os.path.isfile(alt):
                path = alt
            else:
                return ToolResult(success=False, error=f"文件不存在: {path}", source=self.name)

        binary_ext = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',
                      '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac',
                      '.zip', '.rar', '.7z', '.tar', '.gz',
                      '.exe', '.dll', '.so', '.dylib',
                      '.db', '.sqlite', '.safetensors', '.faiss',
                      '.pyc', '.pyo', '.pdf', '.docx', '.xlsx', '.pptx'}
        ext = os.path.splitext(path)[1].lower()
        if ext in binary_ext:
            size = os.path.getsize(path)
            return ToolResult(
                success=True,
                data=f"二进制文件: {os.path.basename(path)}\n类型: {ext}\n大小: {self._fmt_size(size)}\n(不支持预览二进制文件)",
                source=self.name, quality=40,
            )

        try:
            def _read():
                return self._read_file(path, max_lines, offset)
            result = await run_tool_async(_read, timeout=7)
        except Exception as e:
            return ToolResult(success=False, error=f"读取失败: {e}", source=self.name)

        if result:
            return ToolResult(
                success=True, data=result,
                source=self.name, quality=85,
                metadata={"path": path, "lines": max_lines},
            )
        return ToolResult(success=False, error="读取结果为空", source=self.name)

    def _read_file(self, path: str, max_lines: int, offset: int) -> str:
        encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb2312', 'latin-1']

        for enc in encodings:
            try:
                with open(path, 'r', encoding=enc) as f:
                    all_lines = f.readlines()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            return f"无法解码文件: {path}"

        total = len(all_lines)
        start = max(0, offset - 1)
        end = min(total, start + max_lines)
        selected = all_lines[start:end]

        lines = []
        lines.append(f"## 文件: {os.path.basename(path)}")
        lines.append(f"路径: {path}")
        lines.append(f"总行数: {total} | 显示: L{start+1}-L{end}")
        lines.append("")

        for i, line in enumerate(selected, start=start + 1):
            stripped = line.rstrip('\n').rstrip('\r')
            lines.append(f"{i:5d}: {stripped}")

        if end < total:
            lines.append(f"\n... 还有 {total - end} 行未显示")

        return '\n'.join(lines)

    @staticmethod
    def _fmt_size(size: int) -> str:
        if size < 1024:
            return f"{size}B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f}KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f}MB"
        return f"{size / (1024 * 1024 * 1024):.1f}GB"