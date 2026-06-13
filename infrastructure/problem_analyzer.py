"""
问题分析器 - 认知层核心组件
不依赖大模型，基于规则、正则、关键词提取结构化信息

核心能力：
- 提取核心诉求
- 识别约束条件
- 提取已知信息
- 识别信息缺口
"""
import re
from typing import Dict, List, Tuple
from loguru import logger
from infrastructure.config_manager import config


class ProblemAnalyzer:
    """问题分析器 - 认知层第一步"""
    
    def __init__(self):
        self.templates = self._load_templates()
        self.keywords = self._load_keywords()
        logger.info("问题分析器初始化完成")
    
    def analyze(self, text: str, intent_type: str = None) -> Dict:
        """
        分析问题，提取结构化信息
        
        Args:
            text: 用户输入
            intent_type: 意图类型（可选）
        
        Returns:
            {
                "core_need": 核心诉求,
                "constraints": 约束条件列表,
                "known_info": 已知信息列表,
                "info_gaps": 信息缺口列表,
                "problem_type": 问题类型,
                "complexity": 复杂度评估
            }
        """
        logger.info(f"开始问题分析: {text[:50]}...")
        
        analysis = {
            "core_need": self._extract_core_need(text, intent_type),
            "constraints": self._extract_constraints(text),
            "known_info": self._extract_known_info(text),
            "info_gaps": self._extract_gaps(text, intent_type),
            "problem_type": self._classify_problem(text, intent_type),
            "complexity": self._estimate_complexity(text)
        }
        
        logger.info(f"问题分析完成: 类型={analysis['problem_type']}, "
                   f"复杂度={analysis['complexity']:.2f}, "
                   f"缺口数={len(analysis['info_gaps'])}")
        
        return analysis
    
    def _load_templates(self) -> Dict:
        """加载问题模板"""
        return {
            "code": {
                "patterns": [r"写.*代码", r"实现.*功能", r"编写.*程序", r"生成.*脚本"],
                "core_template": "编写{language}代码实现{functionality}",
                "gaps": ["编程语言", "功能需求", "输入输出规格", "性能要求"]
            },
            "question": {
                "patterns": [r"什么是", r"为什么", r"怎么.*做", r"如何.*实现"],
                "core_template": "解释{concept}的{aspect}",
                "gaps": ["概念范围", "解释深度", "目标受众"]
            },
            "analysis": {
                "patterns": [r"分析", r"比较", r"评估", r"对比"],
                "core_template": "分析{subject}的{dimension}",
                "gaps": ["分析对象", "分析维度", "对比基准"]
            }
        }
    
    def _load_keywords(self) -> Dict:
        """加载关键词库"""
        return {
            "constraints": {
                "language": ["Python", "JavaScript", "Java", "C++", "Go", "Rust"],
                "performance": ["快速", "高效", "优化", "O(n)", "时间复杂度", "空间复杂度"],
                "quality": ["稳定", "可靠", "安全", "可维护", "可扩展"],
                "scope": ["仅", "只", "不要", "避免", "必须", "应该"]
            },
            "known_markers": ["已知", "假设", "前提", "当前", "现有", "使用"],
            "gap_markers": ["需要", "要求", "希望", "想要", "请问", "如何"]
        }
    
    def _extract_core_need(self, text: str, intent_type: str = None) -> str:
        """提取核心诉求"""
        # 基于意图类型和模板
        if intent_type == "code":
            # 提取功能描述
            patterns = [
                r"写[一个]?(.+?)的代码",
                r"实现[一个]?(.+?)功能",
                r"编写[一个]?(.+?)程序",
                r"生成[一个]?(.+?)脚本"
            ]
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    return f"编写代码实现：{match.group(1)}"
        
        elif intent_type == "question":
            # 提取问题核心
            if "为什么" in text:
                match = re.search(r"为什么(.+)", text)
                if match:
                    return f"解释原因：{match.group(1)}"
            elif "什么是" in text:
                match = re.search(r"什么是(.+)", text)
                if match:
                    return f"定义概念：{match.group(1)}"
            elif "怎么" in text or "如何" in text:
                match = re.search(r"[怎么如何](.+)", text)
                if match:
                    return f"方法指导：{match.group(1)}"
        
        # 通用：提取主要动词短语
        verbs = ["分析", "比较", "评估", "设计", "优化", "实现", "解释", "说明"]
        for verb in verbs:
            if verb in text:
                idx = text.index(verb)
                return f"{verb}：{text[idx+len(verb):idx+50]}"
        
        # 降级：返回原文
        return text[:100]
    
    def _extract_constraints(self, text: str) -> List[Dict]:
        """提取约束条件"""
        constraints = []
        
        # 语言约束
        for lang in self.keywords["constraints"]["language"]:
            if lang in text:
                constraints.append({
                    "type": "language",
                    "value": lang,
                    "description": f"使用{lang}编程语言"
                })
        
        # 性能约束
        for perf in self.keywords["constraints"]["performance"]:
            if perf in text:
                constraints.append({
                    "type": "performance",
                    "value": perf,
                    "description": f"性能要求：{perf}"
                })
        
        # 质量约束
        for qual in self.keywords["constraints"]["quality"]:
            if qual in text:
                constraints.append({
                    "type": "quality",
                    "value": qual,
                    "description": f"质量要求：{qual}"
                })
        
        # 范围约束
        for scope in self.keywords["constraints"]["scope"]:
            if scope in text:
                # 提取约束内容
                idx = text.index(scope)
                constraint_text = text[max(0, idx-10):idx+20]
                constraints.append({
                    "type": "scope",
                    "value": scope,
                    "description": f"范围约束：{constraint_text}"
                })
        
        return constraints
    
    def _extract_known_info(self, text: str) -> List[Dict]:
        """提取已知信息"""
        known = []
        
        for marker in self.keywords["known_markers"]:
            if marker in text:
                # 提取标记后的内容
                pattern = rf"{marker}[：:]?\s*(.+?)(?=[。，；\n]|$)"
                match = re.search(pattern, text)
                if match:
                    known.append({
                        "marker": marker,
                        "content": match.group(1),
                        "description": f"{marker}：{match.group(1)}"
                    })
        
        return known
    
    def _extract_gaps(self, text: str, intent_type: str = None) -> List[Dict]:
        """识别信息缺口"""
        gaps = []
        
        # 基于模板的缺口
        if intent_type and intent_type in self.templates:
            template = self.templates[intent_type]
            for gap in template.get("gaps", []):
                # 检查是否已明确
                if not any(kw in text for kw in self._get_gap_keywords(gap)):
                    gaps.append({
                        "type": "template_gap",
                        "description": gap,
                        "importance": "high" if gap in ["编程语言", "功能需求"] else "medium"
                    })
        
        # 基于标记的缺口
        for marker in self.keywords["gap_markers"]:
            if marker in text:
                # 检查是否有明确答案
                pattern = rf"{marker}[：:]?\s*(.+?)(?=[。，；\n]|$)"
                match = re.search(pattern, text)
                if match:
                    # 有明确需求，不是缺口
                    continue
                else:
                    gaps.append({
                        "type": "implicit_gap",
                        "description": f"需要明确{marker}的具体内容",
                        "importance": "medium"
                    })
        
        # 代码任务特殊检查
        if intent_type == "code":
            if not any(lang in text for lang in self.keywords["constraints"]["language"]):
                gaps.append({
                    "type": "language_gap",
                    "description": "未指定编程语言",
                    "importance": "high"
                })
            
            if "输入" not in text and "输出" not in text:
                gaps.append({
                    "type": "io_gap",
                    "description": "未明确输入输出规格",
                    "importance": "medium"
                })
        
        return gaps
    
    def _get_gap_keywords(self, gap: str) -> List[str]:
        """获取缺口对应的关键词"""
        mapping = {
            "编程语言": ["Python", "JavaScript", "Java", "C++", "Go"],
            "功能需求": ["实现", "功能", "完成", "支持"],
            "输入输出规格": ["输入", "输出", "参数", "返回"],
            "性能要求": ["快速", "高效", "优化", "复杂度"],
            "概念范围": ["范围", "领域", "方面"],
            "解释深度": ["详细", "简要", "深入", "浅显"]
        }
        return mapping.get(gap, [])
    
    def _classify_problem(self, text: str, intent_type: str = None) -> str:
        """分类问题类型"""
        if intent_type:
            return intent_type
        
        # 基于模板匹配
        for ptype, template in self.templates.items():
            for pattern in template["patterns"]:
                if re.search(pattern, text):
                    return ptype
        
        # 基于关键词
        if any(kw in text for kw in ["代码", "程序", "函数", "算法"]):
            return "code"
        elif any(kw in text for kw in ["为什么", "什么是", "如何"]):
            return "question"
        elif any(kw in text for kw in ["分析", "比较", "评估"]):
            return "analysis"
        
        return "general"
    
    def _estimate_complexity(self, text: str) -> float:
        """评估问题复杂度"""
        factors = {
            "length": min(len(text) / 200, 2),
            "questions": text.count("？") + text.count("?"),
            "conjunctions": sum(1 for kw in ["和", "与", "及", "并且", "同时"] if kw in text),
            "nested": 1 if ("其中" in text or "包括" in text) else 0
        }
        
        complexity = sum(factors.values()) / 4
        return min(complexity, 1.0)


# 全局实例
problem_analyzer = ProblemAnalyzer()