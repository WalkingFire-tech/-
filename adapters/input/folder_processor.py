"""
文件夹批量处理器 - 处理文件夹输入事件
支持自动分析、批量操作等
"""
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime
from loguru import logger
from infrastructure.event_bus import bus
from adapters.input.file_adapter import file_adapter


class FolderBatchProcessor:
    """文件夹批量处理器"""
    
    def __init__(self):
        self.max_concurrent = 5
        self.processors = {
            "code": self._process_code_file,
            "document": self._process_document_file,
            "data": self._process_data_file,
            "text": self._process_text_file
        }
        
        bus.subscribe("folder_input", self.on_folder_input)
        
        logger.info("文件夹批量处理器初始化完成")
    
    async def on_folder_input(self, event_data: Dict):
        """处理文件夹输入事件"""
        folder_path = event_data["path"]
        files = event_data["files"]
        instruction = event_data.get("instruction", "分析这些文件")
        
        logger.info(f"开始批量处理文件夹: {folder_path} ({len(files)}个文件)")
        
        results = {
            "folder": folder_path,
            "total_files": len(files),
            "processed": 0,
            "failed": 0,
            "results": []
        }
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        tasks = []
        for file_info in files:
            task = self._process_file_with_semaphore(
                semaphore, file_info, instruction
            )
            tasks.append(task)
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"处理失败: {result}")
                results["failed"] += 1
            else:
                results["processed"] += 1
                results["results"].append(result)
        
        bus.publish("folder_processing_complete", results)
        
        logger.info(f"文件夹处理完成: {results['processed']}/{results['total_files']}")
        
        return results
    
    async def _process_file_with_semaphore(
        self, semaphore: asyncio.Semaphore, 
        file_info: Dict, instruction: str
    ) -> Dict:
        """使用信号量控制并发"""
        async with semaphore:
            return await self._process_single_file(file_info, instruction)
    
    async def _process_single_file(self, file_info: Dict, instruction: str) -> Dict:
        """处理单个文件"""
        file_path = file_info["path"]
        file_type = file_adapter.get_file_type(file_path)
        
        logger.debug(f"处理文件: {file_info['name']} (类型: {file_type})")
        
        processor = self.processors.get(file_type, self._process_generic_file)
        
        try:
            result = await processor(file_info, instruction)
            
            return {
                "file": file_path,
                "type": file_type,
                "status": "success",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"处理文件失败 {file_info['name']}: {e}")
            
            return {
                "file": file_path,
                "type": file_type,
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _process_code_file(self, file_info: Dict, instruction: str) -> Dict:
        """处理代码文件"""
        file_path = Path(file_info["path"])
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.count('\n') + 1
        functions = content.count('def ')
        classes = content.count('class ')
        imports = content.count('import ')
        
        return {
            "lines": lines,
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "size": file_info["size"]
        }
    
    async def _process_document_file(self, file_info: Dict, instruction: str) -> Dict:
        """处理文档文件"""
        file_path = Path(file_info["path"])
        ext = file_path.suffix.lower()
        
        if ext in {'.md', '.txt', '.rst'}:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            words = len(content.split())
            paragraphs = content.count('\n\n') + 1
            
            return {
                "words": words,
                "paragraphs": paragraphs,
                "size": file_info["size"]
            }
        
        else:
            return {
                "type": "binary_document",
                "size": file_info["size"]
            }
    
    async def _process_data_file(self, file_info: Dict, instruction: str) -> Dict:
        """处理数据文件"""
        file_path = Path(file_info["path"])
        ext = file_path.suffix.lower()
        
        if ext == '.json':
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                return {
                    "type": "array",
                    "count": len(data),
                    "size": file_info["size"]
                }
            elif isinstance(data, dict):
                return {
                    "type": "object",
                    "keys": len(data),
                    "size": file_info["size"]
                }
        
        elif ext == '.csv':
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            return {
                "rows": len(lines) - 1,
                "columns": len(lines[0].split(',')) if lines else 0,
                "size": file_info["size"]
            }
        
        return {
            "type": "data",
            "size": file_info["size"]
        }
    
    async def _process_text_file(self, file_info: Dict, instruction: str) -> Dict:
        """处理文本文件"""
        file_path = Path(file_info["path"])
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        lines = content.count('\n') + 1
        words = len(content.split())
        
        return {
            "lines": lines,
            "words": words,
            "size": file_info["size"]
        }
    
    async def _process_generic_file(self, file_info: Dict, instruction: str) -> Dict:
        """处理通用文件"""
        return {
            "type": "generic",
            "size": file_info["size"],
            "extension": file_info["extension"]
        }
    
    def register_processor(self, file_type: str, processor: Callable):
        """注册自定义处理器"""
        self.processors[file_type] = processor
        logger.info(f"注册文件处理器: {file_type}")
    
    async def analyze_folder(self, folder_path: str, instruction: str = None) -> Dict:
        """主动分析文件夹"""
        event = file_adapter.on_folder_selected(
            folder_path, 
            user_instruction=instruction,
            recursive=True,
            max_files=100
        )
        
        if not event["success"]:
            return event
        
        return await self.on_folder_input(event["event"])


folder_processor = FolderBatchProcessor()