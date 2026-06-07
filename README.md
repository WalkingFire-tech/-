# 联盟拓荒者

**当前版本**: v3.1 | **完成度**: 100%

---

## 🔥 项目简介

**具备元认知能力的自我进化智能体系统**

> 完美理解、合理判断、从实践进化、最终同步

---

## ✨ v3.1 核心特性

### 自我进化能力
- 真正的贝叶斯优化(scikit-optimize)
- 每周自动元学习任务
- 完整学习规则闭环
- 在线规则应用与冲突检测

### 生产级特性
- 优雅退出机制(signal+atexit)
- 事件驱动架构(解耦CLI)
- 线程安全设计
- 数据库连接池
- 配置热加载

### 计算能力
- 通用数学表达式计算
- π值高精度计算(mpmath)
- 安全eval白名单机制

---

## 📚 完整文档

**[ARCHIVE_v3.1.md](ARCHIVE_v3.1.md)** - v3.1完整归档(生产级)  
**[ARCHIVE_v3.0.md](ARCHIVE_v3.0.md)** - v3.0归档(基础版)  
**[CHANGELOG.md](CHANGELOG.md)** - 版本更新记录

---

## 🚀 快速开始

**详细启动指南**: [QUICKSTART.md](QUICKSTART.md)

### 一键启动（推荐）

**Windows**:
```bash
双击运行 start.bat
```

### 手动启动

```bash
# 安装核心依赖
pip install rich loguru pyyaml pydantic pydantic-settings python-dotenv numpy requests schedule

# 启动系统
python main.py
```

### 完整安装

```bash
pip install -r requirements.txt
python main.py
```

---

## 🎯 使用示例

```
:optimize run 20    # 运行贝叶斯优化
:induction run 7    # 运行归纳总结
计算 2+3*4           # 表达式计算
输出π的前100位       # π值计算
```
