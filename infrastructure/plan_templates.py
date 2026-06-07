"""
计划模板库 - 存储和重用成功的执行计划
"""
import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from infrastructure.config_manager import config


class PlanTemplate:
    """计划模板"""
    
    def __init__(self, template_id: str, intent_type: str, steps: List[Dict],
                 success_rate: float, avg_quality: float, use_count: int):
        self.template_id = template_id
        self.intent_type = intent_type
        self.steps = steps
        self.success_rate = success_rate
        self.avg_quality = avg_quality
        self.use_count = use_count


class PlanTemplateLibrary:
    """计划模板库"""
    
    def __init__(self):
        self.db_path = Path("plan_templates.db")
        self._init_db()
        self.min_success_rate = config.get("plan_template.min_success_rate", 0.7)
        self.min_quality = config.get("plan_template.min_quality", 70)
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS plan_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_id TEXT UNIQUE,
                    intent_type TEXT,
                    steps TEXT,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    total_quality INTEGER DEFAULT 0,
                    use_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    last_used_at TEXT,
                    tags TEXT
                )
            ''')
            
            conn.execute('CREATE INDEX IF NOT EXISTS idx_intent ON plan_templates(intent_type)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_success ON plan_templates(success_count)')
    
    def save_template(self, intent_type: str, steps: List[Dict], 
                     quality: int, success: bool, tags: List[str] = None):
        """保存计划模板"""
        # 查找是否已有相似模板
        existing = self._find_similar_template(intent_type, steps)
        
        if existing:
            # 更新现有模板
            self._update_template(existing["template_id"], quality, success)
            logger.debug(f"更新现有模板: {existing['template_id']}")
            return existing["template_id"]
        
        # 创建新模板
        template_id = f"tpl_{intent_type}_{int(datetime.now().timestamp())}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO plan_templates 
                (template_id, intent_type, steps, success_count, failure_count,
                 total_quality, use_count, created_at, last_used_at, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                template_id,
                intent_type,
                json.dumps(steps, ensure_ascii=False),
                1 if success else 0,
                0 if success else 1,
                quality,
                1,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                json.dumps(tags or [], ensure_ascii=False)
            ))
        
        logger.info(f"保存新模板: {template_id}")
        return template_id
    
    def _find_similar_template(self, intent_type: str, steps: List[Dict]) -> Optional[Dict]:
        """查找相似模板"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute('''
                SELECT * FROM plan_templates
                WHERE intent_type = ?
                ORDER BY success_count DESC, total_quality DESC
                LIMIT 5
            ''', (intent_type,))
            
            candidates = [dict(row) for row in cur.fetchall()]
            
            # 简化相似度判断:步骤数量相同
            for candidate in candidates:
                candidate_steps = json.loads(candidate["steps"])
                if len(candidate_steps) == len(steps):
                    return candidate
        
        return None
    
    def _update_template(self, template_id: str, quality: int, success: bool):
        """更新模板统计"""
        with sqlite3.connect(self.db_path) as conn:
            if success:
                conn.execute('''
                    UPDATE plan_templates
                    SET success_count = success_count + 1,
                        total_quality = total_quality + ?,
                        use_count = use_count + 1,
                        last_used_at = ?
                    WHERE template_id = ?
                ''', (quality, datetime.now().isoformat(), template_id))
            else:
                conn.execute('''
                    UPDATE plan_templates
                    SET failure_count = failure_count + 1,
                        use_count = use_count + 1,
                        last_used_at = ?
                    WHERE template_id = ?
                ''', (datetime.now().isoformat(), template_id))
    
    def retrieve_template(self, intent_type: str) -> Optional[PlanTemplate]:
        """检索最佳模板"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute('''
                SELECT *
                FROM plan_templates
                WHERE intent_type = ?
                  AND success_count > failure_count
                ORDER BY 
                    (success_count * 1.0 / (success_count + failure_count)) DESC,
                    total_quality DESC,
                    use_count DESC
                LIMIT 1
            ''', (intent_type,))
            
            row = cur.fetchone()
            
            if not row:
                return None
            
            # 计算成功率
            total = row["success_count"] + row["failure_count"]
            success_rate = row["success_count"] / total if total > 0 else 0
            avg_quality = row["total_quality"] / row["use_count"] if row["use_count"] > 0 else 0
            
            return PlanTemplate(
                template_id=row["template_id"],
                intent_type=row["intent_type"],
                steps=json.loads(row["steps"]),
                success_rate=success_rate,
                avg_quality=avg_quality,
                use_count=row["use_count"]
            )
    
    def get_templates_for_intent(self, intent_type: str, limit: int = 5) -> List[PlanTemplate]:
        """获取意图类型的所有模板"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute('''
                SELECT *
                FROM plan_templates
                WHERE intent_type = ?
                ORDER BY success_count DESC, total_quality DESC
                LIMIT ?
            ''', (intent_type, limit))
            
            templates = []
            for row in cur.fetchall():
                total = row["success_count"] + row["failure_count"]
                success_rate = row["success_count"] / total if total > 0 else 0
                avg_quality = row["total_quality"] / row["use_count"] if row["use_count"] > 0 else 0
                
                templates.append(PlanTemplate(
                    template_id=row["template_id"],
                    intent_type=row["intent_type"],
                    steps=json.loads(row["steps"]),
                    success_rate=success_rate,
                    avg_quality=avg_quality,
                    use_count=row["use_count"]
                ))
            
            return templates
    
    def cleanup_low_quality_templates(self, min_uses: int = 5):
        """清理低质量模板"""
        with sqlite3.connect(self.db_path) as conn:
            # 删除成功率低且使用次数足够的模板
            conn.execute('''
                DELETE FROM plan_templates
                WHERE use_count >= ?
                  AND (success_count * 1.0 / (success_count + failure_count)) < 0.3
            ''', (min_uses,))
            
            deleted = conn.total_changes
            
            # 删除长期未使用的模板
            cutoff = (datetime.now() - timedelta(days=30)).isoformat()
            conn.execute('''
                DELETE FROM plan_templates
                WHERE last_used_at < ?
                  AND use_count < 3
            ''', (cutoff,))
            
            deleted += conn.total_changes
        
        logger.info(f"清理了{deleted}个低质量模板")
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            # 总模板数
            cur = conn.execute('SELECT COUNT(*) FROM plan_templates')
            total = cur.fetchone()[0]
            
            # 按意图类型统计
            cur = conn.execute('''
                SELECT intent_type, COUNT(*) as count
                FROM plan_templates
                GROUP BY intent_type
            ''')
            by_type = {row[0]: row[1] for row in cur.fetchall()}
            
            # 平均成功率
            cur = conn.execute('''
                SELECT AVG(success_count * 1.0 / (success_count + failure_count))
                FROM plan_templates
                WHERE success_count + failure_count > 0
            ''')
            avg_success_rate = cur.fetchone()[0] or 0
            
            # 总使用次数
            cur = conn.execute('SELECT SUM(use_count) FROM plan_templates')
            total_uses = cur.fetchone()[0] or 0
        
        return {
            "total_templates": total,
            "by_intent_type": by_type,
            "avg_success_rate": avg_success_rate,
            "total_uses": total_uses
        }