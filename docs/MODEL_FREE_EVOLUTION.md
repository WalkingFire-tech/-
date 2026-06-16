# 无模型进化模式使用指南

## 概述

无模型进化模式是一个**完全不需要LLM**的自我优化系统，仅通过以下方式持续进化：

- 📊 **统计分析** - 基于历史数据分析模式
- 📏 **规则引擎** - 挖掘经验生成规则
- 🔍 **外部搜索** - DuckDuckGo获取知识（无需API）
- 🧬 **基因演化** - 遗传算法优化参数
- 🧠 **认知转化** - 经验→技能→反射→抽象

## 快速启动

### 方法1: 使用启动脚本（推荐）

```bash
start_evolution.bat
```

### 方法2: Python命令

```bash
python -c "from core.model_free_evolution import run_model_free_evolution; run_model_free_evolution()"
```

### 方法3: API方式

```bash
# 启动后端
python backend/main.py

# 启动进化（另一个终端）
curl -X POST http://localhost:8000/api/evolution/start
```

## 进化周期

| 任务 | 周期 | 说明 |
|------|------|------|
| 自动学习 | 30分钟 | 通过DuckDuckGo搜索获取知识 |
| 基因演化 | 2小时 | 基于适应度优化系统参数 |
| 认知转化 | 6小时 | 经验→技能→反射→抽象 |
| 规则生成 | 1小时 | 挖掘模式生成学习规则 |
| 知识清理 | 4小时 | 质量衰减，删除低质量知识 |
| 进化沙盒 | 12小时 | 多智能体竞争进化 |

## 学习目标配置

编辑 `config/learning_targets.yaml`：

```yaml
learning_targets:
  topics:
    - name: "Python异步编程"
      keywords: ["asyncio", "async await", "coroutine"]
      priority: 5
      min_knowledge: 10
      status: "pending"
    
    - name: "FastAPI框架"
      keywords: ["FastAPI", "依赖注入", "路径操作"]
      priority: 4
      min_knowledge: 15
      status: "pending"
  
  skills:
    - name: "代码生成"
      indicators: ["语法正确率", "逻辑完整性"]
      priority: 5
      min_success_rate: 0.85
      status: "pending"
```

## API端点

### 查看进化状态

```bash
GET /api/evolution/status
```

响应：
```json
{
  "success": true,
  "status": {
    "running": true,
    "knowledge_gained": 150,
    "rules_generated": 25,
    "genes_evolved": 10,
    "skills_formed": 8
  }
}
```

### 启动/停止进化

```bash
POST /api/evolution/start
POST /api/evolution/stop
```

### 查看学习目标

```bash
GET /api/learning/targets
```

响应：
```json
{
  "success": true,
  "status": {
    "topics": [
      {
        "name": "Python异步编程",
        "progress": 12,
        "target": 10,
        "completion": "120.0%",
        "status": "completed"
      }
    ],
    "pending_count": 3
  }
}
```

### 手动触发学习

```bash
POST /api/learning/targets/trigger
{
  "target_name": "FastAPI框架",
  "target_type": "topic"
}
```

## 工作原理

### 1. 自动学习（无需LLM）

```
学习目标 → 关键词提取 → DuckDuckGo搜索 → 知识存储
```

示例：
```python
目标: "Python异步编程"
关键词: ["asyncio", "async await", "coroutine"]

→ 搜索 "Python异步编程 asyncio"
→ 获取搜索结果
→ 存储为知识条目
```

### 2. 基因演化（基于统计）

```
历史数据 → 适应度评估 → 变异/交叉 → 选择最优 → 应用参数
```

适应度计算：
```
fitness = 点赞率×0.3 + 命中率×0.2 + 效率×0.2 + ...
```

### 3. 认知转化（模式固化）

```
经验（≥3次重复）→ 技能（≥3次成功）→ 反射（自动触发）→ 抽象（跨情境）
```

### 4. 规则生成（模式挖掘）

```
经验池 → 模式挖掘 → 规则生成 → 冲突检测 → 应用规则
```

## 监控进化过程

### 查看日志

```bash
# 实时查看
tail -f logs/evolution.log

# 查看统计
python -c "
from core.model_free_evolution import model_free_evolution
print(model_free_evolution.get_status())
"
```

### 查看知识库

```bash
sqlite3 data/knowledge_store.db "SELECT COUNT(*) FROM knowledge_items"
```

### 查看基因组

```bash
sqlite3 data/genome.db "SELECT * FROM genomes ORDER BY fitness DESC LIMIT 5"
```

## 性能指标

运行24小时后预期效果：

| 指标 | 预期值 |
|------|--------|
| 知识获取 | 200-500条 |
| 规则生成 | 30-50条 |
| 基因演化 | 10-20代 |
| 技能形成 | 5-10个 |
| 适应度提升 | 10-30% |

## 优势

1. **零依赖** - 不需要LLM、API密钥
2. **低成本** - 仅CPU计算，无GPU需求
3. **持续运行** - 7×24小时无人值守
4. **自我优化** - 自动调整参数、生成规则
5. **可解释** - 所有决策基于统计数据

## 限制

1. **无对话能力** - 不能直接与用户对话
2. **知识质量** - 外部搜索知识需人工验证
3. **进化速度** - 比有模型模式慢
4. **适用场景** - 适合后台知识积累和参数优化

## 与有模型模式对比

| 特性 | 无模型模式 | 有模型模式 |
|------|-----------|-----------|
| LLM依赖 | ❌ 不需要 | ✅ 需要 |
| 对话能力 | ❌ 无 | ✅ 有 |
| 知识获取 | 外部搜索 | LLM生成+搜索 |
| 进化速度 | 慢 | 快 |
| 成本 | 低 | 高 |
| 适用场景 | 后台优化 | 交互式应用 |

## 最佳实践

1. **混合使用**
   - 后台运行无模型进化
   - 前台使用有模型对话
   - 定期同步知识库

2. **监控调优**
   - 每周检查学习目标进度
   - 调整优先级和阈值
   - 清理低质量知识

3. **知识验证**
   - 定期审查外部搜索知识
   - 标记高质量知识为"important"
   - 删除错误或过时知识

## 故障排查

### 进化不启动

```bash
# 检查依赖
pip install duckduckgo-search schedule

# 检查数据库
sqlite3 data/knowledge_store.db "SELECT COUNT(*) FROM knowledge_items"
```

### 知识不增长

```bash
# 检查网络
curl -s "https://duckduckgo.com/?q=test"

# 检查学习目标
python -c "
from core.auto_learning_trigger import auto_learning_trigger
print(auto_learning_trigger._get_pending_targets())
"
```

### 适应度不提升

```bash
# 检查历史数据
sqlite3 data/knowledge_store.db "SELECT AVG(quality_score) FROM knowledge_items"

# 手动触发演化
curl -X POST http://localhost:8000/api/genome/evolve
```

## 总结

无模型进化模式是一个**纯数据驱动**的自我优化系统，适合：

- ✅ 后台知识积累
- ✅ 参数自动调优
- ✅ 规则自动生成
- ✅ 低成本持续运行

启动命令：
```bash
start_evolution.bat
```

或：
```bash
python -c "from core.model_free_evolution import run_model_free_evolution; run_model_free_evolution()"
```