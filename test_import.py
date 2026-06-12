"""完整错误诊断"""
import sys
import traceback
from pathlib import Path

print("测试API导入...")
print(f"当前目录: {Path.cwd()}")
print(f"Python版本: {sys.version}")
print()

try:
    # 设置路径
    ROOT_DIR = Path(__file__).parent
    sys.path.insert(0, str(ROOT_DIR))
    
    print("步骤1: 导入api模块...")
    import api
    print("  ✓ api模块导入成功")
    
    print("\n步骤2: 获取app对象...")
    app = api.app
    print(f"  ✓ app对象: {app}")
    print(f"  ✓ 标题: {app.title}")
    
except Exception as e:
    print(f"\n✗ 错误: {e}")
    print("\n完整错误信息:")
    traceback.print_exc()
    
    print("\n\n可能的原因:")
    print("1. 依赖未安装 - 运行: pip install -r requirements.txt")
    print("2. 模块导入错误 - 检查backend/main.py")
    print("3. 配置问题 - 检查config/settings.yaml")