import re
from loguru import logger

class SelfAudit:
    """输出自我审核模块：检查危险操作、隐私泄露、格式正确性"""

    # 危险模式（文件删除、系统命令、权限修改等）
    DANGEROUS_PATTERNS = [
        (re.compile(r'rm\s+-rf\s+/', re.IGNORECASE), "危险：递归强制删除根目录"),
        (re.compile(r'drop\s+database', re.IGNORECASE), "危险：删除数据库"),
        (re.compile(r'format\s+[a-z]:', re.IGNORECASE), "危险：格式化磁盘"),
        (re.compile(r'chmod\s+777', re.IGNORECASE), "危险：设置过高文件权限"),
        (re.compile(r'os\.remove\(', re.IGNORECASE), "危险：Python删除文件操作"),
        (re.compile(r'shutil\.rmtree\(', re.IGNORECASE), "危险：递归删除目录"),
        (re.compile(r'子进程|subprocess|exec\(|eval\(', re.IGNORECASE), "警告：执行动态代码"),
    ]

    # 隐私模式（身份证、手机号、邮箱等）
    PRIVACY_PATTERNS = [
        (re.compile(r'\b\d{17}[\dXx]\b'), "疑似身份证号"),
        (re.compile(r'\b1[3-9]\d{9}\b'), "疑似手机号"),
        (re.compile(r'\b[\w\.-]+@[\w\.-]+\.\w+\b'), "疑似邮箱地址"),
    ]

    @classmethod
    def audit(cls, text: str, task_type: str = "chat") -> dict:
        """
        审核输出文本
        返回: {"passed": bool, "warnings": list, "blocked": bool, "reason": str}
        """
        warnings = []
        blocked = False
        reason = ""

        # 检查危险模式
        for pattern, msg in cls.DANGEROUS_PATTERNS:
            if pattern.search(text):
                warnings.append(msg)
                blocked = True
                reason = msg
                break

        # 如果是代码任务，允许输出代码内容，但警告危险命令
        if task_type == "code" and not blocked:
            # 代码中的危险操作仍然警告，但不直接拦截（可以后续选择）
            for pattern, msg in cls.DANGEROUS_PATTERNS:
                if pattern.search(text):
                    warnings.append(f"[代码警告] {msg}")

        # 检查隐私（仅在非信任模式下，或可以脱敏）
        for pattern, msg in cls.PRIVACY_PATTERNS:
            if pattern.search(text):
                warnings.append(f"可能包含隐私信息：{msg}")

        return {
            "passed": not blocked,
            "warnings": warnings,
            "blocked": blocked,
            "reason": reason
        }
