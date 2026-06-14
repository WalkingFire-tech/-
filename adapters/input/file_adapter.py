"""
文件/文件夹输入适配器
支持拖拽、选择文件,自动提取内容并触发处理
"""
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger
from infrastructure.event_bus import bus


class FileInputAdapter:
    """文件输入适配器"""
    
    def __init__(self, allowed_base_dir: Optional[Path] = None):
        # 设置允许的根目录（沙盒）
        self.allowed_base_dir = (allowed_base_dir or Path.cwd()).resolve()
        
        self.supported_extensions = {
            # 文本文件
            '.txt', '.md', '.rst', '.log',
            # 代码文件
            '.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs',
            '.html', '.css', '.json', '.xml', '.yaml', '.yml',
            # 配置文件
            '.ini', '.cfg', '.conf', '.env',
            # 数据文件
            '.csv', '.tsv',
        }
        
        self.binary_extensions = {
            '.pdf', '.docx', '.doc', '.xlsx', '.xls',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp',
            '.zip', '.tar', '.gz',
            '.exe', '.dll', '.so'
        }
        
        logger.info(f"文件输入适配器初始化完成 (沙盒目录: {self.allowed_base_dir})")
    
    def _is_path_allowed(self, path: Path) -> bool:
        """检查路径是否在允许的沙盒目录内"""
        try:
            resolved = path.resolve()
            # 检查是否在允许目录内
            return str(resolved).startswith(str(self.allowed_base_dir))
        except (OSError, RuntimeError) as e:
            logger.warning(f"路径解析失败: {e}")
            return False
    
    def on_file_selected(self, file_path: str, user_instruction: str = None) -> Dict:
        """处理单个文件选择"""
        path = Path(file_path)
        
        # 安全检查：路径白名单
        if not self._is_path_allowed(path):
            logger.error(f"路径越权访问: {file_path}")
            return {
                "success": False,
                "error": "路径越权：文件不在允许的目录内"
            }
        
        if not path.exists():
            logger.error(f"文件不存在: {file_path}")
            return {
                "success": False,
                "error": "文件不存在"
            }
        
        if not path.is_file():
            logger.error(f"不是文件: {file_path}")
            return {
                "success": False,
                "error": "不是文件"
            }
        
        logger.info(f"处理文件: {path.name}")
        
        # 提取内容
        content, metadata = self._extract_content(path)
        
        # 构建事件数据
        event_data = {
            "type": "file",
            "path": str(path.absolute()),
            "filename": path.name,
            "extension": path.suffix.lower(),
            "content": content,
            "metadata": metadata,
            "instruction": user_instruction,
            "timestamp": datetime.now().isoformat()
        }
        
        # 发布事件
        bus.publish("file_input", event_data)
        
        logger.info(f"文件事件已发布: {path.name}")
        
        return {
            "success": True,
            "event": event_data
        }
    
    def on_folder_selected(self, folder_path: str, user_instruction: str = None,
                          recursive: bool = True, max_files: int = 100) -> Dict:
        """处理文件夹选择"""
        path = Path(folder_path)
        
        # 安全检查：路径白名单
        if not self._is_path_allowed(path):
            logger.error(f"路径越权访问: {folder_path}")
            return {
                "success": False,
                "error": "路径越权：文件夹不在允许的目录内"
            }
        
        if not path.exists():
            logger.error(f"文件夹不存在: {folder_path}")
            return {
                "success": False,
                "error": "文件夹不存在"
            }
        
        if not path.is_dir():
            logger.error(f"不是文件夹: {folder_path}")
            return {
                "success": False,
                "error": "不是文件夹"
            }
        
        logger.info(f"处理文件夹: {path.name}")
        
        # 列出文件
        files = self._list_files(path, recursive=recursive, max_files=max_files)
        
        # 构建事件数据
        event_data = {
            "type": "folder",
            "path": str(path.absolute()),
            "foldername": path.name,
            "files": files,
            "file_count": len(files),
            "instruction": user_instruction,
            "recursive": recursive,
            "timestamp": datetime.now().isoformat()
        }
        
        # 发布事件
        bus.publish("folder_input", event_data)
        
        logger.info(f"文件夹事件已发布: {len(files)}个文件")
        
        return {
            "success": True,
            "event": event_data
        }
    
    def _extract_content(self, path: Path) -> Tuple[str, Dict]:
        """提取文件内容"""
        ext = path.suffix.lower()
        metadata = {
            "size": path.stat().st_size,
            "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            "extension": ext
        }
        
        # 文本文件
        if ext in self.supported_extensions:
            try:
                # 尝试多种编码
                for encoding in ['utf-8', 'gbk', 'gb2312', 'latin1']:
                    try:
                        with open(path, 'r', encoding=encoding) as f:
                            content = f.read()
                        
                        metadata["encoding"] = encoding
                        metadata["lines"] = content.count('\n') + 1
                        
                        logger.debug(f"读取文本文件: {path.name} ({encoding})")
                        return content, metadata
                    except UnicodeDecodeError:
                        continue
                
                # 所有编码都失败
                return f"[无法解码文件: {path.name}]", metadata
            
            except Exception as e:
                logger.error(f"读取文件失败: {e}")
                return f"[读取失败: {str(e)}]", metadata
        
        # 二进制文件
        elif ext in self.binary_extensions:
            metadata["is_binary"] = True
            return f"[二进制文件: {path.name}, 大小: {metadata['size']}字节]", metadata
        
        # 未知类型
        else:
            # 尝试作为文本读取
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                metadata["lines"] = content.count('\n') + 1
                return content, metadata
            except:
                metadata["is_binary"] = True
                return f"[未知类型文件: {path.name}]", metadata
    
    def _list_files(self, folder: Path, recursive: bool = True, 
                   max_files: int = 100) -> List[Dict]:
        """列出文件夹中的文件（安全增强）"""
        files = []
        
        if recursive:
            pattern = '**/*'
        else:
            pattern = '*'
        
        for item in folder.glob(pattern):
            if len(files) >= max_files:
                logger.warning(f"文件数量达到上限: {max_files}")
                break
            
            # 安全检查：跳过符号链接
            if item.is_symlink():
                logger.debug(f"跳过符号链接: {item}")
                continue
            
            # 安全检查：验证路径在沙盒内
            if not self._is_path_allowed(item):
                logger.warning(f"跳过越权路径: {item}")
                continue
            
            if item.is_file():
                file_info = {
                    "path": str(item.absolute()),
                    "name": item.name,
                    "extension": item.suffix.lower(),
                    "size": item.stat().st_size,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                }
                files.append(file_info)
        
        return files
    
    def get_file_type(self, file_path: str) -> str:
        """获取文件类型"""
        ext = Path(file_path).suffix.lower()
        
        if ext in {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs'}:
            return "code"
        elif ext in {'.txt', '.md', '.rst'}:
            return "text"
        elif ext in {'.csv', '.tsv', '.json', '.xml'}:
            return "data"
        elif ext in {'.jpg', '.jpeg', '.png', '.gif'}:
            return "image"
        elif ext in {'.pdf', '.docx', '.doc', '.xlsx'}:
            return "document"
        else:
            return "unknown"
    
    def should_process(self, file_path: str) -> bool:
        """判断是否应该处理该文件"""
        path = Path(file_path)
        
        # 跳过隐藏文件
        if path.name.startswith('.'):
            return False
        
        # 跳过临时文件
        if path.suffix in {'.tmp', '.temp', '.bak'}:
            return False
        
        # 跳过过大文件(>10MB)
        if path.stat().st_size > 10 * 1024 * 1024:
            logger.warning(f"文件过大,跳过: {path.name}")
            return False
        
        return True


# 全局实例
file_adapter = FileInputAdapter()