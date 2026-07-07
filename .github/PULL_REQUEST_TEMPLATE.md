## 变更说明

清晰简明地描述本次变更的内容。

## 变更类型

- [ ] Bug修复（fix）
- [ ] 新功能（feat）
- [ ] 文档更新（docs）
- [ ] 代码重构（refactor）
- [ ] 性能优化（perf）
- [ ] 测试相关（test）
- [ ] 其他（chore）

## 相关Issue

链接相关Issue，例如：Closes #123

## 测试情况

描述如何测试本次变更：

1. 测试步骤
2. 测试结果
3. 覆盖范围

## 影响范围

说明本次变更可能影响的模块或功能：

- [ ] 核心服务（core/services）
- [ ] 适配器（adapters）
- [ ] 基础设施（infrastructure）
- [ ] 元控制层（meta）
- [ ] 工具系统（tools）
- [ ] 配置文件（config）
- [ ] 文档（docs）

## 检查清单

- [ ] 代码符合PEP 8规范
- [ ] 已添加类型注解
- [ ] 已添加文档字符串
- [ ] 已添加单元测试
- [ ] 所有测试通过（`python -m pytest tests/unit/ -v`）
- [ ] 已更新相关文档
- [ ] 已更新CHANGELOG.md

### 安全性检查

- [ ] SpiritCore核心常量不可变性未被破坏（`pytest tests/unit/test_spirit_core.py`）
- [ ] SQLite写操作使用`_write_op()`包装（线程安全+WAL模式）
- [ ] 无裸`except:`（应为`except Exception:`）
- [ ] 关键路径超时有SSE反馈（`status: "timeout"`）
- [ ] 无硬编码密钥或敏感信息

## 截图

如果适用，添加截图展示变更效果。

## 附加信息

添加任何其他相关信息。