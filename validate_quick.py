"""快速模块验证 - 分批测试"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("="*60)
print("模块导入验证")
print("="*60)

# 批次1: 核心模块
print("\n[批次1] 核心模块")
try:
    from core.orchestrator import SystemOrchestrator
    print("✅ core.orchestrator.SystemOrchestrator")
except Exception as e:
    print(f"❌ core.orchestrator: {e}")

try:
    from core.cognitive_dispatcher import CognitiveDispatcher
    print("✅ core.cognitive_dispatcher.CognitiveDispatcher")
except Exception as e:
    print(f"❌ core.cognitive_dispatcher: {e}")

try:
    from core.metacognitive_executor import MetacognitiveExecutor
    print("✅ core.metacognitive_executor.MetacognitiveExecutor")
except Exception as e:
    print(f"❌ core.metacognitive_executor: {e}")

# 批次2: 层架构
print("\n[批次2] 层架构")
try:
    from core.layers.l1_perception_enhanced import L1PerceptionLayer
    print("✅ L1PerceptionLayer")
except Exception as e:
    print(f"❌ L1: {e}")

try:
    from core.layers.l2_learning import L2LearningLayer
    print("✅ L2LearningLayer")
except Exception as e:
    print(f"❌ L2: {e}")

try:
    from core.layers.l3_integration import L3IntegrationLayer
    print("✅ L3IntegrationLayer")
except Exception as e:
    print(f"❌ L3: {e}")

# 批次3: 基础设施
print("\n[批次3] 基础设施")
try:
    from infrastructure.reflection_pipeline import ReflectionPipeline
    print("✅ ReflectionPipeline")
except Exception as e:
    print(f"❌ reflection_pipeline: {e}")

try:
    from infrastructure.experience_pool import ExperiencePool
    print("✅ ExperiencePool")
except Exception as e:
    print(f"❌ experience_pool: {e}")

try:
    from infrastructure.quick_reflex import QuickReflexEngine
    print("✅ QuickReflexEngine")
except Exception as e:
    print(f"❌ quick_reflex: {e}")

# 批次4: 工具
print("\n[批次4] 工具层")
try:
    from tools.registry import registry
    print("✅ tools.registry")
except Exception as e:
    print(f"❌ tools.registry: {e}")

try:
    from tools.arbiter import ToolArbiter
    print("✅ ToolArbiter")
except Exception as e:
    print(f"❌ tools.arbiter: {e}")

# 批次5: 适配器
print("\n[批次5] 适配器")
try:
    from adapters.llm.ollama_adapter import OllamaAdapter
    print("✅ OllamaAdapter")
except Exception as e:
    print(f"❌ OllamaAdapter: {e}")

try:
    from adapters.ui.cli_ui import EnhancedCliUI
    print("✅ EnhancedCliUI")
except Exception as e:
    print(f"❌ EnhancedCliUI: {e}")

try:
    from adapters.input.folder_processor import FolderBatchProcessor
    print("✅ FolderBatchProcessor")
except Exception as e:
    print(f"❌ FolderBatchProcessor: {e}")

print("\n" + "="*60)
print("验证完成")
print("="*60)