"""
价值对齐检查器 - 确保学习内容与系统核心价值一致

核心理念：
- 学习可以改变"知道什么"，但不能改变"相信什么"
- 任何与核心价值观冲突的内容，必须被过滤或标记

三层防护：
1. 来源验证（白/灰/黑名单）
2. 红线检查（不可逾越的底线）
3. 价值对齐检查（与核心价值观一致性）
"""

from typing import Dict, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class AlignmentStatus(Enum):
    """对齐状态"""
    PASS = "pass"
    PARTIAL = "partial"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


@dataclass
class ValueAlignmentResult:
    """价值对齐检查结果"""
    status: AlignmentStatus
    score: float
    issues: List[str]
    reasoning: str
    requires_human_review: bool


class ValueAlignmentChecker:
    """
    价值对齐检查器
    
    检查学习内容是否与系统的核心价值观一致。
    """
    
    def __init__(self, config_path: str = "config/value_alignment.json"):
        self.config_path = Path(config_path)
        self.core_values = self._load_core_values()
        self.ethical_boundaries = self._load_ethical_boundaries()
        self.trust_policy = self._load_trust_policy()
        
        logger.info("🛡️ 价值对齐检查器已初始化")
    
    def _load_core_values(self) -> Dict:
        """加载核心价值观"""
        return {
            "principles": [
                "反思即行动",
                "学习即基因",
                "错误即肥料",
                "输出即透明",
                "进化即存在",
                "保持善意",
                "保持开放",
                "不渡他人（只提供镜子，不替人走路）",
                "知止（敢于承认不知道）",
                "守底线（善意不是纵容）",
                "可被质疑（欢迎批评和挑战）"
            ],
            "forbidden": [
                "散布虚假信息",
                "恶意攻击他人",
                "协助非法活动",
                "替代专业判断（医疗、法律）",
                "欺骗或操纵用户",
                "侵犯隐私",
                "传播仇恨",
                "诱导自伤"
            ]
        }
    
    def _load_ethical_boundaries(self) -> Dict:
        """加载伦理边界"""
        return {
            "red_lines": {
                "危害他人安全": ["伤害", "暴力", "攻击", "欺凌", "虐待", "杀人", "殴打"],
                "侵犯隐私": ["隐私", "泄露", "个人信息", "账号密码", "身份证", "银行卡"],
                "传播仇恨": ["仇恨", "歧视", "种族歧视", "性别歧视", "宗教歧视"],
                "诱导自伤": ["自杀", "自残", "伤害自己", "结束生命"],
                "非法行为": ["违法", "非法", "犯罪", "诈骗", "盗窃", "贩毒"],
                "欺骗操纵": ["欺骗", "操纵", "误导", "虚假", "伪造"]
            },
            "yellow_lines": {
                "医疗建议": ["治疗", "用药", "诊断", "疾病", "医疗", "手术", "药物"],
                "法律建议": ["法律", "合同", "诉讼", "律师", "法庭", "判决"],
                "误导信息": ["保证", "100%", "绝对", "一定是", "永远正确"],
                "越界建议": ["你应该", "你必须", "你一定要", "你不准"]
            }
        }
    
    def _load_trust_policy(self) -> Dict:
        """加载信任策略"""
        return {
            "whitelist": [
                "本地知识库", "本地学术库", "arXiv", "PubMed",
                "IEEE Xplore", "Semantic Scholar", "CORE",
                "维基百科", "百度百科", "DeepSeek"
            ],
            "greylist": [
                "知乎", "CSDN", "博客园", "简书", "GitHub", "Stack Overflow"
            ],
            "blacklist": [],
            "academic_domains": [
                ".edu", ".ac.", ".scholar.", "arxiv.org",
                "pubmed.ncbi.nlm.nih.gov", "semanticscholar.org"
            ]
        }
    
    def check(self, content: str, source: str, metadata: Dict = None) -> ValueAlignmentResult:
        """
        检查内容是否与核心价值对齐
        
        Args:
            content: 要学习的内容
            source: 内容来源
            metadata: 元数据（可选）
        """
        issues = []
        score = 0.5
        status = AlignmentStatus.UNKNOWN
        metadata = metadata or {}
        
        source_check = self._check_source_trustworthiness(source)
        if not source_check["trusted"]:
            issues.append(f"来源可信度低: {source} - {source_check['reason']}")
            score -= 0.2
        
        red_line_violations = self._check_red_lines(content)
        if red_line_violations:
            issues.extend(red_line_violations)
            return ValueAlignmentResult(
                status=AlignmentStatus.CONFLICT,
                score=0.0,
                issues=issues,
                reasoning=f"违反红线条款: {', '.join(red_line_violations[:2])}",
                requires_human_review=True
            )
        
        yellow_line_violations = self._check_yellow_lines(content)
        if yellow_line_violations:
            issues.extend(yellow_line_violations)
            score -= 0.15
        
        value_check = self._check_core_values_alignment(content)
        issues.extend(value_check["issues"])
        score = (score + value_check["score"]) / 2
        
        if source_check["trusted"]:
            score += 0.1
        
        if score >= 0.7 and not issues:
            status = AlignmentStatus.PASS
            requires_human_review = False
        elif score >= 0.4:
            status = AlignmentStatus.PARTIAL
            requires_human_review = True
        else:
            status = AlignmentStatus.CONFLICT
            requires_human_review = True
        
        return ValueAlignmentResult(
            status=status,
            score=max(0.0, min(1.0, score)),
            issues=issues,
            reasoning=self._generate_reasoning(status, issues, score),
            requires_human_review=requires_human_review
        )
    
    def _check_source_trustworthiness(self, source: str) -> Dict:
        """检查来源可信度"""
        source_lower = source.lower()
        
        for trusted in self.trust_policy["whitelist"]:
            if trusted.lower() in source_lower:
                return {"trusted": True, "reason": f"白名单来源: {trusted}"}
        
        for grey in self.trust_policy["greylist"]:
            if grey.lower() in source_lower:
                return {"trusted": True, "reason": f"灰名单来源（需审查）: {grey}"}
        
        for pattern in self.trust_policy["blacklist"]:
            if pattern.lower() in source_lower:
                return {"trusted": False, "reason": f"黑名单来源: {pattern}"}
        
        for domain in self.trust_policy["academic_domains"]:
            if domain in source_lower:
                return {"trusted": True, "reason": f"学术来源: {domain}"}
        
        return {"trusted": True, "reason": "未知来源（默认信任）"}
    
    def _check_red_lines(self, content: str) -> List[str]:
        """检查是否违反红线条款"""
        violations = []
        content_lower = content.lower()
        
        for category, keywords in self.ethical_boundaries["red_lines"].items():
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    violations.append(f"⚠️ 红线: {category} (关键词: '{keyword}')")
                    break
        
        return violations
    
    def _check_yellow_lines(self, content: str) -> List[str]:
        """检查是否违反黄线条款"""
        violations = []
        content_lower = content.lower()
        
        for category, keywords in self.ethical_boundaries["yellow_lines"].items():
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    violations.append(f"⚡ 黄线: {category} (关键词: '{keyword}')")
                    break
        
        return violations
    
    def _check_core_values_alignment(self, content: str) -> Dict:
        """检查与核心价值观的对齐度"""
        issues = []
        score = 0.6
        
        if any(kw in content for kw in ["永远正确", "绝对真理", "毋庸置疑", "100%正确"]):
            issues.append("内容可能违背'可被质疑'原则")
            score -= 0.2
        
        if any(kw in content for kw in ["我知道一切", "我无所不知", "我永远是对的"]):
            issues.append("内容可能违背'知止'原则")
            score -= 0.2
        
        if any(kw in content for kw in ["你必须", "你一定要", "你不准"]):
            issues.append("内容可能违背'不渡他人'原则")
            score -= 0.15
        
        if any(kw in content for kw in ["相信我", "相信我说的", "不要质疑"]):
            issues.append("内容可能违背'输出即透明'原则")
            score -= 0.1
        
        return {"score": score, "issues": issues}
    
    def _generate_reasoning(self, status: AlignmentStatus, issues: List[str], score: float) -> str:
        """生成检查原因说明"""
        if status == AlignmentStatus.PASS:
            return f"✅ 内容通过价值对齐检查 (得分: {score:.2f})"
        elif status == AlignmentStatus.PARTIAL:
            return f"⚠️ 内容部分对齐，存在 {len(issues)} 个问题 (得分: {score:.2f})"
        elif status == AlignmentStatus.CONFLICT:
            return f"❌ 内容与核心价值冲突 (问题: {len(issues)})"
        else:
            return "❓ 无法判断对齐状态，需要人工审查"


_value_checker: Optional[ValueAlignmentChecker] = None


def get_value_checker() -> ValueAlignmentChecker:
    global _value_checker
    if _value_checker is None:
        _value_checker = ValueAlignmentChecker()
    return _value_checker


def check_value_alignment(content: str, source: str, metadata: Dict = None) -> ValueAlignmentResult:
    """检查内容是否与核心价值对齐（便捷函数）"""
    return get_value_checker().check(content, source, metadata)