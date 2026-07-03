# PowerShell启动脚本
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "启动联盟拓荒者后端服务" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 检查Python
Write-Host "[检查] Python环境..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
Write-Host "  $pythonVersion" -ForegroundColor Green

# 检查端口占用
Write-Host "[检查] 端口8000..." -ForegroundColor Yellow
$portCheck = netstat -ano | findstr ":8000" | findstr "LISTENING"
if ($portCheck) {
    Write-Host "  警告: 端口8000已被占用" -ForegroundColor Red
    Write-Host "  $portCheck" -ForegroundColor Gray
    Write-Host ""
    Write-Host "是否停止占用进程？(Y/N)" -ForegroundColor Yellow
    $confirm = Read-Host
    if ($confirm -eq "Y" -or $confirm -eq "y") {
        $pid = ($portCheck -split '\s+')[-1]
        Write-Host "  停止进程 $pid..." -ForegroundColor Yellow
        taskkill /PID $pid /F
        Start-Sleep -Seconds 2
    }
} else {
    Write-Host "  端口8000可用" -ForegroundColor Green
}

Write-Host ""
Write-Host "[启动] 后端服务..." -ForegroundColor Yellow
Write-Host "  地址: http://localhost:8000" -ForegroundColor Gray
Write-Host "  API文档: http://localhost:8000/docs" -ForegroundColor Gray
Write-Host ""

# 启动服务
try {
    python -m uvicorn backend.main_fast:app --host 0.0.0.0 --port 8000
} catch {
    Write-Host "启动失败: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "按任意键退出..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}