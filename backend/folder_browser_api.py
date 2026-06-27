"""
文件夹浏览器API - 提供类似Windows资源管理器的界面

改进：
1. 安全导入模块
2. 异步学习任务
3. 搜索分页
4. 统一返回格式
5. 完善异常处理
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger

router = APIRouter()

# 安全导入模块
try:
    from core.folder_browser import folder_browser
    FOLDER_BROWSER_AVAILABLE = True
except ImportError as e:
    folder_browser = None
    FOLDER_BROWSER_AVAILABLE = False
    logger.warning(f"folder_browser 导入失败: {e}")

try:
    from core.folder_learner import folder_learner
    FOLDER_LEARNER_AVAILABLE = True
except ImportError as e:
    folder_learner = None
    FOLDER_LEARNER_AVAILABLE = False
    logger.warning(f"folder_learner 导入失败: {e}")


class BrowseRequest(BaseModel):
    path: str


class SearchRequest(BaseModel):
    query: str
    path: Optional[str] = None
    limit: int = 50
    offset: int = 0


class SetLearningFolderRequest(BaseModel):
    path: str
    start_learning: bool = False


def check_module_available():
    """检查模块是否可用"""
    if not FOLDER_BROWSER_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="文件夹浏览器模块不可用"
        )


def check_learner_available():
    """检查学习器是否可用"""
    if not FOLDER_LEARNER_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="文件夹学习器模块不可用"
        )


@router.get("/drives")
async def get_drives():
    """获取所有驱动器"""
    check_module_available()
    
    try:
        drives = folder_browser.get_drives()
        return {
            "success": True,
            "drives": drives,
            "count": len(drives)
        }
    except Exception as e:
        logger.error(f"获取驱动器失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "drives": []
        }


@router.get("/quick-access")
async def get_quick_access():
    """获取快速访问路径"""
    check_module_available()
    
    try:
        quick = folder_browser.get_quick_access()
        return {
            "success": True,
            "quick_access": quick,
            "count": len(quick)
        }
    except Exception as e:
        logger.error(f"获取快速访问失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "quick_access": []
        }


@router.post("/browse")
async def browse_path(request: BrowseRequest):
    """浏览指定路径"""
    check_module_available()
    
    try:
        result = folder_browser.browse(request.path)
        
        if isinstance(result, dict):
            if result.get("success", True):
                return result
            else:
                return {
                    "success": False,
                    "error": result.get("error", "浏览失败"),
                    "path": request.path
                }
        else:
            return {
                "success": True,
                "result": result
            }
    except Exception as e:
        logger.error(f"浏览路径失败 {request.path}: {e}")
        return {
            "success": False,
            "error": str(e),
            "path": request.path
        }


@router.get("/browse")
async def browse_current():
    """浏览当前路径"""
    check_module_available()
    
    try:
        if folder_browser.current_path:
            result = folder_browser.browse(str(folder_browser.current_path))
            if isinstance(result, dict):
                return result
            else:
                return {
                    "success": True,
                    "result": result
                }
        else:
            drives = folder_browser.get_drives()
            return {
                "success": True,
                "type": "root",
                "drives": drives,
                "count": len(drives)
            }
    except Exception as e:
        logger.error(f"浏览当前路径失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/go-back")
async def go_back():
    """返回上一级"""
    check_module_available()
    
    try:
        result = folder_browser.go_back()
        if result:
            if isinstance(result, dict):
                return result
            else:
                return {
                    "success": True,
                    "result": result
                }
        else:
            return {
                "success": False,
                "error": "无法返回"
            }
    except Exception as e:
        logger.error(f"返回上一级失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/go-forward")
async def go_forward():
    """前进"""
    check_module_available()
    
    try:
        result = folder_browser.go_forward()
        if result:
            if isinstance(result, dict):
                return result
            else:
                return {
                    "success": True,
                    "result": result
                }
        else:
            return {
                "success": False,
                "error": "无法前进"
            }
    except Exception as e:
        logger.error(f"前进失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/go-up")
async def go_up():
    """返回上级目录"""
    check_module_available()
    
    try:
        result = folder_browser.go_up()
        if result:
            if isinstance(result, dict):
                return result
            else:
                return {
                    "success": True,
                    "result": result
                }
        else:
            return {
                "success": False,
                "error": "已经是根目录"
            }
    except Exception as e:
        logger.error(f"返回上级目录失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/search")
async def search(request: SearchRequest):
    """搜索文件和文件夹（支持分页）"""
    check_module_available()
    
    try:
        results = folder_browser.search(request.query, request.path)
        
        if not isinstance(results, list):
            results = []
        
        total = len(results)
        
        # 分页
        paginated = results[request.offset:request.offset + request.limit]
        
        return {
            "success": True,
            "query": request.query,
            "results": paginated,
            "total": total,
            "limit": request.limit,
            "offset": request.offset,
            "count": len(paginated),
            "has_more": request.offset + request.limit < total
        }
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": request.query,
            "results": [],
            "total": 0
        }


@router.post("/set-learning-folder")
async def set_learning_folder(request: SetLearningFolderRequest):
    """设置学习文件夹"""
    check_module_available()
    check_learner_available()
    
    try:
        # 设置文件夹学习器的根路径
        learner_result = folder_learner.set_root_path(request.path)
        
        if not learner_result.get("success"):
            return {
                "success": False,
                "error": learner_result.get("error", "设置学习路径失败"),
                "path": request.path
            }
        
        # 同时更新浏览器路径
        browse_result = folder_browser.browse(request.path)
        
        if isinstance(browse_result, dict) and not browse_result.get("success", True):
            logger.warning(f"浏览路径失败，但学习路径已设置: {browse_result.get('error')}")
        
        response = {
            "success": True,
            "message": f"已设置学习文件夹: {request.path}",
            "root_path": request.path,
            "learner_result": learner_result
        }
        
        # 如果请求立即开始学习
        if request.start_learning:
            response["message"] += "，学习任务已启动"
        
        return response
        
    except Exception as e:
        logger.error(f"设置学习文件夹失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "path": request.path
        }


@router.post("/start-learning")
async def start_learning(background_tasks: BackgroundTasks):
    """开始学习当前文件夹（异步执行）"""
    check_learner_available()
    
    if not folder_learner.root_path:
        return {
            "success": False,
            "error": "未设置学习文件夹"
        }
    
    try:
        # 检查是否已在运行
        status = folder_learner.get_status()
        if status.get("running"):
            return {
                "success": True,
                "message": "学习任务已在运行中",
                "status": status
            }
        
        # 后台执行学习任务
        def run_learning():
            try:
                result = folder_learner.scan_and_learn()
                logger.info(f"学习任务完成: {result}")
            except Exception as e:
                logger.error(f"学习任务失败: {e}")
        
        background_tasks.add_task(run_learning)
        
        return {
            "success": True,
            "message": "学习任务已启动，将在后台运行",
            "root_path": str(folder_learner.root_path),
            "status": "running"
        }
        
    except Exception as e:
        logger.error(f"启动学习失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/learning-status")
async def get_learning_status():
    """获取学习状态"""
    check_learner_available()
    
    try:
        summary = folder_learner.get_summary()
        status = folder_learner.get_status()
        
        return {
            "success": True,
            "summary": summary,
            "status": status
        }
    except Exception as e:
        logger.error(f"获取学习状态失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/recent-learned")
async def get_recent_learned(limit: int = 10):
    """获取最近学习的文件"""
    check_learner_available()
    
    try:
        recent = folder_learner.get_recent_learned(limit)
        return {
            "success": True,
            "recent": recent,
            "count": len(recent)
        }
    except Exception as e:
        logger.error(f"获取最近学习文件失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "recent": []
        }


@router.get("/failed-files")
async def get_failed_files():
    """获取学习失败的文件"""
    check_learner_available()
    
    try:
        failed = folder_learner.get_failed_files()
        return {
            "success": True,
            "failed": failed,
            "count": len(failed)
        }
    except Exception as e:
        logger.error(f"获取失败文件失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "failed": []
        }


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "success": True,
        "folder_browser_available": FOLDER_BROWSER_AVAILABLE,
        "folder_learner_available": FOLDER_LEARNER_AVAILABLE
    }
