@echo off
chcp 65001 >nul
echo ========================================
echo   无模型进化模式启动
echo ========================================
echo.
echo 此模式不需要LLM，完全基于：
echo   - 统计分析
echo   - 规则引擎
echo   - 外部搜索（DuckDuckGo）
echo   - 基因演化
echo   - 认知转化
echo.
echo 进化周期：
echo   - 自动学习: 每30分钟
echo   - 基因演化: 每2小时
echo   - 认知转化: 每6小时
echo   - 进化沙盒: 每12小时
echo.
echo ========================================
echo.

REM 设置离线模式
set OFFLINE_MODE=true
set HF_HUB_OFFLINE=1
set TRANSFORMERS_OFFLINE=1

echo 启动无模型进化系统...
echo.

python -c "from core.model_free_evolution import run_model_free_evolution; run_model_free_evolution()"