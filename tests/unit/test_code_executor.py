"""
单元测试 - 代码执行沙箱 (P1-4)
"""
import pytest
from infrastructure.code_executor import CodeExecutor


class TestCodeExecutorValidation:
    def test_valid_simple_code(self):
        result = CodeExecutor._validate_code("print('hello')")
        assert result["valid"] is True

    def test_code_too_long(self):
        result = CodeExecutor._validate_code("x = 1\n" * 5000)
        assert result["valid"] is False
        assert "过长" in result["error"]

    def test_dangerous_os_usage(self):
        result = CodeExecutor._validate_code("os.listdir('.')")
        assert result["valid"] is False

    def test_dangerous_eval(self):
        result = CodeExecutor._validate_code("eval('1+1')")
        assert result["valid"] is False

    def test_dangerous_open(self):
        result = CodeExecutor._validate_code("open('file.txt')")
        assert result["valid"] is False


class TestCodeExecutorSubprocess:
    def test_simple_print(self):
        result = CodeExecutor.execute("print(2+3)", timeout=5, method="subprocess")
        assert result["success"] is True
        assert "5" in result["output"]

    def test_loop(self):
        result = CodeExecutor.execute("for i in range(3): print(i)", timeout=5, method="subprocess")
        assert result["success"] is True
        assert "0" in result["output"]
        assert "2" in result["output"]

    def test_math_import(self):
        result = CodeExecutor.execute("import math; print(math.sqrt(144))", timeout=5, method="subprocess")
        assert result["success"] is True
        assert "12" in result["output"]

    def test_timeout(self):
        result = CodeExecutor.execute("while True: pass", timeout=2, method="subprocess")
        assert result["success"] is False
        assert "超时" in result["error"]

    def test_syntax_error(self):
        result = CodeExecutor.execute("print(", timeout=5, method="subprocess")
        assert result["success"] is False


class TestCodeExecutorAuto:
    def test_auto_mode(self):
        result = CodeExecutor.execute("print('auto works')", timeout=5, method="auto")
        assert result["success"] is True

    def test_disabled_mode(self):
        result = CodeExecutor.execute("print('test')", timeout=5, method="disabled")
        assert result["success"] is False
        assert "禁用" in result["error"]


class TestCodeExecutorAvailability:
    def test_is_available(self):
        avail = CodeExecutor.is_available()
        assert "docker" in avail
        assert "restricted" in avail
        assert "subprocess" in avail
        assert avail["subprocess"] is True