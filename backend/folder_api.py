"""
异步文件夹学习API - 添加到main.py
"""

# === 在main.py顶部添加导入 ===
import uuid
from fastapi import BackgroundTasks

# === 全局任务存储 ===
learning_tasks = {}

# === 添加以下API端点 ===

def _run_folder_learning_task(task_id: str, folder_path: str):
    """后台执行文件夹学习任务"""
    try:
        from core.folder_learner import folder_learner
        from core.learning import enhanced_learner
        from core.document_parser import get_supported_extensions
        
        # 更新支持的扩展名
        folder_learner.SUPPORTED_EXTENSIONS = get_supported_extensions()
        
        # 设置根目录
        folder_learner.set_root_path(folder_path)
        
        # 进度回调
        def progress_callback(file_path, outcome):
            task = learning_tasks.get(task_id)
            if task:
                task["processed"] = task.get("processed", 0) + 1
                if outcome.get("status") == "success":
                    task["knowledge"] = task.get("knowledge", 0) + outcome.get("knowledge_count", 0)
                task["current_file"] = str(file_path.name)
                if task.get("total_files", 0) > 0:
                    task["progress"] = int((task["processed"] / task["total_files"]) * 100)
        
        # 扫描文件
        learning_tasks[task_id]["status"] = "scanning"
        learning_tasks[task_id]["message"] = "正在扫描文件..."
        
        files = []
        for ext in get_supported_extensions():
            files.extend(Path(folder_path).rglob(f"*{ext}"))
        
        learning_tasks[task_id]["total_files"] = len(files)
        learning_tasks[task_id]["status"] = "learning"
        learning_tasks[task_id]["message"] = f"发现 {len(files)} 个文件，开始学习..."
        
        # 执行学习
        result = folder_learner.scan_and_learn(progress_callback=progress_callback)
        
        # 自动生成规则和工具
        learning_tasks[task_id]["message"] = "正在生成学习规则..."
        try:
            rules_count = enhanced_learner.detect_and_create_rules()
            learning_tasks[task_id]["rules"] = rules_count
        except:
            pass
        
        learning_tasks[task_id]["message"] = "正在生成工具..."
        try:
            tools_count = enhanced_learner.auto_generate_tools()
            learning_tasks[task_id]["tools"] = tools_count
        except:
            pass
        
        # 完成
        learning_tasks[task_id]["status"] = "completed"
        learning_tasks[task_id]["progress"] = 100
        learning_tasks[task_id]["message"] = f"✅ 学习完成！处理 {result.get('new', 0) + result.get('updated', 0)} 个文件"
        learning_tasks[task_id]["result"] = result
        
        # 推送通知
        try:
            from core.active_scheduler import active_scheduler
            active_scheduler.pending_notifications.append({
                "type": "folder_learning",
                "message": f"📚 文件夹学习完成：{result.get('new', 0) + result.get('updated', 0)} 个文件",
                "timestamp": datetime.now().isoformat()
            })
        except:
            pass
        
        logger.info(f"任务 {task_id} 完成: {result}")
        
    except Exception as e:
        learning_tasks[task_id]["status"] = "failed"
        learning_tasks[task_id]["message"] = str(e)
        logger.error(f"任务 {task_id} 失败: {e}")


@app.post("/api/folder/learn_async")
async def learn_folder_async(request: dict, background_tasks: BackgroundTasks):
    """异步学习文件夹"""
    folder_path = request.get("path")
    if not folder_path:
        return {"success": False, "error": "请提供文件夹路径"}
    
    folder = Path(folder_path).resolve()
    
    # 安全检查
    if not folder.exists():
        return {"success": False, "error": "文件夹不存在"}
    if not folder.is_dir():
        return {"success": False, "error": "不是文件夹"}
    
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


@app.get("/api/folder/learn_status/{task_id}")
async def get_learn_status(task_id: str):
    """查询学习任务进度"""
    task = learning_tasks.get(task_id)
    if not task:
        return {"success": False, "error": "任务不存在"}
    return {"success": True, **task}


@app.get("/api/folder/learn_tasks")
async def list_learning_tasks(limit: int = 10):
    """列出最近的学习任务"""
    tasks = []
    for tid, task in list(learning_tasks.items())[-limit:]:
        tasks.append({
            "task_id": tid,
            "status": task.get("status"),
            "progress": task.get("progress"),
            "message": task.get("message"),
            "folder": task.get("folder"),
            "created_at": task.get("created_at")
        })
    return {"tasks": tasks}