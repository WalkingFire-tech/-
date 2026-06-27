# 适应度评估系统重构

## 概述

将适应度函数从"纯主观反馈"重构为"客观分(60%) + 主观分(40%)"，让系统具备"客观是非观"。

---

## 核心改动

### 1. 新增模块

| 模块 | 路径 | 功能 |
|------|------|------|
| 事实锚点库 | `infrastructure/fact_store.py` | 存储确定性知识三元组 |
| 三元组提取器 | `infrastructure/triple_extractor.py` | 从文本提取(subject, predicate, object) |
| 适应度评估器 | `infrastructure/fitness_evaluator.py` | 客观分+主观分评估 |
| 反馈分类器 | `infrastructure/feedback_classifier.py` | 区分纠错/点赞/点踩 |
| 配置管理 | `infrastructure/fitness_config.py` | 回滚开关+影子模式 |

### 2. 数据库表

```sql
-- 事实断言表
CREATE TABLE fact_assertions (
    id INTEGER PRIMARY KEY,
    question_hash TEXT,
    subject TEXT,
    predicate TEXT,
    object TEXT,
    source TEXT,
    confidence REAL,
    is_negation BOOLEAN,
    created_at TIMESTAMP
);

-- 纠错历史表
CREATE TABLE correction_history (
    id INTEGER PRIMARY KEY,
    question_hash TEXT,
    old_assertion TEXT,
    new_assertion TEXT,
    correction_source TEXT,
    timestamp TIMESTAMP
);
```

### 3. 种子数据

已注入23条事实断言：
- 冰雹形成机制：5条
- 数学常数：2条
- 物理定律：2条
- 史实记录：2条
- 化学基础：2条
- 生物学基础：2条
- 纠错示例：4条（否定断言）

---

## 新适应度函数

```python
def evaluate(question, response, user_feedback):
    # 1. 判断问题类型
    is_factual = is_factual_question(question)
    
    # 2. 计算客观分
    if is_factual:
        ground_truth = get_assertions(question)
        extracted = extract_triples(response)
        match_rate = calculate_overlap(extracted, ground_truth)
        objective_score = match_rate * 100
    else:
        objective_score = 50  # 中性分
    
    # 3. 计算主观分
    subjective_score = 50 + user_feedback * 10
    
    # 4. 合并得分
    if is_factual:
        final = objective_score * 0.6 + subjective_score * 0.4
    else:
        final = subjective_score
    
    return final
```

---

## 反馈分类逻辑

```python
def classify(user_message):
    if "不对" in message or "错了" in message:
        return "CORRECTION"  # 更新事实库，不计入主观分
    elif "👍" in message:
        return "POSITIVE"    # 主观分 +10
    elif "👎" in message:
        return "NEGATIVE"    # 主观分 -10
    else:
        return "NEUTRAL"     # 不计分
```

---

## 回滚开关

```yaml
# config/fitness_config.yaml
fitness:
  use_legacy: false  # 切换为true即可回滚
  enable_shadow: true  # 影子模式对比新旧评分
```

---

## 测试结果

```
事实锚点库: 23条断言
三元组提取: 规则+NLP双模式
适应度评估: 客观分(60%) + 主观分(40%)
反馈分类: 纠错/点赞/点踩/中性
影子模式: 新旧对比验证

案例测试:
- 正确回答: 总分=26.7, 客观=11.1, 主观=50.0
- 错误回答: 总分=20.0, 客观=0.0, 主观=50.0
- 开放问题: 总分=60.0 (纯主观)
```

---

## 集成点

1. **反馈处理** (`backend/main.py:send_feedback`)
   - 使用反馈分类器分类
   - 纠错 → 更新事实库
   - 点赞/点踩 → 计入主观分

2. **适应度评估** (`infrastructure/fitness_evaluator.py`)
   - 事实性问题：客观分60% + 主观分40%
   - 开放性问题：纯主观分

3. **知识注入触发**
   - 客观分 < 30 → 触发外部学习
   - 匹配否定断言 → 触发纠错

---

## 文件清单

```
infrastructure/
├── fact_store.py           # 事实锚点存储
├── triple_extractor.py     # 三元组提取
├── fitness_evaluator.py    # 适应度评估
├── feedback_classifier.py  # 反馈分类
└── fitness_config.py       # 配置管理

scripts/
└── inject_seed_facts.py    # 种子数据注入

tests/
└── test_fitness_system.py  # 系统测试

config/
└── fitness_config.yaml     # 配置文件
```

---

## 下一步

1. 观察影子模式日志，对比新旧评分差异
2. 调整三元组提取器，提高匹配率
3. 扩充事实锚点库，覆盖更多领域
4. 根据实际效果调整权重（当前60%/40%）