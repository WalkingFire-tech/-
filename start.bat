@echo off
chcp 65001 >nul
title 联盟拓荒者 - 启动菜单
cd /d "%~dp0"

:menu
cls
echo ====================================================================
echo 联盟拓荒者 - 启动菜单
echo ====================================================================
echo.
echo 请选择启动模式:
echo.
echo   [1] 命令行交互模式 (推荐)
echo       - 直接与系统对话
echo       - 查看决策链、反思报告
echo       - 适合测试和体验
echo.
echo   [2] Web服务模式
echo       - 启动Web后端服务
echo       - 提供API接口
echo       - 适合集成开发
echo.
echo   [3] 运行端到端测试
echo       - 验证所有功能
echo       - 检查系统状态
echo.
echo   [4] 退出
echo.
echo ====================================================================
set /p choice="请输入选项 [1-4]: "

if "%choice%"=="1" goto cli_mode
if "%choice%"=="2" goto web_mode
if "%choice%"=="3" goto test_mode
if "%choice%"=="4" goto end

echo.
echo [错误] 无效选项，请重新选择
timeout /t 2 >nul
goto menu

:cli_mode
cls
echo ====================================================================
echo 启动命令行交互模式
echo ====================================================================
echo.
python main_integrated.py
pause
goto menu

:web_mode
cls
echo ====================================================================
echo 启动Web服务模式
echo ====================================================================
echo.
echo 启动后端服务...
echo 后端地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.

set HF_ENDPOINT=https://hf-mirror.com
set HUGGINGFACE_HUB_CACHE=%USERPROFILE%\.cache\huggingface\hub
set HF_HUB_DISABLE_TELEMETRY=1
set TRANSFORMERS_VERBOSITY=error

start "联盟拓荒者后端" cmd /k "set HF_ENDPOINT=https://hf-mirror.com && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

echo 等待后端启动...
timeout /t 5 >nul

start http://localhost:8000

echo.
echo Web服务已启动，按任意键返回菜单...
pause >nul
goto menu

:test_mode
cls
echo ====================================================================
echo 运行端到端测试
echo ====================================================================
echo.
python tests/test_e2e_full.py
echo.
echo 测试完成，按任意键返回菜单...
pause >nul
goto menu

:end
echo.
echo 感谢使用联盟拓荒者！
timeout /t 1 >nul
exit /b 0
