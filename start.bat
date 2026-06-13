@echo off
chcp 65001 >nul
title 联盟拓荒者 - 启动器
cd /d "%~dp0"

echo ====================================================================
echo 联盟拓荒者 - 启动器
echo ====================================================================
echo.

REM 步骤1: 检查Python
echo [1/5] 检查Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请安装Python 3.8+
    pause
    exit /b 1
)
echo  ✓ Python 就绪
echo.

REM 步骤2: 检查并安装依赖
echo [2/5] 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt
)
echo  ✓ 依赖就绪
echo.

REM 步骤3: 启动后端服务
echo [3/5] 启动后端服务...
echo 后端地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.

start "联盟拓荒者后端" cmd /k "python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

echo 等待后端启动（5秒）...
timeout /t 5 /nobreak >nul

REM 步骤4: 健康检查
echo [4/5] 健康检查...
python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3).read()" >nul 2>&1
if errorlevel 1 (
    echo [警告] 后端可能未完全启动，请稍后手动访问 http://localhost:8000
) else (
    echo  ✓ 后端已就绪
)
echo.

REM 步骤5: 打开浏览器
echo [5/5] 打开前端...
start http://localhost:8000
echo.

echo ====================================================================
echo 启动完成！
echo ====================================================================
echo.
echo 访问地址:
echo   前端: http://localhost:8000
echo   接口文档: http://localhost:8000/docs
echo.
echo 后端运行在独立的命令行窗口中，关闭该窗口即可停止服务。
echo ====================================================================
pause
