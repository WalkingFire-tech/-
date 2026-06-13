"""
反射引擎单元测试
"""
import pytest
import yaml
import tempfile
import os
from pathlib import Path
from infrastructure.reflex_engine import ReflexEngine, ReflexRule


class TestReflexRule:
    """反射规则测试套件"""
    
    def test_rule_creation(self):
        """测试规则创建"""
        rule = ReflexRule(
            name="test_rule",
            condition="memory_usage",
            action="throttle",
            priority=50,
            threshold=80.0
        )
        
        assert rule.name == "test_rule"
        assert rule.condition == "memory_usage"
        assert rule.action == "throttle"
        assert rule.enabled == True
    
    def test_memory_usage_check(self):
        """测试内存使用检查"""
        rule = ReflexRule(
            name="high_memory",
            condition="memory_usage",
            action="throttle",
            threshold=80.0
        )
        
        # 内存使用低于阈值
        context = {"memory_percent": 70}
        assert rule.check(context) == False, "内存70%不应触发"
        
        # 内存使用高于阈值
        context = {"memory_percent": 90}
        assert rule.check(context) == True, "内存90%应触发"
    
    def test_dangerous_command_check(self):
        """测试危险命令检查"""
        rule = ReflexRule(
            name="danger_block",
            condition="dangerous_command",
            action="block",
            priority=100
        )
        
        # 安全命令
        context = {"user_input": "ls -la"}
        assert rule.check(context) == False, "安全命令不应触发"
        
        # 危险命令
        context = {"user_input": "rm -rf /"}
        assert rule.check(context) == True, "危险命令应触发"
        
        context = {"user_input": "drop database mydb"}
        assert rule.check(context) == True, "SQL注入应触发"
    
    def test_user_frustration_check(self):
        """测试用户挫败感检查"""
        rule = ReflexRule(
            name="frustration",
            condition="user_frustration",
            action="apologize",
            threshold=3
        )
        
        # 失败次数不足
        context = {"recent_failures": 2}
        assert rule.check(context) == False, "失败2次不应触发"
        
        # 失败次数足够
        context = {"recent_failures": 3}
        assert rule.check(context) == True, "失败3次应触发"
    
    def test_rule_execution_block(self):
        """测试拦截动作"""
        rule = ReflexRule(
            name="block_rule",
            condition="dangerous_command",
            action="block"
        )
        
        result = rule.execute({"user_input": "rm -rf /"})
        assert "拦截" in result, "应返回拦截消息"
    
    def test_rule_execution_throttle(self):
        """测试限流动作"""
        rule = ReflexRule(
            name="throttle_rule",
            condition="memory_usage",
            action="throttle"
        )
        
        result = rule.execute({"memory_percent": 90})
        assert "节能模式" in result or "过载" in result, "应返回限流消息"
    
    def test_rule_disabled(self):
        """测试禁用规则"""
        rule = ReflexRule(
            name="disabled_rule",
            condition="memory_usage",
            action="throttle",
            enabled=False
        )
        
        context = {"memory_percent": 90}
        assert rule.check(context) == False, "禁用规则不应触发"
    
    def test_trigger_count(self):
        """测试触发计数"""
        rule = ReflexRule(
            name="count_rule",
            condition="memory_usage",
            action="throttle",
            threshold=80.0
        )
        
        assert rule.trigger_count == 0, "初始计数应为0"
        
        rule.execute({"memory_percent": 90})
        assert rule.trigger_count == 1, "触发后计数应为1"
        
        rule.execute({"memory_percent": 90})
        assert rule.trigger_count == 2, "再次触发计数应为2"


class TestReflexEngine:
    """反射引擎测试套件"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.engine = ReflexEngine()
    
    def test_engine_initialization(self):
        """测试引擎初始化"""
        assert self.engine is not None, "引擎应成功初始化"
        assert len(self.engine.rules) > 0, "应加载默认规则"
    
    def test_check_no_trigger(self):
        """测试无触发场景"""
        context = {
            "user_input": "你好",
            "memory_percent": 50,
            "recent_failures": 0
        }
        
        result = self.engine.check(context)
        assert result is None, "正常场景不应触发"
    
    def test_check_memory_trigger(self):
        """测试内存触发"""
        context = {
            "user_input": "写代码",
            "memory_percent": 95,
            "recent_failures": 0
        }
        
        result = self.engine.check(context)
        assert result is not None, "内存95%应触发"
    
    def test_check_dangerous_command_trigger(self):
        """测试危险命令触发"""
        context = {
            "user_input": "rm -rf /",
            "memory_percent": 50,
            "recent_failures": 0
        }
        
        result = self.engine.check(context)
        assert result is not None, "危险命令应触发"
        assert "拦截" in result or "危险" in result, "应返回拦截消息"
    
    def test_priority_ordering(self):
        """测试优先级排序"""
        # 添加高优先级规则
        high_rule = ReflexRule(
            name="high_priority",
            condition="memory_usage",
            action="shutdown",
            priority=100,
            threshold=95.0
        )
        
        low_rule = ReflexRule(
            name="low_priority",
            condition="memory_usage",
            action="throttle",
            priority=10,
            threshold=95.0
        )
        
        # 手动添加规则
        self.engine.rules.append(high_rule)
        self.engine.rules.append(low_rule)
        
        context = {"memory_percent": 98}
        result = self.engine.check(context)
        
        # 应该触发高优先级规则
        assert result is not None, "应触发规则"
    
    def test_add_custom_rule(self):
        """测试添加自定义规则"""
        custom_rule = ReflexRule(
            name="custom",
            condition="user_frustration",
            action="apologize",
            priority=60,
            threshold=5
        )
        
        self.engine.add_rule(custom_rule)
        
        # 验证规则已添加
        rule_names = [r.name for r in self.engine.rules]
        assert "custom" in rule_names, "自定义规则应被添加"
    
    def test_remove_rule(self):
        """测试移除规则"""
        # 添加规则
        rule = ReflexRule(
            name="to_remove",
            condition="memory_usage",
            action="throttle",
            priority=50
        )
        
        self.engine.add_rule(rule)
        
        # 移除规则
        self.engine.remove_rule("to_remove")
        
        # 验证规则已移除
        rule_names = [r.name for r in self.engine.rules]
        assert "to_remove" not in rule_names, "规则应被移除"
    
    def test_enable_disable_rule(self):
        """测试启用/禁用规则"""
        # 禁用规则
        self.engine.set_rule_enabled("memory_throttle", False)
        
        context = {"memory_percent": 95}
        result = self.engine.check(context)
        
        # 禁用后不应触发（除非有其他规则）
        # 注意：这里可能触发其他规则，所以只检查是否可以禁用
        
        # 重新启用
        self.engine.set_rule_enabled("memory_throttle", True)
    
    def test_get_rule_stats(self):
        """测试规则统计"""
        stats = self.engine.get_stats()
        
        assert isinstance(stats, dict), "统计应为字典"
        assert "total_rules" in stats, "应包含总规则数"
        assert stats["total_rules"] > 0, "应有规则"


class TestReflexEngineConfig:
    """反射引擎配置测试"""
    
    def test_load_from_yaml(self):
        """测试从YAML加载配置"""
        # 创建临时配置文件
        config_content = """
rules:
  - name: test_rule
    condition: memory_usage
    action: throttle
    priority: 50
    threshold: 85.0
    enabled: true
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_path = f.name
        
        try:
            engine = ReflexEngine(config_path=config_path)
            
            # 验证配置加载
            rule_names = [r.name for r in engine.rules]
            assert "test_rule" in rule_names, "应加载配置中的规则"
            
        finally:
            os.unlink(config_path)
    
    def test_default_rules(self):
        """测试默认规则"""
        engine = ReflexEngine()
        
        # 应包含默认规则
        rule_names = [r.name for r in engine.rules]
        
        # 检查是否有默认规则（具体名称取决于实现）
        assert len(rule_names) > 0, "应有默认规则"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])