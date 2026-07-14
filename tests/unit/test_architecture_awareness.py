"""
单元测试 — 架构自我认知
"""
import pytest


class TestArchitectureAwareness:
    @pytest.fixture(autouse=True)
    def _setup(self):
        import sys; from pathlib import Path
        root = str(Path(__file__).parent.parent.parent)
        if root not in sys.path: sys.path.insert(0, root)
        yield

    def test_self_portrait_generates(self):
        from core.self.architecture_awareness import ArchitectureAwareness
        aware = ArchitectureAwareness()
        p = aware.generate_self_portrait()
        assert p is not None
        assert len(p.identity) > 50

    def test_identity_is_companion(self):
        from core.self.architecture_awareness import ArchitectureAwareness
        aware = ArchitectureAwareness()
        p = aware.generate_self_portrait()
        assert "同行者" in p.identity, f"identity should mention companion: {p.identity[:80]}"

    def test_architecture_has_5_layers(self):
        from core.self.architecture_awareness import ArchitectureAwareness
        aware = ArchitectureAwareness()
        p = aware.generate_self_portrait()
        assert len(p.layers) >= 4, f"too few layers: {len(p.layers)}"
        layer_names = [l.name for l in p.layers]
        assert "L0" in layer_names

    def test_module_scan_finds_runtime(self):
        from core.self.architecture_awareness import ArchitectureAwareness
        aware = ArchitectureAwareness()
        p = aware.generate_self_portrait()
        assert len(p.runtime_modules) > 0, "should find loaded modules"

    def test_improvement_priorities_have_rank(self):
        from core.self.architecture_awareness import ArchitectureAwareness
        aware = ArchitectureAwareness()
        p = aware.generate_self_portrait()
        assert len(p.improvement_priorities) >= 2
        assert "priority" in p.improvement_priorities[0]

    def test_companion_capabilities_complete(self):
        from core.self.architecture_awareness import ArchitectureAwareness
        aware = ArchitectureAwareness()
        p = aware.generate_self_portrait()
        caps = p.companion_capabilities
        assert len(caps) >= 4, f"too few companion capabilities: {len(caps)}"

    def test_design_gaps_identified(self):
        from core.self.architecture_awareness import ArchitectureAwareness
        aware = ArchitectureAwareness()
        p = aware.generate_self_portrait()
        assert isinstance(p.design_gaps, list), "design_gaps should be a list"
