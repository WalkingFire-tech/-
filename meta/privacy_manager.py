"""
用户隐私控制 - 数据遗忘、导出和导入
实现GDPR级别的隐私保护
"""
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
from infrastructure.event_bus import bus


class PrivacyManager:
    """隐私管理器"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        
        self.user_data_files = [
            "learning_rules.json",
            "learning_history.json",
            "intent_learning.json",
            "plan_corrections.db",
            "active_learning_questions.json",
            "model_stats.json",
            "experience_pool.json",
            "user_preferences.json"
        ]
        
        logger.info("隐私管理器初始化完成")
    
    def forget_me(self, confirm: bool = False) -> Dict:
        """清除用户所有学习数据
        
        Args:
            confirm: 确认删除(必须为True才执行)
        """
        if not confirm:
            logger.warning("遗忘命令需要确认: forget_me(confirm=True)")
            return {
                "success": False,
                "error": "需要确认才能执行遗忘"
            }
        
        logger.warning("执行用户数据遗忘...")
        
        deleted_files = []
        failed_files = []
        
        for filename in self.user_data_files:
            file_path = self.data_dir / filename
            
            if file_path.exists():
                try:
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        shutil.rmtree(file_path)
                    
                    deleted_files.append(filename)
                    logger.info(f"已删除: {filename}")
                
                except Exception as e:
                    failed_files.append((filename, str(e)))
                    logger.error(f"删除失败 {filename}: {e}")
        
        self._clear_experience_pool()
        
        bus.publish("user_data_forgotten", {
            "timestamp": datetime.now().isoformat(),
            "deleted_files": deleted_files
        })
        
        logger.info(f"✓ 用户数据遗忘完成: 删除{len(deleted_files)}个文件")
        
        return {
            "success": True,
            "deleted_files": deleted_files,
            "failed_files": failed_files,
            "message": "所有用户学习数据已清除"
        }
    
    def export_data(self, export_path: str = None) -> Dict:
        """导出用户数据
        
        Args:
            export_path: 导出文件路径(可选)
        """
        logger.info("导出用户数据...")
        
        if export_path is None:
            export_path = f"user_data_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_file = Path(export_path)
        
        data = {
            "export_time": datetime.now().isoformat(),
            "version": "1.0",
            "data": {}
        }
        
        for filename in self.user_data_files:
            file_path = self.data_dir / filename
            
            if file_path.exists() and file_path.is_file():
                try:
                    if filename.endswith('.json'):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data["data"][filename] = json.load(f)
                    elif filename.endswith('.db'):
                        data["data"][filename] = f"[数据库文件: {file_path.stat().st_size}字节]"
                    else:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            data["data"][filename] = f.read()
                
                except Exception as e:
                    logger.error(f"导出失败 {filename}: {e}")
                    data["data"][filename] = f"[导出失败: {str(e)}]"
        
        try:
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✓ 用户数据已导出: {export_file}")
            
            return {
                "success": True,
                "export_file": str(export_file),
                "size": export_file.stat().st_size,
                "files_exported": len(data["data"])
            }
        
        except Exception as e:
            logger.error(f"导出失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def import_data(self, import_path: str, overwrite: bool = False) -> Dict:
        """导入用户数据
        
        Args:
            import_path: 导入文件路径
            overwrite: 是否覆盖已存在的数据
        """
        import_file = Path(import_path)
        
        if not import_file.exists():
            return {
                "success": False,
                "error": f"导入文件不存在: {import_path}"
            }
        
        logger.info(f"导入用户数据: {import_file}")
        
        try:
            with open(import_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if "data" not in data:
                return {
                    "success": False,
                    "error": "无效的导入文件格式"
                }
            
            imported_files = []
            skipped_files = []
            failed_files = []
            
            for filename, content in data["data"].items():
                file_path = self.data_dir / filename
                
                if file_path.exists() and not overwrite:
                    skipped_files.append(filename)
                    continue
                
                try:
                    if isinstance(content, str) and content.startswith("["):
                        logger.debug(f"跳过特殊数据: {filename}")
                        continue
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(content, f, ensure_ascii=False, indent=2)
                    
                    imported_files.append(filename)
                
                except Exception as e:
                    failed_files.append((filename, str(e)))
                    logger.error(f"导入失败 {filename}: {e}")
            
            bus.publish("user_data_imported", {
                "timestamp": datetime.now().isoformat(),
                "imported_files": imported_files
            })
            
            logger.info(f"✓ 用户数据导入完成: 导入{len(imported_files)}个文件")
            
            return {
                "success": True,
                "imported_files": imported_files,
                "skipped_files": skipped_files,
                "failed_files": failed_files,
                "message": f"成功导入{len(imported_files)}个文件"
            }
        
        except Exception as e:
            logger.error(f"导入失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _clear_experience_pool(self):
        """清除经验池中的用户数据"""
        experience_file = self.data_dir / "experience_pool.json"
        
        if experience_file.exists():
            try:
                with open(experience_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, dict):
                    data["experiences"] = []
                    data["user_interactions"] = []
                    
                    with open(experience_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    logger.info("已清除经验池用户数据")
            
            except Exception as e:
                logger.error(f"清除经验池失败: {e}")
    
    def get_data_summary(self) -> Dict:
        """获取数据摘要"""
        summary = {
            "data_dir": str(self.data_dir),
            "files": {}
        }
        
        total_size = 0
        
        for filename in self.user_data_files:
            file_path = self.data_dir / filename
            
            if file_path.exists():
                size = file_path.stat().st_size if file_path.is_file() else 0
                total_size += size
                
                summary["files"][filename] = {
                    "exists": True,
                    "size": size,
                    "modified": datetime.fromtimestamp(
                        file_path.stat().st_mtime
                    ).isoformat() if file_path.is_file() else None
                }
            else:
                summary["files"][filename] = {
                    "exists": False
                }
        
        summary["total_size"] = total_size
        summary["total_size_mb"] = total_size / (1024 * 1024)
        
        return summary
    
    def anonymize_data(self) -> Dict:
        """匿名化数据(移除敏感信息)"""
        logger.info("匿名化用户数据...")
        
        anonymized_files = []
        
        intent_learning = self.data_dir / "intent_learning.json"
        if intent_learning.exists():
            try:
                with open(intent_learning, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, dict):
                    for key in data:
                        if "user_input" in data[key]:
                            data[key]["user_input"] = "[匿名化]"
                        if "raw_text" in data[key]:
                            data[key]["raw_text"] = "[匿名化]"
                    
                    with open(intent_learning, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    
                    anonymized_files.append("intent_learning.json")
            
            except Exception as e:
                logger.error(f"匿名化失败: {e}")
        
        logger.info(f"✓ 数据匿名化完成: {len(anonymized_files)}个文件")
        
        return {
            "success": True,
            "anonymized_files": anonymized_files
        }


privacy_manager = PrivacyManager()