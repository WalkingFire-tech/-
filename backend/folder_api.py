"""
异步文件夹学习API - 修复版

修复问题：
1. 添加缺失的导入（Path, datetime）
2. 扩展名类型统一为set
3. 完善异常处理
4. 添加任务取消功能
"""

import uuid
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import BackgroundTasks
from loguru import logger

# 全局任务存储
learning_tasks = {}


def _run_folder_learning_task(task_id: str, folder_path: str):
    """后台执行文件夹学习任务"""
    try:
        from core.folder_learner import folder_learner
        from core.learning import enhanced_learner
        from core.document_parser import get_supported_extensions
        
        # 1. 初始化任务状态
        learning_tasks[task_id]["status"] = "scanning"
        learning_tasks[task_id]["message"] = "正在扫描文件..."
        
        # 2. 获取支持的文件类型（统一为set）
        supported_exts = set(get_supported_extensions())
        folder_learner.SUPPORTED_EXTENSIONS = supported_exts
        
        # 3. 设置根目录
        result = folder_learner.set_root_path(folder_path)
        if not result.get("success"):
            raise ValueError(result.get("error", "设置根目录失败"))
        
        # 4. 先扫描所有文件，计算总数
        all_files = []
        folder = Path(folder_path)
        for ext in supported_exts:
            try:
                all_files.extend(folder.rglob(f"*{ext}"))
            except Exception as e:
                logger.warning(f"扫描扩展名 {ext} 失败: {e}")
        
        total_files = len(all_files)
        learning_tasks[task_id]["total_files"] = total_files
        learning_tasks[task_id]["status"] = "learning"
        learning_tasks[task_id]["message"] = f"发现 {total_files} 个文件，开始学习..."
        
        # 5. 进度回调
        def progress_callback(file_path, outcome):
            task = learning_tasks.get(task_id)
            if not task:
                return
            
            task["processed"] = task.get("processed", 0) + 1
            if outcome.get("status") == "success":
                task["knowledge"] = task.get("knowledge", 0) + outcome.get("knowledge_count", 0)
            task["current_file"] = str(file_path.name)
            
            if task.get("total_files", 0) > 0:
                task["progress"] = int((task["processed"] / task["total_files"]) * 100)
        
        # 6. 执行学习
        result = folder_learner.scan_and_learn(progress_callback=progress_callback)
        
        # 7. 生成规则
        learning_tasks[task_id]["message"] = "正在生成学习规则..."
        try:
            rules_count = enhanced_learner.detect_and_create_rules()
            learning_tasks[task_id]["rules"] = rules_count or 0
        except Exception as e:
            logger.warning(f"规则生成失败: {e}")
            learning_tasks[task_id]["rules"] = 0
        
        # 8. 生成工具
        learning_tasks[task_id]["message"] = "正在生成工具..."
        try:
            tools_count = enhanced_learner.auto_generate_tools()
            learning_tasks[task_id]["tools"] = tools_count or 0
        except Exception as e:
            logger.warning(f"工具生成失败: {e}")
            learning_tasks[task_id]["tools"] = 0
        
        # 9. 完成
        total_processed = result.get("new", 0) + result.get("updated", 0)
        learning_tasks[task_id]["status"] = "completed"
        learning_tasks[task_id]["progress"] = 100
        learning_tasks[task_id]["message"] = f"✅ 学习完成！处理 {total_processed} 个文件"
        learning_tasks[task_id]["result"] = result
        
        # 10. 推送通知
        try:
            from core.active_scheduler import active_scheduler
            active_scheduler.pending_notifications.append({
                "type": "folder_learning",
                "message": f"📚 文件夹学习完成：{total_processed} 个文件",
                "timestamp": datetime.now().isoformat()
            })
        except Exception:
            pass
        
        logger.info(f"任务 {task_id} 完成: {result}")
        
    except Exception as e:
        learning_tasks[task_id]["status"] = "failed"
        learning_tasks[task_id]["message"] = str(e)
        learning_tasks[task_id]["error"] = str(e)
        logger.error(f"任务 {task_id} 失败: {e}")


# ============================================================
# API 端点（需要添加到main.py）
# ============================================================

# 示例：添加到main.py的端点
"""
@app.post("/api/folder/learn_async")
async def learn_folder_async(request: dict, background_tasks: BackgroundTasks):
    from backend.folder_api import learning_tasks, _run_folder_learning_task
    # ... 实现代码
"""


def create_learning_task(folder_path: str, background_tasks: BackgroundTasks) -> dict:
    """创建学习任务（供main.py调用）"""
    folder = Path(folder_path).resolve()
    
    # 安全检查
    if not folder.exists():
        return {"success": False, "error": "文件夹不存在"}
    if not folder.is_dir():
        return {"success": False, "error": "不是文件夹"}
    
    # 检查是否已有运行中的任务
    for tid, task in learning_tasks.items():
        if task.get("folder") == str(folder) and task.get("status") in ["pending", "scanning", "learning"]:
            return {
                "success": False,
                "error": "该文件夹已有任务正在运行",
                "task_id": tid
            }
    
    # 创建任务
    task_id = str(uuid.uuid4())
    learning_tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "total_files": 0,
        "processed": 0,
        "knowledge": 0,
        "rules": 0,
        "tools": 0,
        "current_file": "",
        "message": "任务已创建",
        "folder": str(folder),
        "created_at": datetime.now().isoformat()
    }
    
    # 后台执行
    background_tasks.add_task(_run_folder_learning_task, task_id, str(folder))
    
    logger.info(f"创建学习任务: {task_id} - {folder}")
    
    return {"success": True, "task_id": task_id}


def get_task_status(task_id: str) -> dict:
    """查询学习任务进度（供main.py调用）"""
    task = learning_tasks.get(task_id)
    if not task:
        return {"success": False, "error": "任务不存在"}
    
    # 返回任务状态（不包含敏感信息）
    return {
        "success": True,
        "task_id": task_id,
        "status": task.get("status"),
        "progress": task.get("progress"),
        "message": task.get("message"),
        "total_files": task.get("total_files"),
        "processed": task.get("processed"),
        "knowledge": task.get("knowledge"),
        "rules": task.get("rules"),
        "tools": task.get("tools"),
        "current_file": task.get("current_file"),
        "folder": task.get("folder"),
        "created_at": task.get("created_at"),
        "error": task.get("error")
    }


def list_tasks(limit: int = 10, status: Optional[str] = None) -> dict:
    """列出学习任务（供main.py调用）"""
    tasks = []
    for tid, task in list(learning_tasks.items())[-limit:]:
        if status and task.get("status") != status:
            continue
        tasks.append({
            "task_id": tid,
            "status": task.get("status"),
            "progress": task.get("progress"),
            "message": task.get("message"),
            "folder": task.get("folder"),
            "created_at": task.get("created_at")
        })
    return {"tasks": tasks}


def cancel_task(task_id: str) -> dict:
    """取消学习任务（供main.py调用）"""
    task = learning_tasks.get(task_id)
    if not task:
        return {"success": False, "error": "任务不存在"}
    
    if task.get("status") not in ["pending", "scanning"]:
        return {"success": False, "error": f"任务正在执行中，无法取消 (状态: {task.get('status')})"}
    
    task["status"] = "cancelled"
    task["message"] = "已取消"
    logger.info(f"任务 {task_id} 已取消")
    
    return {"success": True, "message": "任务已取消"}


def cleanup_old_tasks(max_age_hours: int = 24) -> int:
    """清理旧任务"""
    from datetime import datetime, timedelta
    
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    cleaned = 0
    
    for task_id, task in list(learning_tasks.items()):
        created_at_str = task.get("created_at")
        if not created_at_str:
            continue
        
        try:
            created_at = datetime.fromisoformat(created_at_str)
            if created_at < cutoff and task.get("status") in ["completed", "failed", "cancelled"]:
                del learning_tasks[task_id]
                cleaned += 1
        except Exception:
            pass
    
    if cleaned > 0:
        logger.info(f"清理了 {cleaned} 个旧任务")
    
    return cleaned
