@echo off
echo ========================================
echo 联盟拓荒者 v3.1.1 - 快速启动
echo ========================================
echo.

echo [1/3] 检查Python版本...
python --version
if errorlevel 1 (
    echo 错误: Python未安装或未添加到PATH
    pause
    exit /b 1
)

echo.
echo [2/3] 安装核心依赖...
pip install -q rich loguru pyyaml pydantic pydantic-settings python-dotenv numpy requests schedule
if errorlevel 1 (
    echo 警告: 部分依赖安装失败，继续启动...
)

echo.
echo [3/3] 启动系统...
python main.py

pause