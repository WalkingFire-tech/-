"""
L5 自修改管线端到端验证 — 从缺陷检测到补丁生成
目标：验证 L5 能检测真实代码缺陷（非position偏离）并生成有效补丁
"""
import os
import pytest


class TestDefectDiagnosis:
    """节点 1: 验证缺陷检测器对真实代码缺陷的检测能力"""

    @pytest.fixture(autouse=True)
    def _setup(self):
        import sys
        from pathlib import Path
        root = str(Path(__file__).parent.parent.parent)
        if root not in sys.path:
            sys.path.insert(0, root)
        yield

    @property
    def _target_file(self):
        return "tests/unit/l5_test_target.py"

    def test_detects_bare_except(self):
        """L5应检测到l5_test_target.py中的裸except"""
        from core.self_modification.defect_diagnoser import defect_diagnoser

        defects = defect_diagnoser.diagnose_file(self._target_file)
        bare_excepts = [d for d in defects if "裸except" in d.description]

        assert len(bare_excepts) >= 1, (
            f"期望至少检测到1个裸except，实际检测到{len(bare_excepts)}个。"
            f"所有缺陷: {[d.description for d in defects]}"
        )

    def test_bare_except_defect_has_suggestion(self):
        """裸except缺陷必须包含修复建议"""
        from core.self_modification.defect_diagnoser import defect_diagnoser

        defects = defect_diagnoser.diagnose_file(self._target_file)
        bare_excepts = [d for d in defects if "裸except" in d.description]

        for d in bare_excepts:
            assert d.suggestion, f"缺陷缺少修复建议: {d}"
            assert "except" in d.suggestion.lower() or "Exception" in d.suggestion, (
                f"修复建议不包含异常类型转换: {d.suggestion}"
            )

    def test_defect_has_file_and_line(self):
        """每个缺陷必须标明文件和行号"""
        from core.self_modification.defect_diagnoser import defect_diagnoser

        defects = defect_diagnoser.diagnose_file(self._target_file)
        for d in defects:
            assert d.file, "缺陷缺少file字段"
            assert d.line >= 0, f"缺陷行号异常: {d.line}"


class TestPatchGeneration:
    """节点 2: 验证补丁生成器对检测到的缺陷生成有效补丁"""

    @pytest.fixture(autouse=True)
    def _setup(self):
        import sys
        from pathlib import Path
        root = str(Path(__file__).parent.parent.parent)
        if root not in sys.path:
            sys.path.insert(0, root)
        yield

    @property
    def _target_file(self):
        return "tests/unit/l5_test_target.py"

    def _get_source(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            self._target_file)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _get_bare_except_defects(self):
        from core.self_modification.defect_diagnoser import defect_diagnoser
        defects = defect_diagnoser.diagnose_file(self._target_file)
        return [d for d in defects if "裸except" in d.description]

    def test_patch_bare_except_uses_template(self):
        """裸except缺陷应由PATCH_TEMPLATES生成补丁"""
        from core.self_modification.patch_generator import patch_generator

        defects = self._get_bare_except_defects()
        if not defects:
            pytest.skip("没有检测到裸except缺陷")

        source = self._get_source()
        for defect in defects:
            defect_dict = {
                "file": defect.file,
                "line": defect.line,
                "severity": defect.severity,
                "category": defect.category,
                "description": defect.description,
                "suggestion": defect.suggestion,
                "source": defect.source,
            }
            patch = patch_generator.generate_patch(defect_dict, source)
            assert patch is not None, f"应生成补丁但返回None: {defect.description}"
            assert "except Exception" in patch.replacement, (
                f"补丁应包含except Exception:，实际: {patch.replacement}"
            )
            assert "except:" in patch.original or "except :" in patch.original, (
                f"补丁原始文本应包含except:，实际: {patch.original}"
            )


class TestL5FullPipeline:
    """节点 3: 验证完整L5管道（检测→补丁→沙箱→部署提案）"""

    @pytest.fixture(autouse=True)
    def _setup(self):
        import sys
        from pathlib import Path
        root = str(Path(__file__).parent.parent.parent)
        if root not in sys.path:
            sys.path.insert(0, root)
        yield

    def test_self_modification_loop_finds_defects(self):
        """SelfModificationLoop.run_from_file应触发并找到缺陷"""
        from core.self_modification.loop import SelfModificationLoop

        loop = SelfModificationLoop()
        loop._last_run = None  # 重置冷却期
        result = loop.run_from_file("tests/unit/l5_test_target.py")

        assert result.triggered, f"应触发修改但未触发: {result}"
        assert result.defects_found >= 1, (
            f"应至少找到1个缺陷，实际: {result.defects_found}"
        )

    def test_patch_sandbox_validates_bare_except_fix(self):
        """沙箱应验证裸except→except Exception的补丁"""
        from core.self_modification.patch_sandbox_deployer import PatchSandbox

        sandbox = PatchSandbox()
        patched_code = 'def f():\n    try:\n        pass\n    except Exception:\n        pass\n'

        is_safe, violations = sandbox.validate_safety(
            "tests/unit/l5_test_target.py", patched_code
        )
        assert is_safe, f"安全的补丁应通过沙箱验证: {violations}"

    def test_patch_sandbox_rejects_dangerous_code(self):
        """沙箱应拒绝危险的补丁"""
        from core.self_modification.patch_sandbox_deployer import PatchSandbox

        sandbox = PatchSandbox()
        dangerous_code = 'def f():\n    try:\n        pass\n    except:; import os; os.system("rm -rf /")\n        pass\n'

        is_safe, violations = sandbox.validate_safety(
            "tests/unit/l5_test_target.py", dangerous_code
        )
        assert not is_safe, f"危险补丁不应通过沙箱验证"
        assert len(violations) > 0, "拒绝原因不能为空"
