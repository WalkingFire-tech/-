"""
记忆巩固器 (Sleep Consolidator) - T3睡眠层
每日凌晨自动运行，将高价值对话转化为知识

跨学科理论依据：
- 系统神经科学：睡眠记忆巩固（海马体→新皮层）
- 认知科学：经验回放（Experience Replay）
- 数据工程：ETL管道（Extract-Transform-Load）

设计原则：
1. 只巩固高价值样本（置信度<0.3或>0.8）
2. 向量化存储扩展知识库
3. 浓缩摘要存入经验池
4. 清理过期低价值数据
"""
import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class SleepConsolidator:
    """
    记忆巩固器 - 在"睡眠"中学习
    
    工作流程：
    1. 提取高价值样本（置信度极端值）
    2. 向量化存储（扩展知识库）
    3. 浓缩摘要（存入经验池）
    4. 标记已处理
    5. 清理过期数据
    """
    
    def __init__(
        self,
        reflection_db: str = "logs/campfire_log.db",
        experience_db: str = "data/experience_pool.db",
        knowledge_db: str = "data/knowledge_store.db",
        vector_db: Any = None,
        llm_adapter: Any = None
    ):
        self.reflection_db = reflection_db
        self.experience_db = experience_db
        self.knowledge_db = knowledge_db
        self.vector_db = vector_db
        self.llm = llm_adapter
        
        # 配置
        self.consolidation_window_days = 7
        self.high_value_threshold_high = 0.8
        self.high_value_threshold_low = 0.3
        self.min_answer_length = 20
        self.cleanup_days = 30
        
        logger.info("🌙 记忆巩固器已初始化")
    
    async def consolidate(self) -> Dict[str, Any]:
        """
        执行一次记忆巩固
        
        Returns:
            {
                "consolidated": int,
                "skipped": int,
                "errors": int,
                "details": list
            }
        """
        logger.info("🌙 记忆巩固器启动...")
        
        result = {
            "consolidated": 0,
            "skipped": 0,
            "errors": 0,
            "details": []
        }
        
        try:
            # 1. 获取高价值未巩固样本
            samples = self._fetch_high_value_samples()
            
            if not samples:
                logger.info("🌙 没有新的高价值样本需要巩固")
                return result
            
            logger.info(f"🌙 发现 {len(samples)} 条高价值样本")
            
            # 2. 处理每个样本
            for sample in samples:
                try:
                    detail = await self._process_sample(sample)
                    result["consolidated"] += 1
                    result["details"].append(detail)
                except Exception as e:
                    logger.error(f"巩固样本失败: {e}")
                    result["errors"] += 1
            
            # 3. 标记已巩固
            self._mark_consolidated(samples)
            
            # 4. 清理过期数据
            cleaned = self._cleanup_old_data()
            if cleaned > 0:
                logger.info(f"🌙 清理 {cleaned} 条过期数据")
            
            logger.info(f"🌙 记忆巩固完成: {result['consolidated']} 条")
            
        except Exception as e:
            logger.error(f"记忆巩固失败: {e}")
            result["errors"] += 1
        
        return result
    
    def _fetch_high_value_samples(self) -> List[Dict]:
        """
        获取高价值但未巩固的样本
        
        高价值定义：
        - 置信度 > 0.8（非常成功）
        - 置信度 < 0.3（失败案例，需要学习）
        """
        cutoff = datetime.utcnow() - timedelta(days=self.consolidation_window_days)
        
        conn = sqlite3.connect(self.reflection_db)
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.execute('''
                SELECT id, query, final_answer, confidence, plan, tool_calls, 
                       model_used, duration_ms, timestamp
                FROM reflection_log
                WHERE (confidence > ? OR confidence < ?)
                  AND (consolidated IS NULL OR consolidated = 0)
                  AND timestamp > ?
                  AND LENGTH(final_answer) > ?
                ORDER BY ABS(confidence - 0.5) DESC
                LIMIT 100
            ''', (
                self.high_value_threshold_high,
                self.high_value_threshold_low,
                cutoff.isoformat(),
                self.min_answer_length
            ))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        finally:
            conn.close()
    
    async def _process_sample(self, sample: Dict) -> Dict[str, Any]:
        """
        处理单条样本
        
        动作：
        1. 向量化存储（如果有vector_db）
        2. 经验池浓缩（生成摘要）
        """
        detail = {
            "id": sample["id"],
            "query": sample["query"][:50],
            "confidence": sample["confidence"],
            "actions": []
        }
        
        if self.vector_db:
            try:
                text = f"问题: {sample['query']}\n回答: {sample['final_answer']}"
                
                if hasattr(self.vector_db, 'add_knowledge'):
                    knowledge_id = self.vector_db.add_knowledge(
                        text=text,
                        metadata={"reflection_id": sample.get("id")},
                        category="reflection",
                        source="sleep_consolidator",
                        confidence=sample.get("confidence", 0.5)
                    )
                    detail["knowledge_id"] = knowledge_id
                elif hasattr(self.vector_db, 'add'):
                    self.vector_db.add(text=text, metadata=sample)
                
                detail["actions"].append("vectorized")
                logger.debug(f"样本 {sample['id']} 已向量化")
            except Exception as e:
                logger.warning(f"向量化失败: {e}")
        
        try:
            summary = self._generate_summary(sample)
            self._save_to_experience_pool(sample, summary)
            detail["actions"].append("experience_pool")
            logger.debug(f"样本 {sample['id']} 已存入经验池")
        except Exception as e:
            logger.warning(f"经验池存储失败: {e}")
        
        return detail
    
    def _generate_summary(self, sample: Dict) -> str:
        """
        生成摘要
        
        简单实现：截取前200字符
        后续可用LLM生成更精炼的摘要
        """
        answer = sample.get("final_answer", "")
        
        if self.llm and len(answer) > 500:
            # 使用LLM生成摘要
            try:
                prompt = f"请用一句话总结以下回答的核心要点：\n\n{answer}"
                summary = self.llm.generate(prompt)
                return summary[:200]
            except:
                pass
        
        # 降级：直接截取
        return answer[:200] + "..." if len(answer) > 200 else answer
    
    def _save_to_experience_pool(self, sample: Dict, summary: str):
        """存入经验池"""
        conn = sqlite3.connect(self.experience_db)
        
        try:
            # 解析plan获取intent
            plan = sample.get("plan", "{}")
            if isinstance(plan, str):
                plan = json.loads(plan)
            intent = plan.get("intent", "general")
            
            # 解析tool_calls
            tool_calls = sample.get("tool_calls", "[]")
            if isinstance(tool_calls, str):
                tool_calls = json.loads(tool_calls)
            tools_used = [tc.get("name", "") for tc in tool_calls if tc.get("status") == "success"]
            
            conn.execute('''
                INSERT INTO experiences 
                (timestamp, intent_type, raw_input, plan, model_name, 
                 quality_score, success, duration, user_feedback, response)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sample.get("timestamp", datetime.utcnow().isoformat()),
                intent,
                sample["query"][:500],
                sample.get("plan", "{}"),
                sample.get("model_used", "unknown"),
                int(sample.get("confidence", 0.5) * 100),
                1 if sample.get("confidence", 0) > 0.6 else 0,
                sample.get("duration_ms", 0) / 1000.0,
                None,
                summary
            ))
            
            conn.commit()
            
        finally:
            conn.close()
    
    def _mark_consolidated(self, samples: List[Dict]):
        """标记为已巩固"""
        if not samples:
            return
        
        ids = [s["id"] for s in samples]
        
        conn = sqlite3.connect(self.reflection_db)
        
        try:
            placeholders = ",".join(["?" for _ in ids])
            conn.execute(f'''
                UPDATE reflection_log
                SET consolidated = 1, consolidated_at = ?
                WHERE id IN ({placeholders})
            ''', [datetime.utcnow().isoformat()] + ids)
            
            conn.commit()
            
        finally:
            conn.close()
    
    def _cleanup_old_data(self) -> int:
        """
        清理过期低价值数据
        
        只保留统计计数，删除详细内容
        """
        cutoff = datetime.utcnow() - timedelta(days=self.cleanup_days)
        
        conn = sqlite3.connect(self.reflection_db)
        
        try:
            # 删除30天前的低价值数据
            cursor = conn.execute('''
                DELETE FROM reflection_log
                WHERE timestamp < ?
                  AND confidence >= ?
                  AND confidence <= ?
                  AND consolidated = 1
            ''', (
                cutoff.isoformat(),
                self.high_value_threshold_low,
                self.high_value_threshold_high
            ))
            
            deleted = cursor.rowcount
            conn.commit()
            return deleted
            
        finally:
            conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        conn = sqlite3.connect(self.reflection_db)
        
        try:
            total = conn.execute('SELECT COUNT(*) FROM reflection_log').fetchone()[0]
            consolidated = conn.execute(
                'SELECT COUNT(*) FROM reflection_log WHERE consolidated = 1'
            ).fetchone()[0]
            high_value = conn.execute('''
                SELECT COUNT(*) FROM reflection_log
                WHERE confidence > ? OR confidence < ?
            ''', (self.high_value_threshold_high, self.high_value_threshold_low)).fetchone()[0]
            
            return {
                "total_samples": total,
                "consolidated": consolidated,
                "high_value_pending": high_value - consolidated,
                "consolidation_rate": consolidated / total if total > 0 else 0
            }
            
        finally:
            conn.close()


# 全局实例
_consolidator = None

def get_sleep_consolidator(**kwargs) -> SleepConsolidator:
    """获取记忆巩固器实例（单例）"""
    global _consolidator
    if _consolidator is None:
        _consolidator = SleepConsolidator(**kwargs)
    return _consolidator