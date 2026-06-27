@echo off
chcp 65001 >nul
title 联盟拓荒者 - 一键启动
cd /d "%~dp0"

echo ====================================================================
echo 联盟拓荒者 - 一键启动
echo ====================================================================
echo.

REM 步骤1: 检查Python
echo [1/4] 检查Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请安装Python 3.8+
    pause
    exit /b 1
)
echo  ✓ Python 就绪
echo.

REM 步骤2: 检查依赖
echo [2/4] 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt
)
echo  ✓ 依赖就绪
echo.

REM 步骤3: 启动后端服务
echo [3/4] 启动后端服务...
echo 后端地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.

REM 设置环境变量
set HF_ENDPOINT=https://hf-mirror.com
set HUGGINGFACE_HUB_CACHE=%USERPROFILE%\.cache\huggingface\hub
set HF_HUB_DISABLE_TELEMETRY=1
set TRANSFORMERS_VERBOSITY=error

REM 启动后端（在新窗口）
start "联盟拓荒者后端" cmd /k "cd /d "%~dp0" && set HF_ENDPOINT=https://hf-mirror.com && set HUGGINGFACE_HUB_CACHE=%USERPROFILE%\.cache\huggingface\hub && set HF_HUB_DISABLE_TELEMETRY=1 && set TRANSFORMERS_VERBOSITY=error && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

echo 等待后端启动...
echo 正在初始化模型和系统组件...

REM 等待后端启动（最多30秒）
set /a count=0
:wait_loop
set /a count+=1
if %count% gtr 30 (
    echo.
    echo [警告] 后端启动超时，但服务可能仍在初始化中
    echo 请稍后手动访问 http://localhost:8000
    goto open_browser
)

REM 检查健康端点
curl -s http://localhost:8000/api/health >nul 2>&1
if errorlevel 1 (
    REM 等待1秒后重试
    ping 127.0.0.1 -n 2 >nul
    goto wait_loop
)

echo.
echo  ✓ 后端已就绪 (耗时: %count%秒)

:open_browser
echo.
echo [4/4] 打开前端界面...
start http://localhost:8000
echo.

echo ====================================================================
echo 启动完成！
echo ====================================================================
echo.
echo 访问地址:
echo   前端界面: http://localhost:8000
echo   API文档:  http://localhost:8000/docs
echo   健康检查: http://localhost:8000/api/health
echo.
echo 后端运行在独立的命令行窗口中，关闭该窗口即可停止服务。
echo ====================================================================
echo.
echo 按任意键退出此窗口（后端将继续运行）...
pause >nul