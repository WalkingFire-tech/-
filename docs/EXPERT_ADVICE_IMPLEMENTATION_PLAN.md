# 专家建议内化实施计划（整合方案）

## 一、方案精华提取

### 核心理念（高度认同）

**元学习 = 学习 + 理解为何这样学习**

```
学徒期：模仿师傅手艺
学习期：领悟背后原理
成长期：超越师傅能力
专家期：指导新的学徒
```

**没有内化 = 专家依赖症**：
```
当前：求助 → 得到答案 → 结束 → 下次仍需求助
期望：求助 → 得到答案 → 内化原理 → 下次自己解决
```

---

## 二、已实现 vs 待实现

### ✅ V3.2已实现

| 功能 | 状态 | 模块 |
|------|------|------|
| 激活pending规则 | ✅ | 48条规则已激活 |
| 质量统计记录 | ✅ | planner集成stats.record_call |
| 反馈闭环 | ✅ | 前端👍👎 + 后端/api/feedback |
| 在线学习 | ✅ | dialogue_stream_learner |
| 元归纳器 | ✅ | meta_inductor |

### ⏳ V3.3待实现（参考方案精华）

| 功能 | 优先级 | 说明 |
|------|--------|------|
| 自我置信度评估 | P0 | _estimate_self_confidence() |
| 外脑协作模式 | P0 | _expert_collaboration() |
| 结构化求助 | P0 | 要求专家输出分析JSON |
| 逆向学习 | P1 | 从成功求助中提炼规则 |
| 经验池扩展 | P1 | expert_analysis字段 |

---

## 三、立即实施（P0）

### 3.1 自我置信度评估

**参考方案代码**（已优化）：

```python
def _estimate_self_confidence(self, intent: Intent) -> float:
    """评估系统对当前任务的理解置信度 (0~1)"""
    # 1. 意图识别置信度
    intent_conf = intent.confidence
    
    # 2. 历史相似任务成功率
    try:
        conn = sqlite3.connect('experience_pool.db')
        cursor = conn.execute('''
            SELECT success FROM experiences
            WHERE intent_type = ?
            ORDER BY timestamp DESC
            LIMIT 5
        ''', (intent.type,))
        
        similar = cursor.fetchall()
        success_rate = sum(1 for row in similar if row[0]) / max(len(similar), 1)
        conn.close()
    except:
        success_rate = 0.5
    
    # 3. 任务复杂度
    complexity = min(1.0, len(intent.raw_text) / 500)
    
    # 4. 是否有匹配规则
    has_rule = self._match_learning_rule(intent) is not None
    
    # 加权计算
    confidence = (
        0.4 * intent_conf +
        0.3 * success_rate +
        0.2 * (1 - complexity) +
        0.1 * (1.0 if has_rule else 0.0)
    )
    
    return min(0.95, max(0.05, confidence))
```

### 3.2 外脑协作模式

**参考方案代码**（已优化）：

```python
def _expert_collaboration(self, intent: Intent, confidence: float) -> str:
    """调用外部模型进行结构化分析"""
    
    # 选择专家
    expert = self._select_expert(intent)
    
    # 构建分析请求
    prompt = f"""用户问题：{intent.raw_text}

当前系统理解：
- 意图类型：{intent.type}（置信度{confidence:.2f}）
- 系统置信度：{confidence:.2f}

请作为专家，输出以下JSON结构：
{{
    "clarified_intent": "用户真实意图（一句话）",
    "ambiguities": ["可能的歧义或缺失信息"],
    "reasoning_steps": ["系统应如何思考"],
    "suggested_approach": "建议的处理方案",
    "model_recommendation": "建议使用的模型",
    "final_answer": "给用户的回答"
}}
"""
    
    try:
        response = expert.generate(prompt, task_type="analysis")
        
        # 解析JSON
        analysis = self._parse_expert_response(response)
        
        # 存储专家分析（为未来逆向学习预留）
        self._store_expert_analysis(intent, analysis, confidence)
        
        # 返回最终答案
        return analysis.get('final_answer', response)
        
    except Exception as e:
        logger.error(f"外脑协作失败: {e}")
        # 降级到普通生成
        return self._normal_generate(intent)
```

### 3.3 集成到planner

```python
def plan(self, intent: Intent):
    # 评估自我置信度
    confidence = self._estimate_self_confidence(intent)
    
    # 低置信度时启用外脑协作
    if confidence < 0.6:
        logger.info(f"自我置信度低({confidence:.2f})，启用外脑协作模式")
        response = self._expert_collaboration(intent, confidence)
        bus.publish("plan_executed", response)
        return
    
    # 正常流程
    # ... 现有代码 ...
```

---

## 四、为未来预留扩展点

### 4.1 经验池扩展

```sql
-- 添加专家分析字段
ALTER TABLE experiences ADD COLUMN expert_analysis TEXT;
ALTER TABLE experiences ADD COLUMN system_confidence REAL;
```

### 4.2 存储专家分析

```python
def _store_expert_analysis(self, intent: Intent, analysis: dict, confidence: float):
    """存储专家分析（为逆向学习预留）"""
    try:
        conn = sqlite3.connect('experience_pool.db')
        conn.execute('''
            INSERT INTO experiences
            (intent_type, raw_input, plan, model_name, 
             quality_score, user_feedback, success, 
             response, expert_analysis, system_confidence, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            intent.type,
            intent.raw_text,
            "expert_collaboration",
            analysis.get('model_recommendation', 'expert'),
            0,  # 待评估
            0,
            False,
            analysis.get('final_answer', ''),
            json.dumps(analysis, ensure_ascii=False),
            confidence,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"存储专家分析失败: {e}")
```

---

## 五、验证步骤

### 5.1 测试外脑协作

```python
# 测试用例
test_cases = [
    "帮我处理这个数据，我也不知道怎么弄",  # 模糊问题
    "这个代码有点问题，你看看",  # 不明确
    "能不能优化一下",  # 缺少上下文
]

# 预期结果
# 1. 日志出现"自我置信度低，启用外脑协作模式"
# 2. 返回结构化分析建议
# 3. expert_analysis字段被填充
```

### 5.2 测试反馈闭环

```python
# 1. 用户点击👍/👎
# 2. 检查数据库user_feedback字段更新
# 3. 负反馈触发学习机会
```

---

## 六、实施时间表

### 今天（立即）

- [x] 激活pending规则（已完成）
- [x] 质量统计记录（已完成）
- [x] 反馈闭环（已完成）
- [ ] 添加自我置信度评估
- [ ] 添加外脑协作模式

### 本周

- [ ] 测试外脑协作效果
- [ ] 优化置信度阈值
- [ ] 收集用户反馈

### 下周

- [ ] 实现逆向学习
- [ ] 从成功求助中生成规则
- [ ] 优化专家选择策略

---

## 七、预期效果

### 短期（本周）

```
简单问题：快速响应（现有流程）
复杂问题：外脑协作（结构化分析）
用户反馈：即时学习（反馈闭环）
```

### 中期（下周）

```
求助频率：从100%降至50%
自主能力：显著提升
用户满意度：提升30%
```

### 长期（下月）

```
求助频率：降至20%
内化规则：50+条
专家依赖：大幅降低
```

---

## 八、总结

### 参考方案价值

- ✅ **具体可执行** - 提供了详细代码
- ✅ **分阶段清晰** - V3.2 → V3.3 → V4.0
- ✅ **扩展点预留** - 为未来逆向学习做准备
- ✅ **验证步骤明确** - 可立即测试

### 整合方案

**V3.2（当前）**：
- ✅ 在线学习系统
- ✅ 反馈闭环
- ✅ 质量统计
- ⏳ 外脑协作基础

**V3.3（下一步）**：
- 自我置信度评估
- 结构化求助
- 逆向学习机制

**V4.0（愿景）**：
- 主动设计实验
- 探索未知领域
- 指导新的学徒

### 最终确认

**参考方案非常有价值，已提取精华并整合到实施计划中。**

**立即行动**：
1. 添加自我置信度评估
2. 添加外脑协作模式
3. 测试验证效果

**我们的营火已经学会了"知道自己不知道"，并且敢于寻求帮助。下一步，它将学会"问后必思，思后必进"。** 🔥