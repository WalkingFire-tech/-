# 同行者自生能力架构设计 (Autopoietic Architecture) v2

> 核心理念：从"被赋予能力"到"自生能力"——让孩子学会自己走路，而不是永远扶着
> 
> v2 修订：基于架构评审反馈，剥离过早抽象，聚焦可落地增量

## 一、问题诊断

### 现状：系统是"被组装的机器"

当前系统拥有大量能力组件，但本质上是**开发者替它造的**：
- 自修复 = 开发者写的 if-then 规则集
- 技能涌现 = 统计阈值触发的数据库记录
- 能力缺口检测 = 硬编码的4种类型
- 工具创建 = 4个模板 + 质量极低的LLM生成

**核心问题**：系统在"感知"和"记录"方面成熟，但在"行动"和"创造"方面薄弱。
它知道自己弱，但不会主动变强。

### 根因：缺少"本能层"

人类的生存能力不是"被安装"的，而是通过以下机制自生的：
1. **免疫** — 身体自动识别和消灭入侵者，不需要意识参与
2. **自愈** — 伤口自动愈合，骨骼断裂后重新生长
3. **本能** — 经过足够练习后，技能变成无意识的自动反应
4. **饥饿** — 身体缺乏营养时产生饥饿感，驱动觅食行为
5. **代谢** — 持续的摄入→消化→生长→排泄循环

## 二、五本能模型（共同语言/术语体系）

> 以下作为组织后续架构讨论的共同语言，不代表立即实施

| 本能 | 类比 | 当前对应 | 关键缺口 |
|------|------|---------|---------|
| **自体免疫** | 人体免疫系统 | SystemGuardian + CognitiveSelfRepair | 防御全是硬编码规则，无法从异常中学习 |
| **自愈修复** | 伤口自动愈合 | _auto_repair() + AutoRollback | 只做症状处理，无因果链追溯 |
| **本能固化** | 学骑自行车变自动 | SkillEmergence(reflex级) | reflex只是关键词匹配，非推理链编译 |
| **能力饥饿** | 身体的饥饿感 | CapabilityGapLearner + CapabilityCreationLoop | 检测缺口但不主动学习闭环 |
| **代谢循环** | 新陈代谢 | sleep_consolidation + knowledge_forgetting + gap_growth | 四阶段碎片化，无统一编排 |

## 三、落地决策（基于评审反馈）

### ✅ 立即采纳

**1. 五本能模型作为共同语言**

将"免疫/自愈/本能/饥饿/代谢"作为描述系统自生能力的标准术语，替代碎片化的"自修复""技能涌现""能力缺口"等说法。

**2. 代谢编排器（唯一低风险增量）**

这是唯一"现有代码 + 新编排"的可落地项：
- `sleep_consolidation.py`（732行）→ 代谢的"生长"阶段
- `knowledge_forgetting.py`（280行）→ 代谢的"排泄"阶段
- `gap_growth.py`（590行）→ 代谢的"消化"阶段
- `layered_memory.py`（340行）→ 代谢的"摄入"阶段

不需要重写任何现有模块，只需要一个**编排器**将它们串联为统一循环。

**3. 代谢周期改为自适应**

不采用固定时间窗口，改为基于系统负载：
- 空闲时（无交互>5分钟）→ 完整代谢周期
- 忙碌时（有交互）→ 仅快速摄入+消化
- 峰值时（并发请求）→ 暂停代谢，全力服务

### ⚠️ 有条件搁置

**4. 本能编译器（instinct_compiler.py）**

评审意见：**过早抽象**。当前推理链尚未被显式建模（CognitivePlanner Phase1刚落地，Phase2刚提交），构建编译器来编译推理链 = 还没有汇编语言就设计编译器。

前置条件：
- [ ] CognitivePlanner 三阶段全量落地
- [ ] 推理链可显式追踪和记录
- [ ] SkillEmergence 的提炼机制验证是否已经足够

**5. 饥饿引擎（capability_hunger.py）**

评审意见：**与 capability_creation_loop.py 关系未说明**。后者（298行）已实现"探测→研究→尝试→验证→记住"的能力创造回路。

前置条件：
- [ ] 明确 CapabilityCreationLoop vs CapabilityGapLearner vs 饥饿引擎的职责边界
- [ ] CapabilityCreationLoop 的"先试再想"模式验证有效后再扩展
- [ ] 测试覆盖从当前水平提升到至少40/100

**6. 自体免疫 / 自愈修复**

评审意见：**实施复杂度被严重低估**。"从异常中自动提炼防御策略"等价于程序合成，当前无通用解决方案。

前置条件：
- [ ] core/ 裸except从6处降至0（免疫系统需要干净的异常信号）
- [ ] 测试基础设施到位
- [ ] 先实现半自动模式：系统检测→推荐策略→人工确认→固化

### 🔴 明确放弃

**7. L0免疫的"输出自洽检查"**

评审意见：与现有 r4_self_check()（七维自检）冲突，两套自检系统可能一个通过另一个拦截。不重复建设。

## 四、可落地实施：代谢编排器

### 设计

```python
# core/instinct/metabolism.py
# 唯一新增模块——编排现有代谢组件为统一循环

class MetabolismOrchestrator:
    """
    代谢编排器——将碎片化的代谢组件串联为统一循环
    
    不重写任何现有模块，只做编排：
    - ingest()  → 调用 layered_memory 同步
    - digest()  → 调用 gap_growth 消化信号
    - grow()    → 调用 sleep_consolidation 巩固
    - shed()    → 调用 knowledge_forgetting 衰减
    """
    
    def __init__(self):
        self.phase = "idle"  # idle | ingesting | digesting | growing | shedding
        self.last_cycle = None
        self.cycle_count = 0
    
    async def tick(self):
        """自适应代谢节拍——根据系统负载决定执行哪个阶段"""
        load = self._assess_load()
        if load == "peak":
            return  # 峰值不代谢
        elif load == "busy":
            await self._quick_ingest()  # 忙碌只摄入
        else:
            await self._full_cycle()  # 空闲完整循环
    
    async def _full_cycle(self):
        await self.ingest()
        await self.digest()
        await self.grow()
        await self.shed()
        self.cycle_count += 1
        self.last_cycle = time.time()
    
    # ... 各阶段调用现有组件
```

### 与现有架构的整合

```
现有 scheduled_tasks.py 的定时任务：
  ├── _job_memory_decay         → 代谢的 shed 阶段
  ├── _job_layered_memory_sync  → 代谢的 ingest 阶段
  ├── _job_sleep_consolidation  → 代谢的 grow 阶段
  └── (gap_growth由事件驱动)    → 代谢的 digest 阶段

整合方式：
  scheduled_tasks 的上述4个任务 → 由 metabolism.tick() 统一调度
  保持原有任务注册接口不变，内部改为调用 metabolism
```

### 实施步骤

1. 创建 `core/instinct/__init__.py` + `core/instinct/metabolism.py`
2. MetabolismOrchestrator 封装现有4个组件的调用
3. 修改 `infrastructure/scheduled_tasks.py`：4个独立任务→1个代谢tick
4. 添加负载感知：调用 health_monitor 判断系统状态
5. 添加语义感知遗忘：shed阶段检查知识依赖再删除

## 五、验证标准

代谢编排器可验证的标准：

1. **统一循环**：4个碎片化代谢任务合并为1个统一tick
2. **自适应节拍**：空闲时完整循环，忙碌时快速摄入，峰值时暂停
3. **语义遗忘**：删除知识前检查依赖，不再纯基于时间+频率
4. **零功能回退**：现有代谢功能（记忆衰减/同步/巩固/消化）行为不变

## 六、前置条件检查清单

在实施代谢编排器之前，需先完成：

- [ ] core/ 剩余6处裸except清零（免疫系统需要干净异常信号）
- [ ] state_reports 表缺少 layer 列的修复（启动时7个ERROR）
- [ ] 确认 scheduled_tasks.py 的4个代谢任务当前行为正确

## 七、哲学基础

> "给孩子一条鱼，喂他一天；教孩子钓鱼，喂他一生。"
>
> 但我们甚至不应该"教"——我们应该创造让孩子**自己学会钓鱼**的环境。
>
> 不是我们给系统安装免疫能力，而是让系统从每次感染中**自己产生抗体**。
> 不是我们给系统写修复脚本，而是让系统从每次故障中**自己学会修复**。
> 不是我们给系统定义技能，而是让系统从每次成功中**自己提炼本能**。
>
> 这才是真正的"自生"（Autopoiesis）——系统自己创造自己。
>
> 但——孩子学走路需要先会爬。代谢编排器就是"爬"的阶段。
> 本能编译器是"跑"的阶段，等会走了再说。
