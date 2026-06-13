@echo off
chcp 65001 >nul
title 外脑配置助手
cd /d "%~dp0"

echo ============================================================
echo 外脑配置助手
echo ============================================================
echo.
echo 支持的远程模型：
echo.
echo   1. OpenAI (GPT-4o-mini)
echo      - 通用对话、复杂推理
echo      - 费用: $0.15/百万tokens
echo.
echo   2. DeepSeek (推荐)
echo      - 代码生成、对话
echo      - 费用: ¥1/百万tokens (更便宜)
echo.
echo ============================================================
echo.

set /p choice="请选择: 1=OpenAI, 2=DeepSeek, 3=两者, 4=跳过: "

if "%choice%"=="4" goto :skip
if "%choice%"=="1" goto :openai
if "%choice%"=="2" goto :deepseek
if "%choice%"=="3" goto :both
goto :end

:openai
echo.
set /p openai_key="请输入 OpenAI API 密钥: "
if not "%openai_key%"=="" (
    echo # 外脑配置 > .env
    echo OPENAI_API_KEY=%openai_key% >> .env
    echo.
    echo ✅ OpenAI API 密钥已配置
    goto :restart
) else (
    echo ❌ 密钥不能为空
    goto :end
)

:deepseek
echo.
set /p deepseek_key="请输入 DeepSeek API 密钥: "
if not "%deepseek_key%"=="" (
    echo # 外脑配置 > .env
    echo DEEPSEEK_API_KEY=%deepseek_key% >> .env
    echo.
    echo ✅ DeepSeek API 密钥已配置
    goto :restart
) else (
    echo ❌ 密钥不能为空
    goto :end
)

:both
echo.
set /p openai_key="请输入 OpenAI API 密钥 (没有可跳过): "
set /p deepseek_key="请输入 DeepSeek API 密钥 (没有可跳过): "

echo # 外脑配置 > .env
if not "%openai_key%"=="" (
    echo OPENAI_API_KEY=%openai_key% >> .env
    echo ✅ OpenAI API 密钥已配置
)
if not "%deepseek_key%"=="" (
    echo DEEPSEEK_API_KEY=%deepseek_key% >> .env
    echo ✅ DeepSeek API 密钥已配置
)
goto :restart

:skip
echo.
echo 跳过配置，使用本地模型
goto :end

:restart
echo.
echo ============================================================
echo 配置完成
echo ============================================================
echo.
echo 下一步:
echo   1. 重启服务: 运行 重启服务.bat
echo   2. 查看日志确认外脑已加载
echo.
set /p restart_now="是否立即重启服务? (y/n): "
if /i "%restart_now%"=="y" (
    echo.
    echo 正在重启服务...
    taskkill /F /FI "WINDOWTITLE eq 联盟拓荒者后端*" >nul 2>&1
    timeout /t 2 /nobreak >nul
    start "联盟拓荒者后端" python backend\main.py
    timeout /t 5 /nobreak >nul
    start http://localhost:8000
    echo.
    echo ✅ 服务已重启
)

:end
echo.
pause