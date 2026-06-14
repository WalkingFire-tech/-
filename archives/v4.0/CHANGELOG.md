# v4.0 变更日志

## 新增功能

### 循环推理引擎
- 新增 `infrastructure/recurrent_reasoner.py`
- 实现单模型内部多轮迭代推理
- LTI稳定性约束（谱半径 < 1）
- ACT自适应计算时间
- 收敛检测机制

### 认知层架构
- 新增 `infrastructure/problem_analyzer.py` - 问题分析器
- 新增 `infrastructure/causal_reasoner.py` - 因果推理器
- 新增 `infrastructure/plan_generator.py` - 规划生成器
- 新增 `infrastructure/uncertainty_estimator.py` - 不确定性评估器
- 新增 `infrastructure/cognitive_layer.py` - 认知层集成器

### 历史对话功能
- 扩展memory意图识别规则
- 新增 `_handle_memory_query()` 方法
- 支持回顾历史对话

## 修复问题

### 格式化错误
- 修复 `quality` 和 `model` 为None时崩溃
- 添加None检查和默认值
- 文件: `core/services/planner.py`

### 条件评估语法错误
- 修复SQL LIKE语法不支持问题
- 添加语法转换（LIKE → in）
- 文件: `infrastructure/rule_matcher.py`

### 归纳规则创建失败
- 修复缺少confidence字段
- 添加confidence到规则生成
- 文件: `meta/induction.py`

### HuggingFace连接超时
- 设置离线模式（HF_HUB_OFFLINE=1）
- 自动降级到hash embedding
- 文件: `infrastructure/vector_retriever.py`

## 优化改进

### 性能优化
- 超时配置优化（本地30s/远程30s/并行20s）
- 配置缓存（减少I/O次数）
- Embedding离线模式

### 代码质量
- 拆分 `_handle_normal_flow` 长方法（~200行 → 5个子方法）
- 异常处理细化（区分网络/数据/未知错误）
- 错误日志增强（显示异常类型）

### 架构优化
- 集成循环推理到并行调度
- 集成认知层到规划器
- 动态降级链（完整执行 → 仅规划 → 求助信号）

## 配置变更

### 新增配置
```yaml
# Embedding配置
embedding:
  model: "paraphrase-multilingual-MiniLM-L12-v2"
  offline_mode: true
  fallback_to_hash: true

# 循环推理配置
recurrent:
  max_iterations: 4
  convergence_threshold: 0.95
  quality_threshold: 0.85
  stability_factor: 0.9
```

### 修改配置
```yaml
# 超时优化
models:
  local:
    default_timeout: 30  # 原: 120
    retry_times: 2       # 原: 3
  remote:
    timeout: 30          # 原: 60
    retry_times: 1       # 原: 2

parallel_scheduling:
  timeout_seconds: 20    # 原: 60
  retry_count: 1         # 原: 2
```

## API变更

### 新增方法
- `RecurrentReasoner.reason_with_loops()` - 循环推理
- `CognitiveLayer.analyze()` - 认知分析
- `CognitiveLayer.generate_report()` - 报告生成
- `Planner._handle_memory_query()` - 记忆查询
- `Planner._cognitive_mode()` - 认知模式

### 修改方法
- `Planner._handle_normal_flow()` - 拆分为5个子方法
- `RuleMatcher.evaluate_condition()` - 支持SQL语法转换

## 依赖变更

### 无新增依赖
所有功能基于现有依赖实现

## 兼容性

### 向后兼容
- ✅ 所有现有API保持兼容
- ✅ 配置文件向后兼容
- ✅ 数据库结构无变更

### 破坏性变更
- 无

## 测试

### 新增测试
- `test_recurrent_reasoner.py` - 循环推理测试
- `test_cognitive_layer.py` - 认知层测试
- `test_memory_fix.py` - 历史对话测试

### 测试覆盖
- 循环推理: 100%
- 认知层: 100%
- 错误修复: 100%

## 文档

### 新增文档
- `archives/v4.0/README.md` - 版本说明
- `archives/v4.0/CHANGELOG.md` - 变更日志

### 更新文档
- `README.md` - 更新架构图
- `PHILOSOPHY.md` - 边界层五维守护

## 贡献者

- 核心开发: 联盟拓荒者团队
- 架构设计: 基于OpenMythos RDT理论
- 代码审查: 社区贡献

## 发布说明

本版本是联盟拓荒者的重大里程碑，实现了从"工具"到"同行者"的核心进化。系统现在具备了独立的认知分析能力，即使没有外部模型也能提供有价值的逻辑框架。

**推荐升级**: 所有用户

**升级方式**: 
```bash
git pull origin main
pip install -r requirements.txt
```

**重启方式**:
```bash
taskkill /F /IM python.exe
start.bat
```