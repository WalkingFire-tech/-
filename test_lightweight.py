"""轻量级后端测试"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

print("测试1: 配置管理器")
from infrastructure.config_manager import config
print(f"✓ 配置键: {list(config._config.keys())}")

print("\n测试2: 工具生成器")
from tools.generator import ToolGenerator
tg = ToolGenerator()
print(f"✓ 生成目录: {tg.generated_tools_dir}")

print("\n测试3: FastAPI导入")
from fastapi import FastAPI
print("✓ FastAPI导入成功")

print("\n✅ 基础测试通过")