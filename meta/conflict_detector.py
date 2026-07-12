"""
规则冲突检测器 - 增强版
动作解析、合并策略、条件精确匹配
"""
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger
from infrastructure.config_manager import config
from infrastructure.database_manager import DatabaseManager


class ConflictDetector:
    """规则冲突检测器"""
    
    def __init__(self):
        self.db_path = config.get("learning_rules.db_path", "data/learning_rules.db")
        logger.info("规则冲突检测器初始化完成")
    
    def detect_conflicts(self) -> List[Dict]:
        """检测所有规则冲突"""
        rules = self._load_active_rules()
        
        if len(rules) < 2:
            return []
        
        conflicts = []
        
        for i in range(len(rules)):
            for j in range(i + 1, len(rules)):
                conflict = self._check_conflict(rules[i], rules[j])
                if conflict:
                    conflicts.append(conflict)
        
        logger.info(f"检测到 {len(conflicts)} 个规则冲突")
        return conflicts
    
    def _load_active_rules(self) -> List[Dict]:
        """加载活跃规则"""
        try:
            db = DatabaseManager.get(self.db_path)
            rows = db.query('''
                SELECT id, condition, action, priority, confidence, status, source
                FROM learning_rules
                WHERE status = 'active'
                ORDER BY priority DESC, confidence DESC
            ''')
            
            return [dict(row) for row in rows]
        
        except Exception as e:
            logger.error(f"加载规则失败: {e}")
            return []
    
    def _parse_action(self, action: str) -> Dict:
        """解析动作字符串为结构化字典"""
        if action.startswith("merge:"):
            sub_actions = action.split(":", 1)[1].split("|")
            return {
                "type": "merge",
                "actions": [self._parse_action(a) for a in sub_actions]
            }
        elif action.startswith("reroute:"):
            return {"type": "reroute", "target": action.split(":")[1]}
        elif action.startswith("prefer_model:"):
            return {"type": "prefer", "target": action.split(":")[1]}
        elif action.startswith("avoid_model:"):
            return {"type": "avoid", "target": action.split(":")[1]}
        elif action.startswith("ask_user:"):
            return {"type": "ask_user", "message": action.split(":", 1)[1]}
        elif action.startswith("trigger_"):
            return {"type": "trigger", "action": action}
        else:
            return {"type": "other", "raw": action}
    
    def _check_conflict(self, rule1: Dict, rule2: Dict) -> Optional[Dict]:
        """检查两条规则是否冲突"""
        if rule1["condition"] != rule2["condition"]:
            return None
        
        action1 = self._parse_action(rule1["action"])
        action2 = self._parse_action(rule2["action"])
        
        if action1["type"] != action2["type"]:
            return None
        
        conflict_type = None
        
        if action1["type"] in ("reroute", "prefer", "avoid"):
            if action1["target"] != action2["target"]:
                conflict_type = "model_conflict"
        elif action1["type"] == "ask_user":
            if action1["message"] != action2["message"]:
                conflict_type = "message_conflict"
        elif action1["type"] == "trigger":
            if action1["action"] != action2["action"]:
                conflict_type = "action_conflict"
        
        if not conflict_type:
            return None
        
        return {
            "type": "rule_conflict",
            "rule1_id": rule1["id"],
            "rule2_id": rule2["id"],
            "rule1": rule1,
            "rule2": rule2,
            "conflict_type": conflict_type,
            "suggestion": self._suggest_resolution(rule1, rule2, conflict_type)
        }
    
    def _suggest_resolution(self, rule1: Dict, rule2: Dict, conflict_type: str) -> str:
        """生成冲突解决建议"""
        if conflict_type == "model_conflict":
            if rule1["confidence"] > rule2["confidence"]:
                return f"保留规则 {rule1['id']} (置信度更高), 停用 {rule2['id']}"
            elif rule2["confidence"] > rule1["confidence"]:
                return f"保留规则 {rule2['id']} (置信度更高), 停用 {rule1['id']}"
            else:
                return f"置信度相同, 建议合并规则 {rule1['id']} 和 {rule2['id']}"
        else:
            return f"请人工审核规则 {rule1['id']} 和 {rule2['id']}"
    
    def resolve_conflict(self, conflict: Dict, resolution: str = "auto") -> Dict:
        """解决冲突
        
        Args:
            conflict: 冲突信息
            resolution: 解决方式 (auto, rule1, rule2, merge)
        """
        rule1_id = conflict["rule1_id"]
        rule2_id = conflict["rule2_id"]
        
        if resolution == "auto":
            if conflict["rule1"]["confidence"] >= conflict["rule2"]["confidence"]:
                winner, loser = rule1_id, rule2_id
            else:
                winner, loser = rule2_id, rule1_id
            
            self._deactivate_rule(loser)
            return {
                "success": True,
                "action": "auto_resolve",
                "deactivated": loser,
                "kept": winner
            }
        
        elif resolution == "rule1":
            self._deactivate_rule(rule2_id)
            return {
                "success": True,
                "action": "keep_rule1",
                "deactivated": rule2_id
            }
        
        elif resolution == "rule2":
            self._deactivate_rule(rule1_id)
            return {
                "success": True,
                "action": "keep_rule2",
                "deactivated": rule1_id
            }
        
        elif resolution == "merge":
            merged_action = f"merge:{conflict['rule1']['action']}|{conflict['rule2']['action']}"
            
            self._deactivate_rule(rule1_id)
            self._deactivate_rule(rule2_id)
            
            self._create_merged_rule(
                conflict["rule1"]["condition"],
                merged_action,
                max(conflict["rule1"]["confidence"], conflict["rule2"]["confidence"])
            )
            
            return {
                "success": True,
                "action": "merged",
                "deactivated": [rule1_id, rule2_id]
            }
        
        else:
            return {"success": False, "message": "未支持的解决方式"}
    
    def _deactivate_rule(self, rule_id: int):
        """停用规则"""
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute(
                "UPDATE learning_rules SET status = 'conflicted' WHERE id = ?",
                (rule_id,),
                commit=True
            )
            
            logger.info(f"规则 {rule_id} 已标记为冲突并停用")
        
        except Exception as e:
            logger.error(f"停用规则失败: {e}")
    
    def _create_merged_rule(self, condition: str, action: str, confidence: float):
        """创建合并规则(使用JSON格式存储动作列表)"""
        try:
            import json
            db = DatabaseManager.get(self.db_path)
            db.execute('''
                INSERT INTO learning_rules 
                (condition, action, priority, confidence, status, source, created_at, metadata)
                VALUES (?, ?, ?, ?, 'pending', 'merge_auto', ?, ?)
            ''', (condition, action, 5, confidence, datetime.now().isoformat(), "{}"), commit=True)
            
            logger.info(f"创建合并规则: {condition} -> {action}")
        
        except Exception as e:
            logger.error(f"创建合并规则失败: {e}")
    
    def get_conflict_report(self) -> Dict:
        """获取冲突报告"""
        conflicts = self.detect_conflicts()
        
        report = {
            "total_conflicts": len(conflicts),
            "conflicts": conflicts,
            "summary": {
                "model_conflicts": sum(1 for c in conflicts if c["conflict_type"] == "model_conflict"),
                "message_conflicts": sum(1 for c in conflicts if c["conflict_type"] == "message_conflict"),
                "action_conflicts": sum(1 for c in conflicts if c["conflict_type"] == "action_conflict")
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return report


conflict_detector = ConflictDetector()
