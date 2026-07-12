"""
PDF提取器 - 增强版

支持多个后端库，自动降级：
1. pypdf (PyPDF2升级版) - 最常用
2. pdfplumber - 提取文本布局更准确
3. PyMuPDF (fitz) - 速度快，支持扫描件OCR
4. 最终降级：返回错误信息

处理场景：
- 加密PDF：提示需要密码
- 扫描件：尝试OCR (如果Tesseract可用)
- 损坏PDF：返回错误信息
- 空PDF：返回空内容
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from loguru import logger

from .base import ContentExtractor


class PDFExtractor(ContentExtractor):
    """PDF提取器 - 增强版"""
    
    def __init__(self, use_ocr: bool = False, ocr_lang: str = 'chi_sim+eng'):
        """
        Args:
            use_ocr: 是否尝试OCR识别扫描件（需要安装pytesseract和Tesseract）
            ocr_lang: OCR语言（默认中文简体+英文）
        """
        self.use_ocr = use_ocr
        self.ocr_lang = ocr_lang
        
        self.backends = self._detect_backends()
        self._available = any(self.backends.values())
        
        if not self._available:
            logger.warning("没有可用的PDF库，PDF提取将失败")
        else:
            available_libs = [k for k, v in self.backends.items() if v]
            logger.info(f"PDF支持库: {available_libs}")
    
    def _detect_backends(self) -> Dict[str, bool]:
        """检测可用的PDF库"""
        backends = {}
        
        try:
            import pypdf
            backends['pypdf'] = True
        except ImportError:
            try:
                import PyPDF2
                backends['pypdf'] = True
            except ImportError:
                backends['pypdf'] = False
        
        try:
            import pdfplumber
            backends['pdfplumber'] = True
        except ImportError:
            backends['pdfplumber'] = False
        
        try:
            import fitz
            backends['fitz'] = True
        except ImportError:
            backends['fitz'] = False
        
        if self.use_ocr:
            try:
                import pytesseract
                from PIL import Image
                backends['ocr'] = True
            except ImportError:
                backends['ocr'] = False
        else:
            backends['ocr'] = False
        
        return backends
    
    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.pdf' and self._available
    
    def extract(self, file_path: Path) -> Optional[str]:
        """提取PDF文本，自动尝试多个后端"""
        if not self._available:
            return None
        
        methods = [
            ('pypdf', self._extract_with_pypdf),
            ('pdfplumber', self._extract_with_pdfplumber),
            ('fitz', self._extract_with_fitz),
        ]
        
        if self.backends.get('ocr'):
            methods.append(('ocr', self._extract_with_ocr))
        
        errors = []
        for name, method in methods:
            if not self.backends.get(name):
                continue
            
            try:
                result = method(file_path)
                if result and result.strip():
                    logger.warning(f"PDF提取成功: {name}")
                    return result
                elif result == '':
                    return ''
            except Exception as e:
                error_msg = f"{name}: {str(e)[:100]}"
                logger.error(f"PDF {name} 提取失败: {error_msg}")
                errors.append(error_msg)
                continue
        
        error_summary = '; '.join(errors[:3])
        logger.warning(f"PDF提取失败 {file_path}: {error_summary}")
        
        return f"[PDF提取失败: {error_summary}]"
    
    def _extract_with_pypdf(self, file_path: Path) -> Optional[str]:
        """使用 pypdf 提取"""
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            
            if reader.is_encrypted:
                try:
                    reader.decrypt('')
                except Exception:
                    raise ValueError("PDF已加密，需要密码")
            
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(text.strip())
            
            if not text_parts:
                return ''
            
            return '\n\n'.join(text_parts)
        
        except ImportError:
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(str(file_path))
                if reader.is_encrypted:
                    try:
                        reader.decrypt('')
                    except Exception:
                        raise ValueError("PDF已加密，需要密码")
                
                text_parts = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text and text.strip():
                        text_parts.append(text.strip())
                
                return '\n\n'.join(text_parts) if text_parts else ''
            except ImportError:
                raise RuntimeError("pypdf/PyPDF2 不可用")
    
    def _extract_with_pdfplumber(self, file_path: Path) -> Optional[str]:
        """使用 pdfplumber 提取（更准确）"""
        try:
            import pdfplumber
            
            with pdfplumber.open(str(file_path)) as pdf:
                text_parts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and text.strip():
                        text_parts.append(text.strip())
                
                return '\n\n'.join(text_parts) if text_parts else ''
        except Exception as e:
            logger.error(f"pdfplumber 失败: {e}")
            raise
    
    def _extract_with_fitz(self, file_path: Path) -> Optional[str]:
        """使用 PyMuPDF 提取（最快）"""
        try:
            import fitz
            
            doc = fitz.open(str(file_path))
            text_parts = []
            
            for page in doc:
                text = page.get_text()
                if text and text.strip():
                    text_parts.append(text.strip())
            
            doc.close()
            return '\n\n'.join(text_parts) if text_parts else ''
        except Exception as e:
            logger.error(f"fitz 失败: {e}")
            raise
    
    def _extract_with_ocr(self, file_path: Path) -> Optional[str]:
        """使用OCR识别扫描件（需要 pytesseract + Tesseract）"""
        try:
            import pytesseract
            from PIL import Image
            import fitz
            
            doc = fitz.open(str(file_path))
            text_parts = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("ppm")
                
                from io import BytesIO
                img = Image.open(BytesIO(img_data))
                
                text = pytesseract.image_to_string(img, lang=self.ocr_lang)
                if text and text.strip():
                    text_parts.append(text.strip())
            
            doc.close()
            return '\n\n'.join(text_parts) if text_parts else ''
            
        except Exception as e:
            logger.error(f"OCR 失败: {e}")
            raise

    def get_supported_extensions(self) -> List[str]:
        return ['.pdf']
    
    def get_name(self) -> str:
        return "PDFExtractor"