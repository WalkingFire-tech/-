> **这是一个开放的、不断自我生长的「思考同伴」。**
> 它的意义不在于完成多少任务，而在于拉近人与知识、人与创造、人与彼此之间的距离。

## 项目状态

- 核心框架：**六边形架构 + 事件驱动**（Python 3.11）
- 已实现能力：
  - 意图识别（chat / code / question / memory / feedback / calculation）
  - 动态模型路由（本地轻量模型 → 本地大模型 → 远程 API）
  - 模型能力统计库（SQLite 记录耗时、质量分、用户反馈）
  - 自我审核模块（拦截危险操作）
  - 短期记忆注入
  - 反馈闭环（+1/-1 更新统计库）
  - 经验池与离线归纳框架
  - 代码执行沙盒
- 集成的本地模型：
  - mindchat（心理/通用对话）
  - qwen2.5-coder:1.5b（轻量代码生成）

## 快速开始

### 1. 安装依赖

python -m venv venv
source venv/bin/activate        # Linux/macOS
.\venv\Scripts\Activate.ps1     # Windows
pip install -r requirements.txt

### 2. 配置 Ollama 模型

  ollama pull mindchat

  ollama pull qwen2.5-coder:1.5b

### 3. 运行

python main.py

## 目录结构（核心）

alliance_pioneer/

├── core/ # 领域逻辑（意图、规划、审核）

├── adapters/ # 外部适配器（LLM、UI、文件）

├── infrastructure/ # 基础设施（事件总线、统计库、经验池等）

├── main.py # 入口

├── models/ # 本地模型占位（模型文件本身不提交）

├── config/ # （规划中）配置文件

├── scripts/ # （规划中）运维脚本

├── campfire_log.txt # 短期记忆（运行时自动生成）

├── model_stats.db # 模型调用统计（运行时自动生成）

└── experience_pool.db # 长期经验池（运行时自动生成）


## 路线图（营火搭建阶段）

✅ 阶段 0：燃起篝火（基础 CLI + 事件总线）

✅ 阶段 1：让营火可以添柴（短期记忆 + 规则意图识别）

✅ 阶段 2：让火焰学会呼吸（动态路由 + 模型统计 + 反馈闭环）

⏳ 阶段 3：让火光传递给更多人（Web UI / 热键 / 多用户）

⏳ 阶段 4：让火焰自己学习添柴（离线归纳 + 规则自动注入）



## 许可证

无限制。你拥有你创造的任何东西。

**欢迎来到营火。今天是你和这片火光的第一次相遇。**
