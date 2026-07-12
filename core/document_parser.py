"""
文档解析器 - 支持多种文档格式提取纯文本
"""
import os
from pathlib import Path
import re
from loguru import logger


def extract_text_from_file(file_path: str) -> str:
    """
    从各种文档格式中提取纯文本
    
    支持格式: .txt, .md, .py, .js, .html, .css, .json, .yaml, .yml,
              .pdf, .docx, .xlsx, .xls, .csv
    """
    ext = Path(file_path).suffix.lower()
    
    try:
        # 文本类文件直接读取
        if ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.yaml', '.yml', '.rst', '.xml', '.sql', '.ts', '.tsx', '.jsx', '.vue', '.go', '.java', '.c', '.cpp', '.h', '.sh', '.bat']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        
        # PDF
        elif ext == '.pdf':
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ''
                    for page in reader.pages:
                        text += page.extract_text() or ''
                    return text
            except ImportError:
                logger.warning("PyPDF2 未安装，无法解析PDF")
                return ""
        
        # Word
        elif ext == '.docx':
            try:
                import docx
                doc = docx.Document(file_path)
                return "\n".join([para.text for para in doc.paragraphs])
            except ImportError:
                logger.warning("python-docx 未安装，无法解析Word")
                return ""
        
        # Excel
        elif ext in ['.xlsx', '.xls']:
            try:
                import pandas as pd
                df = pd.read_excel(file_path, engine='openpyxl' if ext == '.xlsx' else None)
                return df.to_string()
            except ImportError:
                logger.warning("pandas 未安装，无法解析Excel")
                return ""
        
        # CSV
        elif ext == '.csv':
            try:
                import pandas as pd
                df = pd.read_csv(file_path)
                return df.to_string()
            except ImportError:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        
        else:
            # 尝试作为文本读取（忽略二进制）
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # 检查是否为二进制
                    if '\x00' in content or len(content) == 0:
                        return ""
                    return content
            except Exception:
                return ""
    
    except Exception as e:
        logger.error(f"解析文档失败 {file_path}: {e}")
        return ""


def extract_text_batch(file_paths: list) -> dict:
    """批量提取文本，返回 {路径: 文本}"""
    results = {}
    for path in file_paths:
        results[path] = extract_text_from_file(path)
    return results


def get_supported_extensions() -> set:
    """获取支持的文件扩展名"""
    return {
        '.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.yaml', '.yml', 
        '.rst', '.xml', '.sql', '.ts', '.tsx', '.jsx', '.vue', '.go', '.java', 
        '.c', '.cpp', '.h', '.sh', '.bat', '.pdf', '.docx', '.xlsx', '.xls', '.csv'
    }