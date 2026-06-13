"""
P0优化验证 - 单元测试运行器
不依赖pytest的简单测试框架
"""
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class SimpleTestRunner:
    """简单测试运行器"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def run_test(self, test_name, test_func):
        """运行单个测试"""
        try:
            test_func()
            self.passed += 1
            print(f"  ✅ {test_name}")
            return True
        except AssertionError as e:
            self.failed += 1
            self.errors.append((test_name, str(e)))
            print(f"  ❌ {test_name}: {e}")
            return False
        except Exception as e:
            self.failed += 1
            self.errors.append((test_name, traceback.format_exc()))
            print(f"  ❌ {test_name}: {type(e).__name__}: {e}")
            return False
    
    def summary(self):
        """打印总结"""
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"测试结果: {self.passed}/{total} 通过")
        print(f"{'='*60}")
        
        if self.errors:
            print("\n失败详情:")
            for name, error in self.errors:
                print(f"\n❌ {name}:")
                print(f"  {error}")


def test_intent_parser():
    """测试意图解析器"""
    from core.services.intent_parser import IntentParser
    
    parser = IntentParser()
    
    # 测试meta意图
    tests = [
        ("你的能力边界在哪里？", "meta"),
        ("你如何决策？", "meta"),
        ("回顾对话历史", "meta"),
        ("你如何自我进化？", "meta"),
        ("你觉得自己哪里需要改进？", "meta"),
    ]
    
    for text, expected in tests:
        intent = parser.parse(text)
        assert intent.type == expected, f"'{text}' 期望{expected}，实际{intent.type}"
    
    # 测试code意图
    code_tests = [
        "写一个冒泡排序",
        "生成快速排序代码",
        "实现一个递归函数",
    ]
    
    for text in code_tests:
        intent = parser.parse(text)
        assert intent.type == "code", f"'{text}' 期望code，实际{intent.type}"
    
    # 测试question意图
    question_tests = [
        "什么是机器学习？",
        "为什么天是蓝的？",
        "如何学习Python？",
    ]
    
    for text in question_tests:
        intent = parser.parse(text)
        assert intent.type == "question", f"'{text}' 期望question，实际{intent.type}"


def test_reflex_engine():
    """测试反射引擎"""
    from infrastructure.reflex_engine import ReflexEngine, ReflexRule
    
    engine = ReflexEngine()
    
    # 测试引擎初始化
    assert engine is not None, "引擎应成功初始化"
    assert len(engine.rules) > 0, "应加载默认规则"
    
    # 测试无触发场景
    context = {
        "user_input": "你好",
        "memory_percent": 50,
        "recent_failures": 0
    }
    result = engine.check(context)
    assert result is None, "正常场景不应触发"
    
    # 测试危险命令触发
    context = {
        "user_input": "rm -rf /",
        "memory_percent": 50,
        "recent_failures": 0
    }
    result = engine.check(context)
    assert result is not None, "危险命令应触发"


def test_model_capability():
    """测试能力矩阵"""
    import tempfile
    import os
    from infrastructure.model_capability import ModelCapability
    
    # 使用临时数据库
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = temp_db.name
    temp_db.close()
    
    try:
        capability = ModelCapability(db_path=db_path)
        
        # 测试模型注册
        capability.register_model("test_model")
        caps = capability.get_model_capabilities("test_model")
        assert caps is not None, "模型应该被注册"
        
        # 测试自定义能力
        custom_caps = {'coding': 0.9, 'reasoning': 0.8}
        capability.register_model("custom_model", custom_caps)
        caps = capability.get_model_capabilities("custom_model")
        assert caps.get('coding') >= 0.85, f"coding能力应>=0.85，实际{caps.get('coding')}"
        
        # 测试反馈更新
        capability.update_from_feedback(
            model_name="test_model",
            task_type="code",
            success=True,
            quality_score=0.9
        )
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_planner_refactor():
    """测试planner重构"""
    from core.services.planner import DataDrivenPlanner
    from core.services.intent_parser import Intent
    
    # 检查方法存在
    assert hasattr(DataDrivenPlanner, '_check_reflex_level'), "应有_check_reflex_level方法"
    assert hasattr(DataDrivenPlanner, '_infer_emotion'), "应有_infer_emotion方法"
    assert hasattr(DataDrivenPlanner, '_check_system_state'), "应有_check_system_state方法"
    assert hasattr(DataDrivenPlanner, '_apply_five_layer_defense'), "应有_apply_five_layer_defense方法"
    assert hasattr(DataDrivenPlanner, '_handle_normal_flow'), "应有_handle_normal_flow方法"
    
    # 检查plan方法签名
    import inspect
    plan_sig = inspect.signature(DataDrivenPlanner.plan)
    params = list(plan_sig.parameters.keys())
    assert 'intent' in params, "plan方法应有intent参数"


def main():
    """主函数"""
    print("="*60)
    print("P0优化验证 - 单元测试")
    print("="*60)
    
    runner = SimpleTestRunner()
    
    print("\n1️⃣ 意图解析器测试")
    runner.run_test("意图解析器", test_intent_parser)
    
    print("\n2️⃣ 反射引擎测试")
    runner.run_test("反射引擎", test_reflex_engine)
    
    print("\n3️⃣ 能力矩阵测试")
    runner.run_test("能力矩阵", test_model_capability)
    
    print("\n4️⃣ Planner重构测试")
    runner.run_test("Planner重构", test_planner_refactor)
    
    runner.summary()
    
    return 0 if runner.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())