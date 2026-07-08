"""
CLI命令注册 - 学习相关命令
"""
from typing import Dict, List
from loguru import logger


class LearningCommands:
    """学习相关CLI命令"""
    
    @staticmethod
    def status() -> str:
        """查看学习器状态"""
        from core.learning_engine import learning_engine
        from core.file_monitor import file_monitor
        
        engine_stats = learning_engine.get_stats()
        monitor_status = file_monitor.get_status()
        
        output = []
        output.append("=" * 60)
        output.append("📚 学习系统状态")
        output.append("=" * 60)
        output.append(f"\n【学习引擎】")
        output.append(f"  模式: {engine_stats['mode']}")
        output.append(f"  运行状态: {'运行中' if engine_stats['is_running'] else '已停止'}")
        output.append(f"  总任务数: {engine_stats['total_tasks']}")
        output.append(f"  待处理: {engine_stats['pending_tasks']}")
        output.append(f"  处理中: {engine_stats['processing_tasks']}")
        output.append(f"  已完成: {engine_stats['completed_tasks']}")
        output.append(f"  失败: {engine_stats['failed_tasks']}")
        output.append(f"  总知识数: {engine_stats['total_knowledge']}")
        
        output.append(f"\n【文件监听】")
        output.append(f"  运行状态: {'运行中' if monitor_status['is_running'] else '已停止'}")
        output.append(f"  监听路径数: {monitor_status['total_paths']}")
        
        for path_info in monitor_status['watched_paths']:
            output.append(f"  - {path_info['path']}")
            output.append(f"    文件数: {path_info['files_count']}, 优先级: {path_info['priority']}")
        
        return "\n".join(output)
    
    @staticmethod
    def mode(mode_str: str) -> str:
        """切换学习模式"""
        from core.learning_engine import learning_engine
        
        result = learning_engine.set_mode(mode_str)
        
        if result['success']:
            return f"✅ 学习模式已切换为: {result['mode']}"
        else:
            return f"❌ 切换失败: {result.get('error', '未知错误')}"
    
    @staticmethod
    def add_folder(path: str, priority: str = "normal") -> str:
        """添加学习文件夹"""
        from core.file_monitor import file_monitor
        from core.learning_engine import learning_engine
        
        monitor_result = file_monitor.add_watch_path(path, priority=priority)
        
        if not monitor_result['success']:
            return f"❌ 添加失败: {monitor_result.get('error', '未知错误')}"
        
        from pathlib import Path
        watch_path = Path(path).resolve()
        
        supported_extensions = {
            '.py', '.md', '.txt', '.json', '.yaml', '.yml',
            '.csv', '.rst', '.js', '.ts', '.html', '.css'
        }
        
        added_count = 0
        for file_path in watch_path.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                result = learning_engine.add_task(str(file_path), event_type="scan")
                if result['success']:
                    added_count += 1
        
        return f"✅ 已添加学习路径: {monitor_result['path']}\n   文件数: {monitor_result['files_count']}\n   已添加任务: {added_count}"
    
    @staticmethod
    def remove_folder(path: str) -> str:
        """移除学习文件夹"""
        from core.file_monitor import file_monitor
        
        result = file_monitor.remove_watch_path(path)
        
        if result['success']:
            return f"✅ 已移除学习路径: {result['path']}"
        else:
            return f"❌ 移除失败: {result.get('error', '未知错误')}"
    
    @staticmethod
    def force_learn(file_path: str) -> str:
        """强制学习文件"""
        from core.learning_engine import learning_engine
        
        result = learning_engine.force_learn(file_path)
        
        if result['success']:
            return f"✅ 已添加强制学习任务: {file_path} (优先级={result['priority']})"
        else:
            return f"❌ 添加失败: {result.get('reason', '未知错误')}"
    
    @staticmethod
    def pause() -> str:
        """暂停学习"""
        from core.file_monitor import file_monitor
        from core.learning_engine import learning_engine
        
        file_monitor.pause()
        learning_engine.stop()
        
        return "✅ 学习系统已暂停"
    
    @staticmethod
    def resume() -> str:
        """恢复学习"""
        from core.file_monitor import file_monitor
        from core.learning_engine import learning_engine
        
        file_monitor.resume()
        learning_engine.start()
        
        return "✅ 学习系统已恢复"
    
    @staticmethod
    def knowledge_list(limit: int = 20) -> str:
        """列出知识库条目"""
        from infrastructure.database_manager import DatabaseManager
        
        conn = DatabaseManager.get('data/knowledge_store.db')._get_conn()
        cursor = conn.execute('''
            SELECT question, source, knowledge_type, created_at
            FROM knowledge_items
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        
        if not rows:
            return "知识库为空"
        
        output = []
        output.append("=" * 60)
        output.append(f"📚 知识库条目 (最近{len(rows)}条)")
        output.append("=" * 60)
        
        for i, row in enumerate(rows, 1):
            output.append(f"\n{i}. {row['question'][:50]}...")
            output.append(f"   类型: {row['knowledge_type']}, 来源: {row['source']}")
        
        return "\n".join(output)
    
    @staticmethod
    def tools_list() -> str:
        """列出自动生成的工具"""
        from infrastructure.database_manager import DatabaseManager
        
        conn = DatabaseManager.get('data/knowledge_store.db')._get_conn()
        cursor = conn.execute('''
            SELECT name, description, usage_count, created_at
            FROM tools
            ORDER BY usage_count DESC
        ''')
        
        rows = cursor.fetchall()
        
        if not rows:
            return "暂无自动生成的工具"
        
        output = []
        output.append("=" * 60)
        output.append(f"🛠️ 自动生成的工具 ({len(rows)}个)")
        output.append("=" * 60)
        
        for i, row in enumerate(rows, 1):
            output.append(f"\n{i}. {row['name']}")
            output.append(f"   描述: {row['description']}")
            output.append(f"   使用次数: {row['usage_count']}")
        
        return "\n".join(output)
    
    @staticmethod
    def tasks_recent(limit: int = 10) -> str:
        """显示最近的学习任务"""
        from core.learning_engine import learning_engine
        
        tasks = learning_engine.get_recent_tasks(limit)
        
        if not tasks:
            return "暂无学习任务"
        
        output = []
        output.append("=" * 60)
        output.append(f"📋 最近的学习任务 ({len(tasks)}个)")
        output.append("=" * 60)
        
        for i, task in enumerate(tasks, 1):
            status_icon = {
                'pending': '⏳',
                'processing': '🔄',
                'completed': '✅',
                'failed': '❌'
            }.get(task['status'], '❓')
            
            output.append(f"\n{i}. {status_icon} {task['file_path']}")
            output.append(f"   状态: {task['status']}, 知识数: {task['knowledge_count']}")
            
            if task['error_msg']:
                output.append(f"   错误: {task['error_msg']}")
        
        return "\n".join(output)


def register_learning_commands():
    """注册学习命令到命令注册表"""
    
    try:
        from meta.command_registry import register_command
        
        register_command(":learning status", LearningCommands.status, 
                        "查看学习器状态")
        register_command(":learning mode", LearningCommands.mode,
                        "切换学习模式 (auto/smart/manual)")
        register_command(":learning add", LearningCommands.add_folder,
                        "添加学习文件夹")
        register_command(":learning remove", LearningCommands.remove_folder,
                        "移除学习文件夹")
        register_command(":learning force", LearningCommands.force_learn,
                        "强制学习文件")
        register_command(":learning pause", LearningCommands.pause,
                        "暂停学习")
        register_command(":learning resume", LearningCommands.resume,
                        "恢复学习")
        register_command(":learning knowledge", LearningCommands.knowledge_list,
                        "列出知识库条目")
        register_command(":learning tools", LearningCommands.tools_list,
                        "列出自动生成的工具")
        register_command(":learning tasks", LearningCommands.tasks_recent,
                        "显示最近的学习任务")
        
        logger.info("学习命令已注册")
        
    except ImportError:
        logger.warning("命令注册表不存在，跳过命令注册")


register_learning_commands()