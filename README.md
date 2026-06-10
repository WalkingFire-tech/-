# 🔥 联盟拓荒者 (Alliance Pioneer)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GitHub Actions](https://github.com/WalkingFire-tech/Alliance-Pioneer/workflows/CI/badge.svg)](https://github.com/WalkingFire-tech/Alliance-Pioneer/actions)

**生产级自我进化智能体系统 | Production-Grade Self-Evolving Agent System**

> 完美理解、合理判断、从实践进化、最终同步
> 
> Perfect understanding, rational judgment, evolution from practice, final synchronization

---

## � 目录 (Table of Contents)

- [项目简介](#-项目简介)
- [核心特性](#-核心特性)
- [系统架构](#-系统架构)
- [快速开始](#-快速开始)
- [使用示例](#-使用示例)
- [性能指标](#-性能指标)
- [文档](#-文档)
- [贡献指南](#-贡献指南)
- [许可证](#-许可证)

---

## 🎯 项目简介 (Introduction)

**联盟拓荒者**是一个具备元认知能力的自我进化智能体系统，能够：

- 🧠 **自动理解**用户意图并选择最优模型
- 📈 **持续学习**从经验中归纳规则并优化策略
- 🔄 **自我进化**通过贝叶斯优化调整超参数
- 💾 **经验复用**通过向量检索重用成功案例

这是一个永远不会完成的项目。我们在这里一起搭建一个会思考的同伴。你可以随意取走任何代码，随意改变方向。**唯一的要求：保持善意，保持开放。**

---

## ✨ 核心特性 (Core Features)

### 🤖 自我进化能力

| 特性 | 技术实现 | 说明 |
|------|----------|------|
| 贝叶斯优化 | scikit-optimize | 高斯过程+EI采集函数，自动调优超参数 |
| 归纳学习 | Pattern Mining | 从经验池挖掘模式，生成学习规则 |
| 规则闭环 | Rule Engine | 归纳→激活→应用→反馈完整闭环 |
| 冲突检测 | Conflict Detector | 自动检测并解决规则冲突 |

### 🏗️ 生产级特性

| 特性 | 说明 |
|------|------|
| 优雅退出 | signal+atexit+try-finally三重保护 |
| 事件驱动 | CLI与业务逻辑完全解耦 |
| 连接池 | 数据库连接池优化性能 |
| 热加载 | 配置文件实时监控与重载 |
| 线程安全 | MetaController可多次安全调用 |

### 🧮 计算能力

- ✅ 通用数学表达式计算（安全eval白名单）
- ✅ π值高精度计算（mpmath支持任意精度）
- ✅ 向量相似度检索（FAISS高效匹配）

### 📂 文件处理

- ✅ 文件输入支持（自动识别文件类型）
- ✅ 文件夹批量处理（递归遍历）
- ✅ 内容自动提取（支持多种格式）

---

## 🏛️ 系统架构 (Architecture)

```
┌─────────────────────────────────────────────────────────────┐
│                    元控制层 (Meta Control)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 贝叶斯优化器 │  │  归纳总结器  │  │  冲突检测器  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    核心推理层 (Core Services)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  意图识别器  │  │   规划器     │  │  问题拆解器  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    路由评估层 (Routing)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  统计库决策  │  │  规则匹配器  │  │  向量检索器  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    执行层 (Execution)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  LLM适配器   │  │  工具执行器  │  │  计算处理器  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  反馈记忆层 (Feedback & Memory)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   经验池     │  │   统计库     │  │  学习规则库  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始 (Quick Start)

### 前置要求 (Prerequisites)

- Python 3.11+
- [Ollama](https://ollama.ai/) (本地LLM服务)
- Git

### 一键启动 (One-Click Start)

**Windows**:
```bash
# 双击运行
start.bat
```

**Linux/Mac**:
```bash
# 安装依赖
pip install -r requirements.txt

# 启动系统
python main.py
```

### 手动安装 (Manual Installation)

```bash
# 1. 克隆仓库
git clone https://github.com/WalkingFire-tech/Alliance-Pioneer.git
cd Alliance-Pioneer

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 .\venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 安装Ollama模型
ollama pull mindchat
ollama pull qwen2.5-coder:1.5b

# 5. 启动系统
python main.py
```

### 使用pyproject.toml安装

```bash
# 基础安装
pip install -e .

# 完整安装（包含所有可选依赖）
pip install -e ".[all]"

# 开发安装
pip install -e ".[dev]"
```

---

## 🎯 使用示例 (Usage Examples)

### 基础对话

```
你: 你好，请帮我写一个Python函数
拓荒者: [使用qwen2.5-coder:1.5b生成代码]
```

### 数学计算

```
你: 计算 2+3*4
拓荒者: 计算结果: 14

你: 输出π的前100位
拓荒者: 3.14159265358979323846...
```

### 元控制命令

```
你: :optimize run 20
拓荒者: [运行贝叶斯优化，20次迭代]

你: :induction run 7
拓荒者: [归纳最近7天经验，生成规则]
```

### 文件输入

```
你: :file README.md
拓荒者: [自动读取并分析文件内容]

你: :folder ./docs
拓荒者: [批量处理文件夹]
```

---

## 📊 性能指标 (Performance Metrics)

| 指标 | 数值 | 说明 |
|------|------|------|
| 代码生成质量 | 45-85/100 | 基于长度、语法、逻辑评估 |
| 响应时间 | 8-16秒 | 包含模型推理和质量评估 |
| 模型路由准确率 | 100% | 学习规则强制匹配 |
| 经验复用阈值 | 相似度>0.85 | FAISS向量检索 |
| 规则匹配支持 | 复杂表达式 | simpleeval安全求值 |

---

## 📚 文档 (Documentation)

### 核心文档

| 文档 | 说明 |
|------|------|
| [ARCHIVE_v3.1.md](ARCHIVE_v3.1.md) | v3.1完整归档（生产级） |
| [ARCHIVE_v3.0.md](ARCHIVE_v3.0.md) | v3.0归档（基础版） |
| [CHANGELOG.md](CHANGELOG.md) | 版本更新记录 |
| [QUICKSTART.md](QUICKSTART.md) | 快速启动指南 |
| [SYSTEM_READY.md](SYSTEM_READY.md) | 系统就绪文档 |

### 架构文档

查看 `docs/` 目录获取详细架构设计文档（20+文档）。

### 📖 设计哲学

阅读 [联盟拓荒者与 Claude 5 的殊途同归](docs/PHILOSOPHY_AND_VISION.md)，了解项目背后的思考。

> 我们不是在建造工具，而是在孕育同行者。

---

## 🤝 贡献指南 (Contributing)

我们欢迎所有形式的贡献！

### 如何贡献

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

### 详细指南

查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解：
- 开发环境设置
- 代码规范
- 测试要求
- PR流程

### 行为准则

请保持善意和开放的态度，尊重所有贡献者。

---

## 📜 许可证 (License)

本项目采用 [MIT License](LICENSE) 开源协议。

你可以自由地：
- ✅ 商业使用
- ✅ 修改
- ✅ 分发
- ✅ 私人使用

---

## 📞 联系方式 (Contact)

- **Issues**: [GitHub Issues](https://github.com/WalkingFire-tech/Alliance-Pioneer/issues)
- **Email**: kun_phone@139.com
- **Repository**: [GitHub](https://github.com/WalkingFire-tech/Alliance-Pioneer)

---

## 🙏 致谢 (Acknowledgments)

感谢所有贡献者和开源社区的支持！

特别感谢：
- [Ollama](https://ollama.ai/) - 本地LLM运行时
- [scikit-optimize](https://scikit-optimize.github.io/) - 贝叶斯优化
- [FAISS](https://github.com/facebookresearch/faiss) - 向量检索
- [Rich](https://github.com/Textualize/rich) - 终端美化

---

## ⭐ Star History

如果这个项目对你有帮助，请给一个⭐支持！

[![Star History Chart](https://api.star-history.com/svg?repos=WalkingFire-tech/Alliance-Pioneer&type=Date)](https://star-history.com/#WalkingFire-tech/Alliance-Pioneer&Date)

---

**Made with ❤️ by WalkingFire-tech**

**版本**: v3.1.1 | **状态**: 生产就绪 (Production Ready) | **完成度**: 100%
