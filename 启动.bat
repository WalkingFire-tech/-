@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ========================================
echo    联盟拓荒者 v3.1.1
echo    生产级自我进化智能体系统
echo ========================================
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.11+
    pause
    exit /b 1
)

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo [√] 激活虚拟环境...
    call venv\Scripts\activate.bat
) else (
    echo [!] 使用系统Python
)

echo.
echo [1/3] 检查依赖...
python -c "import fastapi; import uvicorn" 2>nul
if errorlevel 1 (
    echo [!] 正在安装依赖...
    pip install -r requirements.txt
)

echo.
echo [2/3] 启动后端服务...
echo     API地址: http://localhost:8000
echo     API文档: http://localhost:8000/docs
echo.

start "联盟拓荒者 - 后端服务" cmd /k "python -m uvicorn api:app --reload --port 8000"

echo 等待后端启动...
timeout /t 5 /nobreak >nul

echo.
echo [3/3] 打开前端界面...
start http://localhost:8000/

echo.
echo ========================================
echo    启动完成！
echo ========================================
echo.
echo  访问地址:
echo    - 前端界面: http://localhost:8000/
echo    - API文档:  http://localhost:8000/docs
echo    - 健康检查: http://localhost:8000/api/health
echo.
echo  提示:
echo    - 后端服务在新窗口运行
echo    - 按Ctrl+C停止后端
echo    - Ollama未启动时会使用Mock适配器
echo.
echo ========================================
echo.

pause