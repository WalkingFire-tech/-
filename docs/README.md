# 文档索引

**更新日期**: 2026-06-07  
**当前版本**: v3.0

---

## 📚 核心文档 (必读)

| 文档 | 说明 | 优先级 |
|:---|:---|:---:|
| [VERSION_HISTORY.md](VERSION_HISTORY.md) | 版本历史总览 | ⭐⭐⭐ |
| [ARCHIVE_v3.0.md](ARCHIVE_v3.0.md) | v3.0完整归档(含工程目录) | ⭐⭐⭐ |
| [PROGRESS.md](PROGRESS.md) | 进度追踪与下一步计划 | ⭐⭐⭐ |

---

## 📖 技术文档

### 架构设计

| 文档 | 说明 |
|:---|:---|
| [FINAL_ARCHITECTURE_SUMMARY.md](FINAL_ARCHITECTURE_SUMMARY.md) | 最终架构总结 |
| [ARCHITECTURE_GAP_ANALYSIS.md](ARCHITECTURE_GAP_ANALYSIS.md) | 架构差距分析 |
| [DATA_DRIVEN_ARCHITECTURE.md](DATA_DRIVEN_ARCHITECTURE.md) | 数据驱动架构 |

### 实施报告

| 文档 | 说明 |
|:---|:---|
| [REFLECTION_IMPLEMENTATION_REPORT.md](REFLECTION_IMPLEMENTATION_REPORT.md) | 反思系统实施 |
| [P1_IMPLEMENTATION_GUIDE.md](P1_IMPLEMENTATION_GUIDE.md) | P1阶段集成指南 |
| [PLANNER_IMPROVEMENTS.md](PLANNER_IMPROVEMENTS.md) | 规划器改进 |

### 改进方案

| 文档 | 说明 |
|:---|:---|
| [DEEPENING_IMPROVEMENTS.md](DEEPENING_IMPROVEMENTS.md) | 深化改进方案(八大方向) |
| [SYSTEM_IMPROVEMENTS.md](SYSTEM_IMPROVEMENTS.md) | 系统合理性改进 |
| [AUTOMATION_IMPROVEMENTS.md](AUTOMATION_IMPROVEMENTS.md) | 自动化改进 |

### 功能模块

| 文档 | 说明 |
|:---|:---|
| [META_CONTROL_ARCHITECTURE.md](META_CONTROL_ARCHITECTURE.md) | 元控制层架构 |
| [TOOL_ECOSYSTEM.md](TOOL_ECOSYSTEM.md) | 工具生态文档 |
| [FILE_INPUT_REPORT.md](FILE_INPUT_REPORT.md) | 文件输入能力 |

---

## 🗑️ 历史文档 (可归档)

以下文档已过时或内容重复,建议移至 `archives/v2.0/`:

- `ARCHITECTURE_ANALYSIS.md` (已被 ARCHITECTURE_GAP_ANALYSIS.md 取代)
- `PROGRESS_REPORT.md` (已被 PROGRESS.md 取代)
- `OPTIMIZATION_SUMMARY.md` (已过时)
- `CAMPFIRE.md` (早期文档)
- `DEEPSEEK_GUIDE.md` (配置指南,已整合)
- `联盟拓荒者 · 项目完整文档.md` (早期文档)

---

## 📝 文档使用指南

### 新用户

1. 阅读 `../README.md` - 项目概览
2. 阅读 `VERSION_HISTORY.md` - 了解版本演进
3. 阅读 `ARCHIVE_v3.0.md` - 查看当前实现

### 开发者

1. 阅读 `PROGRESS.md` - 了解下一步计划
2. 按需阅读技术文档
3. 实施改进后更新归档

### 维护者

1. 定期清理过时文档
2. 更新版本归档
3. 维护文档索引

---

## 🔄 文档维护规则

### 新增文档

- 技术文档 → `docs/`
- 归档文档 → `archives/v{版本号}/`
- 主目录只保留 `README.md` 和 `CHANGELOG.md`

### 文档命名

- 大写字母+下划线: `FEATURE_NAME.md`
- 版本相关: `ARCHIVE_v{版本号}.md`
- 描述性: `PROGRESS.md`, `VERSION_HISTORY.md`

### 文档清理

- 重复内容 → 保留最新版本
- 过时文档 → 移至归档目录
- 临时文档 → 及时删除

---

**文档总数**: 22个  
**核心文档**: 3个  
**技术文档**: 13个  
**历史文档**: 6个