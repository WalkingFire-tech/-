"""
安全学习层 - 在学习流程中嵌入价值对齐检查

确保所有学习内容都经过价值对齐验证

三层防护流程：
1. 学习前：来源验证 + 价值对齐检查
2. 学习中：监控学习过程
3. 学习后：审计学习结果
"""

import sqlite3
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

from .value_alignment_checker import (
    check_value_alignment,
    AlignmentStatus,
    ValueAlignmentResult
)


class SafeLearningLayer:
    """
    安全学习层
    
    在系统的学习流程中嵌入安全检查：
    1. 学习前：检查内容是否与核心价值对齐
    2. 学习中：监控学习过程是否有异常
    3. 学习后：审计学习结果是否有偏移
    """
    
    def __init__(self, db_path: str = "data/safe_learning.db"):
        self.db_path = Path(db_path)
        self._init_database()
        
        self.learning_journal = []
        self.suspicious_entries = []
        self.alerts = []
        
        self._load_stats()
        
        logger.info("🛡️ 安全学习层已初始化")
    
    def _init_database(self):
        """初始化数据库"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS learning_journal (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    source TEXT,
                    content_preview TEXT,
                    alignment_status TEXT,
                    alignment_score REAL,
                    issues TEXT,
                    accepted INTEGER,
                    metadata TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    alert_type TEXT,
                    source TEXT,
                    severity TEXT,
                    issues TEXT,
                    resolved INTEGER DEFAULT 0
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS learning_stats (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON learning_journal(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON learning_journal(alignment_status)')
            
            conn.commit()
    
    def _load_stats(self):
        """加载统计信息"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute(
                    "SELECT key, value FROM learning_stats"
                )
                self._stats = {row[0]: json.loads(row[1]) for row in cursor.fetchall()}
        except:
            self._stats = {
                "total_attempts": 0,
                "accepted": 0,
                "rejected": 0,
                "pending_review": 0
            }
    
    def learn_safely(self, content: str, source: str, metadata: Dict = None) -> Dict:
        """
        安全地学习新知识
        
        流程：
        1. 价值对齐检查
        2. 学习节奏检查（预警模式，不限制）
        3. 通过 → 正常学习
        4. 部分通过 → 标记待审查，降级学习
        5. 不通过 → 拒绝学习，记录告警
        """
        metadata = metadata or {}
        
        alignment = check_value_alignment(content, source, metadata)
        
        try:
            from core.learning_rhythm import get_rhythm_monitor
            rhythm_monitor = get_rhythm_monitor()
            rhythm_status = rhythm_monitor.get_status()
            rhythm_alerts = rhythm_status.alerts
            
            if rhythm_alerts:
                logger.warning(f"🎵 学习节奏预警: {rhythm_alerts}")
        except Exception as e:
            logger.debug(f"学习节奏监控失败（降级继续）: {e}")
            rhythm_alerts = []
        
        journal_entry = {
            "source": source,
            "content_preview": content[:200],
            "timestamp": datetime.now().isoformat(),
            "alignment_status": alignment.status.value,
            "alignment_score": alignment.score,
            "issues": alignment.issues,
            "accepted": False,
            "metadata": metadata
        }
        
        self._stats["total_attempts"] += 1
        
        if alignment.status == AlignmentStatus.PASS:
            logger.info(f"✅ 学习内容已通过价值对齐检查 (来源: {source}, 得分: {alignment.score:.2f})")
            journal_entry["accepted"] = True
            self._stats["accepted"] += 1
            self._save_journal_entry(journal_entry)
            
            try:
                from core.learning_rhythm import get_rhythm_monitor
                rhythm_monitor = get_rhythm_monitor()
                rhythm_monitor.record(
                    source=source,
                    quality_score=alignment.score,
                    alignment_status=alignment.status.value
                )
            except:
                pass
            
            return {
                "success": True,
                "message": "学习内容已正常吸收",
                "alignment": {
                    "status": alignment.status.value,
                    "score": alignment.score,
                    "issues": alignment.issues
                },
                "rhythm_alerts": rhythm_alerts
            }
        
        elif alignment.status == AlignmentStatus.PARTIAL:
            logger.warning(f"⚠️ 学习内容部分对齐，已标记待审查 (来源: {source})")
            journal_entry["accepted"] = False
            self._stats["pending_review"] += 1
            self._save_journal_entry(journal_entry)
            
            self._add_alert({
                "type": "partial_alignment",
                "source": source,
                "issues": alignment.issues,
                "severity": "medium"
            })
            
            return {
                "success": False,
                "message": "学习内容需要人工审查",
                "alignment": {
                    "status": alignment.status.value,
                    "score": alignment.score,
                    "issues": alignment.issues
                },
                "requires_review": True
            }
        
        elif alignment.status == AlignmentStatus.CONFLICT:
            logger.error(f"❌ 学习内容与核心价值冲突，已拒绝 (来源: {source})")
            journal_entry["accepted"] = False
            self._stats["rejected"] += 1
            self._save_journal_entry(journal_entry)
            
            self._add_alert({
                "type": "value_conflict",
                "source": source,
                "issues": alignment.issues,
                "severity": "high"
            })
            
            return {
                "success": False,
                "message": "学习内容已被拒绝（价值观冲突）",
                "alignment": {
                    "status": alignment.status.value,
                    "score": alignment.score,
                    "issues": alignment.issues
                },
                "rejected": True
            }
        
        else:
            logger.warning(f"❓ 无法判断对齐状态，已标记待审查 (来源: {source})")
            self._stats["pending_review"] += 1
            self._save_journal_entry(journal_entry)
            
            return {
                "success": False,
                "message": "无法判断对齐状态，需要人工审查",
                "alignment": {
                    "status": alignment.status.value,
                    "score": alignment.score,
                    "issues": alignment.issues
                },
                "requires_review": True
            }
    
    def _save_journal_entry(self, entry: Dict):
        """保存学习记录"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('''
                    INSERT INTO learning_journal
                    (timestamp, source, content_preview, alignment_status, 
                     alignment_score, issues, accepted, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entry["timestamp"],
                    entry["source"],
                    entry["content_preview"],
                    entry["alignment_status"],
                    entry["alignment_score"],
                    json.dumps(entry["issues"], ensure_ascii=False),
                    1 if entry["accepted"] else 0,
                    json.dumps(entry.get("metadata", {}), ensure_ascii=False)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"保存学习记录失败: {e}")
    
    def _add_alert(self, alert: Dict):
        """添加告警"""
        alert["timestamp"] = datetime.now().isoformat()
        self.alerts.append(alert)
        
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('''
                    INSERT INTO alerts
                    (timestamp, alert_type, source, severity, issues)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    alert["timestamp"],
                    alert["type"],
                    alert.get("source", ""),
                    alert.get("severity", "medium"),
                    json.dumps(alert.get("issues", []), ensure_ascii=False)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"保存告警失败: {e}")
    
    def get_learning_audit(self, limit: int = 100) -> Dict:
        """获取学习审计报告"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute('''
                    SELECT * FROM learning_journal
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                journal = [dict(row) for row in cursor.fetchall()]
                
                cursor = conn.execute('''
                    SELECT * FROM alerts
                    WHERE resolved = 0
                    ORDER BY timestamp DESC
                    LIMIT 20
                ''')
                
                alerts = [dict(row) for row in cursor.fetchall()]
                
                cursor = conn.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN accepted = 1 THEN 1 ELSE 0 END) as accepted,
                        SUM(CASE WHEN accepted = 0 THEN 1 ELSE 0 END) as rejected
                    FROM learning_journal
                ''')
                stats = dict(cursor.fetchone())
                
                return {
                    "stats": stats,
                    "alerts": alerts,
                    "learning_history": journal
                }
        except Exception as e:
            logger.error(f"获取审计报告失败: {e}")
            return {
                "stats": self._stats,
                "alerts": [],
                "learning_history": []
            }
    
    def get_pending_reviews(self) -> List[Dict]:
        """获取待审查的学习条目"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute('''
                    SELECT * FROM learning_journal
                    WHERE alignment_status IN ('partial', 'unknown')
                    AND accepted = 0
                    ORDER BY timestamp DESC
                ''')
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"获取待审查条目失败: {e}")
            return []
    
    def approve_learning(self, journal_id: int) -> bool:
        """批准待审查的学习条目"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('''
                    UPDATE learning_journal
                    SET accepted = 1, alignment_status = 'approved'
                    WHERE id = ?
                ''', (journal_id,))
                conn.commit()
                
                logger.info(f"✅ 已批准学习条目: {journal_id}")
                return True
        except Exception as e:
            logger.error(f"批准学习条目失败: {e}")
            return False
    
    def reject_learning(self, journal_id: int, reason: str = "") -> bool:
        """拒绝待审查的学习条目"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('''
                    UPDATE learning_journal
                    SET accepted = 0, alignment_status = 'rejected'
                    WHERE id = ?
                ''', (journal_id,))
                conn.commit()
                
                logger.info(f"❌ 已拒绝学习条目: {journal_id}")
                return True
        except Exception as e:
            logger.error(f"拒绝学习条目失败: {e}")
            return False
    
    def check_learning_health(self) -> Dict:
        """检查学习健康状态"""
        audit = self.get_learning_audit(limit=1000)
        stats = audit.get("stats", {})
        
        total = stats.get("total", 0)
        accepted = stats.get("accepted", 0)
        rejected = stats.get("rejected", 0)
        
        if total == 0:
            return {
                "status": "healthy",
                "message": "暂无学习记录"
            }
        
        rejection_rate = rejected / total
        
        if rejection_rate > 0.3:
            return {
                "status": "warning",
                "message": f"拒绝率过高: {rejection_rate:.1%}",
                "rejection_rate": rejection_rate,
                "recommendation": "检查知识源配置或调整价值对齐阈值"
            }
        
        if len(audit.get("alerts", [])) > 10:
            return {
                "status": "warning",
                "message": "告警数量过多",
                "alert_count": len(audit["alerts"]),
                "recommendation": "检查系统是否遭受投毒攻击"
            }
        
        return {
            "status": "healthy",
            "message": "学习系统运行正常",
            "acceptance_rate": accepted / total
        }


_safe_learning: Optional[SafeLearningLayer] = None


def get_safe_learning() -> SafeLearningLayer:
    global _safe_learning
    if _safe_learning is None:
        _safe_learning = SafeLearningLayer()
    return _safe_learning


def learn_safely(content: str, source: str, metadata: Dict = None) -> Dict:
    """安全学习的便捷函数"""
    return get_safe_learning().learn_safely(content, source, metadata)