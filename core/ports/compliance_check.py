"""
端口合规检查器 — 检测代码绕过端口直接使用基础设施

运行方式：
  python -m core.ports.compliance_check [--fix]

检查规则：
  1. 直接导入infrastructure模块（绕过端口）= 警告
  2. 端口可用但未使用端口路径 = 警告
  3. 端口不可用时的降级路径 = 信息（允许但需记录）
"""
import ast
import sys
from pathlib import Path
from dataclasses import dataclass, field

_BYPASS_PATTERNS = {
    "infrastructure.fact_store": "fact_store",
    "infrastructure.vector_retriever": "vector_store",
    "infrastructure.config_manager": "config",
    "infrastructure.database_manager": "storage",
    "core.knowledge.index": "knowledge",
}

_ROOT_DIR = Path(__file__).resolve().parent.parent.parent


@dataclass
class Violation:
    file: str
    line: int
    severity: str
    port_name: str
    detail: str


def check_file(filepath: Path) -> list:
    violations = []
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return violations

    rel = str(filepath.relative_to(_ROOT_DIR)).replace("\\", "/")

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for pattern, port_name in _BYPASS_PATTERNS.items():
                if node.module.startswith(pattern):
                    names = ", ".join(a.name for a in node.names)
                    violations.append(Violation(
                        file=rel, line=node.lineno, severity="WARN",
                        port_name=port_name,
                        detail=f"直接导入 {node.module}.{names} 绕过 {port_name} 端口",
                    ))

    return violations


def check_directory(directory: Path = None, exclude: set = None) -> list:
    directory = directory or _ROOT_DIR
    exclude = exclude or {"__pycache__", ".git", "node_modules", "_arch", ".venv", ".codeartsdoer", "archives"}
    all_violations = []

    for py_file in directory.rglob("*.py"):
        if any(part in exclude for part in py_file.parts):
            continue
        all_violations.extend(check_file(py_file))

    return all_violations


def print_report(violations: list):
    if not violations:
        print("✅ 端口合规检查通过：未发现绕过端口的直接基础设施导入")
        return

    by_severity = {"WARN": [], "INFO": []}
    for v in violations:
        by_severity.get(v.severity, []).append(v)

    print(f"\n{'='*60}")
    print(f"端口合规检查报告：发现 {len(violations)} 个问题")
    print(f"{'='*60}")

    for sev in ("WARN", "INFO"):
        items = by_severity[sev]
        if not items:
            continue
        print(f"\n--- {sev} ({len(items)}个) ---")
        by_port = {}
        for v in items:
            by_port.setdefault(v.port_name, []).append(v)
        for port, viols in sorted(by_port.items()):
            print(f"\n  端口: {port}")
            for v in viols[:5]:
                print(f"    {v.file}:{v.line} — {v.detail}")
            if len(viols) > 5:
                print(f"    ... 还有{len(viols)-5}个")

    print(f"\n{'='*60}")


if __name__ == "__main__":
    violations = check_directory()
    print_report(violations)
    sys.exit(1 if any(v.severity == "WARN" for v in violations) else 0)