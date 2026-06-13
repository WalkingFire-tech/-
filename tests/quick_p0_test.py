"""
P0优化快速验证
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_planner_methods():
    """验证planner方法已添加"""
    from core.services.planner import DataDrivenPlanner
    
    methods = [
        '_check_reflex_level',
        '_infer_emotion',
        '_check_system_state',
        '_apply_five_layer_defense',
        '_handle_normal_flow'
    ]
    
    for method in methods:
        assert hasattr(DataDrivenPlanner, method), f"缺少方法: {method}"
    
    print("✅ Planner子方法已添加")


def test_intent_parser_meta():
    """验证meta意图识别"""
    from core.services.intent_parser import IntentParser
    
    parser = IntentParser()
    
    tests = [
        ("你的能力边界在哪里？", "meta"),
        ("你如何决策？", "meta"),
        ("回顾对话历史", "meta"),
    ]
    
    for text, expected in tests:
        intent = parser.parse(text)
        assert intent.type == expected, f"'{text}' -> {intent.type} (期望{expected})"
    
    print("✅ Meta意图识别正常")


def test_reflex_engine():
    """验证反射引擎"""
    from infrastructure.reflex_engine import ReflexEngine
    
    engine = ReflexEngine()
    assert len(engine.rules) > 0, "应加载默认规则"
    
    context = {"user_input": "你好", "memory_percent": 50}
    result = engine.check(context)
    assert result is None, "正常场景不应触发"
    
    print("✅ 反射引擎正常")


def main():
    print("="*60)
    print("P0优化快速验证")
    print("="*60)
    
    try:
        test_planner_methods()
        test_intent_parser_meta()
        test_reflex_engine()
        
        print("\n" + "="*60)
        print("✅ 所有验证通过")
        print("="*60)
        return 0
    except Exception as e:
        print(f"\n❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())