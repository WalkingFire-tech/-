"""
反事实模拟器 (Counterfactual Simulator)
让系统能对比"如果选择其他模型会怎样"，驱动路由优化
"""
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from loguru import logger
from pathlib import Path
from collections import defaultdict
from infrastructure.database_manager import DatabaseManager

ALLOWED_TASK_TYPES = {
    'code', 'question', 'chat', 'memory', 'calculation',
    'feedback', 'meta', 'document', 'analysis', 'comparison'
}
MAX_INSIGHTS_PER_TYPE = 100


class CounterfactualSimulator:
    """反事实模拟器 - 探索如果选择其他模型会怎样"""
    
    def __init__(self):
        self.db_path = Path("data/counterfactual_history.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
        self.simulation_queue = []
        self.max_concurrent_simulations = 2
        self.simulation_enabled = True
        
        self.insights = defaultdict(list)
        self._insights_lock = threading.Lock()
        
        logger.info("反事实模拟器已初始化")
    
    def _init_db(self):
        """初始化反事实历史数据库"""
        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS counterfactual_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                task_id TEXT,
                actual_model TEXT,
                actual_score REAL,
                counterfactual_model TEXT,
                counterfactual_score REAL,
                gap REAL,
                insight TEXT,
                applied BOOLEAN
            );
            CREATE INDEX IF NOT EXISTS idx_task ON counterfactual_records(task_id)
        ''')
    
    async def simulate_alternatives(
        self,
        task_id: str,
        actual_model: str,
        actual_score: float,
        task_input: str,
        task_type: str,
        adapters: Dict
    ) -> List[Dict]:
        """模拟替代模型的表现（优化版：超时控制+并行执行）"""
        if not self.simulation_enabled:
            return []
        
        if task_type not in ALLOWED_TASK_TYPES:
            logger.warning(f"非法任务类型: {task_type}")
            return []
        
        if actual_model not in adapters:
            logger.warning(f"模型不存在: {actual_model}")
            return []
        
        results = []
        
        alternative_models = self._select_alternative_models(
            actual_model, task_type, adapters
        )
        
        alternative_models = alternative_models[:2]
        
        async def simulate_one(alt_model):
            try:
                logger.info(f"反事实模拟: {alt_model} 处理任务 {task_id}")
                
                adapter = adapters.get(alt_model)
                if not adapter:
                    return None
                
                sim_score = await asyncio.wait_for(
                    self._simulate_with_model(adapter, task_input, task_type),
                    timeout=15.0
                )
                
                gap = sim_score - actual_score
                
                result = {
                    "task_id": task_id,
                    "actual_model": actual_model,
                    "actual_score": actual_score,
                    "counterfactual_model": alt_model,
                    "counterfactual_score": sim_score,
                    "gap": gap,
                    "timestamp": datetime.now().isoformat()
                }
                
                self._save_counterfactual(result)
                
                if gap > 10:
                    insight = self._generate_insight(result, task_type)
                    with self._insights_lock:
                        if len(self.insights[task_type]) < MAX_INSIGHTS_PER_TYPE:
                            self.insights[task_type].append(insight)
                        else:
                            self.insights[task_type].pop(0)
                            self.insights[task_type].append(insight)
                    logger.warning(f"发现改进机会: {alt_model} 比 {actual_model} 高 {gap:.2f} 分")
                
                return result
                
            except asyncio.TimeoutError:
                logger.warning(f"反事实模拟超时 ({alt_model})")
                return None
            except Exception as e:
                logger.warning(f"反事实模拟失败 ({alt_model}): {e}")
                return None
        
        tasks = [simulate_one(model) for model in alternative_models]
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in completed:
            if isinstance(result, dict):
                results.append(result)
        
        return results
    
    def _select_alternative_models(
        self,
        actual_model: str,
        task_type: str,
        adapters: Dict
    ) -> List[str]:
        """选择替代模型进行模拟"""
        alternatives = []
        
        for model_name in adapters.keys():
            if model_name != actual_model:
                alternatives.append(model_name)
        
        alternatives = alternatives[:3]
        
        return alternatives
    
    async def _simulate_with_model(
        self,
        adapter,
        task_input: str,
        task_type: str
    ) -> float:
        """使用指定模型模拟任务"""
        try:
            start_time = datetime.now()
            
            if asyncio.iscoroutinefunction(adapter.generate):
                response = await adapter.generate(task_input)
            else:
                response = await asyncio.to_thread(adapter.generate, task_input)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            score = self._evaluate_simulation(response, duration, task_type)
            
            return score
            
        except Exception as e:
            logger.warning(f"模拟执行失败: {e}")
            return 0.0
    
    def _evaluate_simulation(
        self,
        response: str,
        duration: float,
        task_type: str
    ) -> float:
        """评估模拟结果"""
        score = 50.0
        
        if response and len(response) > 10:
            score += 20
        
        if len(response) > 100:
            score += 10
        
        if duration < 2.0:
            score += 15
        elif duration < 5.0:
            score += 10
        elif duration < 10.0:
            score += 5
        
        if task_type == "code":
            if "def " in response or "class " in response:
                score += 10
        elif task_type == "question":
            if "。" in response or "？" in response:
                score += 10
        
        return min(100, score)
    
    def _generate_insight(self, result: Dict, task_type: str) -> Dict:
        """生成洞察"""
        insight = {
            "type": "model_preference",
            "task_type": task_type,
            "recommendation": f"对于{task_type}任务，优先使用 {result['counterfactual_model']}",
            "evidence": f"相比 {result['actual_model']}，得分提升 {result['gap']:.2f}",
            "confidence": min(1.0, result['gap'] / 20),
            "timestamp": result['timestamp']
        }
        
        return insight
    
    def _save_counterfactual(self, result: Dict):
        """保存反事实记录"""
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute('''
                INSERT INTO counterfactual_records
                (timestamp, task_id, actual_model, actual_score,
                 counterfactual_model, counterfactual_score, gap, insight, applied)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result['timestamp'],
                result['task_id'],
                result['actual_model'],
                result['actual_score'],
                result['counterfactual_model'],
                result['counterfactual_score'],
                result['gap'],
                '',
                False
            ), commit=True)
        except Exception as e:
            logger.warning(f"反事实记录保存失败: {e}")
    
    def get_top_insights(self, task_type: str = None, limit: int = 10) -> List[Dict]:
        """获取顶级洞察"""
        if task_type:
            return self.insights.get(task_type, [])[:limit]
        
        all_insights = []
        for insights_list in self.insights.values():
            all_insights.extend(insights_list)
        
        all_insights.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        return all_insights[:limit]
    
    def apply_insights(self) -> int:
        """应用洞察优化系统"""
        applied_count = 0
        
        try:
            from infrastructure.model_capability import model_capability
            
            with self._insights_lock:
                insights_copy = {
                    task_type: insights[:]
                    for task_type, insights in self.insights.items()
                }
            
            for task_type, insights in insights_copy.items():
                if task_type not in ALLOWED_TASK_TYPES:
                    continue
                
                for insight in insights[:3]:
                    if insight.get('confidence', 0) < 0.5:
                        continue
                    
                    recommended_model = insight['recommendation'].split()[-1]
                    
                    try:
                        current_score = model_capability.score_model_for_task(
                            recommended_model, task_type
                        )
                        model_capability.update_capability(
                            model_name=recommended_model,
                            task_type=task_type,
                            score=min(1.0, current_score * 1.1),
                            source='counterfactual_insight'
                        )
                        applied_count += 1
                        logger.info(f"应用洞察: {insight['recommendation']}")
                        
                        self._generate_learning_rule_from_insight(
                            insight, task_type, recommended_model
                        )
                        
                    except Exception as e:
                        logger.warning(f"洞察应用失败: {e}")
            
            if applied_count > 0:
                self._mark_insights_applied()
                self._activate_high_confidence_rules()
            
        except Exception as e:
            logger.error(f"洞察应用失败: {e}")
        
        return applied_count
    
    def _generate_learning_rule_from_insight(self, insight: Dict, task_type: str, recommended_model: str):
        """从洞察生成学习规则"""
        try:
            from datetime import datetime
            
            if task_type not in ALLOWED_TASK_TYPES:
                logger.warning(f"非法任务类型: {task_type}")
                return
            
            actual_model = insight.get('evidence', '').split()[1] if '比' in insight.get('evidence', '') else None
            if not actual_model:
                return
            
            condition = f"intent_type == '{task_type}'"
            action = f"prefer_model:{recommended_model}"
            
            gap = insight.get('confidence', 0) * 20
            confidence = min(0.95, 0.6 + gap / 50)
            
            db = DatabaseManager.get("data/learning_rules.db")
            db.execute('''
                INSERT INTO learning_rules
                (condition, action, confidence, status, source, priority, created_at)
                VALUES (?, ?, ?, 'active', 'counterfactual_auto', 8, ?)
            ''', (condition, action, confidence, datetime.now().isoformat()), commit=True)
            
            logger.info(f"自动生成规则: {condition} → {action} (置信度: {confidence:.2f})")
            
        except Exception as e:
            logger.warning(f"生成学习规则失败: {e}")
    
    def _activate_high_confidence_rules(self):
        """激活高置信度规则"""
        try:
            db = DatabaseManager.get("data/learning_rules.db")
            cursor = db.execute('''
                UPDATE learning_rules
                SET status = 'active'
                WHERE status = 'pending' AND confidence >= 0.7
            ''', commit=True)
            activated = cursor.rowcount
            
            if activated > 0:
                logger.info(f"自动激活 {activated} 条高置信度规则")
                    
        except Exception as e:
            logger.warning(f"激活规则失败: {e}")
    
    def _mark_insights_applied(self):
        """标记洞察已应用"""
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute('''
                UPDATE counterfactual_records
                SET applied = TRUE
                WHERE applied = FALSE AND gap > 10
            ''', commit=True)
        except Exception as e:
            logger.warning(f"标记失败: {e}")
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        try:
            db = DatabaseManager.get(self.db_path)
            total_simulations = db.query_one('SELECT COUNT(*) FROM counterfactual_records')[0]
            
            applied_insights = db.query_one('SELECT COUNT(*) FROM counterfactual_records WHERE applied = TRUE')[0]
            
            avg_row = db.query_one('SELECT AVG(gap) FROM counterfactual_records WHERE gap > 0')
            avg_improvement = avg_row[0] if avg_row else 0
            
            return {
                "total_simulations": total_simulations,
                "applied_insights": applied_insights,
                "avg_improvement": round(avg_improvement, 2),
                "pending_insights": len(self.get_top_insights(limit=100))
            }
        except Exception as e:
            logger.warning(f"统计获取失败: {e}")
            return {}


counterfactual_simulator = CounterfactualSimulator()
