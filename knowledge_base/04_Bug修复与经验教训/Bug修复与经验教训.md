# Bug修复与经验教训

> 来源：系统开发过程中的实际修复记录，2026年6月

## 一、前端-后端接口类

### 1. 活跃规则/待激活显示为0
- **现象**：前端显示活跃规则=0，待激活=0
- **根因**：`main_fast.py`的`/api/stats`查询表名是`rules`，但数据库实际表名是`learning_rules`；且只返回总数，没有按status分别统计
- **修复**：表名改为`learning_rules`，新增`active_rules`和`pending_rules`字段
- **教训**：简化版后端（main_fast）与完整版（main）的数据库表名可能不同，需要核对

### 2. 知识水平/学习活力/最近学习无数据
- **现象**：右侧面板三个区域全部无数据
- **根因**：`main_fast.py`缺少9个API端点（knowledge/health, optimize, induction, folder等）
- **修复**：补全所有前端调用的API端点
- **教训**：简化版后端必须覆盖前端所有API调用，否则前端静默失败

### 3. 八卦图谱按钮无效
- **现象**：点击"八卦图谱"打开404页面
- **根因**：`/bagua-knowledge`页面只在`main.py`中注册，`main_fast.py`没有
- **修复**：改为弹窗展示真谛/技能/熵值数据
- **教训**：功能缺失时，用已有数据做降级展示优于跳转404

### 4. 重复端点覆盖
- **现象**：新加的`/api/knowledge/health`返回旧数据
- **根因**：旧的占位端点（只返回`{"status":"ok"}`）和新端点同名，FastAPI用先注册的
- **修复**：删除旧的占位端点
- **教训**：添加新端点前先检查是否有同名旧端点

## 二、推理与验证类

### 5. 科学免责硬编码NASA
- **现象**：生物学问题推荐了NASA
- **根因**：免责声明参考来源硬编码为NASA
- **修复**：领域感知免责——生物→Nature/Science，天文→NASA/ESA，物理→物理学会
- **教训**：任何领域相关的逻辑都不能硬编码单一来源

### 6. 领域感知选错领域
- **现象**："天空为什么是蓝色"推荐了化学参考
- **根因**：回复中提到"氮气和氧气分子"触发了化学关键词，化学在字典中先于物理被匹配
- **修复**：改为匹配关键词数量最多的领域；增加"光""天空""蓝色"等物理关键词
- **教训**：关键词匹配应该用"最多匹配"而非"最先匹配"

### 7. 矛盾检测误判"是vs不是"
- **现象**："太阳光是白色的"和"当我们看天空（不是太阳）时"被判为矛盾
- **根因**：只检测否定词对（"是"vs"不是"），没检查是否讨论同一主语
- **修复**：增加主语一致性检查——提取主语片段，只有主语重叠才判矛盾
- **教训**：矛盾检测必须考虑语义范围，不能只看词汇

### 8. 悖论问题触发科学免责
- **现象**："鸡和蛋"问题触发了生物学免责声明
- **根因**：悖论问题包含"鸡""蛋"等生物关键词，被误判为科学事实问题
- **修复**：悖论关键词检测→跳过科学免责→跳过推理链断裂检查→提前返回"定义边界问题"
- **教训**：不同问题类型需要不同的处理管道，不能一刀切

### 9. 质疑意图识别失败
- **现象**："你确定吗"被识别为complex_query而非challenge
- **根因**：超短句逻辑只检查greeting和confirmation；challenge匹配用精确匹配（"你确定吗"≠"确定吗"）
- **修复**：超短句增加challenge匹配；challenge匹配从精确匹配改为包含匹配
- **教训**：意图识别的匹配策略应该宽松而非严格

## 三、性能与输出类

### 10. 输出被截断
- **现象**：代码生成回复在"关键设计说明"后截断
- **根因**：DeepSeek/OpenAI的`max_tokens`硬编码为1000，约1000-1500字就截断
- **修复**：`max_tokens`从1000改为4096
- **教训**：代码生成类问题通常需要2000+字，max_tokens必须足够大

### 11. DuckDuckGo超时浪费15秒
- **现象**：web事实校验3次超时，每次5秒，共浪费15秒
- **根因**：超时5秒太长，失败后继续重试
- **修复**：超时5s→2s，最多检查2个事实，首次失败立即break
- **教训**：外部API调用必须快速失败，不能阻塞主流程

### 12. 输入末尾斜杠导致问题
- **现象**：输入"你觉得如何才算是真正拥有了自动学习能力/"末尾的/被当作问题的一部分
- **根因**：没有清理输入
- **修复**：`chat_stream`入口自动strip并移除末尾的`/\|`
- **教训**：永远不要信任用户输入的格式

## 四、数据与统计类

### 13. 认知熵值0.59误判为critical
- **现象**：系统启动就报"认知熵值异常: 0.59 — 建议立即回滚"
- **根因**：矛盾率把"多策略部分失败"也算进去了（38/40=0.95），但5条路径中2条失败3条成功是正常的
- **修复**：矛盾率只计"全部失败"（排除多策略部分失败）；真谛冲突率权重0.3→0.15
- **教训**：监控指标的"失败"定义必须精确，不能把正常的部分失败算进去

---

## 五、v3.2.0 系统性修复（2026年6月）

### 14. 反馈信号断裂（P0致命）
- **现象**：经验池2769条success=0、188条success=NULL、0条success=1，整个学习闭环失效
- **根因**：`_save_to_experience_pool()`只写入5个字段，不包含success字段；`chat_handler.py`和`chat_stream.py`各有独立的实现，都缺少success
- **修复**：两个文件中的`_save_to_experience_pool()`增加success/intent_type/quality_score/duration参数，所有调用点传入正确值
- **教训**：学习闭环的"反馈信号"是最关键的数据，必须从第一天就验证

### 15. 双轨问题——核心模块从未被加载（P0致命）
- **现象**：大量核心模块（认知循环、编排器、反思管道、自动学习进化、七大学习机制等）"存在但休眠"
- **根因**：系统有main.py(4369行，集成了全部组件)和main_fast.py(882行，简化版)两个后端入口，实际运行的是main_fast.py
- **修复**：在main_fast.py中逐步集成最关键的核心能力（反思管道、自动学习进化、认知代谢）；认知代谢和压力测试已通过task_queue正确集成
- **教训**：简化版入口必须包含核心闭环，否则系统"看起来能运行"但"实际上没有学习能力"

### 16. 本质推理器"推理链断裂"误报
- **现象**：对天文/物理事实问题报"推理链断裂：无法从物理基本原理直接追溯"
- **根因**：`_first_principles_reasoning`中，`_get_known_truths`只有极少数硬编码真理，大部分科学事实无法匹配；未匹配的事实被标记为traceable=False，触发"推理链断裂"
- **修复**：引入traceable=None（"已知真理库未覆盖"），与traceable=False（"确实断裂"）区分；_check_consistency只计traceable=False
- **教训**："不知道"和"知道有问题"是两种完全不同的状态，不能混为一谈

### 17. infrastructure/__init__.py导入阻塞
- **现象**：`from infrastructure.reflection_pipeline import ...`超时
- **根因**：`__init__.py`在导入时加载所有子模块（config_manager, experience_pool, reflection_pipeline, quick_reflex），其中某些模块初始化耗时很长
- **修复**：改为`__getattr__`延迟导入，只在真正使用时才加载对应模块
- **教训**：包的__init__.py不应该eager import所有子模块，应该用延迟导入

### 18. 技能涌现命名包含查询内容
- **现象**：技能名如"本质追溯者_esp32明明供"，后半部分是查询内容
- **根因**：`_generate_skill_name`用`trigger[:8]`作为后缀，trigger可能包含查询内容
- **修复**：改为用触发模式类型（如"essence_reasoning"）而非查询内容
- **教训**：用户输入不应直接出现在系统内部标识符中

---

## 六、v4.0.0 工具执行链修复（2026年7月）

### 19. 工具意图截断导致serial_port被排除（P0致命）
- **现象**：用户说"读取COM8串口数据"，系统只返回文本指导而非真实NMEA数据
- **根因**：`tool_path.py`中`tool_intent=True`时，`other_tools[:3]`只取前3个非代码工具。serial_port(priority=60)排在web_search(70)、fact_check(65)、knowledge_lookup(60)之后被截断。更致命的是`params.get("_tool_hint")`在`params = extract_tool_params(...)`之前被引用，导致变量未定义异常被catch吞掉
- **修复**：1) 将`extract_tool_params`调用移到`tool_intent`判断之前；2) 当`_tool_hint`指定的工具不在`other_tools[:3]`中时，将其移到首位
- **教训**：工具选择逻辑必须保证hint指定的工具不被截断；变量引用顺序错误在try/except中会静默失败

### 20. 非流式API完全缺少工具调用（P0致命）
- **现象**：`/api/chat`路由的请求走Ollama文本推理，从不调用工具
- **根因**：`chat_handler.py`的处理流程只有：意图识别→Ollama→外部API→知识库，完全没有工具调用逻辑。工具调用只在`chat_orchestrator.py`的parallel_router中，而parallel_router只被`/api/chat/stream`流式接口使用
- **修复**：在`chat_handler.py`策略3（深度认知处理）中，Ollama之前加入工具调用逻辑，当`query_needs_tools`返回True时优先执行工具
- **教训**：每条API路径都必须有完整的处理能力，不能假设所有请求都走同一条路径

### 21. Windows空闲睡眠导致服务器中断（P1严重）
- **现象**：服务器运行一段时间后电脑自动关机/睡眠
- **根因**：Windows电源管理在系统空闲60分钟后自动睡眠（Event ID 42, "System Idle"），导致服务器进程被杀
- **修复**：`powercfg /change standby-timeout-ac 0`禁用睡眠；在`start.bat`中加入自动禁用睡眠步骤
- **教训**：服务器部署在桌面Windows上时，必须禁用空闲睡眠；Windows事件日志是排查"莫名关机"的首选工具

### 22. 前端版本号与后端不同步
- **现象**：修改了前端文件但页面仍显示旧版本号
- **根因**：前端显示的版本号来自后端`/api/health`接口（`main_fast.py`和`health.py`），不是HTML/JS文件中的版本号参数。修改CSS/JS的cache-busting参数不影响health接口返回的版本
- **修复**：同步更新`main_fast.py`和`health.py`中的version字段
- **教训**：版本号有多个来源时必须全部同步更新；浏览器缓存问题要区分"文件缓存"和"API返回值"

### 23. 学习回路断裂——909行代码各自为政
- **现象**：6个学习机制（经验池、技能涌现、基因微调、认知学习、反思记录、ToolBuilder）全部在"记录"但不在"成长"，系统学习能力是精心设计的假象
- **根因**：三座孤岛（tool_builder.py 330行、skill_emergence.py 314行、capability_creation_loop.py 265行）互不知道对方存在，4个关键接线点断裂：①ToolBuilder构建后不注册 ②成熟技能不注册为工具 ③plan_tools()空时不查技能表 ④能力创造回路成功后不通知ToolBuilder
- **修复**：约50行接线代码——①build_tool()成功后自动注册AutoToolWrapper到tool_registry ②_update_skill()成熟时调用_register_mature_skill() ③plan_tools()空时回退查询技能表 ④_register_tool()中调用builder.record_success()
- **教训**：模块间"接线"比模块本身更重要；记录≠学习，只有闭环反馈才是真正的学习；架构巡检必须检查模块间连接而非仅检查模块功能

### 24. 认知驱动断裂——理解是表演不是驱动力
- **现象**：用户说"读取串口8"，EssenceReasoner理解了"串口数据读取"，但tool_path只能用正则重新理解，"串口8"匹配不到COM\d+，返回端口列表而非数据
- **根因**：methodology在parallel_router→fetch_tool_results传递中被丢弃；tool_path用自己的正则重新理解世界，无视EssenceReasoner的结论；query_needs_tools与CognitiveDispatcher做两套独立的意图判断
- **修复**：methodology参数沿调用链传递；extract_tool_params用methodology.domain指导参数提取（"串口8"→COM8）；plan_tools用methodology.domain指导工具优先级；methodology.strategy优先于query_needs_tools
- **教训**：理解必须驱动行动，否则理解只是表演；模块间信息传递不能有"漏斗"；同一系统对同一问题不能做两次不同的理解（SpiritCore逻辑自洽原则）

### 25. chat_history.py写入缺少commit导致历史记录丢失
- **现象**：历史记录只显示很早的内容，最近的对话全没了
- **根因**：从sqlite3.connect()迁移到DatabaseManager._get_conn()时，遗漏了所有写操作的conn.commit()。Python的with sqlite3.connect()上下文管理器正常退出时自动commit，但_get_conn()返回持久连接不会自动提交
- **修复**：全部改用db.execute(sql, params, commit=True)和db.query()，自动获得线程锁+retry+自动提交
- **教训**：迁移数据库访问方式时必须检查commit语义变化；_get_conn()绕过了DatabaseManager的锁+retry+commit机制，应优先使用高级API；infrastructure/下191处_get_conn()直接操作可能存在同类问题

### 26. CognitiveDispatcher不知道系统有什么工具
- **现象**：串口类查询被分类为complex_query(56%)而非hardware，导致走错路径
- **根因**：_scan_capabilities_fast()直接返回空工具列表，完全跳过了工具扫描；没有hardware意图类型
- **修复**：从tool_registry.list_tools()读取已注册工具；新增hardware意图类型(串口/serial/硬件/设备等关键词)；hardware走slow路径
- **教训**：认知调度器必须知道系统的能力边界，否则无法做出正确的路由决策

### 27. 元认知宪法修正——三思后行+七维自检写入基因
- **现象**：多次修复局部问题时忽略全景，重复发明轮子，治标不治本
- **根因**：缺乏行动前的系统性自检机制，没有"先理解再行动"的宪法级约束
- **修复**：SpiritCore新增第9原则"三思后行"和第4元宪法"七维自检"；TruthAccumulator新增3条L4真谛（三思后行、七维自检、依赖链排序）
- **七维自检**：①方向一致 ②看板衔接 ③最小侵入 ④无过度设计 ⑤治标+治本 ⑥可验证 ⑦精神内核对齐
- **教训**：行动的质量取决于行动前的思考质量；"谋定而后动"不是建议是宪法；不做的事和要做的事同样重要

---

## 七、v4.0.0 infrastructure/ _get_conn()全面迁移（2026年7月）

### 28. infrastructure/ 188处_get_conn()绕过线程安全机制
- **现象**：infrastructure/下188处`db._get_conn()`裸cursor调用，绕过DatabaseManager的线程安全锁和重试机制
- **根因**：历史代码直接使用`conn = db._get_conn(); cursor = conn.execute(sql); conn.commit()`模式，这是DatabaseManager内部实现细节，不应被外部调用。手动`conn.commit()`容易遗漏（已发现76处commit缺失）
- **修复**：37个文件全部迁移到DatabaseManager高级API：
  - 写操作: `db.execute(sql, params, commit=True)` — 自动获得线程锁+retry+commit
  - 读多行: `db.query(sql, params)` — 返回`List[sqlite3.Row]`
  - 读单行: `db.query_one(sql, params)` — 返回`Optional[sqlite3.Row]`
  - DDL批量: `db.executescript(script)` — 多个CREATE TABLE/INDEX合并
- **结果**：188处→6处（仅database_manager.py内部self._get_conn保留）
- **教训**：数据库访问必须通过公共API，不应直接使用内部实现；_get_conn()是DatabaseManager的私有方法，外部调用违反封装原则；手动commit是系统性风险源

### 29. closed_loop_orchestrator状态机卡住
- **现象**：闭环调度器在迭代上限时返回False（不保护），导致状态机可能卡在ACCUMULATION→PROTECTION循环
- **根因**：`_check_protection`中`iteration >= max_iterations`时直接返回False，意味着不触发保护机制；`_phase_metacognition`异常后未显式设置状态，导致状态机转移不正确
- **修复**：迭代上限时有结果走ACCUMULATION，无结果走PROTECTION（而非返回False）；异常后显式设`state=METACOGNITION`
- **教训**：状态机的每个分支都必须有明确的下一状态，不能有"无转移"的分支；异常路径必须显式设置状态

### 30. CognitivePlanner.process()从未被调用
- **现象**：CognitivePlanner的核心入口`process()`（完整L1-L6认知循环）从未被主路由调用，chat_orchestrator手动拆解了其内部私有方法
- **根因**：process()设计为同步阻塞调用，而chat_orchestrator是异步流式管道；直接替换风险太高
- **修复**：渐进式三阶段接入——Phase 1: 异步旁路（15秒超时，交叉验证信号补充）；Phase 2: 信号融合（逐步替代手动调用）；Phase 3: 主路由切换（process()成为主路由）
- **教训**：高风险架构变更必须渐进式接入；旁路验证是安全替换的关键模式；私有方法(_perceive等)不应被外部直接调用