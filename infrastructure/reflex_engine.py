"""
反射级规则引擎 - 可配置的硬编码快速响应
仅用于安全与生存关键场景，参数完全可配置
"""
import yaml
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime
from loguru import logger
from infrastructure.database_manager import DatabaseManager


class ReflexRule:
    """反射规则"""
    
    SENSITIVE_FIELDS = {'password', 'token', 'key', 'secret', 'credential', 'api_key'}
    
    def __init__(
        self,
        name: str,
        condition: str,
        action: str,
        priority: int = 50,
        enabled: bool = True,
        threshold: float = None,
        fallback: str = None,
        description: str = ""
    ):
        self.name = name
        self.condition = condition
        self.action = action
        self.priority = priority
        self.enabled = enabled
        self.threshold = threshold
        self.fallback = fallback
        self.description = description
        self.trigger_count = 0
        self.last_trigger_time = None
        self._lock = threading.Lock()
    
    def check(self, context: Dict) -> bool:
        """检查条件是否触发"""
        if not self.enabled:
            return False
        
        try:
            # 安全关键条件检查
            if self.condition == "cpu_temperature":
                current = context.get("cpu_temp", 0)
                return current > self.threshold
            
            elif self.condition == "memory_usage":
                current = context.get("memory_percent", 0)
                return current > self.threshold
            
            elif self.condition == "dangerous_command":
                cmd = context.get("user_input", "")
                dangerous_patterns = ["rm -rf /", "drop database", "format c:"]
                return any(pattern in cmd.lower() for pattern in dangerous_patterns)
            
            elif self.condition == "user_frustration":
                # 连续失败次数
                failures = context.get("recent_failures", 0)
                return failures >= self.threshold
            
            elif self.condition == "security_breach":
                return context.get("security_alert", False)
            
            return False
            
        except Exception as e:
            logger.error(f"反射规则检查失败 ({self.name}): {e}")
            return False
    
    def execute(self, context: Dict) -> Optional[str]:
        """执行动作"""
        with self._lock:
            self.trigger_count += 1
            self.last_trigger_time = datetime.now().isoformat()
        
        logger.warning(f"【反射触发】{self.name} (优先级: {self.priority})")
        
        self._log_trigger(context)
        
        if self.action == "block":
            return "⚠️ 危险操作已被拦截"
        
        elif self.action == "reject":
            return "⚠️ 系统资源紧张，请求被拒绝"
        
        elif self.action == "throttle":
            return "⚠️ 系统过载，已启用节能模式"
        
        elif self.action == "shutdown":
            logger.critical("系统即将关闭（安全保护）")
            return "⚠️ 系统检测到严重问题，即将关闭"
        
        elif self.action == "apologize":
            return "抱歉，我遇到了一些困难。让我换种方式尝试..."
        
        elif self.action == "alert":
            return "⚠️ 检测到安全风险，已记录并通知"
        
        elif self.action == "safe_mode":
            return "⚠️ 进入安全模式，部分功能受限"
        
        return None
    
    def _log_trigger(self, context: Dict):
        """记录触发日志"""
        try:
            safe_context = {}
            for key, value in context.items():
                if key.lower() in self.SENSITIVE_FIELDS:
                    safe_context[key] = "***REDACTED***"
                elif key == "user_input":
                    safe_context[key] = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                else:
                    safe_context[key] = value
            
            db = DatabaseManager.get("reflex_logs.db")
            conn = db._get_conn()
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reflex_triggers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name TEXT,
                    priority INTEGER,
                    action TEXT,
                    context TEXT,
                    timestamp TEXT
                )
            ''')
            conn.execute('''
                INSERT INTO reflex_triggers
                (rule_name, priority, action, context, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                self.name,
                self.priority,
                self.action,
                str(safe_context)[:200],
                datetime.now().isoformat()
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"反射日志记录失败: {e}")


class ReflexEngine:
    """反射引擎 - 可配置的硬编码快速响应"""
    
    DEFAULT_RULES = [
        {
            "name": "dangerous_command_block",
            "condition": "dangerous_command",
            "action": "block",
            "priority": 100,
            "enabled": True,
            "description": "拦截危险命令（rm -rf /, drop database等）"
        },
        {
            "name": "cpu_overheat",
            "condition": "cpu_temperature",
            "action": "throttle",
            "threshold": 85.0,
            "priority": 95,
            "enabled": True,
            "fallback": "shutdown",
            "description": "CPU过热保护"
        },
        {
            "name": "memory_exhaustion",
            "condition": "memory_usage",
            "action": "reject",
            "threshold": 90.0,
            "priority": 90,
            "enabled": True,
            "description": "内存耗尽保护"
        },
        {
            "name": "user_frustration_response",
            "condition": "user_frustration",
            "action": "apologize",
            "threshold": 3,
            "priority": 70,
            "enabled": True,
            "description": "用户挫折响应（连续失败3次）"
        },
        {
            "name": "security_breach_alert",
            "condition": "security_breach",
            "action": "alert",
            "priority": 99,
            "enabled": True,
            "description": "安全漏洞告警"
        }
    ]
    
    def __init__(self, config_path: str = "config/reflexes.yaml"):
        self.config_path = Path(config_path)
        self.rules: List[ReflexRule] = []
        self.monitoring = False
        self.monitor_thread = None
        self._lock = threading.RLock()
        
        self._load_rules()
        logger.info(f"反射引擎已初始化 ({len(self.rules)}条规则)")
    
    def _load_rules(self):
        """加载规则（配置优先，默认兜底）"""
        # 尝试从配置文件加载
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    rules_config = config.get("reflexes", [])
                
                for rule_dict in rules_config:
                    self.rules.append(ReflexRule(**rule_dict))
                
                logger.info(f"从配置加载 {len(self.rules)} 条反射规则")
                return
                
            except Exception as e:
                logger.warning(f"配置加载失败，使用默认规则: {e}")
        
        # 使用默认规则
        for rule_dict in self.DEFAULT_RULES:
            self.rules.append(ReflexRule(**rule_dict))
        
        logger.info(f"使用默认 {len(self.rules)} 条反射规则")
    
    def check(self, context: Dict) -> Optional[str]:
        """检查所有规则（按优先级排序）"""
        # 按优先级排序（高优先级先检查）
        sorted_rules = sorted(self.rules, key=lambda r: -r.priority)
        
        for rule in sorted_rules:
            if rule.check(context):
                result = rule.execute(context)
                if result:
                    return result
        
        return None
    
    def get_rule(self, name: str) -> Optional[ReflexRule]:
        """获取规则"""
        for rule in self.rules:
            if rule.name == name:
                return rule
        return None
    
    def set_rule_param(
        self,
        name: str,
        param: str,
        value: any
    ) -> bool:
        """设置规则参数（用户可调用）"""
        with self._lock:
            rule = self.get_rule(name)
            if not rule:
                return False
            
            if param == "threshold":
                if not isinstance(value, (int, float)):
                    return False
                rule.threshold = float(value)
            elif param == "enabled":
                if not isinstance(value, bool):
                    return False
                rule.enabled = value
            elif param == "priority":
                if not isinstance(value, int) or not (0 <= value <= 100):
                    return False
                rule.priority = value
            elif param == "action":
                valid_actions = {"block", "reject", "throttle", "shutdown", "apologize", "alert", "safe_mode"}
                if value not in valid_actions:
                    return False
                rule.action = value
            else:
                return False
            
            logger.info(f"反射规则参数更新: {name}.{param} = {value}")
            self._save_config()
            return True
    
    def _save_config(self):
        """保存配置"""
        with self._lock:
            try:
                self.config_path.parent.mkdir(exist_ok=True)
                
                config = {
                    "reflexes": [
                        {
                            "name": r.name,
                            "condition": r.condition,
                            "action": r.action,
                            "priority": r.priority,
                            "enabled": r.enabled,
                            "threshold": r.threshold,
                            "fallback": r.fallback,
                            "description": r.description
                        }
                        for r in self.rules
                    ]
                }
                
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, allow_unicode=True, indent=2)
                
                logger.info(f"反射规则配置已保存到 {self.config_path}")
                
            except Exception as e:
                logger.error(f"配置保存失败: {e}")
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules if r.enabled),
            "total_triggers": sum(r.trigger_count for r in self.rules),
            "rules": [
                {
                    "name": r.name,
                    "enabled": r.enabled,
                    "priority": r.priority,
                    "triggers": r.trigger_count,
                    "last_trigger": r.last_trigger_time
                }
                for r in self.rules
            ]
        }
    
    def start_monitoring(self, sensor_callback: Callable[[], Dict]):
        """启动后台监控线程"""
        if self.monitoring:
            return
        
        self.monitoring = True
        
        def monitor_loop():
            while self.monitoring:
                try:
                    context = sensor_callback()
                    self.check(context)
                    time.sleep(1.0)  # 每秒检查一次
                except Exception as e:
                    logger.error(f"监控循环错误: {e}")
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("反射引擎监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("反射引擎监控已停止")


reflex_engine = ReflexEngine()
