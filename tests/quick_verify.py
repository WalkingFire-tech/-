"""轻量级验证脚本"""
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

print("=" * 60)
print("持续学习单元验证")
print("=" * 60)

# 1. 检查依赖
print("\n[1] 检查依赖...")
try:
    import duckduckgo_search
    print("  ✓ duckduckgo-search 已安装")
except ImportError:
    print("  ✗ duckduckgo-search 未安装")

# 2. 检查文件创建
print("\n[2] 检查文件创建...")
files = [
    "tools/web_search.py",
    "infrastructure/active_learner.py"
]
for f in files:
    path = ROOT_DIR / f
    if path.exists():
        print(f"  ✓ {f}")
    else:
        print(f"  ✗ {f} 不存在")

# 3. 检查导入
print("\n[3] 检查导入...")
try:
    from tools.web_search import WebSearchTool, QuickSearchTool
    print("  ✓ 网络搜索工具导入成功")
except Exception as e:
    print(f"  ✗ 网络搜索工具导入失败: {e}")

try:
    from infrastructure.active_learner import active_learner
    print("  ✓ 主动学习器导入成功")
except Exception as e:
    print(f"  ✗ 主动学习器导入失败: {e}")

# 4. 检查集成
print("\n[4] 检查集成...")
try:
    from tools.builtin import register_builtin_tools
    register_builtin_tools()
    
    from tools.registry import registry
    web = registry.get("web_search")
    quick = registry.get("quick_search")
    
    if web and quick:
        print("  ✓ 工具已注册到注册表")
    else:
        print("  ⚠ 工具未注册")
except Exception as e:
    print(f"  ✗ 工具注册失败: {e}")

try:
    from infrastructure.active_learner import active_learner
    stats = active_learner.get_statistics()
    print(f"  ✓ 学习器已初始化 (活动: {stats['total_activities']}, 知识: {stats['total_knowledge']})")
except Exception as e:
    print(f"  ✗ 学习器初始化失败: {e}")

# 5. 检查API
print("\n[5] 检查API端点...")
try:
    import backend.main as backend
    routes = [r.path for r in backend.app.routes]
    
    learning_routes = [r for r in routes if "/learning" in r]
    if learning_routes:
        print(f"  ✓ 学习API已添加 ({len(learning_routes)} 个端点)")
        for r in learning_routes[:5]:
            print(f"    - {r}")
    else:
        print("  ⚠ 未找到学习API")
except Exception as e:
    print(f"  ✗ API检查失败: {e}")

# 6. 检查CLI命令
print("\n[6] 检查CLI命令...")
try:
    with open(ROOT_DIR / "adapters/ui/cli_ui.py", "r", encoding="utf-8") as f:
        content = f.read()
    
    if ":learning log" in content:
        print("  ✓ :learning log 命令已添加")
    if ":learning knowledge" in content:
        print("  ✓ :learning knowledge 命令已添加")
    if ":learning pause" in content:
        print("  ✓ :learning pause 命令已添加")
    if ":learning resume" in content:
        print("  ✓ :learning resume 命令已添加")
except Exception as e:
    print(f"  ✗ CLI检查失败: {e}")

print("\n" + "=" * 60)
print("验证完成！")
print("=" * 60)
print("\n新增功能:")
print("  1. 网络搜索工具 (web_search, quick_search)")
print("  2. 主动学习器 (active_learner)")
print("  3. 学习API端点 (/api/learning/*)")
print("  4. CLI命令 (:learning log/knowledge/pause/resume)")
print("\n下一步:")
print("  - 启动后端: python backend/main.py")
print("  - 访问API文档: http://localhost:8000/docs")
print("  - 测试CLI: python main.py (然后输入 :learning log)")