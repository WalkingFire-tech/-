"""
L5元编程层 — 自我代码诊断与修复

5个子层级：
- L5.1 代码阅读：读取自己的.py文件（基于file_reader_tool）
- L5.2 代码理解：AST解析+缺陷诊断
- L5.3 补丁生成：LLM驱动的diff/patch
- L5.4 沙盒验证：隔离环境加载修改后模块（基于tool_builder._sandbox_exec）
- L5.5 渐进部署：0.1%→1%→20%→100%部署（基于truth_accumulator 6步安全协议）

设计原则：
- L5不是从零建设，而是在现有认知架构上叠加一层元认知
- file_reader_tool、tool_builder沙箱、truth_accumulator安全协议、spirit_lessons教训系统，都是L5的"预埋基础设施"
- spirit_lessons中的偏离和失败教训，是缺陷诊断的天然输入
"""

IMMUTABLE_FILES = frozenset({
    "core/spirit_core.py",
    "core/truth_accumulator.py",
    "core/resource_awareness/health_monitor.py",
    "core/resource_awareness/adaptive_governor.py",
})

from core.self_modification.code_reader import CodeReader
from core.self_modification.defect_diagnoser import DefectDiagnoser
from core.self_modification.patch_generator import PatchGenerator
from core.self_modification.patch_sandbox_deployer import PatchSandbox, PatchDeployer
from core.self_modification.loop import SelfModificationLoop, self_modification_loop
from core.self_modification.bootstrap_sandbox import BootstrapSandbox, bootstrap_sandbox
from core.self_modification.strategy_evolver import StrategyEvolver, strategy_evolver

__all__ = [
    "IMMUTABLE_FILES",
    "CodeReader", "DefectDiagnoser", "PatchGenerator",
    "PatchSandbox", "PatchDeployer",
    "SelfModificationLoop", "self_modification_loop",
    "BootstrapSandbox", "bootstrap_sandbox",
    "StrategyEvolver", "strategy_evolver",
]