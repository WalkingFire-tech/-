@echo off
echo ========================================
echo 联盟拓荒者 - 后端服务启动
echo ========================================
echo.

REM 检查虚拟环境
if exist "..\venv\Scripts\activate.bat" (
    echo 激活虚拟环境...
    call ..\venv\Scripts\activate.bat
) else (
    echo 警告: 虚拟环境不存在，使用系统Python
)

echo.
echo 启动FastAPI服务...
echo 后端地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.

cd ..\backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause