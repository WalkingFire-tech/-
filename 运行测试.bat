@echo off
chcp 65001 >nul
title 联盟拓荒者 - 自动化测试
cd /d "%~dp0"

echo ====================================================================
echo 联盟拓荒者 - 自动化测试
echo ====================================================================
echo.

REM 步骤1: 检查环境
echo [步骤1] 检查环境...
python --version
if errorlevel 1 (
    echo [错误] Python未安装
    pause
    exit /b 1
)
echo.

REM 步骤2: 启动后端
echo [步骤2] 启动后端服务...
echo 启动命令: python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
echo.

start "后端服务" cmd /k "cd /d "%~dp0" && python -m uvicorn backend.main_fast:app --host 0.0.0.0 --port 8000"

echo 等待后端启动（10秒）...
timeout /t 10 /nobreak >nul
echo.

REM 步骤3: 测试API
echo [步骤3] 测试API端点...
echo.

echo 测试1: 健康检查 (GET /api/health)
python -c "import urllib.request, json; r = urllib.request.urlopen('http://localhost:8000/api/health', timeout=5); print('  结果:', json.loads(r.read()))" 2>nul
if errorlevel 1 (
    echo   [失败] 无法连接到后端
    echo   请检查后端窗口是否有错误
) else (
    echo   [成功]
)
echo.

echo 测试2: 统计信息 (GET /api/stats)
python -c "import urllib.request, json; r = urllib.request.urlopen('http://localhost:8000/api/stats', timeout=5); d = json.loads(r.read()); print(f'  经验池: {d[\"experiences\"]}条'); print(f'  活跃规则: {d[\"active_rules\"]}条'); print(f'  模型: {d[\"models\"]}个')" 2>nul
if errorlevel 1 (
    echo   [失败]
) else (
    echo   [成功]
)
echo.

echo 测试3: 模型列表 (GET /api/models)
python -c "import urllib.request, json; r = urllib.request.urlopen('http://localhost:8000/api/models', timeout=5); d = json.loads(r.read()); print(f'  模型数: {len(d[\"models\"])}个'); [print(f'    - {m[\"name\"]}') for m in d[\"models\"]]" 2>nul
if errorlevel 1 (
    echo   [失败]
) else (
    echo   [成功]
)
echo.

echo 测试4: 前端页面 (GET /)
python -c "import urllib.request; r = urllib.request.urlopen('http://localhost:8000/', timeout=5); print(f'  状态码: {r.status}'); print(f'  内容长度: {len(r.read())} bytes')" 2>nul
if errorlevel 1 (
    echo   [失败]
) else (
    echo   [成功]
)
echo.

REM 步骤4: 打开浏览器
echo [步骤4] 打开前端界面...
start http://localhost:8000/
echo.

echo ====================================================================
echo 测试完成
echo ====================================================================
echo.
echo 访问地址:
echo   - 前端界面: http://localhost:8000/
echo   - API文档:  http://localhost:8000/docs
echo   - 健康检查: http://localhost:8000/api/health
echo.
echo 后端服务在新窗口运行中
echo 关闭后端窗口可停止服务
echo.
echo ====================================================================

pause