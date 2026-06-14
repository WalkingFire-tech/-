"""
自动意图识别器 - 支持进化的意图理解
结合规则匹配(快速)和LLM语义理解(智能)
"""
import re
import json
import threading
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from loguru import logger
from infrastructure.event_bus import bus
from infrastructure.config_manager import config


@dataclass
class Intent:
    type: str
    raw_text: str
    entities: dict
    confidence: float = 1.0
    source: str = "rule"  # rule, llm, corrected


class AutoIntentParser:
    """自动进化的意图识别器"""
    
    def __init__(self, llm_adapter=None):
        self.llm_adapter = llm_adapter
        self.rules = self._load_rules()
        self.confidence_threshold = config.get("intent.confidence_threshold", 0.6)
        self.learning_file = Path("intent_learning.json")
        self.learning_data = self._load_learning_data()
        self.correction_count = 0
        
        self._data_lock = threading.Lock()
        self._file_lock = threading.Lock()
        
        self.intent_types = {
            "code": "代码生成、编程任务",
            "question": "知识问答、概念解释",
            "chat": "日常对话、情感交流",
            "memory": "记忆查询、历史回顾",
            "calculation": "数学计算、数值计算",
            "feedback": "用户反馈、评分评价"
        }
    
    def _load_rules(self) -> dict:
        """加载规则(从配置或默认)"""
        custom_rules = config.get("intent.custom_rules", {})
        
        if custom_rules:
            rules = {}
            for intent_type, patterns in custom_rules.items():
                combined_pattern = "|".join(patterns)
                rules[intent_type] = re.compile(combined_pattern, re.IGNORECASE)
            return rules
        
        # 默认规则
        return {
            "feedback": re.compile(r"^(\+1|-1|点赞|踩|好评|差评)$", re.IGNORECASE),
            "calculation": re.compile(r"Π|π|圆周率|前\s*\d+\s*位|输出.*数值|计算.*值", re.IGNORECASE),
            "code": re.compile(r"代码|写.*代码|生成.*代码|编程|实现|算法|冒泡|快速|递归|函数|类|模块|排序", re.IGNORECASE),
            "question": re.compile(r"什么是|为什么|怎么|如何|哪|谁|多少|解释|介绍|说明", re.IGNORECASE),
            "memory": re.compile(r"记住|忘记|回忆|之前|刚才|聊过|说过|我们.*什么", re.IGNORECASE),
        }
    
    def _load_learning_data(self) -> Dict:
        """加载学习数据"""
        if self.learning_file.exists():
            try:
                with open(self.learning_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载学习数据失败: {e}")
        
        return {
            "corrections": [],  # 用户修正记录
            "learned_rules": {},  # 学习到的规则
            "intent_examples": {}  # 意图示例
        }
    
    def _save_learning_data(self):
        """保存学习数据（线程安全）"""
        with self._file_lock:
            try:
                temp_file = self.learning_file.with_suffix('.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(self.learning_data, f, ensure_ascii=False, indent=2)
                temp_file.replace(self.learning_file)
            except Exception as e:
                logger.error(f"保存学习数据失败: {e}")
                if temp_file.exists():
                    temp_file.unlink()
    
    def parse(self, user_input: str) -> Intent:
        """解析意图(双模式)"""
        # 1. 先尝试规则匹配(快速)
        rule_intent = self._rule_based_parse(user_input)
        
        # 如果规则匹配置信度高,直接返回
        if rule_intent.confidence >= 0.85:
            logger.info(f"规则匹配置图: {rule_intent.type} (置信度: {rule_intent.confidence:.2f})")
            bus.publish("intent_parsed", rule_intent)
            return rule_intent
        
        # 2. 检查是否有学习到的规则
        learned_intent = self._check_learned_rules(user_input)
        if learned_intent:
            logger.info(f"学习规则匹配置图: {learned_intent.type}")
            bus.publish("intent_parsed", learned_intent)
            return learned_intent
        
        # 3. 使用LLM语义理解(如果可用)
        if self.llm_adapter and rule_intent.confidence < 0.7:
            llm_intent = self._llm_based_parse(user_input)
            if llm_intent:
                logger.info(f"LLM语义理解意图: {llm_intent.type} (置信度: {llm_intent.confidence:.2f})")
                # 记录用于后续学习
                self._record_for_learning(user_input, llm_intent)
                bus.publish("intent_parsed", llm_intent)
                return llm_intent
        
        # 4. 返回规则匹配结果(即使置信度较低)
        logger.info(f"使用规则匹配置图: {rule_intent.type} (置信度: {rule_intent.confidence:.2f})")
        bus.publish("intent_parsed", rule_intent)
        return rule_intent
    
    def _rule_based_parse(self, text: str) -> Intent:
        """基于规则的意图识别"""
        candidates = []
        
        for intent_type, pattern in self.rules.items():
            if pattern.search(text):
                confidence = self._calculate_rule_confidence(text, intent_type)
                candidates.append((intent_type, confidence))
        
        if not candidates:
            return Intent(type="chat", raw_text=text, entities={}, confidence=0.5, source="rule")
        
        # 选择置信度最高的
        best_type, best_conf = max(candidates, key=lambda x: x[1])
        entities = self._extract_entities(text, best_type)
        
        return Intent(type=best_type, raw_text=text, entities=entities, confidence=best_conf, source="rule")
    
    def _calculate_rule_confidence(self, text: str, intent_type: str) -> float:
        """计算规则匹配置信度"""
        pattern = self.rules[intent_type]
        matches = pattern.findall(text)
        
        if not matches:
            return 0.0
        
        # 基础置信度
        match_ratio = len(matches) / max(len(text.split()), 1)
        base_confidence = min(0.6 + match_ratio * 2, 0.95)
        
        # 关键词加成
        keyword_boost = {
            "code": ["代码", "写", "生成", "算法", "函数"],
            "question": ["什么", "为什么", "怎么", "如何", "解释"],
            "memory": ["刚才", "之前", "聊过", "说过", "我们"],
            "calculation": ["π", "计算", "输出", "数值"],
            "feedback": ["+1", "-1", "点赞", "好评"]
        }
        
        boost_keywords = keyword_boost.get(intent_type, [])
        boost_count = sum(1 for kw in boost_keywords if kw in text)
        boost = min(boost_count * 0.05, 0.15)
        
        return min(base_confidence + boost, 0.95)
    
    def _check_learned_rules(self, text: str) -> Optional[Intent]:
        """检查学习到的规则"""
        learned_rules = self.learning_data.get("learned_rules", {})
        
        for intent_type, patterns in learned_rules.items():
            for pattern_str in patterns:
                if re.search(pattern_str, text, re.IGNORECASE):
                    return Intent(
                        type=intent_type,
                        raw_text=text,
                        entities={},
                        confidence=0.8,
                        source="learned"
                    )
        
        return None
    
    def _llm_based_parse(self, text: str) -> Optional[Intent]:
        """基于LLM的语义理解"""
        if not self.llm_adapter:
            return None
        
        try:
            prompt = f"""分析以下用户输入的意图类型。

用户输入: {text}

意图类型选项:
{json.dumps(self.intent_types, ensure_ascii=False, indent=2)}

请以JSON格式返回:
{{
  "intent_type": "意图类型",
  "confidence": 0.0-1.0的置信度,
  "reasoning": "判断理由"
}}

只返回JSON,不要其他内容。"""

            try:
                if asyncio.iscoroutinefunction(self.llm_adapter.generate):
                    response = asyncio.run(asyncio.wait_for(
                        self.llm_adapter.generate(prompt, task_type="intent_classification"),
                        timeout=10.0
                    ))
                else:
                    response = self.llm_adapter.generate(prompt, task_type="intent_classification")
            except asyncio.TimeoutError:
                logger.warning("LLM意图识别超时")
                return None
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                intent_type = result.get("intent_type", "chat")
                confidence = float(result.get("confidence", 0.7))
                
                if intent_type not in self.intent_types:
                    intent_type = "chat"
                    confidence = 0.5
                
                entities = self._extract_entities(text, intent_type)
                
                return Intent(
                    type=intent_type,
                    raw_text=text,
                    entities=entities,
                    confidence=confidence,
                    source="llm"
                )
        
        except Exception as e:
            logger.warning(f"LLM意图识别失败: {e}")
        
        return None
    
    def _extract_entities(self, text: str, intent_type: str) -> dict:
        """提取实体"""
        entities = {}
        
        if intent_type == "feedback":
            entities["score"] = 1 if ("+1" in text or "点赞" in text or "好评" in text) else -1
        
        elif intent_type == "calculation":
            pi_pattern = re.compile(r'前\s*(\d+)\s*位')
            match = pi_pattern.search(text)
            if match:
                entities["digits"] = int(match.group(1))
        
        elif intent_type == "code":
            code_keywords = {
                "排序": "sorting",
                "快速": "quick",
                "冒泡": "bubble",
                "递归": "recursive"
            }
            for keyword, code_type in code_keywords.items():
                if keyword in text:
                    entities.setdefault("code_types", []).append(code_type)
        
        return entities
    
    def _record_for_learning(self, text: str, intent: Intent):
        """记录用于学习（线程安全）"""
        with self._data_lock:
            intent_type = intent.type
            
            if intent_type not in self.learning_data["intent_examples"]:
                self.learning_data["intent_examples"][intent_type] = []
            
            examples = self.learning_data["intent_examples"][intent_type]
            if len(examples) < 100:
                examples.append({
                    "text": text,
                    "confidence": intent.confidence,
                    "source": intent.source
                })
            
            self._save_learning_data()
    
    def learn_from_correction(self, text: str, correct_intent: str, wrong_intent: str = None):
        """从用户修正中学习（线程安全）"""
        logger.info(f"学习用户修正: '{text}' -> {correct_intent}")
        
        with self._data_lock:
            correction = {
                "text": text,
                "wrong_intent": wrong_intent,
                "correct_intent": correct_intent,
                "timestamp": str(Path.cwd())
            }
            self.learning_data["corrections"].append(correction)
            self.correction_count += 1
            
            keywords = self._extract_keywords(text)
            if keywords:
                if correct_intent not in self.learning_data["learned_rules"]:
                    self.learning_data["learned_rules"][correct_intent] = []
                
                pattern = "|".join(keywords[:3])
                if pattern not in self.learning_data["learned_rules"][correct_intent]:
                    self.learning_data["learned_rules"][correct_intent].append(pattern)
            
            self._save_learning_data()
            
            if self.correction_count % 10 == 0:
                logger.info(f"已收集{self.correction_count}次修正,可进行模型微调")
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单实现:提取中文词组
        keywords = re.findall(r'[\u4e00-\u9fa5]{2,}', text)
        return keywords[:5]  # 最多5个关键词
    
    def get_statistics(self) -> Dict:
        """获取学习统计"""
        return {
            "total_corrections": len(self.learning_data.get("corrections", [])),
            "learned_rules_count": sum(len(rules) for rules in self.learning_data.get("learned_rules", {}).values()),
            "intent_examples_count": sum(len(examples) for examples in self.learning_data.get("intent_examples", {}).values())
        }