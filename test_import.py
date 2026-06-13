"""测试backend.main导入"""
import sys
import traceback
from pathlib import Path

print("=" * 60)
print("测试backend.main导入")
print("=" * 60)
print(f"当前目录: {Path.cwd()}")
print(f"Python版本: {sys.version}")
print()

try:
    # 设置路径
    ROOT_DIR = Path(__file__).parent
    sys.path.insert(0, str(ROOT_DIR))
    
    print("[步骤1] 导入基础模块...")
    import os
    from fastapi import FastAPI
    from loguru import logger
    from dotenv import load_dotenv
    load_dotenv()
    print("  ✓ 基础模块导入成功")
    
    print("\n[步骤2] 导入infrastructure...")
    from infrastructure.event_bus import bus
    print("  ✓ event_bus")
    
    print("\n[步骤3] 导入core.services...")
    from core.services.intent_parser import IntentParser
    from core.services.planner import Planner
    print("  ✓ intent_parser, planner")
    
    print("\n[步骤4] 导入adapters...")
    from adapters.llm.ollama_adapter import OllamaAdapter
    from adapters.llm.remote_adapter import RemoteAdapter
    print("  ✓ ollama_adapter, remote_adapter")
    
    print("\n[步骤5] 导入backend.main...")
    from backend import main
    print("  ✓ backend.main导入成功")
    print(f"  ✓ App对象: {main.app}")
    print(f"  ✓ App标题: {main.app.title}")
    print(f"  ✓ 路由数量: {len(main.app.routes)}")
    
    print("\n" + "=" * 60)
    print("所有模块导入成功！")
    print("=" * 60)
    
except Exception as e:
    print(f"\n✗ 错误: {e}")
    print("\n完整错误信息:")
    traceback.print_exc()
    
    print("\n\n可能的原因:")
    print("1. 依赖未安装 - 运行: pip install -r requirements.txt")
    print("2. 模块导入错误 - 检查backend/main.py")
    print("3. 配置问题 - 检查config/settings.yaml")