"""
整理项目结构 - 移动文件到合适的目录
"""
import shutil
from pathlib import Path

root = Path(".")

# 创建目标目录
(root / "tests").mkdir(exist_ok=True)
(root / "docs" / "archive").mkdir(parents=True, exist_ok=True)
(root / "docs" / "reports").mkdir(parents=True, exist_ok=True)
(root / "scripts").mkdir(exist_ok=True)

# 测试文件移动到tests/
test_files = [
    "auto_test.py",
    "check_backend.py",
    "check_dbs.py",
    "check_full_service.py",
    "check_meta_rule.py",
    "check_pending_rules.py",
    "diagnose_detailed.py",
    "diagnose_memory.py",
    "diagnose_startup.py",
    "full_system_test.py",
    "quick_verify.py",
    "simple_test.py",
    "simple_verify.py",
    "staged_test.py",
    "start_and_test.py",
    "test_backend_startup.py",
    "test_complete.py",
    "test_complete_integration.py",
    "test_decision_health.py",
    "test_emotion_optimized.py",
    "test_federation.py",
    "test_federation_integration.py",
    "test_fixes.py",
    "test_frontend.py",
    "test_import.py",
    "test_lightweight.py",
    "test_meta_flow.py",
    "test_meta_recognition.py",
    "test_ollama_models.py",
    "test_online_learning.py",
    "test_p2_decomposition.py",
    "test_reflex_emotion.py",
    "test_running_backend.py",
    "verify_backend_models.py",
    "verify_capability.py",
    "verify_charter.py",
    "verify_core_features.py",
    "verify_expert_collaboration.py",
    "verify_external_model_config.py",
    "verify_final_integration.py",
    "verify_fixes.py",
    "verify_meta_ability.py",
    "verify_p0_tasks.py",
    "verify_system.py",
    "verify_v3_4_milestone.py",
    "verify_v3_4_quick.py",
    "wait_and_test.py",
]

# 工具脚本移动到scripts/
script_files = [
    "activate_all_rules.py",
    "activate_rules.py",
    "add_meta_rule.py",
    "configure_brain.py",
    "download_model.py",
    "init_knowledge.py",
    "quick_restart.py",
    "quick_start.py",
]

# 文档文件移动到docs/
doc_files = {
    "archive": [
        "ARCHIVE_v3.0.md",
        "ARCHIVE_v3.1.md",
    ],
    "reports": [
        "ARCHITECTURE_ANALYSIS.md",
        "CORE_VERIFICATION_REPORT.md",
        "FINAL_REPORT.md",
        "FIXES_COMPLETE.md",
        "FULL_TEST_GUIDE.md",
        "FULL_TEST_REPORT.md",
        "ONLINE_LEARNING_COMPARISON.md",
        "ONLINE_LEARNING_REPORT.md",
        "OPTIMAL_DECISION.md",
        "PHASE1_COMPLETE.md",
        "START_TEST.md",
    ],
    "root": [
        "PROJECT_STATUS.md",
        "QUICKSTART.md",
        "RELEASE_NOTES.md",
        "ROADMAP.md",
        "SYSTEM_READY.md",
    ]
}

moved_count = 0

# 移动测试文件
for file in test_files:
    src = root / file
    dst = root / "tests" / file
    if src.exists() and not dst.exists():
        shutil.move(str(src), str(dst))
        moved_count += 1
        print(f"✓ {file} → tests/")

# 移动脚本文件
for file in script_files:
    src = root / file
    dst = root / "scripts" / file
    if src.exists() and not dst.exists():
        shutil.move(str(src), str(dst))
        moved_count += 1
        print(f"✓ {file} → scripts/")

# 移动文档文件
for category, files in doc_files.items():
    for file in files:
        src = root / file
        if category == "root":
            dst = root / "docs" / file
        else:
            dst = root / "docs" / category / file
        
        if src.exists() and not dst.exists():
            shutil.move(str(src), str(dst))
            moved_count += 1
            print(f"✓ {file} → docs/{category}/")

print(f"\n总计移动 {moved_count} 个文件")