@echo off
chcp 65001 >nul
title 联盟拓荒者 - 命令行交互
cd /d "%~dp0"

echo ====================================================================
echo 联盟拓荒者 - 自我进化AI系统
echo ====================================================================
echo.

REM 步骤1: 检查Python
echo [1/3] 检查Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请安装Python 3.8+
    pause
    exit /b 1
)
echo  ✓ Python 就绪
echo.

REM 步骤2: 检查依赖
echo [2/3] 检查依赖...
pip show loguru >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install loguru requests duckduckgo-search
)
echo  ✓ 依赖就绪
echo.

REM 步骤3: 启动系统
echo [3/3] 启动命令行交互系统...
echo.
echo ====================================================================
echo 使用说明:
echo   - 直接输入问题与系统对话
echo   - 输入 :stats  查看系统统计
echo   - 输入 :why    查看决策链
echo   - 输入 :reflect 查看反思报告
echo   - 输入 :export  导出训练数据
echo   - 输入 :help   查看帮助
echo   - 输入 exit    退出系统
echo ====================================================================
echo.

python main_integrated.py

pause