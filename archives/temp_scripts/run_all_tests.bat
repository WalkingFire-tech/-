@echo off
chcp 65001 >nul
echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║       联盟拓荒者一键测试脚本                           ║
echo ╚════════════════════════════════════════════════════════╝
echo.

echo [阶段1] 测试精神内核...
python test_stage1_spirit.py
if errorlevel 1 (
    echo ❌ 阶段1测试失败
    pause
    exit /b 1
)

echo.
echo [阶段2] 测试永不放弃引擎...
python test_stage2_simple.py
if errorlevel 1 (
    echo ❌ 阶段2测试失败
    pause
    exit /b 1
)

echo.
echo [阶段3] 测试聊天处理器...
python test_stage3_simple.py
if errorlevel 1 (
    echo ❌ 阶段3测试失败
    pause
    exit /b 1
)

echo.
echo [阶段4] 测试文件结构...
python test_stage4_structure.py
if errorlevel 1 (
    echo ❌ 阶段4测试失败
    pause
    exit /b 1
)

echo.
echo [生成] 最终测试报告...
python test_final_report.py

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║       ✅ 所有测试完成                                 ║
echo ╚════════════════════════════════════════════════════════╝
echo.
echo 📄 详细报告: test_report.txt
echo 📊 测试总结: 端到端测试报告.md
echo.

pause