"""
快速反射引擎 (Quick Reflex Engine) - T0反射层
基于关键词匹配的快速拦截器，响应时间 < 100ms

跨学科理论依据：
- 认知科学：双重加工理论（System 1快思考）
- 神经科学：脊髓反射弧（不经过大脑的快速反应）
- 控制论：前馈控制（预测性响应）

设计原则：
1. 简单问题不走复杂流程
2. 匹配速度优先
3. 可配置、可扩展
"""
import yaml
import time
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


class QuickReflexEngine:
    """
    快速反射引擎 - 快速拦截简单问题
    
    匹配流程：
    1. 文本清洗
    2. 完全匹配
    3. 包含匹配
    4. 模糊匹配（关键词重叠）
    """
    
    def __init__(self, config_path: str = "config/reflex_rules.yaml"):
        self.rules: List[Dict] = []
        self.case_sensitive = False
        self.min_ratio = 0.8
        self.max_time_ms = 100
        self._load_rules(config_path)
        
    def _load_rules(self, config_path: str):
        """加载反射规则"""
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"反射规则文件不存在: {config_path}，使用默认规则")
            self._load_default_rules()
            return
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            self.case_sensitive = config.get("match_options", {}).get("case_sensitive", False)
            self.min_ratio = config.get("match_options", {}).get("min_match_ratio", 0.8)
            self.max_time_ms = config.get("match_options", {}).get("max_response_time_ms", 100)
            
            # 加载停用词
            self.stopwords = set(config.get("match_options", {}).get("stopwords", [
                "的", "了", "是", "在", "我", "你", "他", "她", "它", "们",
                "这", "那", "有", "和", "与", "或", "但", "如果", "因为"
            ]))
            
            for rule in config.get("rules", []):
                patterns = rule.get("patterns", [])
                response = rule.get("response", "")
                priority = rule.get("priority", 0)
                category = rule.get("category", "general")
                # 规则级阈值（覆盖全局）
                rule_min_ratio = rule.get("min_ratio", self.min_ratio)
                
                # 过滤空模式
                patterns = [p for p in patterns if p and p.strip()]
                if not patterns:
                    logger.warning(f"规则 '{category}' 无有效模式，已跳过")
                    continue
                
                self.rules.append({
                    "patterns": patterns,
                    "response": response,
                    "priority": priority,
                    "category": category,
                    "min_ratio": rule_min_ratio
                })
            
            # 按优先级排序（高优先级先匹配）
            self.rules.sort(key=lambda x: x["priority"], reverse=True)
            logger.info(f"✅ 快速反射引擎加载 {len(self.rules)} 条规则")
            
        except Exception as e:
            logger.error(f"加载反射规则失败: {e}")
            self._load_default_rules()
    
    def _load_default_rules(self):
        """加载默认规则（兜底）"""
        self.rules = [
            {
                "patterns": ["你好", "hi", "hello"],
                "response": "你好！有什么可以帮你的吗？",
                "priority": 100,
                "category": "greeting"
            },
            {
                "patterns": ["谢谢", "感谢"],
                "response": "不客气！",
                "priority": 90,
                "category": "confirmation"
            }
        ]
        logger.info("✅ 快速反射引擎使用默认规则")
    
    def match(self, text: str) -> Optional[Dict[str, Any]]:
        """
        匹配用户输入，返回响应
        
        Args:
            text: 用户输入文本
            
        Returns:
            匹配成功返回 {"response": str, "matched_pattern": str, ...}
            未匹配返回 None
        """
        # 边界保护：空输入
        if not text or not text.strip():
            return None
        
        start_time = time.time()
        
        # 清理文本
        clean_text = text.strip()
        if not self.case_sensitive:
            clean_text = clean_text.lower()
        
        # 遍历规则
        for rule in self.rules:
            rule_min_ratio = rule.get("min_ratio", self.min_ratio)
            
            for pattern in rule["patterns"]:
                # 边界保护：空模式
                if not pattern or not pattern.strip():
                    continue
                
                pattern_text = pattern.strip().lower() if not self.case_sensitive else pattern.strip()
                
                # 边界保护：模式为空字符串
                if not pattern_text:
                    continue
                
                # 1. 完全匹配
                if clean_text == pattern_text:
                    self._log_match(rule, pattern, "exact")
                    return self._build_result(rule, pattern, "exact", start_time)
                
                # 2. 包含匹配
                if pattern_text in clean_text or clean_text in pattern_text:
                    self._log_match(rule, pattern, "contains")
                    return self._build_result(rule, pattern, "contains", start_time)
                
                # 3. 模糊匹配（关键词重叠，过滤停用词）
                words_pattern = self._filter_stopwords(set(pattern_text.split()))
                words_text = self._filter_stopwords(set(clean_text.split()))
                
                # 边界保护：空词集
                if not words_pattern or not words_text:
                    continue
                
                overlap = len(words_pattern & words_text) / len(words_pattern)
                if overlap >= rule_min_ratio:
                    self._log_match(rule, pattern, "fuzzy", overlap)
                    return self._build_result(rule, pattern, "fuzzy", start_time, overlap)
        
        return None
    
    def _filter_stopwords(self, words: set) -> set:
        """过滤停用词"""
        if not hasattr(self, 'stopwords'):
            return words
        return words - self.stopwords
    
    def _log_match(self, rule: Dict, pattern: str, match_type: str, ratio: float = 1.0):
        """记录匹配命中（用于统计分析）"""
        # 更新统计计数器
        if not hasattr(self, '_match_stats'):
            self._match_stats = {}
        
        category = rule.get("category", "general")
        key = f"{category}:{match_type}"
        self._match_stats[key] = self._match_stats.get(key, 0) + 1
        
        logger.debug(f"反射匹配: {pattern} ({match_type}, ratio={ratio:.2f})")
    
    def _build_result(
        self, 
        rule: Dict, 
        pattern: str, 
        match_type: str,
        start_time: float,
        match_ratio: float = 1.0
    ) -> Dict[str, Any]:
        """构建匹配结果"""
        elapsed_ms = (time.time() - start_time) * 1000
        
        return {
            "response": rule["response"],
            "matched_pattern": pattern,
            "priority": rule["priority"],
            "category": rule.get("category", "general"),
            "match_type": match_type,
            "match_ratio": match_ratio,
            "elapsed_ms": elapsed_ms
        }
    
    def is_match(self, text: str) -> bool:
        """快速判断是否匹配（用于路由决策）"""
        return self.match(text) is not None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_rules": len(self.rules),
            "categories": list(set(r.get("category", "general") for r in self.rules)),
            "case_sensitive": self.case_sensitive,
            "min_ratio": self.min_ratio,
            "stopwords_count": len(getattr(self, 'stopwords', set()))
        }
        
        # 添加匹配统计
        if hasattr(self, '_match_stats'):
            stats["match_stats"] = self._match_stats
            stats["total_matches"] = sum(self._match_stats.values())
        
        return stats
    
    def reload(self, config_path: str = None):
        """
        热加载配置（无需重启服务）
        
        Args:
            config_path: 新配置文件路径（None则使用原路径）
        """
        if config_path:
            self.config_path = config_path
        
        # 清空现有规则
        self.rules = []
        
        # 重新加载
        self._load_rules(self.config_path)
        self._match_stats = {}  # 重置统计
        
        logger.info(f"🔄 反射引擎已热加载: {len(self.rules)} 条规则")


# 全局实例
_quick_reflex = None
_config_path = "config/reflex_rules.yaml"

def get_quick_reflex(config_path: str = "config/reflex_rules.yaml") -> QuickReflexEngine:
    """获取快速反射引擎实例（单例）"""
    global _quick_reflex, _config_path
    if _quick_reflex is None:
        _config_path = config_path
        _quick_reflex = QuickReflexEngine(config_path)
    return _quick_reflex

def reload_reflex():
    """热加载反射规则"""
    global _quick_reflex
    if _quick_reflex:
        _quick_reflex.reload()
        return True
    return False