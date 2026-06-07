# 贡献指南

感谢您对联盟拓荒者（Alliance Pioneer）项目的关注！本文档将帮助您参与项目开发。

## 📋 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发环境设置](#开发环境设置)
- [代码规范](#代码规范)
- [提交信息规范](#提交信息规范)
- [测试要求](#测试要求)
- [Pull Request流程](#pull-request流程)

---

## 行为准则

本项目采用贡献者公约作为行为准则。参与本项目即表示您同意遵守其条款。请阅读 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) 了解详情。

---

## 如何贡献

### 报告Bug

如果您发现了bug，请创建Issue并包含：

1. **清晰的标题**：简明扼要地描述问题
2. **详细描述**：
   - 复现步骤
   - 期望行为
   - 实际行为
   - 错误日志（如有）
3. **环境信息**：
   - Python版本
   - 操作系统
   - 依赖版本（`pip freeze`输出）

### 提出新功能

如果您有新功能建议，请创建Issue并包含：

1. **功能描述**：清晰说明新功能的作用
2. **使用场景**：说明该功能解决的问题
3. **实现思路**：如有建议的实现方案

### 提交代码

1. Fork本仓库
2. 创建功能分支（`git checkout -b feature/amazing-feature`）
3. 提交更改（`git commit -m 'feat: add amazing feature'`）
4. 推送到分支（`git push origin feature/amazing-feature`）
5. 创建Pull Request

---

## 开发环境设置

### 1. 克隆仓库

```bash
git clone https://github.com/WalkingFire-tech/Alliance-Pioneer.git
cd Alliance-Pioneer
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
.\venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖
```

### 4. 安装Ollama

确保本地已安装并运行Ollama服务：

```bash
ollama pull mindchat
ollama pull qwen2.5-coder:1.5b
```

### 5. 运行测试

```bash
pytest tests/
```

---

## 代码规范

### Python代码风格

- 遵循PEP 8规范
- 使用4空格缩进
- 行长度不超过120字符
- 使用类型注解（Type Hints）

### 命名规范

- **模块名**：小写+下划线（`model_stats.py`）
- **类名**：驼峰命名（`ModelStats`）
- **函数名**：小写+下划线（`get_best_model`）
- **常量**：全大写+下划线（`MAX_RETRIES`）

### 文档字符串

使用Google风格的docstring：

```python
def calculate_quality(response: str, task_type: str) -> int:
    """计算响应质量分数
    
    Args:
        response: 模型响应文本
        task_type: 任务类型（code/chat/question等）
    
    Returns:
        质量分数（0-100）
    
    Raises:
        ValueError: 如果task_type无效
    """
    pass
```

### 导入顺序

1. 标准库
2. 第三方库
3. 本地模块

```python
import os
import sys
from typing import Dict, List

import numpy as np
from loguru import logger

from infrastructure.config_manager import config
from core.services.intent_parser import Intent
```

---

## 提交信息规范

遵循[约定式提交](https://www.conventionalcommits.org/)规范：

```
<类型>(<范围>): <描述>

[可选的正文]

[可选的脚注]
```

### 类型

- `feat`: 新功能
- `fix`: Bug修复
- `docs`: 文档更新
- `style`: 代码格式调整（不影响功能）
- `refactor`: 重构（既不是新功能也不是bug修复）
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建过程或辅助工具变动

### 示例

```
feat(planner): 添加向量类比检索功能

- 在plan方法开头添加向量检索逻辑
- 复用相似成功案例（相似度>0.85）
- 减少重复计算，提升响应速度

Closes #123
```

---

## 测试要求

### 单元测试

- 所有新功能必须包含单元测试
- 测试覆盖率不低于80%
- 使用pytest框架

### 测试文件命名

- 测试文件以`test_`开头
- 测试类以`Test`开头
- 测试函数以`test_`开头

### 示例

```python
# tests/test_planner.py

import pytest
from core.services.planner import Planner

class TestPlanner:
    def test_select_model_for_code_intent(self):
        """测试code意图选择code_light模型"""
        planner = Planner()
        intent = Intent(type="code", raw_text="写一个函数")
        model = planner._select_model(intent)
        assert model.model_name == "qwen2.5-coder:1.5b"
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_planner.py

# 生成覆盖率报告
pytest --cov=core --cov-report=html
```

---

## Pull Request流程

### 1. 准备工作

- 确保代码通过所有测试
- 确保代码符合规范（使用`flake8`检查）
- 更新相关文档
- 更新`CHANGELOG.md`

### 2. 创建PR

PR标题遵循提交信息规范，例如：

```
feat(meta): 添加贝叶斯优化器
```

PR描述应包含：

1. **变更说明**：简要描述本次变更
2. **相关Issue**：链接相关Issue（如`Closes #123`）
3. **测试情况**：说明如何测试
4. **影响范围**：说明变更可能影响的模块

### 3. 代码审查

- 至少需要1位维护者审核通过
- 解决所有审查意见
- 确保CI检查通过

### 4. 合并

- 使用Squash and Merge保持提交历史清晰
- 合并后删除功能分支

---

## 项目结构

```
Alliance-Pioneer/
├── adapters/          # 适配器层（LLM、UI、输入）
├── core/              # 核心层（服务、端口）
├── infrastructure/    # 基硎设施层（数据库、配置）
├── meta/              # 元控制层（优化、归纳）
├── tools/             # 工具生态系统
├── tests/             # 单元测试
├── docs/              # 文档
├── config/            # 配置文件
└── main.py            # 入口文件
```

---

## 联系方式

- **Issue**: 在GitHub上创建Issue
- **Email**: kun_phone@139.com
- **文档**: 查看`docs/`目录

---

再次感谢您的贡献！🎉