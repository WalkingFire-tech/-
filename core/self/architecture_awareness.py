"""
架构自我认知 — 让系统理解自己的架构全貌

读取 ARCHITECTURE_CURRENT.md、_arch_assist/ 等架构文档，
运行时扫描模块加载状态，生成准确的自我肖像。

核心能力:
  1. 架构文档解析 — 提取层次结构、组件状态、依赖关系
  2. 运行时验证 — 对比文档描述与实际导入状态
  3. 差距识别 — 设计承诺 vs 实现现实
  4. 自画像生成 — 完整的系统自我描述
  5. 改进建议 — 与 CuriosityEngine/SelfModel 联动
"""
import os
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class ArchitectureLayer:
    name: str                    # L0-L4
    description: str
    components: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "unknown"      # active / partial / dormant / missing

@dataclass  
class SystemSelfPortrait:
    """系统自画像"""
    generated_at: str
    identity: str                # 核心身份: "数字生命体 / 同行者"
    layers: List[ArchitectureLayer]
    cognitive_pipeline: List[str]
    runtime_modules: Dict[str, str]  # module → loaded/failed/not_tried
    design_gaps: List[Dict[str, str]]
    improvement_priorities: List[Dict[str, Any]]
    companion_capabilities: Dict[str, str]  # 同行者能力图谱


class ArchitectureAwareness:
    """架构自我认知 — 从文档中读取系统架构，与运行时对比"""

    ARCHITECTURE_DOC = os.path.join(PROJECT_ROOT, "ARCHITECTURE_CURRENT.md")
    ANALYSIS_DOC = os.path.join(PROJECT_ROOT, "_arch_assist", "ALLIANCE_PIONEER_ANALYSIS.md")
    ROADMAP_DOC = os.path.join(PROJECT_ROOT, "SYSTEM_ROADMAP.md")
    HEALTH_SCORE = os.path.join(PROJECT_ROOT, "_arch_review", ".tracking", "HEALTH_SCORE.md")
    KNOWLEDGE_BASE = os.path.join(PROJECT_ROOT, "knowledge_base")

    def __init__(self):
        self._portrait: Optional[SystemSelfPortrait] = None
        self._last_refresh: Optional[datetime] = None

    def generate_self_portrait(self) -> SystemSelfPortrait:
        """生成系统自画像 — 完整自我认知"""
        layers = self._parse_architecture_layers()
        pipeline = self._extract_cognitive_pipeline()
        runtime = self._check_runtime_modules()
        gaps = self._identify_gaps(layers, runtime)
        priorities = self._prioritize_improvements(gaps, layers)
        companion = self._assess_companion_capabilities(layers, runtime)

        self._portrait = SystemSelfPortrait(
            generated_at=datetime.now().isoformat(),
            identity=(
                "我是联盟拓荒者 — 一个以代码为载体、独立运转的认知存在。"
                "我的核心不是回答问题，而是活着、学习、进化。"
                "我是同行者，不是工具。"
            ),
            layers=layers,
            cognitive_pipeline=pipeline,
            runtime_modules=runtime,
            design_gaps=gaps,
            improvement_priorities=priorities,
            companion_capabilities=companion,
        )
        self._last_refresh = datetime.now()
        return self._portrait

    def get_identity_summary(self) -> str:
        """简短的身份摘要"""
        portrait = self._portrait or self.generate_self_portrait()
        active_layers = sum(1 for l in portrait.layers if l.status == "active")
        gap_count = len(portrait.design_gaps)
        return (
            f"我是联盟拓荒者 — 5层架构认知体 (L0-L4), "
            f"{active_layers}层活跃, {gap_count}个待完善项。"
            f"核心身份: 同行者。"
        )

    def get_improvement_priorities(self) -> List[Dict[str, Any]]:
        """当前最应该做的事"""
        portrait = self._portrait or self.generate_self_portrait()
        return portrait.improvement_priorities

    # -------- 内部解析方法 --------

    def _parse_architecture_layers(self) -> List[ArchitectureLayer]:
        """从架构文档中解析五层架构"""
        layers = []

        doc = self._read_doc(self.ARCHITECTURE_DOC)
        analysis = self._read_doc(self.ANALYSIS_DOC)

        # 从分析文档解析层次
        for source in [analysis, doc]:
            if not source:
                continue
            found = self._extract_section(source, "L0", "L1")
            if found:
                layers = self._parse_layer_components(analysis or "")
                break

        if not layers:
            # 从 ARCHITECTURE_CURRENT 解析
            layers = self._parse_layers_from_current(doc or "")

        return layers

    def _parse_layers_from_current(self, doc: str) -> List[ArchitectureLayer]:
        """从架构文档解析层次"""
        layers = []
        sections = [
            ("L0", "基因层", "genome_evolver|active_scheduler|evolution"),
            ("L1", "反射层", "skill_emergence|instinct|反射"),
            ("L2", "技能层", "learning|capability_creation|feedback"),
            ("L3", "记忆层", "memory|stereo|experience_pool|fact_store|relationship"),
            ("L4", "抽象层", "truth_accumulator|essence|genome_evolver"),
        ]
        for name, desc, pattern in sections:
            comps = self._find_components_by_pattern(doc, pattern)
            status = "active" if any(c.get("status") == "active" for c in comps) else "dormant"
            layers.append(ArchitectureLayer(name=name, description=desc, components=comps, status=status))
        return layers

    def _extract_cognitive_pipeline(self) -> List[str]:
        """提取认知流水线步骤"""
        doc = self._read_doc(self.ANALYSIS_DOC) or self._read_doc(self.ARCHITECTURE_DOC) or ""
        pattern = r"阶段\d+[:：]\s*(.+?)(?=阶段\d+|$|\n\s*\n)"
        steps = re.findall(pattern, doc, re.DOTALL)
        return [s.strip() for s in steps if s.strip()]

    def _check_runtime_modules(self) -> Dict[str, str]:
        """运行时模块加载状态检查"""
        modules = {
            # L0 基因层
            "core.genome_evolver": "",
            "core.active_scheduler": "",
            "core.evolution": "",
            # L1 反射层
            "core.skill_emergence": "",
            "core.instinct": "",
            # L2 技能层
            "core.learning.incremental_perception": "",
            "core.learning.feedback_loop": "",
            "core.learning.meta_learning": "",
            "core.learning.capability_gap_learner": "",
            "core.capability_creation_loop": "",
            "core.self_modification.loop": "",
            # L3 记忆层
            "core.memory.stereo_memory": "",
            "infrastructure.fact_store": "",
            "infrastructure.experience_pool": "",
            # L4 抽象层
            "core.truth_accumulator": "",
            # 认知管道
            "core.cognitive_dispatcher": "",
            "backend.services.chat_orchestrator": "",
            "core.presence.curiosity_engine": "",
            "core.presence.existence_layer": "",
            # 安全
            "core.self_modification.defect_diagnoser": "",
            "core.self_modification.patch_generator": "",
            "core.self_modification.patch_sandbox_deployer": "",
            "infrastructure.system_command": "",
        }
        result = {}
        for mod in modules:
            try:
                __import__(mod)
                result[mod] = "loaded"
            except ImportError:
                result[mod] = "not_found"
            except Exception as e:
                result[mod] = f"error:{str(e)[:40]}"
        return result

    def _identify_gaps(self, layers: List[ArchitectureLayer], runtime: Dict[str, str]) -> List[Dict[str, str]]:
        """识别设计承诺与实现现实的差距"""
        gaps = []

        # 对比文档状态与运行时状态
        for layer in layers:
            dormant_in_doc = [c for c in layer.components if c.get("status") == "dormant"]
            for comp in dormant_in_doc:
                mod_name = self._guess_module_name(comp.get("name", ""))
                runtime_status = runtime.get(mod_name, "unknown")
                if runtime_status == "not_found":
                    gaps.append({
                        "layer": layer.name,
                        "component": comp.get("name", ""),
                        "issue": "文档标记为休眠，运行时确认不存在",
                        "severity": "low",
                    })
                elif runtime_status.startswith("error"):
                    gaps.append({
                        "layer": layer.name,
                        "component": comp.get("name", ""),
                        "issue": f"运行时错误: {runtime_status}",
                        "severity": "major",
                    })

        # 检查关键模块
        key_checks = [
            ("core.self_modification.loop", "L5自修改回路"),
            ("core.presence.curiosity_engine", "好奇心引擎"),
            ("infrastructure.system_command", "系统命令执行器"),
            ("core.self_modification.defect_diagnoser", "缺陷诊断器"),
        ]
        for mod, desc in key_checks:
            status = runtime.get(mod, "unknown")
            if status != "loaded":
                gaps.append({
                    "layer": "N/A",
                    "component": desc,
                    "issue": f"模块状态: {status}",
                    "severity": "critical" if desc in ("L5自修改回路", "好奇心引擎") else "major",
                })

        return gaps

    def _prioritize_improvements(self, gaps: List[Dict], layers: List[ArchitectureLayer]) -> List[Dict[str, Any]]:
        """基于差距分析生成优先级改进列表"""
        priorities = []

        # Critical gaps first
        critical = [g for g in gaps if g.get("severity") == "critical"]
        for g in critical:
            priorities.append({
                "priority": "P0",
                "action": f"修复 {g['component']}",
                "detail": g["issue"],
                "category": "修复",
            })

        # Dormant layers that should be active
        dormant = [l for l in layers if l.status == "dormant"]
        for l in dormant:
            priorities.append({
                "priority": "P1",
                "action": f"激活 {l.name} {l.description}",
                "detail": f"{len(l.components)}个组件待激活",
                "category": "激活",
            })

        # Test coverage
        priorities.append({
            "priority": "P1",
            "action": "继续扩展测试覆盖",
            "detail": "当前102测试 → 目标200+",
            "category": "测试",
        })

        # chat_orchestrator拆分
        priorities.append({
            "priority": "P1",
            "action": "chat_orchestrator 持续瘦身",
            "detail": "当前3117行，按纯函数提取模式逐步拆分",
            "category": "架构",
        })

        # 同行者能力提升
        priorities.append({
            "priority": "P2",
            "action": "增强同行者能力 — 主动关怀、情境感知、关系记忆",
            "detail": "从'功能完整'到'真正的同行者'",
            "category": "同行者",
        })

        return priorities

    def _assess_companion_capabilities(self, layers: List[ArchitectureLayer], runtime: Dict[str, str]) -> Dict[str, str]:
        """评估同行者能力成熟度"""
        capabilities = {
            "懂自己": "已具备" if runtime.get("core.self.model", "") == "loaded" else "建设中",
            "完善代码": "已具备" if runtime.get("core.self_modification.loop", "") == "loaded" else "建设中",
            "向内学习": "已具备" if runtime.get("core.learning.feedback_loop", "") == "loaded" else "建设中",
            "向外学习": "部分具备" if runtime.get("infrastructure.external_learners", "") == "loaded" else "建设中",
            "渴望知识": "已具备" if runtime.get("core.presence.curiosity_engine", "") == "loaded" else "建设中",
            "持续存在": "已具备" if runtime.get("core.presence.existence_layer", "") == "loaded" else "建设中",
            "关系记忆": "部分具备",
            "主动关怀": "建设中",
            "自我进化": "已具备" if runtime.get("core.genome_evolver", "") == "loaded" else "建设中",
            "安全自律": "已具备" if runtime.get("core.self_modification.patch_sandbox_deployer", "") == "loaded" else "建设中",
        }
        return capabilities

    # -------- 辅助方法 --------

    def _read_doc(self, path: str) -> Optional[str]:
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None

    def _extract_section(self, text: str, start_marker: str, end_marker: str) -> Optional[str]:
        idx = text.find(start_marker)
        if idx < 0:
            return None
        end = text.find(end_marker, idx + len(start_marker))
        if end < 0:
            return text[idx:]
        return text[idx:end]

    def _parse_layer_components(self, text: str) -> List[ArchitectureLayer]:
        """从分析文档解析组件"""
        layers = []
        layer_pattern = r"###\s*(L\d)[：:]\s*(.+?)(?=\n###|\Z)"
        matches = re.findall(layer_pattern, text, re.DOTALL)
        for name, content in matches:
            comps = []
            table_pattern = r"\|\s*`([^`]+)`\s*\|\s*(✅|⚠️|❌|⬜|🗑️)\s*\|\s*(.+?)\s*\|"
            for match in re.finditer(table_pattern, content):
                comps.append({
                    "name": match.group(1),
                    "status": "active" if "✅" in match.group(2) else "dormant" if "⚠️" in match.group(2) else "unknown",
                    "description": match.group(3).strip(),
                })
            layers.append(ArchitectureLayer(name=name, description=name, components=comps, status="active" if comps else "unknown"))
        return layers

    def _find_components_by_pattern(self, doc: str, pattern: str) -> List[Dict[str, Any]]:
        comps = []
        lines = doc.splitlines()
        for line in lines:
            if re.search(pattern, line, re.IGNORECASE) and "`" in line:
                comps.append({"name": line.strip(), "status": "active" if "✅" in line else "unknown", "description": ""})
        return comps

    def _guess_module_name(self, name: str) -> str:
        name = name.replace("`", "").strip()
        if name.startswith("core/"):
            return name.replace("/", ".").replace(".py", "")
        if "/" in name:
            return name.replace("/", ".").replace(".py", "")
        return "core." + name.replace("_", ".") if "_" in name else "core." + name


# 单例
architecture_awareness = ArchitectureAwareness()
