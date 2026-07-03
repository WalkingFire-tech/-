"""
系统性模块导入验证测试
逐个验证所有模块的导入是否正常
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

class ModuleValidator:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def test_import(self, module_path, class_name=None):
        """测试导入"""
        try:
            module = __import__(module_path, fromlist=[class_name] if class_name else [])
            if class_name:
                cls = getattr(module, class_name)
                self.passed.append(f"{module_path}.{class_name}")
                return True, cls
            else:
                self.passed.append(module_path)
                return True, module
        except Exception as e:
            error_msg = str(e)[:100]
            self.failed.append(f"{module_path}.{class_name}: {error_msg}")
            return False, None
    
    def print_result(self, test_name, success, detail=""):
        if success:
            print(f"  ✅ {test_name} {detail}")
        else:
            print(f"  ❌ {test_name} - {detail}")

def validate_core_modules(validator):
    """验证核心模块"""
    print("\n[1] 核心模块验证")
    print("-" * 60)
    
    modules = [
        ("core.orchestrator", "SystemOrchestrator"),
        ("core.cognitive_dispatcher", "CognitiveDispatcher"),
        ("core.metacognitive_executor", "MetacognitiveExecutor"),
        ("core.sleep_consolidator", "SleepConsolidator"),
        ("core.canary_evaluator", "CanaryEvaluator"),
        ("core.cognitive_loop", "CognitiveLoop"),
        ("core.external_learner", "ExternalLearner"),
    ]
    
    for module_path, class_name in modules:
        success, _ = validator.test_import(module_path, class_name)
        validator.print_result(f"{module_path}.{class_name}", success)

def validate_layers(validator):
    """验证层架构"""
    print("\n[2] 层架构验证")
    print("-" * 60)
    
    layers = [
        ("core.layers.l1_perception_enhanced", "L1PerceptionLayer"),
        ("core.layers.l2_learning", "L2LearningLayer"),
        ("core.layers.l3_integration", "L3IntegrationLayer"),
        ("core.layers.l4_validation", "L4ValidationLayer"),
        ("core.layers.l5_evolution", "L5EvolutionLayer"),
        ("core.layers.l6_introspection", "L6IntrospectionLayer"),
    ]
    
    for module_path, class_name in layers:
        success, _ = validator.test_import(module_path, class_name)
        validator.print_result(f"{module_path}.{class_name}", success)

def validate_infrastructure(validator):
    """验证基础设施层"""
    print("\n[3] 基础设施层验证")
    print("-" * 60)
    
    modules = [
        ("infrastructure.event_bus", "EventBus"),
        ("infrastructure.config_manager", "ConfigManager"),
        ("infrastructure.experience_pool", "ExperiencePool"),
        ("infrastructure.reflection_pipeline", "ReflectionPipeline"),
        ("infrastructure.quick_reflex", "QuickReflexEngine"),
    ]
    
    for module_path, class_name in modules:
        success, _ = validator.test_import(module_path, class_name)
        validator.print_result(f"{module_path}.{class_name}", success)

def validate_tools(validator):
    """验证工具层"""
    print("\n[4] 工具层验证")
    print("-" * 60)
    
    modules = [
        ("tools.base", "Tool"),
        ("tools.registry", "ToolRegistry"),
        ("tools.arbiter", "ToolArbiter"),
        ("tools.math_calculator", None),
        ("tools.web_search", None),
        ("tools.file_operations", None),
    ]
    
    for module_path, class_name in modules:
        success, _ = validator.test_import(module_path, class_name)
        name = f"{module_path}.{class_name}" if class_name else module_path
        validator.print_result(name, success)

def validate_adapters(validator):
    """验证适配器层"""
    print("\n[5] 适配器层验证")
    print("-" * 60)
    
    modules = [
        ("adapters.llm.ollama_adapter", "OllamaAdapter"),
        ("adapters.llm.openai_adapter", "OpenAIAdapter"),
        ("adapters.llm.local_qwen_adapter", "LocalQwenAdapter"),
        ("adapters.llm.mock_adapter", "MockAdapter"),
        ("adapters.llm.remote_adapter", "RemoteAdapter"),
        ("adapters.llm.lora_adapter", "LoRAAdapter"),
        ("adapters.ui.cli_ui", "EnhancedCliUI"),
        ("adapters.input.file_adapter", "FileAdapter"),
        ("adapters.input.folder_processor", "FolderBatchProcessor"),
    ]
    
    for module_path, class_name in modules:
        success, _ = validator.test_import(module_path, class_name)
        validator.print_result(f"{module_path}.{class_name}", success)

def validate_meta(validator):
    """验证元认知层"""
    print("\n[6] 元认知层验证")
    print("-" * 60)
    
    modules = [
        ("meta.induction", "InductionScheduler"),
        ("meta.meta_induction", "MetaInduction"),
    ]
    
    for module_path, class_name in modules:
        success, _ = validator.test_import(module_path, class_name)
        validator.print_result(f"{module_path}.{class_name}", success)

def validate_presence(validator):
    """验证存在层"""
    print("\n[7] 存在层验证")
    print("-" * 60)
    
    modules = [
        ("core.presence.existence_layer", "ExistenceLayer"),
        ("core.presence.self_perception", "SelfPerceptionModule"),
        ("core.presence.gap_growth", "GapGrowthEngine"),
        ("core.presence.sleep_consolidation", "SleepConsolidationEngine"),
    ]
    
    for module_path, class_name in modules:
        success, _ = validator.test_import(module_path, class_name)
        validator.print_result(f"{module_path}.{class_name}", success)

def validate_introspection(validator):
    """验证内省层"""
    print("\n[8] 内省层验证")
    print("-" * 60)
    
    modules = [
        ("core.introspection.heartbeat", "HeartbeatManager"),
        ("core.reporting.state_collector", "StateCollector"),
    ]
    
    for module_path, class_name in modules:
        success, _ = validator.test_import(module_path, class_name)
        validator.print_result(f"{module_path}.{class_name}", success)

def validate_services(validator):
    """验证服务层"""
    print("\n[9] 服务层验证")
    print("-" * 60)
    
    modules = [
        ("core.services.intent_parser", "IntentParser"),
        ("core.services.planner", "Planner"),
    ]
    
    for module_path, class_name in modules:
        success, _ = validator.test_import(module_path, class_name)
        validator.print_result(f"{module_path}.{class_name}", success)

def main():
    print("=" * 60)
    print("系统性模块导入验证")
    print("=" * 60)
    
    validator = ModuleValidator()
    
    validate_core_modules(validator)
    validate_layers(validator)
    validate_infrastructure(validator)
    validate_tools(validator)
    validate_adapters(validator)
    validate_meta(validator)
    validate_presence(validator)
    validate_introspection(validator)
    validate_services(validator)
    
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    print(f"✅ 通过: {len(validator.passed)}")
    print(f"❌ 失败: {len(validator.failed)}")
    
    if validator.failed:
        print("\n失败详情:")
        for item in validator.failed:
            print(f"  ❌ {item}")
        return 1
    else:
        print("\n🎉 所有模块导入验证通过！")
        return 0

if __name__ == "__main__":
    sys.exit(main())