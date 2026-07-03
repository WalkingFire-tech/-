import os

print("=" * 70)
print("目录结构完整性检查")
print("=" * 70)
print()

dirs = {
    "tools": ["base.py", "registry.py", "arbiter.py", "math_calculator.py", "web_search.py", "file_operations.py", "__init__.py"],
    "infrastructure": ["reflection_pipeline.py", "experience_pool.py", "config_manager.py", "quick_reflex.py", "__init__.py"],
    "core": ["orchestrator.py", "cognitive_dispatcher.py", "metacognitive_executor.py", "sleep_consolidator.py", "canary_evaluator.py", "__init__.py"],
    "meta": ["induction.py", "__init__.py"],
    "adapters": ["__init__.py"],
    "backend": ["main.py", "main_fast.py", "__init__.py"],
    "frontend": ["index.html", "styles.css", "app.js"],
}

all_ok = True
for dir_name, files in dirs.items():
    print(f"{dir_name}/")
    for f in files:
        path = os.path.join(dir_name, f)
        exists = os.path.exists(path)
        status = "✓" if exists else "✗"
        print(f"  {status} {f}")
        if not exists:
            all_ok = False
    print()

print("=" * 70)
if all_ok:
    print("✅ 所有文件就绪")
else:
    print("❌ 存在缺失文件")
print("=" * 70)