"""
L1 预防层 - 输入验证增强 (Input Sanitizer)

类比：皮肤屏障
- 阻挡有害输入进入系统内部
- 清洗、截断、脱敏
- 注入攻击检测
"""
import re
import html
from typing import Optional, Tuple
from loguru import logger


class InputSanitizer:
    MAX_INPUT_LENGTH = 10000
    DANGEROUS_PATTERNS = [
        (r'(\bDROP\s+TABLE\b)', "SQL注入: DROP TABLE"),
        (r'(\bDELETE\s+FROM\b)', "SQL注入: DELETE FROM"),
        (r'(\bINSERT\s+INTO\b)', "SQL注入: INSERT INTO"),
        (r'(\bUPDATE\s+\w+\s+SET\b)', "SQL注入: UPDATE SET"),
        (r'(<script[^>]*>)', "XSS: script标签"),
        (r'(javascript\s*:)', "XSS: javascript协议"),
        (r'(\bon\w+\s*=)', "XSS: 事件处理器"),
        (r'(\.\.[\\/])', "路径遍历"),
        (r'(__import__\s*\()', "Python注入: __import__"),
        (r'(exec\s*\()', "Python注入: exec"),
        (r'(eval\s*\()', "Python注入: eval"),
        (r'(os\.system\s*\()', "Python注入: os.system"),
        (r'(subprocess\.)', "Python注入: subprocess"),
    ]

    def __init__(self, max_length: int = None):
        self.max_length = max_length or self.MAX_INPUT_LENGTH

    def sanitize(self, raw_input: str) -> Tuple[str, Optional[str]]:
        if not raw_input:
            return "", None
        raw_input = raw_input.strip()
        threat = self._detect_threats(raw_input)
        if threat:
            logger.warning(f"🛡️ 输入威胁检测: {threat}")
            raw_input = self._neutralize(raw_input, threat)
        raw_input = raw_input[:self.max_length]
        raw_input = html.escape(raw_input) if self._has_html_chars(raw_input) else raw_input
        raw_input = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw_input)
        raw_input = raw_input.strip().rstrip("/\\|")
        return raw_input, threat

    def _detect_threats(self, text: str) -> Optional[str]:
        text_upper = text.upper()
        for pattern, label in self.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return label
        return None

    def _neutralize(self, text: str, threat: str) -> str:
        if "SQL注入" in threat or "Python注入" in threat:
            text = re.sub(r'[;\-\-]', '', text)
        if "XSS" in threat:
            text = html.escape(text)
        if "路径遍历" in threat:
            text = re.sub(r'\.\.[/\\]', '', text)
        return text

    def _has_html_chars(self, text: str) -> bool:
        return bool(re.search(r'[<>&"]', text))

    def is_safe(self, raw_input: str) -> bool:
        _, threat = self.sanitize(raw_input)
        return threat is None


input_sanitizer = InputSanitizer()