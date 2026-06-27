"""
验证所有修复的模块可以正常导入
"""
import sys
import traceback

def test_import(module_path, class_name=None):
    """测试模块导入"""
    try:
        module = __import__(module_path, fromlist=[class_name] if class_name else [])
        if class_name:
            cls = getattr(module, class_name)
            print(f"✅ {module_path}.{class_name}")
        else:
            print(f"✅ {module_path}")
        return True
    except Exception as e:
        print(f"❌ {module_path}: {str(e)[:100]}")
        return False

def main():
    print("=" * 60)
    print("验证核心模块导入")
    print("=" * 60)
    
    modules = [
        # 认知规划器
        ("core.services.cognitive_planner", "CognitivePlanner"),
        
        # 意图系统
        ("core.intent", "Intent"),
        ("core.intent_router", "IntentRouter"),
        ("core.services.intent_parser", "IntentParser"),
        ("core.services.auto_intent_parser", "AutoIntentParser"),
        
        # 外部学习器
        ("core.external_learner", "ExternalLearner"),
        
        # 间隙生长引擎
        ("core.presence.gap_growth", "GapGrowthEngine"),
        
        # 知识检测器（新版本）
        ("core.knowledge.detector", "SemanticGapDetector"),
        ("core.knowledge.validator", "KnowledgeValidator"),
        ("core.knowledge.learner", "DomainKnowledgeLearner"),
        
        # 反思驱动进化
        ("core.reflective_model_free_evolution", "ReflectiveModelFreeEvolution"),
        
        # 旧版本（保留兼容性）
        ("core.knowledge_gap_detector", "KnowledgeGapDetector"),
        ("core.recommendation_validator", "RecommendationValidator"),
    ]
    
    success = 0
    failed = 0
    
    for module_path, class_name in modules:
        if test_import(module_path, class_name):
            success += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"总计: {success + failed} 个模块")
    print(f"成功: {success} 个")
    print(f"失败: {failed} 个")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)