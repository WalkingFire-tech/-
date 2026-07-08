"""
行为进化层 - 优化回答的表达方式和语气

对应六层架构的 L1 感知层扩展
职责：分析不同风格/语气的接受度，优化表达方式
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from infrastructure.database_manager import DatabaseManager
import json
import hashlib
import os
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class ResponseProfile:
    """回答特征档案"""
    profile_id: str
    response_id: str
    conversation_id: str
    content: str
    length: int
    structure_type: str
    tone_type: str
    confidence: float
    user_feedback_score: float
    context_fit_score: float
    timestamp: str


class BehaviorEvolutionEngine:
    """
    行为进化引擎
    
    分析回答特征与用户接受度的关系，优化表达方式。
    """
    
    def __init__(self, db_path: str = "data/behavior_evolution.db"):
        self.db_path = db_path
        self._init_database()
        logger.info("🎭 行为进化引擎已初始化")
    
    def _init_database(self):
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = DatabaseManager.get(self.db_path)._get_conn()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS response_profiles (
                id TEXT PRIMARY KEY,
                response_id TEXT,
                conversation_id TEXT,
                content TEXT,
                length INTEGER,
                structure_type TEXT,
                tone_type TEXT,
                confidence REAL,
                user_feedback_score REAL,
                context_fit_score REAL,
                timestamp TEXT
            )
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_response_id ON response_profiles(response_id)
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_structure_type ON response_profiles(structure_type)
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_tone_type ON response_profiles(tone_type)
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS style_effectiveness (
                style_key TEXT PRIMARY KEY,
                avg_feedback_score REAL,
                sample_count INTEGER,
                last_updated TEXT
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tone_effectiveness (
                tone_key TEXT PRIMARY KEY,
                avg_feedback_score REAL,
                sample_count INTEGER,
                last_updated TEXT
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS context_style_mapping (
                context_type TEXT,
                style_type TEXT,
                effectiveness_score REAL,
                sample_count INTEGER,
                last_updated TEXT,
                PRIMARY KEY (context_type, style_type)
            )
        ''')
        
        conn.commit()
    
    def record_response(self, response_id: str, conversation_id: str,
                       content: str, confidence: float,
                       context_type: str = "general") -> str:
        """
        记录一次回答的特征
        
        Args:
            response_id: 回答ID
            conversation_id: 对话ID
            content: 回答内容
            confidence: 置信度
            context_type: 上下文类型
        
        Returns:
            profile_id: 特征档案ID
        """
        profile_id = hashlib.md5(
            f"{response_id}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        length = len(content)
        structure_type = self._detect_structure(content)
        tone_type = self._detect_tone(content)
        
        conn = DatabaseManager.get(self.db_path)._get_conn()
        conn.execute('''
            INSERT INTO response_profiles
            (id, response_id, conversation_id, content, length,
             structure_type, tone_type, confidence,
             user_feedback_score, context_fit_score, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            profile_id,
            response_id,
            conversation_id,
            content[:500],
            length,
            structure_type,
            tone_type,
            confidence,
            0.0,
            0.5,
            datetime.now().isoformat()
        ))
        
        conn.execute('''
            INSERT OR IGNORE INTO context_style_mapping
            (context_type, style_type, effectiveness_score, sample_count, last_updated)
            VALUES (?, ?, 0.5, 0, ?)
        ''', (context_type, structure_type, datetime.now().isoformat()))
        
        conn.commit()
        
        logger.debug(f"记录回答特征: {profile_id} (结构={structure_type}, 语气={tone_type})")
        return profile_id
    
    def update_with_feedback(self, response_id: str, feedback_score: float,
                            context_fit_score: Optional[float] = None,
                            context_type: str = "general"):
        """
        用用户反馈更新回答特征
        
        Args:
            response_id: 回答ID
            feedback_score: 用户反馈分数 (0-1)
            context_fit_score: 上下文匹配度 (可选)
            context_type: 上下文类型
        """
        conn = DatabaseManager.get(self.db_path)._get_conn()
        cursor = conn.execute(
            "SELECT structure_type FROM response_profiles WHERE response_id = ?",
            (response_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            logger.warning(f"未找到回答记录: {response_id}")
            return
        
        structure_type = row[0]
        
        if context_fit_score is not None:
            conn.execute('''
                UPDATE response_profiles
                SET user_feedback_score = ?,
                    context_fit_score = ?
                WHERE response_id = ?
            ''', (feedback_score, context_fit_score, response_id))
        else:
            conn.execute('''
                UPDATE response_profiles
                SET user_feedback_score = ?
                WHERE response_id = ?
            ''', (feedback_score, response_id))
        
        cursor = conn.execute('''
            SELECT effectiveness_score, sample_count
            FROM context_style_mapping
            WHERE context_type = ? AND style_type = ?
        ''', (context_type, structure_type))
        
        mapping_row = cursor.fetchone()
        
        if mapping_row:
            old_score = mapping_row[0]
            old_count = mapping_row[1]
            new_count = old_count + 1
            new_score = (old_score * old_count + feedback_score) / new_count
            
            conn.execute('''
                UPDATE context_style_mapping
                SET effectiveness_score = ?, sample_count = ?, last_updated = ?
                WHERE context_type = ? AND style_type = ?
            ''', (new_score, new_count, datetime.now().isoformat(), context_type, structure_type))
        
        conn.commit()
        
        self._update_style_stats()
        self._update_tone_stats()
        
        logger.debug(f"更新反馈: {response_id} -> {feedback_score:.2f}")
    
    def _update_style_stats(self):
        """更新风格有效性统计"""
        conn = DatabaseManager.get(self.db_path)._get_conn()
        cursor = conn.execute('''
            SELECT structure_type, 
                   AVG(user_feedback_score) as avg_score,
                   COUNT(*) as count
            FROM response_profiles
            WHERE user_feedback_score > 0
            GROUP BY structure_type
        ''')
        
        for row in cursor.fetchall():
            style_key = row[0]
            avg_score = row[1] if row[1] is not None else 0.0
            count = row[2]
            
            conn.execute('''
                INSERT OR REPLACE INTO style_effectiveness
                (style_key, avg_feedback_score, sample_count, last_updated)
                VALUES (?, ?, ?, ?)
            ''', (style_key, avg_score, count, datetime.now().isoformat()))
        conn.commit()
    
    def _update_tone_stats(self):
        """更新语气有效性统计"""
        conn = DatabaseManager.get(self.db_path)._get_conn()
        cursor = conn.execute('''
            SELECT tone_type, 
                   AVG(user_feedback_score) as avg_score,
                   COUNT(*) as count
            FROM response_profiles
            WHERE user_feedback_score > 0
            GROUP BY tone_type
        ''')
        
        for row in cursor.fetchall():
            tone_key = row[0]
            avg_score = row[1] if row[1] is not None else 0.0
            count = row[2]
            
            conn.execute('''
                INSERT OR REPLACE INTO tone_effectiveness
                (tone_key, avg_feedback_score, sample_count, last_updated)
                VALUES (?, ?, ?, ?)
            ''', (tone_key, avg_score, count, datetime.now().isoformat()))
        conn.commit()
    
    def get_recommended_style(self, context_type: str = "general") -> Dict[str, str]:
        """
        获取推荐的回答风格和语气
        
        Args:
            context_type: 上下文类型 (general | technical | emotional)
        
        Returns:
            推荐的风格和语气
        """
        conn = DatabaseManager.get(self.db_path)._get_conn()
        
        cursor = conn.execute('''
            SELECT style_type, effectiveness_score
            FROM context_style_mapping
            WHERE context_type = ?
            ORDER BY effectiveness_score DESC, sample_count DESC
            LIMIT 1
        ''', (context_type,))
        
        context_style_row = cursor.fetchone()
        
        cursor = conn.execute('''
            SELECT style_key FROM style_effectiveness
            ORDER BY avg_feedback_score DESC, sample_count DESC
            LIMIT 1
        ''')
        style_row = cursor.fetchone()
        
        cursor = conn.execute('''
            SELECT tone_key FROM tone_effectiveness
            ORDER BY avg_feedback_score DESC, sample_count DESC
            LIMIT 1
        ''')
        tone_row = cursor.fetchone()
        
        if context_type == "emotional":
            return {
                "structure_type": context_style_row["style_type"] if context_style_row else "mixed",
                "tone_type": "empathic",
                "confidence": context_style_row["effectiveness_score"] if context_style_row else 0.5
            }
        
        if context_type == "technical":
            return {
                "structure_type": context_style_row["style_type"] if context_style_row else "structured",
                "tone_type": "formal",
                "confidence": context_style_row["effectiveness_score"] if context_style_row else 0.5
            }
        
        return {
            "structure_type": context_style_row["style_type"] if context_style_row else (style_row["style_key"] if style_row else "mixed"),
            "tone_type": tone_row["tone_key"] if tone_row else "conversational",
            "confidence": context_style_row["effectiveness_score"] if context_style_row else 0.5
        }
    
    def _detect_structure(self, content: str) -> str:
        """检测回答的结构类型"""
        if len(content) < 50:
            return "short"
        
        line_count = content.count("\n") + 1
        
        if line_count > 5:
            if any(marker in content for marker in ["1.", "2.", "首先", "其次", "第一", "第二"]):
                return "bulleted"
            if any(marker in content for marker in ["```", "def ", "class ", "import "]):
                return "code"
            return "structured"
        
        if any(marker in content for marker in ["：\n", ":\n", "。\n\n"]):
            return "mixed"
        
        if len(content) > 200:
            return "paragraph"
        
        return "mixed"
    
    def _detect_tone(self, content: str) -> str:
        """检测回答的语气类型"""
        empathic_words = ["理解", "感受", "体会", "辛苦", "不容易", "抱歉", "遗憾", "希望"]
        formal_words = ["根据", "研究表明", "理论上", "综上所述", "因此", "由此可见", "基于"]
        direct_words = ["应该", "必须", "需要", "建议", "推荐", "可以", "请"]
        conversational_words = ["我觉得", "我认为", "感觉", "其实", "说实话"]
        
        content_lower = content.lower()
        
        empathic_count = sum(1 for w in empathic_words if w in content_lower)
        formal_count = sum(1 for w in formal_words if w in content_lower)
        direct_count = sum(1 for w in direct_words if w in content_lower)
        conversational_count = sum(1 for w in conversational_words if w in content_lower)
        
        counts = {
            "empathic": empathic_count,
            "formal": formal_count,
            "direct": direct_count,
            "conversational": conversational_count
        }
        
        max_type = max(counts, key=counts.get)
        max_count = counts[max_type]
        
        if max_count == 0:
            if len(content) < 100:
                return "direct"
            return "conversational"
        
        if max_type == "empathic" and empathic_count > formal_count:
            return "empathic"
        
        if max_type == "formal" and formal_count > direct_count:
            return "formal"
        
        if max_type == "direct":
            return "direct"
        
        return "conversational"
    
    def analyze_style_effectiveness(self) -> Dict[str, Any]:
        """分析各风格的有效性"""
        conn = DatabaseManager.get(self.db_path)._get_conn()
        
        cursor = conn.execute('''
            SELECT structure_type,
                   COUNT(*) as total,
                   AVG(user_feedback_score) as avg_feedback,
                   AVG(confidence) as avg_confidence,
                   AVG(length) as avg_length
            FROM response_profiles
            WHERE user_feedback_score > 0
            GROUP BY structure_type
            ORDER BY avg_feedback DESC
        ''')
        
        style_analysis = []
        for row in cursor.fetchall():
            style_analysis.append({
                "structure_type": row["structure_type"],
                "total_samples": row["total"],
                "avg_feedback": row["avg_feedback"] if row["avg_feedback"] else 0.0,
                "avg_confidence": row["avg_confidence"] if row["avg_confidence"] else 0.0,
                "avg_length": int(row["avg_length"]) if row["avg_length"] else 0
            })
        
        return {
            "style_analysis": style_analysis,
            "timestamp": datetime.now().isoformat()
        }
    
    def analyze_tone_effectiveness(self) -> Dict[str, Any]:
        """分析各语气的有效性"""
        conn = DatabaseManager.get(self.db_path)._get_conn()
        
        cursor = conn.execute('''
            SELECT tone_type,
                   COUNT(*) as total,
                   AVG(user_feedback_score) as avg_feedback,
                   AVG(confidence) as avg_confidence
            FROM response_profiles
            WHERE user_feedback_score > 0
            GROUP BY tone_type
            ORDER BY avg_feedback DESC
        ''')
        
        tone_analysis = []
        for row in cursor.fetchall():
            tone_analysis.append({
                "tone_type": row["tone_type"],
                "total_samples": row["total"],
                "avg_feedback": row["avg_feedback"] if row["avg_feedback"] else 0.0,
                "avg_confidence": row["avg_confidence"] if row["avg_confidence"] else 0.0
            })
        
        return {
            "tone_analysis": tone_analysis,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        conn = DatabaseManager.get(self.db_path)._get_conn()
        
        cursor = conn.execute("SELECT COUNT(*) as total FROM response_profiles")
        total = cursor.fetchone()['total']
        
        cursor = conn.execute('''
            SELECT COUNT(*) as with_feedback
            FROM response_profiles
            WHERE user_feedback_score > 0
        ''')
        with_feedback = cursor.fetchone()['with_feedback']
        
        cursor = conn.execute('''
            SELECT * FROM style_effectiveness
            ORDER BY avg_feedback_score DESC
        ''')
        styles = [dict(row) for row in cursor.fetchall()]
        
        cursor = conn.execute('''
            SELECT * FROM tone_effectiveness
            ORDER BY avg_feedback_score DESC
        ''')
        tones = [dict(row) for row in cursor.fetchall()]
        
        cursor = conn.execute('''
            SELECT context_type, style_type, effectiveness_score, sample_count
            FROM context_style_mapping
            WHERE sample_count > 0
            ORDER BY context_type, effectiveness_score DESC
        ''')
        context_mappings = [dict(row) for row in cursor.fetchall()]
        
        return {
            "total_profiles": total,
            "profiles_with_feedback": with_feedback,
            "style_effectiveness": styles,
            "tone_effectiveness": tones,
            "context_style_mapping": context_mappings
        }
    
    def get_evolution_report(self) -> Dict:
        """获取进化报告"""
        stats = self.get_statistics()
        style_analysis = self.analyze_style_effectiveness()
        tone_analysis = self.analyze_tone_effectiveness()
        
        recommendations = []
        
        if stats["style_effectiveness"]:
            best_style = stats["style_effectiveness"][0]
            worst_style = stats["style_effectiveness"][-1] if len(stats["style_effectiveness"]) > 1 else None
            
            if best_style["avg_feedback_score"] > 0.7:
                recommendations.append({
                    "type": "style_optimization",
                    "message": f"推荐使用 {best_style['style_key']} 风格（平均反馈: {best_style['avg_feedback_score']:.2f}）",
                    "priority": "high"
                })
            
            if worst_style and worst_style["avg_feedback_score"] < 0.5:
                recommendations.append({
                    "type": "style_warning",
                    "message": f"{worst_style['style_key']} 风格效果不佳（平均反馈: {worst_style['avg_feedback_score']:.2f}）",
                    "priority": "medium"
                })
        
        return {
            "statistics": stats,
            "style_analysis": style_analysis,
            "tone_analysis": tone_analysis,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }


_behavior_engine: Optional[BehaviorEvolutionEngine] = None


def get_behavior_evolution_engine() -> BehaviorEvolutionEngine:
    """获取行为进化引擎单例"""
    global _behavior_engine
    if _behavior_engine is None:
        _behavior_engine = BehaviorEvolutionEngine()
    return _behavior_engine
