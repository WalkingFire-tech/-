# 求助内化进化系统设计方案

## 一、核心理念

**从"被动求助"到"主动学习"，从"一次性咨询"到"持续内化"**

```
认知螺旋：
求助 → 消化 → 内化 → 优化 → 求助更少、解决更优
  ↑                                              ↓
  └────────────── 持续进化 ←───────────────────┘
```

**比喻演进**:
- **学徒期**: 遇到不懂就问老师，只记答案
- **学习期**: 问老师，记解题步骤，总结笔记
- **成长期**: 比较多个老师，融合方法论
- **专家期**: 能指导他人，反思教学方式

---

## 二、当前系统基础评估

### ✅ 已具备的能力

| 能力 | 模块 | 状态 | 说明 |
|------|------|------|------|
| 记录经验 | experience_pool | ✅ | 成功/失败案例存储 |
| 离线归纳 | induction_scheduler | ✅ | 挖掘模式，生成规则 |
| 规则应用 | _match_learning_rule | ✅ | 规则影响路由 |
| 求助外部 | remote_adapter | ✅ | 调用GPT/DeepSeek |
| 在线学习 | dialogue_stream_learner | ✅ | 实时检测学习信号 |
| 元归纳 | meta_inductor | ✅ | 优化学习参数 |

### ❌ 缺失的关键环节

**求助后内化不足**:
```
当前流程：
用户问题 → 置信度低 → 调用外部专家 → 返回答案 → 结束
                                           ↑
                                     没有内化！
```

**期望流程**:
```
用户问题 → 置信度低 → 调用外部专家 → 结构化分析
    ↓
    ├─ 答案部分 → 返回用户
    ├─ 分析部分 → 存入expert_advice_pool
    └─ 规则模板 → 生成pending规则
    ↓
定期内化 → 验证效果 → 激活规则 → 下次不再求助
```

---

## 三、实施方案

### 3.1 结构化求助（P0）

#### 步骤1：扩展remote_adapter

```python
# adapters/llm/remote_adapter.py

class RemoteAdapter:
    def generate_with_analysis(self, prompt: str, context: dict) -> dict:
        """生成答案并附带结构化分析"""
        
        expert_prompt = f"""
用户问题：{prompt}

当前系统理解（可能不完整）：
- 意图类型：{context.get('intent_type', 'unknown')}（置信度{context.get('confidence', 0):.2f}）
- 已有知识：{context.get('relevant_rules', [])}
- 历史类似案例：{context.get('similar_experiences', [])}

请作为专家，输出以下JSON结构：
{{
    "answer": "给用户的最终答案",
    "analysis": {{
        "clarified_intent": "对用户问题的重新表述",
        "understanding_gap": "系统理解偏差的原因",
        "suggested_approach": "合理的处理方案",
        "model_recommendation": "建议使用的模型或工具"
    }},
    "rule_template": {{
        "condition": "触发条件（如：intent_type == 'X' and keyword in text）",
        "action": "建议动作（如：prefer_model:Y）",
        "confidence": 0.8,
        "reasoning": "为什么这样建议"
    }}
}}
"""
        
        response = self._call_api(expert_prompt)
        return self._parse_structured_response(response)
```

#### 步骤2：创建expert_advice_pool表

```python
# infrastructure/expert_advice_pool.py

class ExpertAdvicePool:
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect('expert_advice_pool.db')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS expert_advices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                
                -- 原始问题
                user_input TEXT,
                intent_type TEXT,
                system_confidence REAL,
                
                -- 专家信息
                expert_model TEXT,
                
                -- 结构化分析
                clarified_intent TEXT,
                understanding_gap TEXT,
                suggested_approach TEXT,
                model_recommendation TEXT,
                
                -- 规则模板
                rule_condition TEXT,
                rule_action TEXT,
                rule_confidence REAL,
                rule_reasoning TEXT,
                
                -- 验证状态
                status TEXT DEFAULT 'pending',
                validation_score REAL,
                applied_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                
                -- 用户反馈
                user_feedback INTEGER
            )
        ''')
        conn.close()
    
    def add_advice(self, advice: dict):
        """存储专家建议"""
        conn = sqlite3.connect('expert_advice_pool.db')
        conn.execute('''
            INSERT INTO expert_advices 
            (timestamp, user_input, intent_type, system_confidence,
             expert_model, clarified_intent, understanding_gap,
             suggested_approach, model_recommendation,
             rule_condition, rule_action, rule_confidence, rule_reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            advice['user_input'],
            advice['intent_type'],
            advice['system_confidence'],
            advice['expert_model'],
            advice['analysis']['clarified_intent'],
            advice['analysis']['understanding_gap'],
            advice['analysis']['suggested_approach'],
            advice['analysis']['model_recommendation'],
            advice['rule_template']['condition'],
            advice['rule_template']['action'],
            advice['rule_template']['confidence'],
            advice['rule_template']['reasoning']
        ))
        conn.commit()
        conn.close()
```

---

### 3.2 内化机制（P0）

#### 步骤1：定期内化任务

```python
# meta/expert_advice_integrator.py

class ExpertAdviceIntegrator:
    """专家建议内化器"""
    
    def __init__(self):
        self.advice_pool = ExpertAdvicePool()
        self.min_confidence = 0.7
    
    def run_integration(self) -> dict:
        """运行内化任务"""
        # 1. 获取待内化的建议
        pending_advices = self._get_pending_advices()
        
        # 2. 提取规则模板
        rule_templates = self._extract_rule_templates(pending_advices)
        
        # 3. 冲突检测
        validated_rules = self._validate_rules(rule_templates)
        
        # 4. 生成pending规则
        generated = self._generate_rules(validated_rules)
        
        return {
            'processed': len(pending_advices),
            'generated_rules': generated,
            'conflicts_resolved': len(rule_templates) - len(validated_rules)
        }
    
    def _get_pending_advices(self) -> List[dict]:
        """获取待内化的专家建议"""
        conn = sqlite3.connect('expert_advice_pool.db')
        cursor = conn.execute('''
            SELECT * FROM expert_advices
            WHERE status = 'pending'
            ORDER BY timestamp DESC
            LIMIT 50
        ''')
        advices = [self._row_to_dict(row) for row in cursor.fetchall()]
        conn.close()
        return advices
    
    def _extract_rule_templates(self, advices: List[dict]) -> List[dict]:
        """从建议中提取规则模板"""
        templates = []
        
        for advice in advices:
            if advice['rule_confidence'] >= self.min_confidence:
                templates.append({
                    'condition': advice['rule_condition'],
                    'action': advice['rule_action'],
                    'confidence': advice['rule_confidence'],
                    'source': f"expert:{advice['expert_model']}",
                    'reasoning': advice['rule_reasoning'],
                    'advice_id': advice['id']
                })
        
        return templates
    
    def _validate_rules(self, templates: List[dict]) -> List[dict]:
        """验证规则（冲突检测）"""
        validated = []
        
        for template in templates:
            # 检查是否与现有规则冲突
            conflicts = self._check_conflicts(template)
            
            if not conflicts:
                validated.append(template)
            else:
                # 尝试解决冲突
                resolved = self._resolve_conflict(template, conflicts)
                if resolved:
                    validated.append(resolved)
        
        return validated
    
    def _generate_rules(self, templates: List[dict]) -> int:
        """生成pending规则"""
        conn = sqlite3.connect('learning_rules.db')
        count = 0
        
        for template in templates:
            conn.execute('''
                INSERT INTO learning_rules
                (condition, action, confidence, status, source, created_at)
                VALUES (?, ?, ?, 'pending', ?, ?)
            ''', (
                template['condition'],
                template['action'],
                template['confidence'],
                template['source'],
                time.time()
            ))
            count += 1
            
            # 标记建议已内化
            self._mark_advice_integrated(template['advice_id'])
        
        conn.commit()
        conn.close()
        return count
```

#### 步骤2：集成到planner

```python
# core/services/planner.py

def plan(self, intent: Intent):
    # ... 现有逻辑 ...
    
    # 当置信度低时，求助外部专家
    if intent.confidence < 0.5:
        logger.info("置信度低，求助外部专家")
        
        # 结构化求助
        expert_result = self._consult_expert(intent)
        
        # 存储专家建议
        self.expert_advice_pool.add_advice({
            'user_input': intent.raw_text,
            'intent_type': intent.type,
            'system_confidence': intent.confidence,
            'expert_model': expert_result['model'],
            'analysis': expert_result['analysis'],
            'rule_template': expert_result['rule_template']
        })
        
        # 返回答案
        bus.publish("plan_executed", expert_result['answer'])
        return

def _consult_expert(self, intent: Intent) -> dict:
    """咨询外部专家"""
    # 选择最佳专家
    expert = self._select_expert(intent)
    
    # 准备上下文
    context = {
        'intent_type': intent.type,
        'confidence': intent.confidence,
        'relevant_rules': self._get_relevant_rules(intent),
        'similar_experiences': self._get_similar_experiences(intent)
    }
    
    # 结构化求助
    result = expert.generate_with_analysis(intent.raw_text, context)
    
    return result
```

---

### 3.3 验证与优化（P1）

#### 步骤1：规则模拟验证

```python
# meta/rule_validator.py

class RuleValidator:
    """规则验证器"""
    
    def validate_rule_on_history(self, rule: dict) -> dict:
        """在历史经验上验证规则"""
        conn = sqlite3.connect('experience_pool.db')
        
        # 找到符合条件的历史案例
        cursor = conn.execute('''
            SELECT * FROM experiences
            WHERE intent_type = ?
        ''', (self._extract_intent_type(rule['condition']),))
        
        cases = cursor.fetchall()
        
        # 模拟应用规则
        improvements = 0
        for case in cases:
            # 假设应用规则
            simulated_quality = self._simulate_rule_application(case, rule)
            actual_quality = case['quality_score']
            
            if simulated_quality > actual_quality:
                improvements += 1
        
        # 计算提升率
        improvement_rate = improvements / len(cases) if cases else 0
        
        return {
            'rule_id': rule['id'],
            'test_cases': len(cases),
            'improvements': improvements,
            'improvement_rate': improvement_rate,
            'should_activate': improvement_rate > 0.3
        }
```

#### 步骤2：动态调整专家优先级

```python
# infrastructure/expert_selector.py

class ExpertSelector:
    """专家选择器"""
    
    def __init__(self):
        self.expert_scores = {}  # {model_name: avg_quality}
    
    def select_best_expert(self, intent: Intent) -> RemoteAdapter:
        """选择最佳专家"""
        # 从统计库获取专家质量
        conn = sqlite3.connect('model_stats.db')
        cursor = conn.execute('''
            SELECT model_name, AVG(quality_score) as avg_quality
            FROM model_performance
            WHERE task_type = ? AND model_name LIKE 'remote_%'
            GROUP BY model_name
            ORDER BY avg_quality DESC
        ''', (intent.type,))
        
        experts = cursor.fetchall()
        
        if experts:
            # 选择质量最高的专家
            best_expert = experts[0][0]
            return self.adapters[best_expert]
        
        # 默认选择
        return self.adapters.get('remote_gpt4') or next(iter(self.adapters.values()))
```

---

### 3.4 元级优化（P2）

#### 扩展元归纳器

```python
# meta/meta_induction.py

class MetaInductor:
    def __init__(self):
        self.params = {
            # 现有参数
            'min_support': 3,
            'min_confidence': 0.7,
            
            # 新增：求助策略参数
            'help_threshold': 0.5,      # 置信度低于此值时求助
            'expert_priority': [        # 专家优先级
                'remote_gpt4',
                'deepseek-chat',
                'deepcoder'
            ],
            'integration_delay': 3600,  # 求助后多久内化（秒）
            'min_help_success_rate': 0.6  # 最低求助成功率
        }
    
    def optimize_help_strategy(self) -> dict:
        """优化求助策略"""
        # 分析历史求助效果
        help_stats = self._analyze_help_history()
        
        adjustments = []
        
        # 1. 调整求助阈值
        if help_stats['success_rate'] < self.params['min_help_success_rate']:
            # 成功率低，提高阈值（减少求助）
            old_threshold = self.params['help_threshold']
            self.params['help_threshold'] = min(0.7, old_threshold + 0.1)
            adjustments.append({
                'type': 'increase_help_threshold',
                'reason': '求助成功率低',
                'old': old_threshold,
                'new': self.params['help_threshold']
            })
        
        # 2. 调整专家优先级
        expert_quality = help_stats['expert_quality']
        if expert_quality:
            # 按质量重新排序
            sorted_experts = sorted(
                expert_quality.items(),
                key=lambda x: x[1],
                reverse=True
            )
            self.params['expert_priority'] = [e for e, _ in sorted_experts]
            adjustments.append({
                'type': 'reorder_experts',
                'reason': '按质量重新排序',
                'new_order': self.params['expert_priority']
            })
        
        return {
            'adjustments': adjustments,
            'current_params': self.params
        }
```

---

## 四、实施路线图

### P0（1-2周）：建立基础

- [ ] 扩展remote_adapter，支持结构化分析
- [ ] 创建expert_advice_pool表
- [ ] 实现ExpertAdviceIntegrator
- [ ] 集成到planner的求助流程
- [ ] 添加定期内化任务

### P1（2-3周）：验证优化

- [ ] 实现RuleValidator
- [ ] 实现ExpertSelector
- [ ] 添加求助效果反馈记录
- [ ] 动态调整专家优先级

### P2（1个月）：元级优化

- [ ] 扩展元归纳器，优化求助策略
- [ ] 实现"拒绝求助"策略
- [ ] 添加内化效果可视化
- [ ] 用户审计界面

---

## 五、预期效果

### 效率提升

```
初期：每次遇到新问题都求助专家
中期：50%的问题通过内化规则解决
后期：80%的问题自己解决，只求助真正新颖的问题
```

### 成本降低

```
初期：每次求助成本 $0.01-0.05
中期：求助频率降低50%，成本减半
后期：求助频率降低80%，成本降至20%
```

### 能力提升

```
初期：只能处理训练过的任务
中期：能处理专家指导过的任务
后期：能处理专家未见过的新任务（通过归纳）
```

---

## 六、根本价值

| 价值 | 说明 |
|------|------|
| **可持续进化** | 不依赖开发者，自己从求助中提炼知识 |
| **成本降低** | 随着内化积累，求助频率自然下降 |
| **透明度** | 用户可看到系统学到了什么规则 |
| **适应性** | 专家更换时，系统自然更新经验池 |
| **同伴感** | 用户感知系统在"跟着我一起学习" |

---

## 七、总结

**这正是自我进化的高级形式**：

✅ **不耻下问** - 置信度低时主动求助  
✅ **问后必思** - 结构化分析，理解为什么  
✅ **思后必进** - 内化知识，生成规则  
✅ **进后必善** - 优化策略，减少求助  

**系统从"被动吸收反馈"跃迁到"主动向专家学习并内化知识"，真正实现螺旋式上升的自我完善。**

**这就是"同行者"该有的样子：每次处理都在学习，每次学习都在进化。** 🔥