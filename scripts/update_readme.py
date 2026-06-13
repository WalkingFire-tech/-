"""更新README.md添加持续学习单元说明"""
import re

with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

# 在冲突检测行后添加持续学习单元
pattern = r'(\| 冲突检测 \| Conflict Detector \| 自动检测并解决规则冲突 \|)'
replacement = r'''\1

### 🔍 持续学习单元

| 特性 | 技术实现 | 说明 |
|------|----------|------|
| 主动学习 | ddgs + 白名单过滤 | 自动搜索外部知识 |
| 知识积累 | SQLite + 影响评分 | 持久化存储学习成果 |
| 事件驱动 | 触发机制 | 失败、提问、APHI下降自动学习 |
| 用户干预 | API + CLI | 暂停、恢复、回滚、删除 |

**学习API端点**：
- `GET /api/learning/log` - 查看学习活动日志
- `GET /api/learning/knowledge` - 查询知识库
- `POST /api/learning/trigger` - 手动触发学习
- `POST /api/learning/pause/resume` - 暂停/恢复学习
- `POST /api/learning/rollback/{id}` - 回滚学习

**CLI命令**：
- `:learning log` - 查看学习日志
- `:learning knowledge [topic]` - 查询知识
- `:learning pause/resume` - 暂停/恢复学习'''

content = re.sub(pattern, replacement, content)

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(content)

print('README.md已更新')