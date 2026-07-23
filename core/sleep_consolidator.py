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
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from core.ports.adapters import get_storage_port

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
        
        db = get_storage_port(self.reflection_db)
        
        rows = db.query('''
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
        
        return [dict(r) for r in rows]
    
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
            except Exception:
                logger.warning("操作降级跳过")
        
        # 降级：直接截取
        return answer[:200] + "..." if len(answer) > 200 else answer
    
    def _save_to_experience_pool(self, sample: Dict, summary: str):
        """存入经验池 — 通过ExperiencePool触发因果图学习"""
        try:
            from infrastructure.experience_pool import get_experience_pool
            ep = get_experience_pool()

            plan = sample.get("plan", "{}")
            if isinstance(plan, str):
                plan = json.loads(plan)
            intent = plan.get("intent", "general")

            ep.add_experience(
                intent_type=intent,
                raw_input=sample.get("query", "")[:500],
                plan=sample.get("plan", "{}"),
                model_name=sample.get("model_used", "unknown"),
                quality_score=int(sample.get("confidence", 0.5) * 100),
                success=sample.get("confidence", 0) > 0.6,
                duration=sample.get("duration_ms", 0) / 1000.0,
                user_feedback=0,
                response=summary
            )
        except Exception as e:
            logger.warning(f"睡眠巩固经验存储失败: {e}")
    
    def _mark_consolidated(self, samples: List[Dict]):
        """标记为已巩固"""
        if not samples:
            return
        
        ids = [s["id"] for s in samples]
        
        db = get_storage_port(self.reflection_db)
        
        placeholders = ",".join(["?" for _ in ids])
        db.execute(f'''
            UPDATE reflection_log
            SET consolidated = 1, consolidated_at = ?
            WHERE id IN ({placeholders})
        ''', [datetime.utcnow().isoformat()] + ids, commit=True)
    
    def _cleanup_old_data(self) -> int:
        """
        清理过期低价值数据
        
        只保留统计计数，删除详细内容
        """
        cutoff = datetime.utcnow() - timedelta(days=self.cleanup_days)
        
        db = get_storage_port(self.reflection_db)
        
        cursor = db.execute('''
            DELETE FROM reflection_log
            WHERE timestamp < ?
              AND confidence >= ?
              AND confidence <= ?
              AND consolidated = 1
        ''', (
            cutoff.isoformat(),
            self.high_value_threshold_low,
            self.high_value_threshold_high
        ), commit=True)
        
        deleted = cursor.rowcount
        return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        db = get_storage_port(self.reflection_db)
        
        total_row = db.query_one('SELECT COUNT(*) as cnt FROM reflection_log')
        total = total_row['cnt'] if total_row else 0
        cons_row = db.query_one('SELECT COUNT(*) as cnt FROM reflection_log WHERE consolidated = 1')
        consolidated = cons_row['cnt'] if cons_row else 0
        hv_row = db.query_one('''
            SELECT COUNT(*) as cnt FROM reflection_log
            WHERE confidence > ? OR confidence < ?
        ''', (self.high_value_threshold_high, self.high_value_threshold_low))
        high_value = hv_row['cnt'] if hv_row else 0
        
        return {
            "total_samples": total,
            "consolidated": consolidated,
            "high_value_pending": high_value - consolidated,
            "consolidation_rate": consolidated / total if total > 0 else 0
        }


# 全局实例
_consolidator = None

def get_sleep_consolidator(**kwargs) -> SleepConsolidator:
    """获取记忆巩固器实例（单例）"""
    global _consolidator
    if _consolidator is None:
        _consolidator = SleepConsolidator(**kwargs)
    return _consolidator