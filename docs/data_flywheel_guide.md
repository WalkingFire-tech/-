# 数据飞轮实施指南

## 核心认知纠正

### ❌ 错误理解
"用DeepSeek API实时监督系统学习"

### ✅ 正确理解
**API是"用"模型，不是"训练"模型**

- API调用：每次独立，模型不会因为你问了问题就变聪明
- 模型微调（SFT）：真正的学习，需要积累数据后离线训练

---

## 正确路径：三步走

### 第一步：积累高质量训练数据 ✅

**目标**：把每次交互变成未来的"教材"

**已实现**：`infrastructure/interaction_data_collector.py`

**记录内容**：
```python
{
    'session_id': '会话ID',
    'question': '用户问题',
    'response': '系统回答',
    'feedback_type': 'positive/negative/correction/neutral',
    'feedback_content': '反馈内容',
    'objective_score': 75.0,  # 客观分
    'subjective_score': 80.0,  # 主观分
    'total_score': 77.0,       # 总分
    'decision_chain_summary': '决策链摘要',
    'knowledge_sources': ['fact_store', 'external_learn'],
    'quality_score': 0.8       # 数据质量分
}
```

**数据质量评估**：
- 问题长度 ≥ 10字符：+0.2分
- 回答长度 ≥ 20字符：+0.2分
- 有明确反馈：+0.3分
- 总分 ≥ 60：+0.3分

**高质量数据标准**：质量分 ≥ 0.7

---

### 第二步：离线监督微调（SFT）

**时机**：积累 ≥ 100条高质量数据

**数据格式**：已实现自动导出

```json
{
  "instruction": "请回答以下问题",
  "input": "什么是机器学习?",
  "output": "机器学习是人工智能的一个分支...",
  "metadata": {
    "quality_score": 0.8,
    "timestamp": "2026-06-23T01:37:22"
  }
}
```

**纠错数据处理**：
```json
{
  "instruction": "请回答以下问题",
  "input": "Python是什么时候发布的?",
  "output": "不对，应该是1991年发布的",  // 使用纠错内容
  "metadata": {...}
}
```

**微调方案**：

1. **官方微调服务**（推荐）
   - 上传数据到DeepSeek平台
   - 平台自动完成微调
   - 最简单快捷

2. **开源微调框架**
   - 使用LoRA高效微调
   - 在自己的服务器训练
   - 部署为新API服务

---

### 第三步：数据飞轮

**完整循环**：
```
交互 → 数据收集 → 离线微调 → 模型升级 → 再交互
```

**影子模式部署**：
```
新模型 + 旧模型 → 并行回答 → 对比效果 → 确认升级
```

---

## 已实现的功能

### 1. 交互数据收集器 ✅

**文件**：`infrastructure/interaction_data_collector.py`

**核心方法**：

| 方法 | 功能 |
|------|------|
| `save_interaction()` | 保存交互记录 |
| `get_training_data()` | 获取训练数据 |
| `export_for_sft()` | 导出SFT格式 |
| `get_statistics()` | 获取统计信息 |

### 2. 数据质量评估 ✅

**自动评估**：
- 问题质量
- 回答质量
- 反馈明确性
- 评分高低

### 3. SFT数据导出 ✅

**支持格式**：
- JSON（标准格式）
- JSONL（流式格式）
- CSV（表格格式）

**导出示例**：
```python
collector.export_for_sft(
    output_path="data/sft_training_data.json",
    format_type="json",
    min_quality_score=0.7,
    include_corrections=True
)
```

---

## 测试结果

```
✅ 数据收集系统已测试
✅ SFT数据导出已测试
✅ 数据质量评估已测试

导出数据示例：
[
  {
    "instruction": "请回答以下问题",
    "input": "Python是什么时候发布的?",
    "output": "不对，应该是1991年发布的"
  },
  {
    "instruction": "请回答以下问题",
    "input": "什么是机器学习?",
    "output": "机器学习是人工智能的一个分支..."
  }
]
```

---

## 具体行动建议

### 立即行动

1. **集成到主流程**
```python
# 在 AlliancePioneer 类中
def process_question(self, question: str) -> str:
    response = self._generate_response(question)
    
    # 记录交互
    self.interaction_collector.save_interaction(
        session_id=self.session_id,
        question=question,
        response=response,
        feedback_type="neutral",
        objective_score=objective_score,
        total_score=total_score
    )
    
    return response
```

2. **处理用户反馈**
```python
def handle_feedback(self, question, response, feedback):
    feedback_type = self._classify_feedback(feedback)
    
    # 更新交互记录
    self.interaction_collector.save_interaction(
        session_id=self.session_id,
        question=question,
        response=response,
        feedback_type=feedback_type,
        feedback_content=feedback
    )
```

### 短期目标（1-2周）

1. 收集100+条高质量交互数据
2. 研究DeepSeek微调文档
3. 准备第一次微调实验

### 中期目标（1-2月）

1. 完成第一次模型微调
2. 影子模式部署测试
3. 对比新旧模型效果

### 长期目标（3-6月）

1. 建立自动化微调流程
2. 实现数据飞轮
3. 持续迭代优化

---

## 微调实验建议

### 第一个实验：修正自我认知

**目标**：改变系统的"人格"和回答风格

**数据准备**：
- 收集"你是谁？"类问题
- 标注期望的回答风格
- 至少50条同类数据

**预期效果**：
- 系统回答更符合预期风格
- 自我认知更准确
- 回答一致性提升

---

## 关键提醒

### ⚠️ 不要做的事

1. **不要实时调用API"训练"**
   - API不会记住你的反馈
   - 每次调用都是独立的

2. **不要跳过数据积累**
   - 少于100条数据效果不佳
   - 质量比数量更重要

3. **不要忽视数据质量**
   - 低质量数据会降低模型效果
   - 必须有质量评估机制

### ✅ 必须做的事

1. **持续收集数据**
   - 每次交互都记录
   - 自动质量评估

2. **定期导出训练**
   - 达到阈值自动提醒
   - 支持多种格式导出

3. **影子模式部署**
   - 新旧模型并行
   - 对比验证效果

---

## 总结

**核心认知**：让系统进化的关键，不在于"实时调用"外部模型，而在于**建立一个能够不断收集反馈、离线学习、并自我更新的工程化闭环**。

**已实现**：
- ✅ 交互数据收集系统
- ✅ 数据质量评估机制
- ✅ SFT数据格式化导出

**下一步**：
- 集成到主流程
- 积累训练数据
- 准备第一次微调实验

系统现在具备了数据飞轮的基础设施，可以开始积累训练数据了。