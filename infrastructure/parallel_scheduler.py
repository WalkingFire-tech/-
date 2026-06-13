"""
并行调度器 - 多模型并发调用
实现联邦调度核心能力
"""
import asyncio
import time
from typing import List, Dict, Optional, Callable, Any, Tuple
from loguru import logger
from datetime import datetime
import sqlite3
from pathlib import Path


class ParallelScheduler:
    """并行调度器"""
    
    def __init__(self, db_path: str = "data/scheduler_stats.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(exist_ok=True)
        self._init_db()
        
        self.max_concurrent = 3
        self.timeout_seconds = 30  # 降低超时时间，避免长时间阻塞
        self.retry_count = 2
        
        # 模型性能阈值（秒）
        self.performance_thresholds = {
            'fast': 5.0,      # 快速模型阈值
            'normal': 15.0,   # 正常模型阈值
            'slow': 30.0      # 慢速模型阈值
        }
        
        # 模型黑名单（失败后暂时禁用）
        self.model_blacklist = {}  # {model_name: until_timestamp}
        
        # 模型性能记录（用于动态调整）
        self.model_performance = {}  # {model_name: avg_duration}
        
        logger.info("并行调度器已初始化（超时30秒，性能监控启用）")
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS parallel_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    model_name TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    duration REAL,
                    success BOOLEAN,
                    result_preview TEXT,
                    error_message TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS task_results (
                    task_id TEXT PRIMARY KEY,
                    task_type TEXT,
                    models_used TEXT,
                    best_model TEXT,
                    fusion_strategy TEXT,
                    quality_score REAL,
                    created_at TEXT
                )
            ''')
            conn.commit()
    
    def _is_blacklisted(self, model_name: str) -> bool:
        """检查模型是否在黑名单中"""
        if model_name in self.model_blacklist:
            if time.time() < self.model_blacklist[model_name]:
                return True
            else:
                # 黑名单过期，移除
                del self.model_blacklist[model_name]
        return False
    
    def _mark_failed(self, model_name: str, duration: int = 300):
        """将失败模型加入黑名单
        
        Args:
            model_name: 模型名称
            duration: 禁用时长（秒），默认5分钟
        """
        self.model_blacklist[model_name] = time.time() + duration
        logger.warning(f"模型 {model_name} 已加入黑名单（{duration}秒）")
    
    def _get_available_models(self, models: List[Any]) -> List[Any]:
        """过滤黑名单模型"""
        available = []
        for model in models:
            model_name = getattr(model, 'model_name', str(model))
            if not self._is_blacklisted(model_name):
                available.append(model)
        return available
    
    async def parallel_call(self, models: List[Any], prompt: str,
                           task_type: str = 'default',
                           progress_callback: Optional[Callable] = None) -> Dict:
        """并行调用多个模型
        
        Args:
            models: 模型适配器列表
            prompt: 输入提示
            task_type: 任务类型
            progress_callback: 进度回调函数
        
        Returns:
            结果字典 {'results': [...], 'best': {...}, 'stats': {...}}
        """
        task_id = f"{task_type}_{int(time.time()*1000)}"
        start_time = time.time()
        
        # 过滤黑名单模型
        available_models = self._get_available_models(models)
        if not available_models:
            logger.warning("所有模型都在黑名单中")
            return {'error': 'all_models_blacklisted', 'best': None}
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def call_with_semaphore(model_adapter, model_name):
            async with semaphore:
                result = await self._safe_call(model_adapter, model_name, prompt, task_id)
                # 如果失败，加入黑名单
                if not result or not result.get('success'):
                    self._mark_failed(model_name)
                return result
        
        tasks = []
        for model_adapter in available_models:
            model_name = getattr(model_adapter, 'model_name', str(model_adapter))
            tasks.append(call_with_semaphore(model_adapter, model_name))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"模型 {i} 调用异常: {result}")
            elif result and result.get('success'):
                valid_results.append(result)
        
        best_result = self._select_best_result(valid_results, task_type)
        
        duration = time.time() - start_time
        
        self._save_parallel_call(task_id, task_type, valid_results, best_result, duration)
        
        if progress_callback:
            await progress_callback({
                'task_id': task_id,
                'completed': len(valid_results),
                'total': len(models),
                'best_model': best_result.get('model_name') if best_result else None
            })
        
        return {
            'task_id': task_id,
            'results': valid_results,
            'best': best_result,
            'stats': {
                'total_models': len(models),
                'successful': len(valid_results),
                'duration': duration,
                'parallelism': min(len(models), self.max_concurrent)
            }
        }
    
    async def _safe_call(self, model_adapter, model_name: str, 
                        prompt: str, task_id: str) -> Optional[Dict]:
        """安全调用单个模型 - 智能重试和动态超时"""
        # 可重试的错误类型
        RETRYABLE_ERRORS = (asyncio.TimeoutError, ConnectionError, ConnectionResetError)
        
        # 永久性错误（不重试）
        PERMANENT_ERRORS = (FileNotFoundError, PermissionError)
        
        last_error = None
        
        # 动态调整超时时间
        dynamic_timeout = self.timeout_seconds
        if model_name in self.model_performance:
            avg_duration = self.model_performance[model_name]
            # 根据历史性能动态调整超时
            if avg_duration > 20:
                dynamic_timeout = min(60, avg_duration * 1.5)  # 慢模型给更多时间
            elif avg_duration < 5:
                dynamic_timeout = 10  # 快模型减少超时
        
        for attempt in range(self.retry_count):
            try:
                start = time.time()
                
                if asyncio.iscoroutinefunction(model_adapter.generate):
                    response = await asyncio.wait_for(
                        model_adapter.generate(prompt),
                        timeout=dynamic_timeout
                    )
                else:
                    response = await asyncio.wait_for(
                        asyncio.to_thread(model_adapter.generate, prompt),
                        timeout=dynamic_timeout
                    )
                
                duration = time.time() - start
                
                # 更新模型性能记录
                if model_name not in self.model_performance:
                    self.model_performance[model_name] = duration
                else:
                    # 指数移动平均
                    self.model_performance[model_name] = 0.7 * self.model_performance[model_name] + 0.3 * duration
                
                result_text = response if isinstance(response, str) else str(response)
                
                # 记录成功
                try:
                    from infrastructure.model_health_checker import model_health_checker
                    model_health_checker.record_success(model_name, duration)
                except:
                    pass
                
                return {
                    'task_id': task_id,
                    'model_name': model_name,
                    'response': result_text,
                    'duration': duration,
                    'success': True,
                    'quality_score': self._estimate_quality(result_text),
                    'timestamp': datetime.now().isoformat()
                }
                
            except PERMANENT_ERRORS as e:
                # 永久性错误，不重试
                logger.error(f"模型 {model_name} 永久性错误: {e}")
                last_error = str(e)
                
                # 记录失败
                try:
                    from infrastructure.model_health_checker import model_health_checker
                    model_health_checker.record_failure(model_name, "permanent_error", str(e))
                except:
                    pass
                
                break
            
            except RETRYABLE_ERRORS as e:
                # 可重试错误
                logger.warning(f"模型 {model_name} 可重试错误 ({attempt+1}/{self.retry_count}): {e}")
                last_error = str(e)
                
                # 指数退避
                if attempt < self.retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
            
            except Exception as e:
                # 未知错误
                logger.error(f"模型 {model_name} 未知错误: {e}")
                last_error = str(e)
                
                # 只重试一次
                if attempt == 0:
                    continue
        
        # 记录失败
        try:
            from infrastructure.model_health_checker import model_health_checker
            model_health_checker.record_failure(model_name, "call_failed", last_error)
        except:
            pass
        
        return {
            'task_id': task_id,
            'model_name': model_name,
            'response': None,
            'duration': 0,
            'success': False,
            'error': last_error or '调用失败',
            'timestamp': datetime.now().isoformat()
        }
    
    def _estimate_quality(self, text: str) -> float:
        """估算回答质量
        
        Args:
            text: 回答文本
        
        Returns:
            质量评分 (0-1)
        """
        if not text:
            return 0.0
        
        score = 0.5
        
        if len(text) < 10:
            score -= 0.3
        elif len(text) > 100:
            score += 0.1
        elif len(text) > 500:
            score += 0.15
        
        if '错误' in text or 'error' in text.lower():
            score -= 0.2
        
        if '```' in text:
            score += 0.1
        
        if any(word in text for word in ['因为', '所以', '因此', 'however', 'because']):
            score += 0.05
        
        return max(0.0, min(1.0, score))
    
    def _select_best_result(self, results: List[Dict], task_type: str) -> Optional[Dict]:
        """选择最佳结果
        
        Args:
            results: 结果列表
            task_type: 任务类型
        
        Returns:
            最佳结果
        """
        if not results:
            return None
        
        if len(results) == 1:
            return results[0]
        
        from infrastructure.model_capability import model_capability
        
        scored_results = []
        for result in results:
            model_name = result['model_name']
            base_score = result.get('quality_score', 0.5)
            
            capability_score = model_capability.score_model_for_task(model_name, task_type)
            
            speed_score = max(0, 1 - result['duration'] / 60.0)
            
            final_score = (
                0.5 * base_score +
                0.3 * capability_score +
                0.2 * speed_score
            )
            
            scored_results.append((final_score, result))
        
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        best = scored_results[0][1]
        best['final_score'] = scored_results[0][0]
        
        return best
    
    def _save_parallel_call(self, task_id: str, task_type: str,
                           results: List[Dict], best_result: Optional[Dict],
                           duration: float):
        """保存并行调用记录"""
        with sqlite3.connect(self.db_path) as conn:
            for result in results:
                conn.execute('''
                    INSERT INTO parallel_calls
                    (task_id, model_name, start_time, end_time, duration, 
                     success, result_preview, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task_id,
                    result['model_name'],
                    result.get('timestamp', ''),
                    result.get('timestamp', ''),
                    result.get('duration', 0),
                    result['success'],
                    result.get('response', '')[:200] if result.get('response') else None,
                    result.get('error')
                ))
            
            if best_result:
                import json
                models_used = json.dumps([r['model_name'] for r in results])
                
                conn.execute('''
                    INSERT OR REPLACE INTO task_results
                    (task_id, task_type, models_used, best_model, 
                     fusion_strategy, quality_score, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task_id,
                    task_type,
                    models_used,
                    best_result['model_name'],
                    'parallel_best',
                    best_result.get('final_score', 0.5),
                    datetime.now().isoformat()
                ))
            
            conn.commit()
    
    async def federated_call(self, prompt: str, task_type: str,
                            adapters: Dict[str, Any],
                            top_k: int = 3) -> Dict:
        """联邦调度调用
        
        Args:
            prompt: 输入提示
            task_type: 任务类型
            adapters: 模型适配器字典
            top_k: 使用前K个模型（0表示自动）
        
        Returns:
            结果字典
        """
        from infrastructure.model_capability import model_capability
        
        model_names = list(adapters.keys())
        ranked = model_capability.rank_models_for_task(task_type, model_names)
        
        # 动态调整top_k
        if top_k == 0:
            top_k = self._dynamic_top_k(prompt, task_type, ranked)
        
        selected_models = []
        for model_name, score in ranked[:top_k]:
            if model_name in adapters:
                adapter = adapters[model_name]
                adapter.model_name = model_name
                selected_models.append(adapter)
        
        if not selected_models:
            if adapters:
                adapter = next(iter(adapters.values()))
                adapter.model_name = next(iter(adapters.keys()))
                selected_models = [adapter]
            else:
                return {'error': '无可用模型'}
        
        logger.info(f"联邦调度: 任务={task_type}, top_k={top_k}, 模型={[m.model_name for m in selected_models]}")
        
        return await self.parallel_call(selected_models, prompt, task_type)
    
    def _dynamic_top_k(self, prompt: str, task_type: str, 
                      ranked_models: List[Tuple[str, float]]) -> int:
        """动态调整top_k
        
        Args:
            prompt: 输入提示
            task_type: 任务类型
            ranked_models: 排序后的模型列表
        
        Returns:
            动态计算的top_k值
        """
        # 基础值
        base_k = 2
        
        # 1. 基于长度调整
        length_factor = min(2, len(prompt) / 200)
        
        # 2. 基于任务类型调整
        type_factors = {
            'code': 1.5,
            'analysis': 1.3,
            'comparison': 1.4,
            'creative': 1.2,
            'question': 1.0,
            'calculation': 0.8
        }
        type_factor = type_factors.get(task_type, 1.0)
        
        # 3. 基于模型能力差异调整
        if len(ranked_models) >= 2:
            top_score = ranked_models[0][1]
            second_score = ranked_models[1][1]
            
            # 如果第一名明显优于第二名，减少并行数
            if top_score - second_score > 0.15:
                quality_factor = 0.7
            # 如果能力接近，增加并行数以获得更多选择
            elif top_score - second_score < 0.05:
                quality_factor = 1.5
            else:
                quality_factor = 1.0
        else:
            quality_factor = 1.0
        
        # 综合计算
        dynamic_k = int(base_k * length_factor * type_factor * quality_factor)
        
        # 限制范围
        return max(1, min(4, dynamic_k))
    
    def get_stats(self, days: int = 7) -> Dict:
        """获取调度统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT COUNT(*), AVG(duration), SUM(CASE WHEN success THEN 1 ELSE 0 END)
                FROM parallel_calls
                WHERE start_time >= datetime('now', ?)
            ''', (f'-{days} days',))
            
            row = cursor.fetchone()
            
            cursor = conn.execute('''
                SELECT COUNT(DISTINCT task_id) FROM task_results
                WHERE created_at >= datetime('now', ?)
            ''', (f'-{days} days',))
            
            task_count = cursor.fetchone()[0]
            
            return {
                'total_calls': row[0] if row[0] else 0,
                'avg_duration': row[1] if row[1] else 0,
                'success_rate': row[2] / row[0] if row[0] and row[0] > 0 else 0,
                'unique_tasks': task_count
            }


parallel_scheduler = ParallelScheduler()