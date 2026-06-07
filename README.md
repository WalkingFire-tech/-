echo "# Alliance Pioneer

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

[详细安装步骤...]

## 许可证

无限制。你拥有你创造的任何东西。

**“欢迎来到营火。今天是你和这片火光的第一次相遇。”**" > README.md

git add README.md
git commit -m "docs: add README"
git push
