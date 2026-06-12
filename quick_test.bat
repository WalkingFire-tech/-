@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo 启动后端服务并测试
echo ========================================
echo.

echo [步骤1] 启动后端...
start "后端服务" /min cmd /c "python -m uvicorn api:app --host 0.0.0.0 --port 8000"

echo 等待启动...
timeout /t 8 /nobreak >nul

echo.
echo [步骤2] 测试API...

echo 测试健康检查...
python -c "import requests; print(requests.get('http://localhost:8000/api/health').json())" 2>nul
if errorlevel 1 echo [失败] 无法连接

echo.
echo 测试统计信息...
python -c "import requests; print(requests.get('http://localhost:8000/api/stats').json())" 2>nul

echo.
echo 测试模型列表...
python -c "import requests; print(requests.get('http://localhost:8000/api/models').json())" 2>nul

echo.
echo ========================================
echo 测试完成
echo ========================================
echo.
echo 访问地址:
echo   前端: http://localhost:8000/
echo   文档: http://localhost:8000/docs
echo.
echo 后端服务在后台运行中
echo.

pause