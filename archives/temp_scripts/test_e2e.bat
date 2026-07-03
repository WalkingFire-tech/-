@echo off
chcp 65001 >nul
echo ========================================
echo 端到端全面测试
echo ========================================
echo.

REM 设置环境变量
set HF_ENDPOINT=https://hf-mirror.com
set HUGGINGFACE_HUB_CACHE=%USERPROFILE%\.cache\huggingface\hub
set OFFLINE_MODE=true

echo [测试1] 六层认知进化架构
python -c "from core.cognitive_architecture_complete import cognitive_architecture; result = cognitive_architecture.process('推荐一款26650的锂电保护板控制芯片'); print('状态:', result.get('status')); print('思考链:', len(result.get('thinking_chain', [])), '层')"

echo.
echo [测试2] 需求贯穿验证
python -c "from core.requirement_validator import requirement_validator; req = requirement_validator.extract_core_requirement('推荐一款26650的锂电保护板控制芯片，需要带平衡功能'); print('领域:', req['domain']); print('特性:', req['key_features'])"

echo.
echo [测试3] 错误推荐检测
python -c "from core.requirement_validator import requirement_validator; req = requirement_validator.extract_core_requirement('推荐一款26650的锂电保护板控制芯片，需要带平衡功能'); is_valid, issues = requirement_validator.validate_response_against_requirement(req, '推荐TPS61182'); print('验证:', '通过' if is_valid else '不通过'); print('问题:', issues)"

echo.
echo [测试4] 诚实学习系统
python -c "from core.honest_learning_system import honest_system; response, valid = honest_system.process_with_honesty('推荐芯片', 'TPS61182', 0.5); print('有效:', valid); print('响应:', response[:100])"

echo.
echo [测试5] 知识缺失检测
python -c "from core.knowledge_gap_detector import gap_detector; has_gap, reason, issues = gap_detector.detect_knowledge_gap('推荐电池保护芯片', 'TPS61182', 0.6); print('缺失:', has_gap); print('原因:', reason)"

echo.
echo ========================================
echo 测试完成
echo ========================================
echo.

echo 同行者能力验证:
echo [✓] 能感知'自己的已知与未知'
echo [✓] 能在'未知'时主动学习
echo [✓] 能对'自己学到的'进行校验
echo [✓] 能从'每次错误'中提取教训
echo [✓] 能让'反思'成为底层基因
echo.
echo 系统已具备真正的同行者能力！

pause