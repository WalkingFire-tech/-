"""
自修复循环 — 检测孤立模块并生成接入桩

三步：
1. 扫描 core/ 中无 import 引用的 .py 文件
2. 为每个孤立模块生成 try/except 保护的接入桩
3. 产出报告

原则：不自大、安全、诚实、可验证
"""
import os
import ast
import sys
from pathlib import Path
from typing import List, Tuple, Optional
from loguru import logger


class SelfRepairLoop:
    """检测孤立模块并自动生成最小接入桩"""

    def __init__(self, project_root: str = "."):
        self.root = Path(project_root).resolve()
        self.core_dir = self.root / "core"

    def find_dangling_modules(self) -> List[Path]:
        """找出 core/ 下没有被任何代码 import 的 .py 文件"""
        all_py = sorted(self.core_dir.rglob("*.py"))
        imported = set()

        for py_file in all_py:
            try:
                text = py_file.read_text(encoding="utf-8")
                tree = ast.parse(text)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imported.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        mod = node.module.split(".")[0]
                        imported.add(mod)
            except SyntaxError:
                continue

        dangling = []
        for py_file in all_py:
            rel = py_file.relative_to(self.root)
            name = py_file.stem
            if name == "__init__":
                continue
            if name.startswith("test_"):
                continue
            if py_file.parent.name == "OLD":
                continue
            if name not in imported and not self._is_init_submodule(py_file):
                dangling.append(py_file)

        return dangling

    def _is_init_submodule(self, path: Path) -> bool:
        """检查文件是否通过 __init__.py 间接导出"""
        init_path = path.parent / "__init__.py"
        if not init_path.exists():
            return False
        try:
            text = init_path.read_text(encoding="utf-8")
            return path.stem in text
        except Exception:
            return False

    def generate_hook_stub(self, module_path: Path) -> str:
        """为孤立模块生成最小接入桩"""
        rel = module_path.relative_to(self.root)
        module_name = module_path.stem
        import_path = str(rel).replace(os.sep, ".").replace(".py", "")

        # 猜测类名
        class_name = "".join(p.capitalize() for p in module_name.split("_"))
        var_name = f"_{module_name}_available"

        return f'''
# AUTO-GENERATED HOOK for {rel}
# 生成时间: {__import__('datetime').datetime.now().isoformat()}
# 人工审核后移动到合适位置

try:
    from {import_path} import {class_name}
    {var_name} = True
except ImportError:
    {var_name} = False
    logger.warning("{module_name} 模块加载失败")

def try_{module_name}(context: dict) -> Optional[dict]:
    """自动生成的降级安全接入点（假设接口 process(context)）"""
    if not {var_name}:
        return None
    try:
        instance = {class_name}()
        if hasattr(instance, 'process'):
            return instance.process(context)
        elif hasattr(instance, 'run'):
            return instance.run(context)
        return {{"status": "loaded", "module": "{module_name}"}}
    except Exception as e:
        logger.warning(f"{module_name} 执行失败: {{e}}")
        return None
'''

    def run_audit(self) -> Tuple[List[Path], str]:
        """运行完整审计，返回 (孤立模块列表, 报告文本)"""
        dangling = self.find_dangling_modules()
        lines = []
        lines.append("# 孤立模块审计报告")
        lines.append(f"生成时间: {__import__('datetime').datetime.now().isoformat()}")
        lines.append(f"扫描目录: {self.core_dir}")
        lines.append(f"孤立模块数: {len(dangling)}")
        lines.append("")
        lines.append("| # | 模块路径 | 大小 | 建议 |")
        lines.append("|---|---------|------|------|")

        hooks_generated = 0
        for i, mod in enumerate(dangling, 1):
            size = mod.stat().st_size
            # 根据大小和目录判断价值
            rel = mod.relative_to(self.root)
            parent_dir = mod.parent.name
            if size > 10000:
                suggestion = "高价值 — 建议接入"
            elif parent_dir in ("feedback", "dialogue", "ethics"):
                suggestion = "已部分接线，检查导入链"
            else:
                suggestion = "待评估"

            lines.append(f"| {i} | `{rel}` | {size}B | {suggestion} |")

            # 为大文件生成接入桩
            if size > 5000:
                stub = self.generate_hook_stub(mod)
                stub_path = self.root / "_arch" / "hooks" / f"{mod.stem}_hook.py"
                stub_path.parent.mkdir(parents=True, exist_ok=True)
                stub_path.write_text(stub)
                hooks_generated += 1

        lines.append("")
        lines.append(f"生成接入桩: {hooks_generated} 个 (已保存至 _arch/hooks/)")
        lines.append("")

        if not dangling:
            lines.append("🎉 无孤立模块 — 所有 core/ 文件均被引用")
        else:
            lines.append("### 下一步")
            lines.append("1. 人工审核 _arch/hooks/ 中的接入桩")
            lines.append("2. 将合适的桩移动到相关服务文件")
            lines.append("3. 运行 `SelfRepairLoop().run_audit()` 验证减少")

        return dangling, "\n".join(lines)


if __name__ == "__main__":
    loop = SelfRepairLoop()
    dangling, report = loop.run_audit()
    print(report)
