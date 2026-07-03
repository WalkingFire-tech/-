"""
联盟拓荒者 - 测试配置
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: 慢速测试（>5s）")
    config.addinivalue_line("markers", "e2e: 端到端测试（需要服务运行）")
    config.addinivalue_line("markers", "ollama: 需要Ollama服务")