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
            # 元认知意图 - 价值性问题（最高优先级）
            "meta_value": re.compile(
                r"最优|最好|最佳|理想|完美|标准|判断.*标准|应该.*如何|"
                r"什么样.*算.*好|什么.*才算|评价.*标准|好坏|优劣|"
                r"贴切|恰当|合适|满意|期望|希望.*达到",
                re.IGNORECASE
            ),
            # 元认知意图 - 机制性问题
            "meta_mechanism": re.compile(
                r"你.*如何.*理解|你怎么.*知道|你觉得自己|你.*改进|你.*学习|"
                r"你.*自我.*进化|你的.*能力|如何.*让你.*更.*好|"
                r"你.*理解.*需求|你.*思考|你的.*理解|你.*优化|"
                r"系统.*如何|系统.*改进|如何.*提升.*理解|"
                r"你.*处理.*不了|你明白我.*意思|我讲的是你|你.*反思|"
                r"你.*分析.*意图|你.*进化|你.*自我|你.*成长|"
                r"你.*能力.*边界|能力边界.*在哪|你的.*边界|"
                r"自我.*评估|评估.*体系|你.*决策|你.*如何.*认识|"
                r"完善.*你|给出.*评价|能力边界|自我评估|决策机制|"
                r"怎么认识自己|评估体系|知道自己.*?|你的.*能力|"
                r"你.*如何.*决策|你.*学习.*方式|你.*改进.*自己|你.*反思|"
                r"你.*优点|你.*缺点|能力的理解|你的.*学习.*能力|系统的.*学习",
                re.IGNORECASE
            ),
            # 元认知意图 - 能力边界问题
            "meta_capability": re.compile(
                r"你能.*做什么|你.*能力.*范围|你.*限制|你.*边界|"
                r"你.*不会|你.*不能|你.*擅长|你.*不擅长",
                re.IGNORECASE
            ),
            # 兼容旧版meta意图
            "meta": re.compile(
                r"你.*如何.*理解|你怎么.*知道|你觉得自己|你.*改进|你.*学习|"
                r"你.*自我.*进化|你的.*能力|如何.*让你.*更.*好|"
                r"你.*理解.*需求|你.*思考|你的.*理解|你.*优化|"
                r"系统.*如何|系统.*改进|如何.*提升.*理解|"
                r"你.*处理.*不了|你明白我.*意思|我讲的是你|你.*反思|"
                r"你.*分析.*意图|你.*进化|你.*自我|你.*成长|"
                r"你.*能力.*边界|能力边界.*在哪|你的.*边界|"
                r"自我.*评估|评估.*体系|你.*决策|你.*如何.*认识|"
                r"你.*最优|你.*贴切|完善.*你|给出.*评价|"
                r"能力边界|自我评估|决策机制|怎么认识自己|评估体系|"
                r"知道自己.*?|你的.*能力|你.*如何.*决策|你.*学习.*方式|"
                r"你.*改进.*自己|你.*反思|你.*优点|你.*缺点|"
                r"能力的理解|你的.*学习.*能力|系统的.*学习",
                re.IGNORECASE
            ),
            # 代码意图（更精确的匹配）
            "code": re.compile(
                r"代码|写.*代码|生成.*代码|编程|实现|算法|冒泡|快速|递归|函数|模块|排序|查找|def\s|class\s|import\s|"
                r"编写.*程序|程序.*实现|代码.*实现|实现.*功能",
                re.IGNORECASE
            ),
            # 问题意图
            "question": re.compile(
                r"什么是|为什么|怎么|如何|哪|谁|多少|解释|介绍|说明|讲解|分析|"
                r"是什么|有哪些|怎样|何时|哪里|哪种|谁的|多长|多大|多重|"
                r"有没有|是否|能否|可以.*吗|会.*吗|应该.*吗",
                re.IGNORECASE
            ),
            # 记忆意图
            "memory": re.compile(
                r"记住|忘记|回忆|之前|刚才|聊过|说过|我们.*什么|讨论.*什么|谈.*什么|"
                r"回顾.*历史|历史对话|之前的对话|历史问题|回顾对话",
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
            # 验证/质疑意图
            "verification": re.compile(
                r"对么|对吗|正确吗|是这样吗|对不对|是不是|有问题|不对吧|错了吧|这不对|有问题吧|"
                r"质疑|怀疑|真的吗|确定吗|凭什么|证据|验证|检查.*对|确认.*正确",
                re.IGNORECASE
            ),
        }
        
        custom_rules = config.get("intent.custom_rules", {})
        
        for intent_type, patterns in custom_rules.items():
            combined_pattern = "|".join(patterns)
            default_rules[intent_type] = re.compile(combined_pattern, re.IGNORECASE)
        
        return default_rules
    
    def _calculate_confidence(self, text: str, intent_type: str) -> float:
        """计算意图识别的置信度（优化版：使用匹配字符覆盖率）"""
        if intent_type == "chat":
            return 0.5
        
        pattern = self.rules.get(intent_type)
        if not pattern:
            return 0.0
        
        matches = pattern.findall(text)
        if not matches:
            return 0.0
        
        matched_chars = sum(len(m) if isinstance(m, str) else len(str(m)) for m in matches)
        coverage = min(1.0, matched_chars / max(len(text), 1))
        base_confidence = 0.5 + coverage * 0.4
        
        keyword_boost = {
            "code": ["代码", "写", "生成", "算法"],
            "question": ["什么", "为什么", "怎么", "如何"],
            "memory": ["刚才", "之前", "聊过", "说过", "回顾", "历史", "对话"],
            "calculation": ["π", "计算", "输出"],
            "feedback": ["+1", "-1", "点赞"],
            "verification": ["对么", "对吗", "正确", "质疑", "怀疑", "验证"]
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
            "meta_value": 13,
            "meta_mechanism": 12,
            "meta_capability": 11,
            "meta": 10,
            "feedback": 9,
            "calculation": 8,
            "document": 7,
            "code": 6,
            "memory": 5,
            "question": 4,
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
            
            # 分析用户输入中的动词
            user_lower = user_input.lower()
            has_explain = any(kw in user_input for kw in ["解释", "explain", "说明", "describe"])
            has_analyze = any(kw in user_input for kw in ["分析", "analyze", "评估", "evaluate"])
            has_summarize = any(kw in user_input for kw in ["总结", "summarize", "摘要", "abstract"])
            has_generate = any(kw in user_input for kw in ["写", "生成", "generate", "编写", "实现", "implement"])
            
            if file_ext in {'.py', '.js', '.ts', '.java', '.cpp', '.go'}:
                # 根据动词决定意图
                if has_explain or has_analyze or has_summarize:
                    intent_type = "document"
                    confidence = 0.90
                elif has_generate:
                    intent_type = "code"
                    confidence = 0.95
                else:
                    intent_type = "code"
                    confidence = 0.85
                
                candidates = [(intent_type, confidence)]
                
                entities = {
                    "file_path": file_info.get("path"),
                    "file_type": "code",
                    "file_ext": file_ext
                }
                
                if "分析" in user_input or "analyze" in user_lower:
                    entities["code_action"] = "analyze"
                elif "优化" in user_input or "optimize" in user_lower:
                    entities["code_action"] = "optimize"
                elif "重构" in user_input or "refactor" in user_lower:
                    entities["code_action"] = "refactor"
                
                logger.info(f"文件意图: {intent_type} (文件类型: {file_ext}, 动作: {entities.get('code_action', 'default')})")
                
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
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/learning_rules.db")
            db.execute('''
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
            escaped_text = text.replace("'", "''")
            condition = f"raw_input LIKE '%{escaped_text}%'"
            action = f"set_intent:{correct_intent}"
            
            db.execute('''
                INSERT INTO learning_rules 
                (condition, action, confidence, status, source, created_at)
                VALUES (?, ?, 0.8, 'pending', 'user_correction', datetime('now'))
            ''', (condition, action), commit=True)

            
            logger.info(f"从纠正中学习: '{text[:30]}...' -> {correct_intent}")
            
        except Exception as e:
            logger.warning(f"学习记录失败: {e}")
