"""
意图识别器 - 优化版本
使用配置文件驱动的规则系统,提升识别准确率
"""
import re
from dataclasses import dataclass
from typing import List, Tuple, Optional
from loguru import logger
from infrastructure.event_bus import bus
from infrastructure.config_manager import config


@dataclass
class Intent:
    type: str
    raw_text: str
    entities: dict
    confidence: float = 1.0


class IntentParser:
    def __init__(self):
        self.rules = self._load_rules()
        self.confidence_threshold = config.get("intent.confidence_threshold", 0.6)
    
    def _load_rules(self) -> dict:
        """从配置文件加载规则"""
        default_rules = {
            # 元认知意图 - 关于系统自身的问题（最高优先级）
            "meta": re.compile(
                r"你.*如何.*理解|你怎么.*知道|你觉得自己|你.*改进|你.*学习|"
                r"你.*自我.*进化|你的.*能力|如何.*让你.*更.*好|"
                r"你.*理解.*需求|你.*思考|你的.*理解|你.*优化|"
                r"系统.*如何|系统.*改进|如何.*提升.*理解|"
                r"你.*处理.*不了|你明白我.*意思|我讲的是你|你.*反思|"
                r"你.*分析.*意图|你.*进化|你.*自我|你.*成长|"
                r"你.*懂|你.*明白|你.*认为|如何.*让.*你.*更|"
                r"你.*能力.*边界|能力边界.*在哪|你的.*边界|"
                r"自我.*评估|评估.*体系|你.*决策|你.*如何.*认识|"
                r"你.*最优|你.*贴切|完善.*你|回顾.*对话|给出.*评价|"
                r"能力边界|自我评估|决策机制|怎么认识自己|评估体系|"
                r"知道自己.*?|你的.*能力|你.*如何.*决策|你.*学习.*方式|"
                r"你.*改进.*自己|你.*反思|你.*优点|你.*缺点|"
                r"能力的理解|学习能力|培养.*学习|提升.*学习|"
                r"如何.*学习|怎样.*学习|怎么.*学习|学习.*方法|"
                r"学习.*能力|学习.*技巧|学习.*习惯|自主.*学习",
                re.IGNORECASE
            ),
            # 代码意图
            "code": re.compile(
                r"代码|写.*代码|生成.*代码|编程|实现|算法|冒泡|快速|递归|函数|类|模块|排序|查找|def\s|class\s|import\s",
                re.IGNORECASE
            ),
            # 问题意图
            "question": re.compile(
                r"什么是|为什么|怎么|如何|哪|谁|多少|解释|介绍|说明|讲解|分析",
                re.IGNORECASE
            ),
            # 记忆意图
            "memory": re.compile(
                r"记住|忘记|回忆|之前|刚才|聊过|说过|我们.*什么|讨论.*什么|谈.*什么",
                re.IGNORECASE
            ),
            # 反馈意图
            "feedback": re.compile(
                r"^(\+1|-1|点赞|踩|好评|差评)$",
                re.IGNORECASE
            ),
            # 计算意图
            "calculation": re.compile(
                r"Π|π|圆周率|前\s*\d+\s*位|输出.*数值|计算.*值|给出.*结果|求.*值",
                re.IGNORECASE
            ),
            # 文档意图
            "document": re.compile(
                r"^##|^\*|^- |项目状态|已实现|核心框架|^\d+\.|能力|功能|特性",
                re.IGNORECASE
            ),
        }
        
        custom_rules = config.get("intent.custom_rules", {})
        
        for intent_type, patterns in custom_rules.items():
            combined_pattern = "|".join(patterns)
            default_rules[intent_type] = re.compile(combined_pattern, re.IGNORECASE)
        
        return default_rules
    
    def _calculate_confidence(self, text: str, intent_type: str) -> float:
        """计算意图识别的置信度"""
        if intent_type == "chat":
            return 0.5
        
        pattern = self.rules.get(intent_type)
        if not pattern:
            return 0.0
        
        matches = pattern.findall(text)
        if not matches:
            return 0.0
        
        match_ratio = len(matches) / max(len(text.split()), 1)
        base_confidence = min(0.5 + match_ratio * 2, 1.0)
        
        keyword_boost = {
            "code": ["代码", "写", "生成", "算法"],
            "question": ["什么", "为什么", "怎么", "如何"],
            "memory": ["刚才", "之前", "聊过", "说过"],
            "calculation": ["π", "计算", "输出"],
            "feedback": ["+1", "-1", "点赞"]
        }
        
        boost_keywords = keyword_boost.get(intent_type, [])
        boost_count = sum(1 for kw in boost_keywords if kw in text)
        boost = min(boost_count * 0.1, 0.3)
        
        return min(base_confidence + boost, 1.0)
    
    def _extract_entities(self, user_input: str, intent_type: str) -> dict:
        """提取实体信息"""
        entities = {}
        
        if intent_type == "feedback":
            entities["score"] = 1 if ("+1" in user_input or "点赞" in user_input or "好评" in user_input) else -1
        
        elif intent_type == "calculation":
            pi_pattern = re.compile(r'前\s*(\d+)\s*位')
            match = pi_pattern.search(user_input)
            if match:
                entities["digits"] = int(match.group(1))
        
        elif intent_type == "code":
            code_keywords = {
                "排序": "sorting",
                "快速": "quick",
                "冒泡": "bubble",
                "递归": "recursive",
                "函数": "function",
                "类": "class"
            }
            for keyword, code_type in code_keywords.items():
                if keyword in user_input:
                    entities.setdefault("code_types", []).append(code_type)
        
        elif intent_type == "document":
            doc_keywords = {
                "分析": "analyze",
                "总结": "summarize",
                "解释": "explain",
                "提取": "extract",
                "转换": "convert",
                "优化": "optimize"
            }
            for keyword, action in doc_keywords.items():
                if keyword in user_input:
                    entities.setdefault("doc_actions", []).append(action)
            
            if "项目" in user_input or "状态" in user_input:
                entities["doc_context"] = "project_status"
            elif "能力" in user_input or "功能" in user_input:
                entities["doc_context"] = "capabilities"
        
        return entities
    
    def _disambiguate(self, user_input: str, candidates: List[Tuple[str, float]]) -> str:
        """消除歧义,选择最可能的意图"""
        if len(candidates) == 1:
            return candidates[0][0]
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        if candidates[0][1] - candidates[1][1] > 0.2:
            return candidates[0][0]
        
        priority = {
            "meta": 11,
            "feedback": 10,
            "calculation": 9,
            "document": 8,
            "code": 7,
            "memory": 6,
            "question": 5,
            "chat": 1
        }
        
        top_candidates = [c for c in candidates if c[1] >= candidates[0][1] - 0.1]
        top_candidates.sort(key=lambda x: priority.get(x[0], 0), reverse=True)
        
        return top_candidates[0][0]
    
    def parse(self, user_input: str, context: dict = None) -> Intent:
        """解析用户输入的意图
        
        Args:
            user_input: 用户输入文本
            context: 上下文信息,可能包含文件输入等
        """
        candidates = []
        
        if context and context.get("file_input"):
            file_info = context["file_input"]
            file_ext = file_info.get("extension", "")
            
            if file_ext in {'.py', '.js', '.ts', '.java', '.cpp', '.go'}:
                intent_type = "code"
                confidence = 0.95
                candidates = [(intent_type, confidence)]
                
                entities = {
                    "file_path": file_info.get("path"),
                    "file_type": "code",
                    "file_ext": file_ext
                }
                
                if "分析" in user_input or "analyze" in user_input.lower():
                    entities["code_action"] = "analyze"
                elif "优化" in user_input or "optimize" in user_input.lower():
                    entities["code_action"] = "optimize"
                elif "重构" in user_input or "refactor" in user_input.lower():
                    entities["code_action"] = "refactor"
                
                logger.info(f"文件意图: {intent_type} (文件类型: {file_ext})")
                
                intent = Intent(
                    type=intent_type,
                    raw_text=user_input,
                    entities=entities,
                    confidence=confidence
                )
                
                bus.publish("intent_parsed", intent)
                return intent
            
            elif file_ext in {'.md', '.txt', '.rst', '.pdf', '.docx'}:
                intent_type = "document"
                confidence = 0.95
                candidates = [(intent_type, confidence)]
                
                entities = {
                    "file_path": file_info.get("path"),
                    "file_type": "document",
                    "file_ext": file_ext
                }
                
                logger.info(f"文件意图: {intent_type} (文件类型: {file_ext})")
                
                intent = Intent(
                    type=intent_type,
                    raw_text=user_input,
                    entities=entities,
                    confidence=confidence
                )
                
                bus.publish("intent_parsed", intent)
                return intent
        
        for intent_type, pattern in self.rules.items():
            if pattern.search(user_input):
                confidence = self._calculate_confidence(user_input, intent_type)
                candidates.append((intent_type, confidence))
        
        if not candidates:
            intent_type = "chat"
            confidence = 0.5
        else:
            intent_type = self._disambiguate(user_input, candidates)
            confidence = next((c for t, c in candidates if t == intent_type), 0.5)
        
        entities = self._extract_entities(user_input, intent_type)
        
        logger.info(f"解析意图: {intent_type} (置信度: {confidence:.2f}) <- {user_input[:50]}")
        
        intent = Intent(
            type=intent_type,
            raw_text=user_input,
            entities=entities,
            confidence=confidence
        )
        
        bus.publish("intent_parsed", intent)
        return intent
    
    def add_custom_rule(self, intent_type: str, pattern: str):
        """动态添加自定义规则"""
        if intent_type not in self.rules:
            self.rules[intent_type] = re.compile(pattern, re.IGNORECASE)
        else:
            existing_pattern = self.rules[intent_type].pattern
            new_pattern = f"{existing_pattern}|{pattern}"
            self.rules[intent_type] = re.compile(new_pattern, re.IGNORECASE)
        
        logger.info(f"添加自定义规则: {intent_type} <- {pattern}")
    
    def learn_from_correction(self, text: str, correct_intent: str):
        """从用户纠正中学习
        
        Args:
            text: 用户输入文本
            correct_intent: 正确的意图类型
        """
        try:
            import sqlite3
            conn = sqlite3.connect("learning_rules.db")
            conn.execute('''
                CREATE TABLE IF NOT EXISTS learning_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    condition TEXT,
                    action TEXT,
                    confidence REAL,
                    status TEXT,
                    source TEXT,
                    created_at TEXT
                )
            ''')
            conn.execute('''
                INSERT INTO learning_rules 
                (condition, action, confidence, status, source, created_at)
                VALUES (?, ?, 0.8, 'pending', 'user_correction', datetime('now'))
            ''', (f"raw_input LIKE '%{text}%'", f"set_intent:{correct_intent}"))
            conn.commit()
            conn.close()
            
            logger.info(f"从纠正中学习: '{text[:30]}...' -> {correct_intent}")
            
        except Exception as e:
            logger.warning(f"学习记录失败: {e}")
