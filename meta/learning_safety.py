"""
学习安全边界与回滚系统 - 防止错误学习
实现学习规则的置信度衰减、历史记录和回滚机制
"""
import json
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from loguru import logger
from infrastructure.event_bus import bus


@dataclass
class LearningRule:
    """学习规则"""
    rule_id: str
    pattern: str
    intent_type: str
    confidence: float
    created_at: str
    last_used_at: str
    use_count: int
    is_fixed: bool = False
    source: str = "auto"
    
    def get_effective_confidence(self) -> float:
        """计算有效置信度(考虑半衰期)"""
        if self.is_fixed:
            return self.confidence
        
        last_used = datetime.fromisoformat(self.last_used_at)
        age_days = (datetime.now() - last_used).days
        half_life = 30
        
        decay = 0.5 ** (age_days / half_life)
        return self.confidence * decay
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LearningRule':
        return cls(**data)


class LearningHistory:
    """学习历史管理"""
    
    BASE_DATA_DIR = Path("data")
    
    def __init__(self, history_file: str = "data/learning_history.json"):
        self.history_file = self.BASE_DATA_DIR / Path(history_file).name
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.max_history = 100
        self._lock = threading.Lock()
        
    def _load_history(self) -> List[Dict]:
        """加载历史记录"""
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载学习历史失败: {e}")
            return []
    
    def _save_history(self, history: List[Dict]):
        """保存历史记录"""
        with self._lock:
            try:
                with open(self.history_file, 'w', encoding='utf-8') as f:
                    json.dump(history, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"保存学习历史失败: {e}")
    
    def record_change(self, change_type: str, change_data: Dict) -> str:
        """记录学习修改"""
        change_id = f"chg_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self._load_history())}"
        
        entry = {
            "id": change_id,
            "timestamp": datetime.now().isoformat(),
            "type": change_type,
            "data": change_data,
            "can_rollback": True
        }
        
        history = self._load_history()
        history.append(entry)
        
        if len(history) > self.max_history:
            history = history[-self.max_history:]
        
        self._save_history(history)
        
        logger.info(f"记录学习修改: {change_id} ({change_type})")
        
        return change_id
    
    def get_recent_changes(self, count: int = 10) -> List[Dict]:
        """获取最近的修改记录"""
        history = self._load_history()
        return history[-count:]
    
    def get_change_by_id(self, change_id: str) -> Optional[Dict]:
        """根据ID获取修改记录"""
        history = self._load_history()
        for entry in history:
            if entry["id"] == change_id:
                return entry
        return None


class LearningSafetyManager:
    """学习安全管理器"""
    
    BASE_DATA_DIR = Path("data")
    
    def __init__(self, rules_file: str = "data/learning_rules.json"):
        self.rules_file = self.BASE_DATA_DIR / Path(rules_file).name
        self.rules_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.history = LearningHistory()
        self.rules: Dict[str, LearningRule] = {}
        self._lock = threading.Lock()
        
        self._load_rules()
        
        bus.subscribe("learning_rule_created", self._on_rule_created)
        bus.subscribe("learning_rule_used", self._on_rule_used)
        
        logger.info(f"学习安全管理器初始化完成,加载{len(self.rules)}条规则")
    
    def _load_rules(self):
        """加载学习规则"""
        if not self.rules_file.exists():
            return
        
        try:
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for rule_id, rule_data in data.items():
                self.rules[rule_id] = LearningRule.from_dict(rule_data)
        
        except Exception as e:
            logger.error(f"加载学习规则失败: {e}")
    
    def _save_rules(self):
        """保存学习规则"""
        with self._lock:
            try:
                data = {
                    rule_id: rule.to_dict()
                    for rule_id, rule in self.rules.items()
                }
                
                with open(self.rules_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            except Exception as e:
                logger.error(f"保存学习规则失败: {e}")
    
    def create_rule(self, pattern: str, intent_type: str, 
                   confidence: float = 0.7, source: str = "auto") -> LearningRule:
        """创建新学习规则"""
        with self._lock:
            rule_id = f"rule_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.rules)}"
            
            now = datetime.now().isoformat()
            
            rule = LearningRule(
                rule_id=rule_id,
                pattern=pattern,
                intent_type=intent_type,
                confidence=confidence,
                created_at=now,
                last_used_at=now,
                use_count=0,
                is_fixed=False,
                source=source
            )
            
            self.rules[rule_id] = rule
        
        self._save_rules()
        
        self.history.record_change("rule_created", {
            "rule_id": rule_id,
            "pattern": pattern,
            "intent_type": intent_type,
            "confidence": confidence
        })
        
        logger.info(f"创建学习规则: {rule_id} ({pattern} -> {intent_type})")
        
        return rule
    
    def update_rule(self, rule_id: str, **kwargs) -> Optional[LearningRule]:
        """更新学习规则"""
        with self._lock:
            if rule_id not in self.rules:
                logger.error(f"规则不存在: {rule_id}")
                return None
            
            rule = self.rules[rule_id]
            old_data = rule.to_dict()
            
            for key, value in kwargs.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
        
        self._save_rules()
        
        self.history.record_change("rule_updated", {
            "rule_id": rule_id,
            "old_data": old_data,
            "new_data": rule.to_dict()
        })
        
        logger.info(f"更新学习规则: {rule_id}")
        
        return rule
    
    def delete_rule(self, rule_id: str) -> bool:
        """删除学习规则"""
        with self._lock:
            if rule_id not in self.rules:
                logger.error(f"规则不存在: {rule_id}")
                return False
            
            rule = self.rules[rule_id]
        
        self.history.record_change("rule_deleted", {
            "rule_id": rule_id,
            "rule_data": rule.to_dict()
        })
        
        with self._lock:
            del self.rules[rule_id]
        
        self._save_rules()
        
        logger.info(f"删除学习规则: {rule_id}")
        
        return True
    
    def fix_rule(self, rule_id: str) -> bool:
        """固定规则(不衰减)"""
        return self.update_rule(rule_id, is_fixed=True) is not None
    
    def unfix_rule(self, rule_id: str) -> bool:
        """取消固定"""
        return self.update_rule(rule_id, is_fixed=False) is not None
    
    def rollback(self, steps: int = 1) -> Dict[str, Any]:
        """回滚最近N次学习"""
        history = self.history._load_history()
        
        rolled_back = []
        
        for _ in range(steps):
            if not history:
                break
            
            last_change = history.pop()
            
            if not last_change.get("can_rollback", False):
                logger.warning(f"无法回滚: {last_change['id']}")
                history.append(last_change)
                break
            
            success = self._apply_reverse_change(last_change)
            
            if success:
                rolled_back.append(last_change)
            else:
                logger.error(f"回滚失败: {last_change['id']}")
                history.append(last_change)
                break
        
        self.history._save_history(history)
        
        logger.info(f"回滚{len(rolled_back)}次学习")
        
        return {
            "success": len(rolled_back) > 0,
            "rolled_back": rolled_back,
            "count": len(rolled_back)
        }
    
    def _apply_reverse_change(self, change: Dict) -> bool:
        """应用反向修改"""
        change_type = change["type"]
        data = change["data"]
        
        try:
            if change_type == "rule_created":
                rule_id = data["rule_id"]
                if rule_id in self.rules:
                    del self.rules[rule_id]
                    self._save_rules()
            
            elif change_type == "rule_deleted":
                rule_data = data["rule_data"]
                rule = LearningRule.from_dict(rule_data)
                self.rules[rule.rule_id] = rule
                self._save_rules()
            
            elif change_type == "rule_updated":
                rule_id = data["rule_id"]
                old_data = data["old_data"]
                rule = LearningRule.from_dict(old_data)
                self.rules[rule_id] = rule
                self._save_rules()
            
            return True
        
        except Exception as e:
            logger.error(f"应用反向修改失败: {e}")
            return False
    
    def get_active_rules(self, min_confidence: float = 0.3) -> List[LearningRule]:
        """获取活跃规则(有效置信度大于阈值)"""
        active = []
        
        for rule in self.rules.values():
            effective_conf = rule.get_effective_confidence()
            if effective_conf >= min_confidence:
                active.append(rule)
        
        active.sort(key=lambda r: r.get_effective_confidence(), reverse=True)
        
        return active
    
    def cleanup_expired_rules(self, days: int = 90) -> int:
        """清理过期规则(未使用超过指定天数)"""
        threshold = datetime.now() - timedelta(days=days)
        cleaned = 0
        
        to_delete = []
        for rule_id, rule in self.rules.items():
            if rule.is_fixed:
                continue
            
            last_used = datetime.fromisoformat(rule.last_used_at)
            if last_used < threshold:
                to_delete.append(rule_id)
        
        for rule_id in to_delete:
            self.delete_rule(rule_id)
            cleaned += 1
        
        logger.info(f"清理{cleaned}条过期规则")
        
        return cleaned
    
    def _on_rule_created(self, event_data: Dict):
        """处理规则创建事件"""
        pattern = event_data.get("pattern")
        intent_type = event_data.get("intent_type")
        confidence = event_data.get("confidence", 0.7)
        source = event_data.get("source", "auto")
        
        if pattern and intent_type:
            self.create_rule(pattern, intent_type, confidence, source)
    
    def _on_rule_used(self, event_data: Dict):
        """处理规则使用事件"""
        rule_id = event_data.get("rule_id")
        
        if rule_id:
            with self._lock:
                if rule_id in self.rules:
                    rule = self.rules[rule_id]
                    rule.use_count += 1
                    rule.last_used_at = datetime.now().isoformat()
            
            self._save_rules()
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = len(self.rules)
        fixed = sum(1 for r in self.rules.values() if r.is_fixed)
        active = len(self.get_active_rules())
        
        avg_confidence = 0
        if total > 0:
            avg_confidence = sum(r.confidence for r in self.rules.values()) / total
        
        return {
            "total_rules": total,
            "fixed_rules": fixed,
            "active_rules": active,
            "avg_confidence": avg_confidence,
            "history_count": len(self.history._load_history())
        }


learning_safety = LearningSafetyManager()