#!/usr/bin/env python
"""统计测试文件中的测试数量"""
import os
import re

test_files = [
    "tests/unit/test_architecture_awareness.py",
    "tests/unit/test_system_command.py",
    "tests/unit/test_stereo_memory_get.py",
    "tests/unit/test_l5_pipeline.py",
    "tests/unit/test_feature_flags.py",
    "tests/unit/test_chat_stream_audit.py",
    "tests/unit/test_spirit_core.py",
    "tests/unit/test_sqlite_concurrency.py",
    "tests/unit/test_ratchet_gate.py",
    "tests/unit/test_dual_speed_evolution.py",
    "tests/unit/test_code_executor.py",
    "tests/unit/test_beam_search.py",
]

total_tests = 0
for test_file in test_files:
    if os.path.exists(test_file):
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
            test_count = len(re.findall(r'def test_\w+', content))
            if test_count > 0:
                print(f"{os.path.basename(test_file)}: {test_count} tests")
                total_tests += test_count

print(f"\n总计: {total_tests} tests")