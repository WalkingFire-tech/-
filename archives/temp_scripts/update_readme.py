#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""更新README.md - v3.2.0"""

with open('README.md', 'r', encoding='utf-8-sig') as f:
    content = f.read()

# Update API endpoints
old_apis = """**学习API端点**：
- `GET /api/learning/log` - 查看学习活动日志
- `GET /api/learning/knowledge` - 查询知识库
- `POST /api/learning/trigger` - 手动触发学习
- `POST /api/learning/pause/resume` - 暂停/恢复学习
- `POST /api/learning/rollback/{id}` - 回滚学习

**进化API端点**：
- `GET /api/genome/stats` - 基因演化统计
- `POST /api/genome/evolve` - 手动触发演化
- `GET /api/cognitive/stats` - 认知转化统计
- `POST /api/cognitive/transform` - 手动触发转化
- `POST /api/evolution/run` - 运行进化沙盒
- `GET /api/memory/review` - 记忆回顾
- `POST /api/memory/important` - 刻骨铭心标记

**CLI命令**：
- `:learning log` - 查看学习日志
- `:learning knowledge [topic]` - 查询知识
- `:learning pause/resume` - 暂停/恢复学习"""

new_apis = """**学习API端点**：
- `POST /api/optimize` - 系统优化分析
- `POST /api/induction` - 归纳总结（激活待定规则）
- `POST /api/files/learn` - 从文件学习
- `POST /api/folder/learn` - 从文件夹学习
- `GET /api/recent_learning` - 最近学习记录
- `GET /api/knowledge/health` - 知识健康度

**进化API端点**：
- `GET /api/genes` - 基因池状态（含表达谱）
- `GET /api/skills` - 技能涌现状态
- `GET /api/truths` - 真谛沉淀状态
- `GET /api/truths/entropy` - 认知熵值
- `POST /api/truths/reorganization/propose` - 生成认知重组提案
- `POST /api/truths/reorganization/approve` - 人类批准认知重组
- `POST /api/evolution/run` - 运行进化岛沙盒
- `GET /api/reflection/stats` - 反思管道统计

**核心API端点**：
- `GET /api/health` - 健康检查
- `GET /api/stats` - 系统统计
- `POST /api/chat` - 聊天接口
- `POST /api/chat/stream` - 流式聊天接口（SSE）
- `POST /api/feedback` - 用户反馈
- `GET /api/models` - 模型列表
- `POST /api/models/test` - 测试模型连接"""

if old_apis in content:
    content = content.replace(old_apis, new_apis)
    print("API endpoints updated")
else:
    print("Old API text not found, searching...")
    lines = content.split('\n')
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        if '学习API端点' in line:
            start_idx = i
        if start_idx and 'CLI命令' in line:
            end_idx = i
            break
    if start_idx and end_idx:
        cli_end = end_idx
        for j in range(end_idx, min(end_idx + 5, len(lines))):
            if lines[j].startswith('###'):
                cli_end = j
                break
            if not lines[j].startswith('- `:learning'):
                cli_end = j
                break
        new_lines = lines[:start_idx] + new_apis.split('\n') + lines[cli_end:]
        content = '\n'.join(new_lines)
        print(f"Replaced lines {start_idx}-{cli_end-1}")

# Update version
content = content.replace('v3.1.2', 'v3.2.0')
content = content.replace('3.1.2', '3.2.0')
content = content.replace('96.7%', '')

# Update production features
old_prod = """| 优雅退出 | signal+atexit+try-finally三重保护 |
| 事件驱动 | CLI与业务逻辑完全解耦 |
| 连接池 | 数据库连接池优化性能 |
| 热加载 | 配置文件实时监控与重载 |"""

new_prod = """| 优雅退出 | signal+atexit+try-finally三重保护 |
| 事件驱动 | CLI与业务逻辑完全解耦 |
| 持久化队列 | SQLite持久化任务队列，后台异步执行 |
| 认知代谢 | 每10次交互自动清理低价值经验 |"""

content = content.replace(old_prod, new_prod)

with open('README.md', 'w', encoding='utf-8-sig') as f:
    f.write(content)

print("README.md updated to v3.2.0")
