# 联盟拓荒者 - 目录结构说明

## 📁 核心目录结构

```
alliance_pioneer/
│
├── 📄 核心文档（主目录）
│   ├── README.md                 # 项目总览和快速开始
│   ├── CHANGELOG.md              # 变更日志
│   ├── CONTRIBUTING.md           # 贡献指南
│   ├── PHILOSOPHY.md             # 哲学理念（边界层五维守护）
│   ├── RESPONSE_BOUNDARIES.md    # 回应边界速查表
│   ├── 快速启动.md                # 中文快速启动指南
│   └── 外脑配置指南.md            # 外脑配置说明
│
├── 📂 archives/                  # 版本归档
│   ├── README.md                 # 归档总览
│   ├── v1.0/                     # 基础框架版
│   ├── v2.0/                     # 智能体框架版
│   ├── v3.0/                     # 自我进化版
│   └── v4.0/                     # 认知进化版（当前）
│       ├── README.md             # 版本说明
│       ├── CHANGELOG.md          # 变更日志
│       └── ARCHITECTURE.md       # 架构演进
│
├── 📂 docs/                      # 文档中心
│   ├── user/                     # 用户文档
│   │   ├── USER_GUIDE.md         # 用户指南
│   │   ├── QUICKSTART.md         # 快速开始
│   │   └── ...
│   ├── developer/                # 开发者文档
│   │   ├── API.md                # API文档
│   │   ├── DOCKER.md             # Docker使用
│   │   └── ...
│   ├── architecture/             # 架构文档
│   │   ├── INTRODUCTION.md       # 系统介绍
│   │   ├── boundary_cases.md     # 边界案例
│   │   └── ...
│   └── reports/                  # 历史报告
│       ├── VERSION_HISTORY.md    # 版本历史
│       └── ...
│
├── 📂 core/                      # 核心业务逻辑
│   ├── ports/                    # 端口（接口定义）
│   └── services/                 # 服务层
│       ├── planner.py            # 核心规划器
│       ├── intent_parser.py      # 意图识别
│       └── ...
│
├── 📂 infrastructure/            # 基础设施层
│   ├── cognitive_layer.py        # 认知层（v4.0新增）
│   ├── recurrent_reasoner.py     # 循环推理（v4.0新增）
│   ├── problem_analyzer.py       # 问题分析器
│   ├── causal_reasoner.py        # 因果推理器
│   ├── plan_generator.py         # 规划生成器
│   ├── uncertainty_estimator.py  # 不确定性评估
│   └── ...
│
├── 📂 adapters/                  # 适配器层
│   ├── llm/                      # LLM适配器
│   │   ├── ollama_adapter.py     # Ollama本地模型
│   │   ├── remote_adapter.py     # 远程模型
│   │   └── ...
│   └── ui/                       # UI适配器
│       └── cli_ui.py             # CLI界面
│
├── 📂 tools/                     # 工具系统
│   ├── web_search.py             # 安全网络搜索
│   ├── math_calculator.py        # 数学计算器
│   └── ...
│
├── 📂 meta/                      # 元认知层
│   ├── induction.py              # 归纳总结器
│   ├── conflict_detector.py      # 冲突检测
│   └── ...
│
├── 📂 backend/                   # 后端服务
│   └── main.py                   # FastAPI主程序
│
├── 📂 frontend/                  # 前端界面
│   └── index.html                # Web界面
│
├── 📂 config/                    # 配置文件
│   ├── settings.yaml             # 主配置
│   ├── reflexes.yaml             # 反射规则
│   └── ...
│
├── 📂 data/                      # 数据存储
│   ├── experience_pool.db        # 经验池
│   ├── learning_rules.db         # 学习规则
│   ├── campfire_log.txt          # 对话日志
│   └── ...
│
├── 📂 logs/                      # 日志文件
│   └── *.log                     # 运行日志
│
├── 📂 tests/                     # 测试文件
│   └── test_*.py                 # 单元测试
│
├── 📂 scripts/                   # 工具脚本
│   ├── quick_verify.py           # 快速验证
│   └── ...
│
└── 📄 配置文件（根目录）
    ├── requirements.txt          # Python依赖
    ├── Dockerfile                # Docker镜像
    ├── docker-compose.yml        # 容器编排
    ├── .env.example              # 环境变量模板
    └── start.bat                 # 启动脚本
```

---

## 🎯 快速导航

### 用户查看文档

1. **快速开始**: 主目录 `README.md` 或 `快速启动.md`
2. **版本说明**: `archives/v4.0/README.md`
3. **使用指南**: `docs/user/USER_GUIDE.md`

### 开发者查看文档

1. **贡献指南**: 主目录 `CONTRIBUTING.md`
2. **API文档**: `docs/developer/API.md`
3. **架构设计**: `docs/architecture/INTRODUCTION.md`
4. **边界案例**: `docs/architecture/boundary_cases.md`

### 理解系统哲学

1. **哲学理念**: 主目录 `PHILOSOPHY.md`
2. **回应边界**: 主目录 `RESPONSE_BOUNDARIES.md`
3. **数字生命宣言**: `docs/architecture/DIGITAL_LIFE_MANIFESTO.md`

---

## 📊 目录职责说明

| 目录 | 职责 | 示例文件 |
|------|------|----------|
| **core/** | 核心业务逻辑 | planner.py, intent_parser.py |
| **infrastructure/** | 基础设施层 | cognitive_layer.py, recurrent_reasoner.py |
| **adapters/** | 外部适配器 | ollama_adapter.py, cli_ui.py |
| **tools/** | 工具系统 | web_search.py, math_calculator.py |
| **meta/** | 元认知层 | induction.py, conflict_detector.py |
| **backend/** | 后端服务 | main.py (FastAPI) |
| **frontend/** | 前端界面 | index.html |
| **config/** | 配置文件 | settings.yaml |
| **data/** | 数据存储 | experience_pool.db |
| **logs/** | 运行日志 | campfire.log |
| **tests/** | 测试文件 | test_*.py |
| **scripts/** | 工具脚本 | quick_verify.py |
| **docs/** | 文档中心 | 按类型分类 |
| **archives/** | 版本归档 | v1.0/, v2.0/, v3.0/, v4.0/ |

---

## 🔄 版本归档说明

**archives/** 目录保存历史版本的完整归档：

- **查看当前版本**: `archives/v4.0/`
- **查看历史版本**: `archives/v3.0/`, `archives/v2.0/`, `archives/v1.0/`
- **查看版本对比**: 每个版本的 `ARCHITECTURE.md`

**docs/reports/** 保存开发过程中的临时报告（已归档的历史报告）

---

## 📝 文档分类原则

### 主目录文档
- **README.md**: 项目总览（必读）
- **核心理念**: PHILOSOPHY.md, RESPONSE_BOUNDARIES.md
- **贡献指南**: CONTRIBUTING.md
- **变更日志**: CHANGELOG.md

### docs/子目录
- **user/**: 面向用户的文档
- **developer/**: 面向开发者的文档
- **architecture/**: 架构设计文档
- **reports/**: 历史报告（已归档）

### archives/子目录
- **v{版本号}/**: 该版本的完整归档
- 包含: README.md, CHANGELOG.md, ARCHITECTURE.md

---

## 🚀 推荐阅读顺序

### 新用户
1. 主目录 `README.md`
2. `快速启动.md`
3. `docs/user/USER_GUIDE.md`

### 新开发者
1. 主目录 `README.md`
2. `CONTRIBUTING.md`
3. `docs/architecture/INTRODUCTION.md`
4. `archives/v4.0/ARCHITECTURE.md`

### 深入理解
1. `PHILOSOPHY.md`
2. `docs/architecture/boundary_cases.md`
3. `archives/v4.0/` 完整阅读

---

**维护者**: 联盟拓荒者团队  
**更新日期**: 2026-06-14  
**版本**: v4.0