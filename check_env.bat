@echo off
chcp 65001 >nul
echo ========================================
echo 端口和依赖检查
echo ========================================
echo.

echo [1/3] 检查端口8000是否被占用...
netstat -ano | findstr ":8000.*LISTENING"
if errorlevel 1 (
    echo   ✓ 端口8000可用
) else (
    echo   ✗ 端口8000已被占用
    echo.
    echo   结束占用进程:
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
        echo   taskkill /F /PID %%a
    )
    echo.
    pause
    exit /b 1
)

echo.
echo [2/3] 检查Python依赖...
python -c "import fastapi; print('  ✓ FastAPI:', fastapi.__version__)" 2>nul
if errorlevel 1 (
    echo   ✗ FastAPI未安装
    echo   安装: pip install fastapi
)

python -c "import uvicorn; print('  ✓ Uvicorn:', uvicorn.__version__)" 2>nul
if errorlevel 1 (
    echo   ✗ Uvicorn未安装
    echo   安装: pip install uvicorn
)

python -c "import loguru; print('  ✓ Loguru')" 2>nul
if errorlevel 1 (
    echo   ✗ Loguru未安装
    echo   安装: pip install loguru
)

echo.
echo [3/3] 检查前端文件...
if exist "frontend\index.html" (
    echo   ✓ frontend\index.html 存在
) else (
    echo   ✗ frontend\index.html 不存在
)

if exist "frontend\styles.css" (
    echo   ✓ frontend\styles.css 存在
) else (
    echo   ✗ frontend\styles.css 不存在
)

if exist "frontend\app.js" (
    echo   ✓ frontend\app.js 存在
) else (
    echo   ✗ frontend\app.js 不存在
)

echo.
echo ========================================
echo 检查完成
echo ========================================
echo.
pause