"""
因果推理器 - 认知层核心组件
基于预置因果模板和经验池中的历史案例，构建因果链

核心能力：
- 构建因果链
- 识别依赖关系
- 推断可能后果
"""
import json
from typing import Dict, List, Optional
from pathlib import Path
from loguru import logger
from infrastructure.config_manager import config
from infrastructure.database_manager import DatabaseManager


class CausalReasoner:
    """因果推理器 - 认知层第二步"""
    
    def __init__(self):
        self.templates = self._load_templates()
        self.experience_db = Path("data/experience_pool.db")
        logger.info("因果推理器初始化完成")
    
    def reason(
        self,
        core_need: str,
        analysis: Dict,
        context: str = ""
    ) -> List[Dict]:
        """
        构建因果链
        
        Args:
            core_need: 核心诉求
            analysis: 问题分析结果
            context: 上下文
        
        Returns:
            [
                {
                    "cause": 原因,
                    "effect": 影响/结果,
                    "confidence": 置信度,
                    "type": 类型
                }
            ]
        """
        logger.info(f"开始因果推理: {core_need[:50]}...")
        
        causal_chain = []
        
        # 1. 基于模板的因果推理
        template_chain = self._reason_from_templates(core_need, analysis)
        causal_chain.extend(template_chain)
        
        # 2. 基于约束的因果推理
        constraint_chain = self._reason_from_constraints(analysis)
        causal_chain.extend(constraint_chain)
        
        # 3. 基于信息缺口的因果推理
        gap_chain = self._reason_from_gaps(analysis)
        causal_chain.extend(gap_chain)
        
        # 4. 基于经验池的因果推理
        experience_chain = self._reason_from_experience(core_need)
        causal_chain.extend(experience_chain)
        
        # 去重和排序
        causal_chain = self._deduplicate_and_sort(causal_chain)
        
        logger.info(f"因果推理完成: 发现{len(causal_chain)}条因果链")
        
        return causal_chain
    
    def _load_templates(self) -> Dict:
        """加载因果模板"""
        return {
            "code": [
                {
                    "pattern": "编写代码",
                    "causes": [
                        {"cause": "需求不明确", "effect": "需要澄清输入输出规格", "confidence": 0.85},
                        {"cause": "未指定语言", "effect": "需要确认编程语言", "confidence": 0.90},
                        {"cause": "代码复杂度高", "effect": "需要考虑模块化设计", "confidence": 0.75}
                    ]
                },
                {
                    "pattern": "实现算法",
                    "causes": [
                        {"cause": "算法选择", "effect": "影响时间和空间复杂度", "confidence": 0.80},
                        {"cause": "边界条件", "effect": "需要处理特殊情况", "confidence": 0.85},
                        {"cause": "性能要求", "effect": "需要优化实现", "confidence": 0.70}
                    ]
                }
            ],
            "question": [
                {
                    "pattern": "解释概念",
                    "causes": [
                        {"cause": "概念抽象", "effect": "需要具体例子辅助理解", "confidence": 0.75},
                        {"cause": "概念关联", "effect": "需要说明与其他概念的关系", "confidence": 0.70}
                    ]
                },
                {
                    "pattern": "分析原因",
                    "causes": [
                        {"cause": "多因素影响", "effect": "需要识别主要和次要因素", "confidence": 0.80},
                        {"cause": "因果关系", "effect": "需要区分相关性和因果性", "confidence": 0.85}
                    ]
                }
            ],
            "analysis": [
                {
                    "pattern": "比较分析",
                    "causes": [
                        {"cause": "对比维度", "effect": "需要明确比较标准", "confidence": 0.85},
                        {"cause": "对象差异", "effect": "需要识别关键差异点", "confidence": 0.80}
                    ]
                }
            ]
        }
    
    def _reason_from_templates(self, core_need: str, analysis: Dict) -> List[Dict]:
        """基于模板的因果推理"""
        chain = []
        problem_type = analysis.get("problem_type", "general")
        
        if problem_type in self.templates:
            for template in self.templates[problem_type]:
                # 检查是否匹配
                if template["pattern"] in core_need:
                    for causal in template["causes"]:
                        chain.append({
                            "cause": causal["cause"],
                            "effect": causal["effect"],
                            "confidence": causal["confidence"],
                            "type": "template",
                            "source": template["pattern"]
                        })
        
        return chain
    
    def _reason_from_constraints(self, analysis: Dict) -> List[Dict]:
        """基于约束的因果推理"""
        chain = []
        constraints = analysis.get("constraints", [])
        
        for constraint in constraints:
            ctype = constraint.get("type")
            value = constraint.get("value")
            
            if ctype == "language":
                chain.append({
                    "cause": f"使用{value}编程语言",
                    "effect": f"需要遵循{value}语法和最佳实践",
                    "confidence": 0.95,
                    "type": "constraint"
                })
            
            elif ctype == "performance":
                chain.append({
                    "cause": f"性能要求：{value}",
                    "effect": "需要考虑算法复杂度和优化策略",
                    "confidence": 0.85,
                    "type": "constraint"
                })
            
            elif ctype == "quality":
                chain.append({
                    "cause": f"质量要求：{value}",
                    "effect": f"需要确保代码{value}",
                    "confidence": 0.80,
                    "type": "constraint"
                })
        
        return chain
    
    def _reason_from_gaps(self, analysis: Dict) -> List[Dict]:
        """基于信息缺口的因果推理"""
        chain = []
        gaps = analysis.get("info_gaps", [])
        
        for gap in gaps:
            description = gap.get("description")
            importance = gap.get("importance", "medium")
            
            confidence = 0.90 if importance == "high" else 0.75
            
            chain.append({
                "cause": f"信息缺口：{description}",
                "effect": f"需要先{description}才能继续",
                "confidence": confidence,
                "type": "gap",
                "importance": importance
            })
        
        return chain
    
    def _reason_from_experience(self, core_need: str) -> List[Dict]:
        """基于经验池的因果推理"""
        chain = []
        
        try:
            if not self.experience_db.exists():
                return chain
            
            db = DatabaseManager.get(str(self.experience_db))
            failures = db.query('''
                SELECT raw_input, intent_type, success, quality_score
                FROM experiences
                WHERE success = 0
                ORDER BY timestamp DESC
                LIMIT 10
            ''')
            
            for raw_input, intent_type, success, quality in failures:
                # 简单相似度检查
                if self._is_similar(core_need, raw_input):
                    chain.append({
                        "cause": f"历史失败案例：{raw_input[:50]}",
                        "effect": f"需要避免类似错误（质量：{quality}分）",
                        "confidence": 0.70,
                        "type": "experience"
                    })
        
        except Exception as e:
            logger.error(f"经验池查询失败: {e}")
        
        return chain
    
    def _is_similar(self, text1: str, text2: str) -> bool:
        """简单相似度检查"""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return (intersection / union) > 0.5 if union > 0 else False
    
    def _deduplicate_and_sort(self, chain: List[Dict]) -> List[Dict]:
        """去重和排序"""
        # 去重
        seen = set()
        unique_chain = []
        for item in chain:
            key = f"{item['cause']}->{item['effect']}"
            if key not in seen:
                seen.add(key)
                unique_chain.append(item)
        
        # 按置信度排序
        unique_chain.sort(key=lambda x: x["confidence"], reverse=True)
        
        return unique_chain


# 全局实例
causal_reasoner = CausalReasoner()
