"""
文件夹浏览器 - 提供类似Windows资源管理器的文件夹浏览界面
支持直接选择文件夹并浏览其内容
"""
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import sqlite3
from loguru import logger


class FolderBrowser:
    """文件夹浏览器 - 提供文件夹选择和浏览功能"""
    
    def __init__(self):
        self.current_path: Optional[Path] = None
        self.history: List[Path] = []
        self.history_index = -1
    
    def get_drives(self) -> List[Dict]:
        """获取所有驱动器"""
        drives = []
        if os.name == 'nt':  # Windows
            import string
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    try:
                        usage = self._get_drive_usage(drive)
                        drives.append({
                            "name": f"本地磁盘 ({letter}:)",
                            "path": drive,
                            "type": "drive",
                            "total": usage.get("total", 0),
                            "used": usage.get("used", 0),
                            "free": usage.get("free", 0)
                        })
                    except Exception:
                        drives.append({
                            "name": f"本地磁盘 ({letter}:)",
                            "path": drive,
                            "type": "drive"
                        })
        else:  # Linux/Mac
            drives.append({
                "name": "根目录",
                "path": "/",
                "type": "drive"
            })
        
        return drives
    
    def _get_drive_usage(self, drive: str) -> Dict:
        """获取驱动器使用情况"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(drive)
            return {
                "total": total,
                "used": used,
                "free": free
            }
        except Exception:
            return {}
    
    def browse(self, path: str) -> Dict:
        """浏览指定路径"""
        try:
            target = Path(path).resolve()
            
            if not target.exists():
                return {
                    "success": False,
                    "error": "路径不存在"
                }
            
            if target.is_file():
                # 如果是文件，返回文件信息
                return self._browse_file(target)
            else:
                # 如果是文件夹，返回文件夹内容
                return self._browse_folder(target)
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _browse_folder(self, folder: Path) -> Dict:
        """浏览文件夹"""
        self.current_path = folder
        self._add_to_history(folder)
        
        items = {
            "folders": [],
            "files": [],
            "supported_files": [],
            "unsupported_files": []
        }
        
        supported_extensions = {
            '.py', '.md', '.txt', '.json', '.yaml', '.yml', 
            '.csv', '.rst', '.js', '.html', '.css', '.ts',
            '.xml', '.ini', '.cfg', '.toml', '.sh', '.bat',
            '.pdf', '.docx', '.doc', '.xlsx', '.xls'
        }
        
        try:
            for item in sorted(folder.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if item.is_dir():
                    items["folders"].append({
                        "name": item.name,
                        "path": str(item),
                        "type": "folder",
                        "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                    })
                else:
                    file_info = {
                        "name": item.name,
                        "path": str(item),
                        "type": "file",
                        "extension": item.suffix.lower(),
                        "size": item.stat().st_size,
                        "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                    }
                    
                    if item.suffix.lower() in supported_extensions:
                        items["supported_files"].append(file_info)
                    else:
                        items["unsupported_files"].append(file_info)
                    
                    items["files"].append(file_info)
        
        except PermissionError:
            return {
                "success": False,
                "error": "没有权限访问此文件夹"
            }
        
        # 统计信息
        stats = {
            "total_folders": len(items["folders"]),
            "total_files": len(items["files"]),
            "supported_files": len(items["supported_files"]),
            "unsupported_files": len(items["unsupported_files"]),
            "total_size": sum(f.get("size", 0) for f in items["files"])
        }
        
        return {
            "success": True,
            "path": str(folder),
            "parent": str(folder.parent) if folder.parent != folder else None,
            "items": items,
            "stats": stats,
            "can_learn": len(items["supported_files"]) > 0
        }
    
    def _browse_file(self, file: Path) -> Dict:
        """浏览文件"""
        return {
            "success": True,
            "type": "file",
            "path": str(file),
            "name": file.name,
            "extension": file.suffix.lower(),
            "size": file.stat().st_size,
            "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
            "parent": str(file.parent),
            "can_learn": file.suffix.lower() in {
                '.py', '.md', '.txt', '.json', '.yaml', '.yml', 
                '.csv', '.rst', '.js', '.html', '.css', '.ts',
                '.xml', '.ini', '.cfg', '.toml', '.sh', '.bat',
                '.pdf', '.docx', '.doc', '.xlsx', '.xls'
            }
        }
    
    def _add_to_history(self, path: Path):
        """添加到历史记录"""
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        
        if not self.history or self.history[-1] != path:
            self.history.append(path)
            self.history_index = len(self.history) - 1
    
    def go_back(self) -> Optional[Dict]:
        """返回上一级"""
        if self.history_index > 0:
            self.history_index -= 1
            return self.browse(str(self.history[self.history_index]))
        return None
    
    def go_forward(self) -> Optional[Dict]:
        """前进"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            return self.browse(str(self.history[self.history_index]))
        return None
    
    def go_up(self) -> Optional[Dict]:
        """返回上级目录"""
        if self.current_path and self.current_path.parent != self.current_path:
            return self.browse(str(self.current_path.parent))
        return None
    
    def get_quick_access(self) -> List[Dict]:
        """获取快速访问路径"""
        quick = []
        
        # 常用路径
        common_paths = [
            ("桌面", Path.home() / "Desktop"),
            ("文档", Path.home() / "Documents"),
            ("下载", Path.home() / "Downloads"),
            ("用户目录", Path.home()),
        ]
        
        for name, path in common_paths:
            if path.exists():
                quick.append({
                    "name": name,
                    "path": str(path),
                    "type": "quick"
                })
        
        return quick
    
    def search(self, query: str, path: str = None) -> List[Dict]:
        """搜索文件和文件夹"""
        search_path = Path(path) if path else self.current_path or Path.home()
        results = []
        
        try:
            for item in search_path.rglob(f"*{query}*"):
                if len(results) >= 100:  # 限制结果数量
                    break
                
                results.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "folder" if item.is_dir() else "file",
                    "extension": item.suffix.lower() if item.is_file() else None
                })
        except Exception as e:
            logger.error(f"搜索失败: {e}")
        
        return results


# 全局实例
folder_browser = FolderBrowser()