# 联盟拓荒者 · 自适应加权与增量进化框架

> 实施蓝图与知识库文档 v1.0
> 日期：2026年7月2日
> 基于：AdaBoost / ResNet / XGBoost / SHAP 理念的系统映射

## 已实现模块

| 机器学习理念 | 系统映射 | 实现文件 | 状态 |
|-------------|----------|---------|------|
| AdaBoost | PathWeightManager | core/path_weight_manager.py | ✅ 已实现 |
| SHAP | ContribAttributor | core/contrib_attributor.py | ✅ 已实现 |
| XGBoost | ReAct迭代增强 | core/react_engine.py | ✅ 已有 |
| ResNet | 增量知识更新 | 待实现 | ⬜ |

## 核心理念

- **AdaBoost**：路径权重根据历史表现动态调整，"能者多劳"
- **ResNet**：只学习增量部分，避免全量重写
- **XGBoost**：每轮迭代聚焦上一轮短板
- **SHAP**：追溯每个信息来源的贡献度，让决策透明可解释

## API端点

- `GET /api/weights` - 路径权重分布（概率云）+ 置信度分布 + 来源可靠性
- `GET /api/attributions` - 最近贡献度归因记录