# 知识检测与验证模块彻底重构报告

## 问题本质

你指出的问题非常准确：**过度依赖硬编码的领域知识，导致系统在遇到未预定义的专业领域时完全失效。**

### 原设计的根本缺陷

| 问题 | 表现 | 后果 |
|------|------|------|
| **硬编码领域知识** | `PROFESSIONAL_DOMAINS`、`CHIP_TYPES` | 新领域需要改代码 |
| **写死关键词映射** | `关键词 → 专业领域 → 芯片类型` | 仅覆盖预定义场景 |
| **固定芯片型号** | `TPS611`, `BQ769` 等硬编码 | 新芯片无法识别 |
| **规则不可扩展** | 所有规则写在代码里 | 用户无法自定义 |

**本质问题：这是一个"写死的专家系统"，而不是一个"能学习的系统"。**

---

## 重构理念

### 从"硬编码规则"到"知识驱动 + 学习进化"

| 原来（硬编码） | 重构后（知识驱动） |
|---------------|-------------------|
| 代码里写 `['芯片', 'IC']` | 从知识库查询领域关键词 |
| 代码里写 `{'TPS611': 'LED驱动'}` | 从知识库查询实体类型 |
| 代码里写 `if '均衡' in user_query` | 通过语义匹配判断需求 |
| 开发者改代码添加新领域 | 系统通过对话学习新领域 |

---

## 重构架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                     知识驱动的检测与验证系统                         │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   知识库 (SQLite + Vectors)                  │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │   │
│  │  │ 领域知识     │ │ 实体映射     │ │ 学习到的规则  │       │   │
│  │  │ domain_      │ │ entity_      │ │ learned_      │       │   │
│  │  │ knowledge    │ │ mapping      │ │ associations  │       │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ▲                                      │
│                              │ 读取/写入                            │
│  ┌───────────────────────────┼─────────────────────────────────────┐│
│  │                           │                                      ││
│  │  ┌────────────────────────┴────────────────────────┐           ││
│  │  │          SemanticGapDetector (语义检测器)        │           ││
│  │  │  ┌─────────────────────────────────────────────┐│           ││
│  │  │  │ 1. 向量检索判断领域                          ││           ││
│  │  │  │ 2. 知识覆盖度评估                            ││           ││
│  │  │  │ 3. 不确定性检测                              ││           ││
│  │  │  │ 4. 降级：规则匹配                            ││           ││
│  │  │  └─────────────────────────────────────────────┘│           ││
│  │  └──────────────────────────────────────────────────┘           ││
│  │                              │                                  ││
│  │  ┌──────────────────────────┴────────────────────────┐        ││
│  │  │      KnowledgeBasedValidator (知识库验证器)        │        ││
│  │  │  ┌─────────────────────────────────────────────┐  │        ││
│  │  │  │ 1. 从知识库查询需求类型                      │  │        ││
│  │  │  │ 2. 从知识库查询实体类型                      │  │        ││
│  │  │  │ 3. 验证类型兼容性                            │  │        ││
│  │  │  │ 4. 降级：LLM验证                             │  │        ││
│  │  │  └─────────────────────────────────────────────┘  │        ││
│  │  └──────────────────────────────────────────────────┘        ││
│  │                              │                                  ││
│  │  ┌──────────────────────────┴────────────────────────┐        ││
│  │  │       DomainKnowledgeLearner (领域学习器)          │        ││
│  │  │  ┌─────────────────────────────────────────────┐  │        ││
│  │  │  │ 1. 从纠正中学习新领域                        │  │        ││
│  │  │  │ 2. 自动提取关键词                            │  │        ││
│  │  │  │ 3. 更新知识库                                │  │        ││
│  │  │  └─────────────────────────────────────────────┘  │        ││
│  │  └──────────────────────────────────────────────────┘        ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## 核心实现

### 1. SemanticGapDetector - 语义检测器

**文件**: `core/knowledge/detector.py`

#### 关键改进

##### 1.1 向量检索替代关键词匹配

```python
def _identify_domain_semantic(self, query: str) -> Tuple[Optional[str], float]:
    """通过语义识别领域"""
    # 使用嵌入模型编码查询
    query_vec = self._embedding_model.encode(query)
    
    # 计算与所有领域的相似度
    for domain, domain_vec in domains.items():
        score = cosine_similarity([query_vec], [domain_vec])[0][0]
        if score > best_score:
            best_score = score
            best_domain = domain
    
    return best_domain, best_score
```

**优势**:
- 不依赖硬编码关键词
- 可识别语义相似但词汇不同的查询
- 支持任意新领域（只需添加向量）

##### 1.2 知识库驱动的领域知识

```python
def _get_domain_embeddings(self) -> Dict[str, np.ndarray]:
    """从知识库获取领域嵌入向量"""
    cursor = conn.execute(
        "SELECT domain, embedding FROM domain_knowledge WHERE embedding IS NOT NULL"
    )
    for domain, embedding_json in cursor.fetchall():
        self._domain_embeddings[domain] = np.array(json.loads(embedding_json))
```

**优势**:
- 领域知识存储在数据库，可动态更新
- 无需修改代码即可添加新领域

##### 1.3 降级策略

```python
def _identify_domain_semantic(self, query: str):
    """语义识别，失败则降级到规则"""
    if not self._embedding_model:
        return self._identify_domain_rule(query)  # 降级
    
    try:
        # 语义识别
        ...
    except:
        return self._identify_domain_rule(query)  # 降级
```

**优势**:
- 嵌入模型不可用时仍能工作
- 保证系统健壮性

---

### 2. KnowledgeBasedValidator - 知识库验证器

**文件**: `core/knowledge/validator.py`

#### 关键改进

##### 2.1 知识库查询替代硬编码

```python
# ❌ 原设计：硬编码
CHIP_TYPES = {
    '电池保护': ['BQ769', 'BQ779', 'SH367'],
    'LED驱动': ['TPS611', 'LM36'],
}

# ✅ 改进后：知识库查询
def _identify_entity_type(self, text: str) -> Optional[str]:
    """从知识库识别实体类型"""
    cursor = conn.execute(
        "SELECT entity_type FROM entity_mapping WHERE ? LIKE '%' || pattern || '%'",
        (text,)
    )
    return cursor.fetchone()[0]
```

**优势**:
- 实体类型存储在数据库
- 可动态添加新产品

##### 2.2 动态添加规则

```python
def add_entity_pattern(self, entity_type: str, pattern: str, confidence: float = 0.9):
    """添加实体模式"""
    conn.execute(
        "INSERT INTO entity_mapping (entity_type, pattern, confidence) VALUES (?, ?, ?)",
        (entity_type, pattern, confidence)
    )
```

**使用示例**:

```python
# 添加新产品（无需修改代码）
validator.add_entity_pattern("电机控制", "DRV8323", 0.9)
validator.add_entity_pattern("传感器", "INA219", 0.9)
validator.add_entity_pattern("传感器", "MPU6050", 0.9)
```

##### 2.3 学习类型关联

```python
def learn_association(self, source_type: str, target_type: str):
    """学习类型关联"""
    # 如果多次出现 source_type → target_type，提高置信度
    conn.execute(
        "UPDATE learned_associations SET occurrences = ?, confidence = ? WHERE ...",
        (occurrences + 1, min(1.0, occurrences / 10))
    )
```

**优势**:
- 从历史数据中学习类型关联
- 自动优化验证规则

---

### 3. DomainKnowledgeLearner - 领域学习器

**文件**: `core/knowledge/learner.py`

#### 关键功能

##### 3.1 从纠正中学习

```python
def learn_from_correction(self, query: str, correct_type: str, wrong_type: str = None):
    """从用户纠正中学习"""
    # 1. 提取关键词
    keywords = self._extract_keywords(query)
    
    # 2. 更新领域知识
    if domain_exists:
        # 合并关键词
        existing_keywords.extend(keywords)
    else:
        # 创建新领域
        insert_new_domain(correct_type, keywords)
```

**使用示例**:

```python
# 用户纠正：推荐错了
learner.learn_from_correction(
    query="推荐一款FOC电机驱动芯片",
    correct_type="电机控制",
    wrong_type="LED驱动"
)

# 系统自动学习：
# - 提取关键词：["FOC", "电机", "驱动", "芯片"]
# - 更新"电机控制"领域的关键词列表
# - 下次遇到类似查询可正确识别
```

##### 3.2 自动关键词提取

```python
def _extract_keywords(self, text: str) -> List[str]:
    """提取关键词（使用jieba分词）"""
    import jieba
    words = [w for w in jieba.cut(text) if len(w) >= 2]
    
    # 过滤停用词
    stop_words = {"推荐", "一款", "需要", "具有", "功能"}
    words = [w for w in words if w not in stop_words]
    
    return words[:10]
```

**优势**:
- 自动提取有意义的词汇
- 无需人工标注

---

## 数据库设计

### 表结构

```sql
-- 领域知识表
CREATE TABLE domain_knowledge (
    domain TEXT PRIMARY KEY,
    keywords TEXT,        -- JSON数组
    description TEXT,
    embedding TEXT,       -- 向量JSON
    created_at TEXT
);

-- 实体类型映射表
CREATE TABLE entity_mapping (
    id INTEGER PRIMARY KEY,
    entity_type TEXT,
    pattern TEXT,
    confidence REAL,
    created_at TEXT
);

-- 类别映射表
CREATE TABLE category_mapping (
    id INTEGER PRIMARY KEY,
    category TEXT,
    keyword TEXT,
    created_at TEXT
);

-- 学习到的关联规则
CREATE TABLE learned_associations (
    id INTEGER PRIMARY KEY,
    source_type TEXT,
    target_type TEXT,
    confidence REAL,
    occurrences INTEGER,
    created_at TEXT
);

-- 学习历史
CREATE TABLE learning_history (
    id INTEGER PRIMARY KEY,
    query TEXT,
    correct_type TEXT,
    wrong_type TEXT,
    keywords_extracted TEXT,
    learned_at TEXT
);
```

---

## 使用示例

### 1. 检测知识缺失

```python
from core.knowledge.detector import semantic_detector

# 检测知识缺失
has_gap, reason, issues = semantic_detector.detect_knowledge_gap(
    user_query="推荐一款FOC电机驱动芯片",
    response="推荐使用TPS61182...",
    confidence=0.6
)

print(has_gap)  # True
print(reason)   # "领域知识不足: 电机控制"
```

### 2. 验证推荐

```python
from core.knowledge.validator import knowledge_validator

# 验证推荐
result = knowledge_validator.validate_recommendation(
    user_query="推荐一款FOC电机驱动芯片",
    recommendation="推荐使用TPS61182..."
)

print(result['is_valid'])  # False
print(result['issues'])    # ["需求 ['电机控制'] 与推荐 'LED驱动' 不匹配"]
```

### 3. 学习新领域

```python
from core.knowledge.learner import domain_learner

# 从纠正中学习
domain_learner.learn_from_correction(
    query="推荐一款FOC电机驱动芯片",
    correct_type="电机控制",
    wrong_type="LED驱动"
)

# 添加新领域
semantic_detector.learn_domain(
    domain="电机控制",
    keywords=["电机", "FOC", "BLDC", "步进电机", "伺服电机"],
    description="电机驱动与控制芯片"
)

# 添加新产品
knowledge_validator.add_entity_pattern("电机控制", "DRV8323", 0.9)
knowledge_validator.add_entity_pattern("电机控制", "DRV8305", 0.9)
```

### 4. 动态扩展

```python
# 添加全新的领域（无需修改代码）
semantic_detector.learn_domain(
    domain="传感器",
    keywords=["传感器", "IMU", "加速度计", "陀螺仪", "温度传感器"],
    description="各类传感器芯片"
)

knowledge_validator.add_category_keyword("传感器", "IMU")
knowledge_validator.add_category_keyword("传感器", "加速度计")

knowledge_validator.add_entity_pattern("传感器", "MPU6050", 0.9)
knowledge_validator.add_entity_pattern("传感器", "INA219", 0.9)

# 立即生效，无需重启
```

---

## 对比总结

| 维度 | 原设计 | 重构后 |
|------|--------|--------|
| **领域识别** | ❌ 硬编码关键词 | ✅ 向量检索 + 知识库 |
| **实体识别** | ❌ 硬编码芯片型号 | ✅ 知识库映射表 |
| **扩展性** | ❌ 需要改代码 | ✅ API动态添加 |
| **学习能力** | ❌ 无法学习 | ✅ 从纠正中学习 |
| **适用范围** | ❌ 仅预定义领域 | ✅ 任意领域 |
| **维护成本** | ❌ 修改代码+重新部署 | ✅ API调用即可 |

---

## 总结

### ✅ 核心改进

1. **语义驱动** - 使用向量检索替代关键词匹配
2. **知识库驱动** - 所有规则存储在数据库，可动态更新
3. **学习能力** - 从用户纠正中自动学习新领域
4. **可扩展** - 新领域无需改代码，通过API添加

### 🎯 设计理念

**从"写死的专家系统"到"能学习的系统"**

- ❌ 原设计：遇到新领域就失效
- ✅ 重构后：可扩展、可学习、自适应

### 📊 适用性

- **原设计**: 仅适用于预定义的芯片选型场景
- **重构后**: 适用于任意领域（芯片、传感器、电机、软件、服务等）

### 📁 新增文件

```
core/knowledge/detector.py      # 语义检测器
core/knowledge/validator.py     # 知识库验证器
core/knowledge/learner.py       # 领域学习器
core/knowledge/__init__.py      # 模块入口
```

感谢你的批评，这次重构从根本上解决了硬编码问题，使系统具备了真正的学习与进化能力！