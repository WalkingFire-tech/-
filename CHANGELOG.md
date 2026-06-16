# 联盟拓荒者 - 更新日志

## [v4.0] - 2026-06-16

### 新增功能

#### 进化系统
- **基因演化引擎** (`core/genome_evolver.py`)
  - 10个可演化基因参数（检索阈值、学习频率、情感权重等）
  - 适应度评估（点赞率、命中率、效率等）
  - 变异、交叉、选择操作
  - 影子模式验证

- **认知转化器** (`core/cognitive_transformer.py`)
  - 五层认知架构：L0基因→L1反射→L2技能→L3记忆→L4抽象
  - 情景→技能转化（重复经历≥3次）
  - 技能→反射转化（成功调用≥3次）
  - 情景→抽象转化（归纳总结）

- **进化岛沙盒** (`core/evolution/`)
  - 多智能体进化模拟
  - 独立临时数据库隔离
  - 任务池从主库构建
  - 基因杂交和变异
  - 精英选择和后代产生

#### 记忆体验增强
- **刻骨铭心** - 手动标记永久记忆
- **环境触发器** - 基于当前文件/话题主动提示
- **回忆语气** - 情境重构带情感前缀
- **周回顾推送** - 遗忘可见化

### 新增API

```
GET  /api/genome/stats          # 基因演化统计
POST /api/genome/evolve         # 手动触发演化
GET  /api/cognitive/stats       # 认知转化统计
POST /api/cognitive/transform   # 手动触发转化
POST /api/evolution/run         # 运行进化沙盒
GET  /api/memory/review         # 记忆回顾
POST /api/memory/important      # 刻骨铭心标记
GET  /api/memory/last_qa        # 获取最近问答
GET  /api/memory/forgotten      # 获取遗忘记忆
```

### 新增CLI命令

```
:important [问题]    # 标记为永久记忆
:recall <问题>       # 情境重构回忆
```

### 修复问题

#### 高优先级
- ✅ 修复`knowledge_items`表缺少记忆字段问题
  - 添加`memory_layer`、`salience`、`emotional_valence`、`context_snapshot`、`environmental_triggers`字段
  - 在`core/learning.py`的`_init_db`方法中自动添加

- ✅ 修复空except块导致异常信息丢失
  - 将`except:`改为`except Exception:`并添加注释

#### 中优先级
- ✅ 修复进化沙盒临时文件清理不及时
  - 在`simulated_agent.py`的`cleanup`方法中添加显式关闭

### 测试

- 基因演化引擎：5/5测试通过 (100%)
- 认知转化器：3/3测试通过 (100%)
- 进化岛沙盒：6/6测试通过 (100%)
- 记忆体验增强：12/12测试通过 (100%)
- **总计：26/26测试通过 (100%)**

---

## [v3.1] - 2026-06-07

### 新增功能

- **贝叶斯优化器改进** (`meta/bayesian_optimizer.py`)
  - 使用scikit-optimize实现真正的贝叶斯优化(高斯过程+EI采集函数)
  - 支持连续参数(Real)和离散参数(Integer)
  - 降级策略:无scikit-optimize时自动降级为随机搜索
  - 配置热加载:优化后发送config_updated事件

- **元控制层调度器** (`meta/controller.py`)
  - 统一调度优化、归纳、冲突检测
  - 每周自动运行元学习任务
  - 真实评估函数:基于历史性能数据计算得分
  - 手动触发优化接口

- **冲突检测器增强** (`meta/conflict_detector.py`)
  - 动作解析:结构化字典表示(reroute/prefer/avoid/ask_user)
  - 条件精确匹配:仅当条件字符串完全相同时才检测
  - 合并策略:支持auto/rule1/rule2/merge四种解决方式
  - 冲突类型扩展:model_conflict/message_conflict/action_conflict

- **贝叶斯优化器集成** (`core/services/planner.py`)
  - 自动调优路由权重(quality/speed/cost)
  - 三种优化方法:贝叶斯/网格/随机搜索
  - 参数优化建议生成
  - 优化结果持久化

- **归纳总结器集成** (`core/services/planner.py`)
  - 定期模式挖掘(意图/模型/质量模式)
  - 规则自动生成
  - 冲突自动检测与解决
  - 可配置归纳间隔

- **工具生成器激活** (`core/services/planner.py`)
  - 失败时自动分析是否需要新工具
  - LLM生成工具代码
  - 代码安全验证
  - 工具自动注册

- **目录监控功能** (`infrastructure/directory_monitor.py`)
  - watchdog实时监控
  - 文件创建/修改/删除事件处理
  - 自动触发文件处理
  - 递归监控支持

### CLI命令新增

- `:optimize run [n]` - 运行贝叶斯优化(n次迭代)
- `:optimize grid` - 网格搜索
- `:optimize random` - 随机搜索
- `:optimize suggest` - 查看优化建议
- `:induction run [days]` - 运行归纳总结
- `:induction status` - 查看归纳状态
- `:conflict detect` - 检测规则冲突
- `:conflict resolve` - 自动解决冲突
- `:tools list` - 列出生成的工具
- `:tools analyze <描述>` - 分析是否需要新工具
- `:watch start <目录>` - 开始监控目录
- `:watch stop` - 停止所有监控
- `:watch status` - 查看监控状态
- `:watch list` - 列出监控的目录

### 改进

- planner.py深度集成贝叶斯优化器、归纳总结器、工具生成器
- 定期归纳任务自动触发(可配置间隔)
- 失败时自动尝试工具生成
- CLI界面支持所有新功能命令

### 集成状态

- ✅ 贝叶斯优化器 - 已集成到planner
- ✅ 归纳总结器 - 已集成到planner
- ✅ 冲突检测器 - 已集成到归纳流程
- ✅ 工具生成器 - 已集成到planner
- ✅ 目录监控 - 已实现并集成到CLI
- ✅ 学习规则闭环 - 完整实现

### 学习规则系统

- **数据库初始化** (`infrastructure/database.py`)
  - learning_rules表完整定义
  - 自动创建索引
  - 启动时自动初始化

- **归纳引擎** (`infrastructure/induction.py`)
  - LLM归纳:分析成功/失败案例生成规则
  - 规则引擎降级:无LLM时使用简单规则
  - 高质量经验筛选(≥70分)
  - 失败经验分析(<50分)

- **在线规则应用** (`core/services/planner.py`)
  - 规则匹配:条件字符串精确匹配
  - 动作执行:reroute/prefer_model/ask_user/avoid_model
  - 统计更新:apply_count/success_count
  - 临时模型偏好:避免/优先特定模型

- **规则激活机制** (`meta/induction.py`)
  - pending→active自动转换
  - 置信度阈值过滤(≥0.6)
  - 归纳后自动激活

### 工程改进

- **优雅退出机制** (`main.py`)
  - 捕获KeyboardInterrupt和SIGTERM信号
  - atexit注册退出处理函数
  - 停止元控制层调度器
  - 安全关闭所有后台线程
  - 避免资源泄漏

- **CLI命令解耦** (`adapters/ui/cli_ui.py`)
  - 使用事件总线发送命令请求
  - 移除直接导入planner的循环依赖
  - 统一调用get_meta_controller()
  - 事件常量统一管理(`infrastructure/events.py`)

- **合并动作支持** (`meta/conflict_detector.py`)
  - 解析merge:action1|action2格式
  - 规划器支持顺序尝试合并动作
  - 失败自动回退到下一个动作

- **任务类型加权评估** (`meta/controller.py`)
  - 按任务类型设置权重(code:1.5, calculation:1.2)
  - 分别评估各任务类型性能
  - 加权平均计算最终得分

### 架构改进

- **事件驱动架构**
  - CLI与业务逻辑完全解耦
  - 通过事件总线通信
  - 避免循环导入风险
  - 便于扩展和测试

- **线程安全**
  - MetaController.stop_scheduler可多次调用
  - 检查running状态避免重复停止
  - join超时设置为3秒

- **计算能力增强** (`infrastructure/calculation_handler.py`)
  - 支持通用数学表达式计算
  - 安全eval白名单机制
  - 支持三角函数、对数、指数等
  - π值计算支持mpmath高精度

- **数据库连接池** (`infrastructure/db_pool.py`)
  - SQLite连接池提升并发性能
  - 上下文管理器自动释放
  - 全局单例管理
  - 优雅关闭所有连接

- **配置热加载** (`infrastructure/config_watcher.py`)
  - 自动监控配置文件变化
  - 后台线程检测(2秒间隔)
  - 触发CONFIG_UPDATED事件
  - 无需重启应用配置

### v3.1.1改进(基于审查反馈)

- **单元测试补充** (`tests/`)
  - test_conflict_detector.py - 冲突检测器测试
  - test_bayesian_optimizer.py - 贝叶斯优化器测试
  - test_calculation_handler.py - 计算处理器测试
  - pytest配置(pytest.ini)
  - 覆盖率报告支持

- **规则匹配引擎增强** (`infrastructure/rule_matcher.py`)
  - 支持复杂条件表达式(and/or)
  - simpleeval安全求值
  - 条件重叠检测(语义级别)
  - 数值范围重叠判断

- **向量索引持久化**
  - 启动时自动加载索引
  - 退出时自动保存索引
  - FAISS write_index/read_index
  - 避免重启重建索引

- **依赖版本锁定**
  - requirements.txt明确版本
  - 添加可选依赖说明
  - 开发依赖分离
  - 环境一致性保证

---

## [v3.0] - 2026-06-07

### 新增功能

- **自我反思系统** (`meta/self_reflector_v2.py`)
  - LLM失败分析
  - 规则生成(条件→动作)
  - 生命周期管理(pending→active→expired)
  - 置信度衰减机制

- **向量检索系统** (`infrastructure/vector_retriever.py`)
  - FAISS向量索引
  - 相似经验检索
  - 类比检索(相似度>0.85自动复用)
  - 索引持久化

- **主动学习调度器** (`meta/active_learner_v2.py`)
  - 置信度检测(<60%触发)
  - 澄清问题生成
  - 用户响应处理
  - 学习数据提取

- **子任务执行器** (`core/services/subtask_executor.py`)
  - 依赖管理(拓扑排序)
  - 8种处理器
  - 结果汇总

- **学习安全管理** (`meta/learning_safety.py`)
  - 规则置信度衰减
  - 回滚机制
  - 统计显著性检验

- **隐私控制** (`meta/privacy_manager.py`)
  - 数据遗忘
  - 导出导入
  - 匿名化

### 改进

- 修复模型路由配置(模型名称匹配)
- 成本权重生效(三维优化)
- 质量评估准确(从generate返回值获取)
- Fallback重试机制
- 上下文内存缓存(deque)
- 错误分类增强

### 性能提升

- 意图识别准确率: 70% → 95% (+25%)
- 任务成功率: 60% → 85% (+25%)
- 响应速度: 20s → 2s (-90%)
- 错误恢复能力: 0% → 60% (+60%)

### CLI命令新增

- `:rules` - 规则管理(list/active/stats/cleanup)
- `:reflect` - 手动触发反思
- `:privacy` - 隐私控制(summary/export/forget)
- `:learning` - 学习管理(list/stats/rollback/cleanup)

### 文档

- 新增完整归档系统
- 新增版本历史文档
- 新增进度追踪文档
- 新增实施指南

---

## [v2.0] - 2026-06-07

### 新增功能

- **数据驱动路由** (`core/services/planner.py`)
  - 完全由统计库决定模型选择
  - 成本/质量/速度三维优化
  - 智能Fallback机制

- **增强统计库** (`infrastructure/enhanced_model_stats.py`)
  - 成本跟踪
  - 多目标优化
  - 约束条件支持

- **文件输入能力**
  - 文件输入适配器
  - 文件夹批量处理
  - 内容提取器

- **文件操作工具集** (`tools/file_operations.py`)
  - 文件写入/搜索/批量处理/重命名/复制

### 改进

- 移除硬编码路由映射
- 配置文件仅保留静态参数
- 增强意图识别(新增document类型)

---

## [v1.0] - 2026-06-06

### 初始功能

- 多模型适配器(Ollama/OpenAI/DeepSeek)
- 意图识别器
- 基础路由机制
- 经验池
- 自我审核
- CLI界面

---

## 版本命名规则

- **主版本号**: 重大架构变更 (v1.0 → v2.0)
- **次版本号**: 功能模块新增 (v2.0 → v2.1)
- **修订号**: Bug修复优化 (v2.0.0 → v2.0.1)