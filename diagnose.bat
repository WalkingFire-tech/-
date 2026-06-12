@echo off
chcp 65001 >nul
echo ========================================
echo 后端服务诊断
echo ========================================
echo.

echo [1] 检查Python进程...
tasklist | findstr python.exe
echo.

echo [2] 检查8000端口...
netstat -ano | findstr :8000
echo.

echo [3] 测试API加载...
python -c "from api import app; print('API加载成功:', app.title)"
if errorlevel 1 (
    echo [错误] API加载失败
    pause
    exit /b 1
)
echo.

echo [4] 启动后端服务...
echo 地址: http://localhost:8000
echo 文档: http://localhost:8000/docs
echo.
python -m uvicorn api:app --host 0.0.0.0 --port 8000

pause