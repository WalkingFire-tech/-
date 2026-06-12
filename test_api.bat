@echo off
chcp 65001 >nul
echo 测试API应用加载...
python -c "from api import app; print('✓ API应用:', app.title)"
pause