"""
知识缺失检测器 - 智能检测模型知识不足或错误

设计原则：
1. 配置驱动：规则可外部配置，无需修改代码
2. LLM辅助：复杂判断交给LLM，而非硬规则
3. 动态学习：从错误中学习，持续优化规则
4. 语义理解：基于语义而非关键词匹配
"""
import re
import json

from typing import Tuple, List, Dict, Optional
from pathlib import Path
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from infrastructure.database_manager import DatabaseManager


class KnowledgeGapDetector:
    """知识缺失检测器 - 智能版"""
    
    def __init__(self, config_path: str = None, db_path: str = "data/knowledge_rules.db"):
        self.config_path = config_path or "config/knowledge_gap_config.json"
        self.db_path = db_path
        self.config = self._load_config()
        self._init_database()
        
        logger.info("🔍 知识缺失检测器已初始化")
    
    def _load_config(self) -> Dict:
        """加载配置（支持外部配置文件）"""
        default_config = {
            "uncertainty_phrases": [
                "可能", "不确定", "我不清楚", "不太确定",
                "也许", "大概", "应该是", "我不太了解"
            ],
            "confidence_thresholds": {
                "general": 0.5,
                "professional": 0.8,
                "recommendation": 0.9
            },
            "min_response_length": 50,
            "enable_llm_validation": True,
            "enable_dynamic_learning": True
        }
        
        config_file = Path(self.config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"加载配置失败: {e}")
        
        return default_config
    
    def _init_database(self):
        """初始化数据库（存储学习到的规则）"""
        Path(self.db_path).parent.mkdir(exist_ok=True)
        
        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS domain_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT,
                keywords TEXT,
                confidence_threshold REAL,
                created_at TEXT,
                source TEXT
            );
            CREATE TABLE IF NOT EXISTS error_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT,
                pattern TEXT,
                correction TEXT,
                confidence REAL,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS validation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT,
                has_gap INTEGER,
                reason TEXT,
                confidence REAL,
                validated_at TEXT
            );
        ''')
    
    def detect_knowledge_gap(self, user_query: str, response: str,
                            confidence: float = 1.0,
                            llm_adapter = None) -> Tuple[bool, str, List[str]]:
        """
        检测知识缺失
        
        Args:
            user_query: 用户查询
            response: 系统响应
            confidence: 置信度
            llm_adapter: LLM适配器（可选，用于智能判断）
        
        Returns:
            (has_gap, reason, issues)
        """
        issues = []
        
        has_gap, reason = self._detect_uncertainty(response)
        if has_gap:
            issues.append(reason)
            return True, "模型表达不确定性", issues
        
        has_gap, reason = self._detect_response_quality(response)
        if has_gap:
            issues.append(reason)
            return True, "响应质量问题", issues
        
        has_gap, reason = self._detect_low_confidence(user_query, confidence)
        if has_gap:
            issues.append(reason)
            return True, "置信度不足", issues
        
        if llm_adapter and self.config.get("enable_llm_validation"):
            has_gap, reason = self._llm_validate(user_query, response, llm_adapter)
            if has_gap:
                issues.append(reason)
                return True, "LLM验证发现问题", issues
        
        has_gap, reason = self._check_error_patterns(user_query, response)
        if has_gap:
            issues.append(reason)
            return True, "匹配已知错误模式", issues
        
        return False, "", issues
    
    def _detect_uncertainty(self, response: str) -> Tuple[bool, str]:
        """检测不确定性表达"""
        phrases = self.config.get("uncertainty_phrases", [])
        for phrase in phrases:
            if phrase in response:
                return True, f"响应包含不确定性短语: '{phrase}'"
        return False, ""
    
    def _detect_response_quality(self, response: str) -> Tuple[bool, str]:
        """检测响应质量"""
        min_length = self.config.get("min_response_length", 50)
        if len(response) < min_length:
            return True, f"响应过短({len(response)}字符 < {min_length})"
        
        if response.count("。") < 2 and len(response) > 100:
            return True, "响应缺少结构化内容"
        
        return False, ""
    
    def _detect_low_confidence(self, user_query: str, confidence: float) -> Tuple[bool, str]:
        """检测置信度不足"""
        thresholds = self.config.get("confidence_thresholds", {})
        
        is_professional = self._is_professional_query(user_query)
        
        if is_professional:
            threshold = thresholds.get("professional", 0.8)
            if confidence < threshold:
                return True, f"专业问题置信度不足({confidence:.2f} < {threshold})"
        else:
            threshold = thresholds.get("general", 0.5)
            if confidence < threshold:
                return True, f"置信度过低({confidence:.2f} < {threshold})"
        
        return False, ""
    
    def _is_professional_query(self, query: str) -> bool:
        """判断是否为专业问题（动态规则）"""
        professional_indicators = [
            "推荐", "选型", "对比", "方案",
            "如何设计", "如何实现", "最佳实践",
            "原理", "机制", "架构"
        ]
        
        if any(indicator in query for indicator in professional_indicators):
            return True
        
        try:
            db = DatabaseManager.get(self.db_path)
            rows = db.query(
                "SELECT keywords FROM domain_rules WHERE confidence_threshold >= 0.8"
            )
            for row in rows:
                keywords = json.loads(row[0])
                if any(kw in query for kw in keywords):
                    return True
        except Exception:
            pass
        
        return False
    
    def _llm_validate(self, user_query: str, response: str, 
                      llm_adapter) -> Tuple[bool, str]:
        """使用LLM进行智能验证"""
        try:
            prompt = f"""分析以下问答是否存在知识错误或缺失：

用户问题：{user_query}

系统回答：{response}

请判断：
1. 回答是否正确？
2. 是否存在明显的知识错误？
3. 是否需要补充更多信息？

以JSON格式返回：
{{
  "is_correct": true/false,
  "has_error": true/false,
  "error_type": "错误类型（如果有）",
  "reason": "判断理由"
}}
"""
            
            llm_response = llm_adapter.generate(prompt, task_type="validation")
            
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                if result.get("has_error"):
                    return True, result.get("reason", "LLM检测到错误")
        except Exception as e:
            logger.debug(f"LLM验证失败: {e}")
        
        return False, ""
    
    def _check_error_patterns(self, user_query: str, response: str) -> Tuple[bool, str]:
        """检查已知错误模式"""
        try:
            db = DatabaseManager.get(self.db_path)
            rows = db.query(
                "SELECT pattern_type, pattern, correction FROM error_patterns WHERE confidence >= 0.7"
            )
            for row in rows:
                pattern_type, pattern, correction = row[0], row[1], row[2]
                if re.search(pattern, response):
                    return True, f"匹配错误模式({pattern_type})，应修正为: {correction}"
        except Exception:
            pass
        
        return False, ""
    
    def learn_error_pattern(self, pattern_type: str, pattern: str, 
                           correction: str, confidence: float = 0.8):
        """学习新的错误模式"""
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute(
                "INSERT INTO error_patterns (pattern_type, pattern, correction, confidence, created_at) VALUES (?, ?, ?, ?, ?)",
                (pattern_type, pattern, correction, confidence, datetime.now().isoformat()),
                commit=True
            )
            logger.info(f"学习错误模式: {pattern_type}")
        except Exception as e:
            logger.warning(f"学习失败: {e}")
    
    def add_domain_rule(self, domain: str, keywords: List[str], 
                       confidence_threshold: float = 0.8):
        """添加领域规则"""
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute(
                "INSERT INTO domain_rules (domain, keywords, confidence_threshold, created_at, source) VALUES (?, ?, ?, ?, ?)",
                (domain, json.dumps(keywords, ensure_ascii=False), confidence_threshold, datetime.now().isoformat(), "user_added"),
                commit=True
            )
            logger.info(f"添加领域规则: {domain}")
        except Exception as e:
            logger.warning(f"添加规则失败: {e}")
    
    def should_learn_externally(self, user_query: str, response: str,
                                confidence: float = 1.0,
                                llm_adapter = None) -> Tuple[bool, str]:
        """判断是否应该外部学习"""
        
        has_gap, reason, issues = self.detect_knowledge_gap(
            user_query, response, confidence, llm_adapter
        )
        
        if has_gap:
            self._record_validation(user_query, has_gap, reason, confidence)
            return True, f"检测到知识缺失: {reason}"
        
        learn_keywords = ["如何", "为什么", "原理", "详解", "深入", "请教", "推荐", "选型"]
        if any(kw in user_query for kw in learn_keywords):
            self._record_validation(user_query, False, "学习型问题", confidence)
            return True, "学习型问题，建议外部学习"
        
        return False, ""
    
    def _record_validation(self, query: str, has_gap: bool, reason: str, confidence: float):
        """记录验证历史"""
        try:
            query_hash = str(hash(query))[:12]
            db = DatabaseManager.get(self.db_path)
            db.execute(
                "INSERT INTO validation_history (query_hash, has_gap, reason, confidence, validated_at) VALUES (?, ?, ?, ?, ?)",
                (query_hash, int(has_gap), reason, confidence, datetime.now().isoformat()),
                commit=True
            )
        except Exception:
            pass


gap_detector = KnowledgeGapDetector()
