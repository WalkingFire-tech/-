"""
内容提取器模块 - 统一导出

提供多种文件内容提取器：
- TextExtractor: 纯文本文件
- CodeExtractor: 代码文件（提取关键结构）
- PDFExtractor: PDF文档（支持多库备选）
- DocxExtractor: Word文档
"""

from .base import ContentExtractor
from .text_extractor import TextExtractor
from .code_extractor import CodeExtractor
from .pdf_extractor import PDFExtractor
from .docx_extractor import DocxExtractor


__all__ = [
    'ContentExtractor',
    'TextExtractor',
    'CodeExtractor',
    'PDFExtractor',
    'DocxExtractor',
]


def get_default_extractors():
    """获取默认提取器列表"""
    return [
        CodeExtractor(),
        PDFExtractor(),
        DocxExtractor(),
        TextExtractor(),
    ]