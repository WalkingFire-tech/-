"""
结果融合器 - 整合多个子任务结果
支持多种融合策略、冲突检测、质量评估
"""
import json
import re
from typing import List, Dict, Optional
from loguru import logger
from datetime import datetime
import sqlite3
from pathlib import Path


class ResultFusion:
    """结果融合器"""
    
    FUSION_STRATEGIES = {
        'concat',      # 简单拼接
        'summarize',   # LLM总结
        'best',        # 选择最佳
        'merge'        # 智能合并
    }
    
    def __init__(self, db_path: str = "data/result_fusion.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(exist_ok=True)
        self._init_db()
        logger.info("结果融合器已初始化")
    
    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS fusions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    strategy TEXT,
                    subtask_count INTEGER,
                    input_results TEXT,
                    fused_result TEXT,
                    quality_score REAL,
                    timestamp TEXT
                )
            ''')
            conn.commit()
    
    def fuse(self, subtasks: List[Dict], results: List[str],
            original_intent: str, strategy: str = 'auto',
            summary_model=None) -> str:
        """融合多个子任务结果
        
        Args:
            subtasks: 子任务列表
            results: 子任务结果列表
            original_intent: 原始意图
            strategy: 融合策略
            summary_model: 总结模型（可选）
        
        Returns:
            融合后的结果
        """
        if not results:
            return ""
        
        if len(results) == 1:
            return results[0]
        
        # 自动选择策略
        if strategy == 'auto':
            strategy = self._select_strategy(subtasks, results)
        
        logger.info(f"使用融合策略: {strategy}")
        
        if strategy == 'concat':
            fused = self._fuse_concat(subtasks, results)
        elif strategy == 'summarize':
            fused = self._fuse_summarize(subtasks, results, original_intent, summary_model)
        elif strategy == 'best':
            fused = self._fuse_best(subtasks, results)
        elif strategy == 'merge':
            fused = self._fuse_merge(subtasks, results, original_intent, summary_model)
        else:
            fused = self._fuse_concat(subtasks, results)
        
        # 保存融合记录
        self._save_fusion(
            task_id=f"fusion_{int(datetime.now().timestamp())}",
            strategy=strategy,
            subtask_count=len(subtasks),
            input_results=results,
            fused_result=fused
        )
        
        return fused
    
    def _select_strategy(self, subtasks: List[Dict], results: List[str]) -> str:
        """自动选择融合策略"""
        # 检查任务类型组合
        types = [t['type'] for t in subtasks]
        
        # 如果都是代码任务，选择best
        if all(t == 'code' for t in types):
            return 'best'
        
        # 如果有解释/分析任务，选择summarize
        if any(t in ['explanation', 'analysis'] for t in types):
            return 'summarize'
        
        # 如果有依赖关系，选择merge
        if any(t.get('dependencies') for t in subtasks):
            return 'merge'
        
        # 默认拼接
        return 'concat'
    
    def _fuse_concat(self, subtasks: List[Dict], results: List[str]) -> str:
        """简单拼接"""
        sections = []
        
        for task, result in zip(subtasks, results):
            if result and len(result) > 10:
                header = self._get_section_header(task['type'])
                sections.append(f"{header}\n{result}")
        
        return "\n\n".join(sections)
    
    def _get_section_header(self, task_type: str) -> str:
        """获取段落标题"""
        headers = {
            'code': '### 代码实现',
            'analysis': '### 分析结果',
            'explanation': '### 解释说明',
            'calculation': '### 计算结果',
            'creative': '### 创作内容',
            'general': '### 结果'
        }
        return headers.get(task_type, '### 结果')
    
    def _fuse_summarize(self, subtasks: List[Dict], results: List[str],
                       original_intent: str, summary_model=None) -> str:
        """LLM总结融合"""
        if not summary_model:
            logger.warning("未提供总结模型，使用拼接策略")
            return self._fuse_concat(subtasks, results)
        
        # 构建总结提示
        sections = []
        for task, result in zip(subtasks, results):
            sections.append(f"【{task['type']}】{result}")
        
        prompt = f"""原始需求：{original_intent}

以下是针对不同方面的回答：
{chr(10).join(sections)}

请将上述内容整合为一个连贯、完整、条理清晰的最终回答。要求：
1. 保留关键信息和代码
2. 去除重复内容
3. 保持逻辑连贯
4. 适当使用分段和标题

请直接输出整合后的回答："""

        try:
            response = summary_model.generate(prompt)
            if isinstance(response, tuple):
                response = response[0]
            return response
        except Exception as e:
            logger.error(f"总结融合失败: {e}")
            return self._fuse_concat(subtasks, results)
    
    def _fuse_best(self, subtasks: List[Dict], results: List[str]) -> str:
        """选择最佳结果"""
        if not results:
            return ""
        
        # 评估每个结果的质量
        scored_results = []
        for result in results:
            score = self._estimate_quality(result)
            scored_results.append((score, result))
        
        # 选择最高分
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return scored_results[0][1]
    
    def _estimate_quality(self, text: str) -> float:
        """评估结果质量"""
        if not text:
            return 0.0
        
        score = 0.5
        
        # 长度奖励
        if len(text) > 100:
            score += 0.1
        if len(text) > 500:
            score += 0.1
        
        # 代码检测
        if '```' in text or 'def ' in text or 'class ' in text:
            score += 0.15
        
        # 结构检测
        if any(marker in text for marker in ['###', '1.', '首先', '第一']):
            score += 0.1
        
        # 错误检测
        if '错误' in text or 'error' in text.lower():
            score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _fuse_merge(self, subtasks: List[Dict], results: List[str],
                   original_intent: str, summary_model=None) -> str:
        """智能合并（考虑依赖关系）"""
        # 构建依赖图
        result_map = {i: r for i, r in enumerate(results)}
        merged = {}
        
        # 按依赖顺序处理
        processed = set()
        
        for i, task in enumerate(subtasks):
            deps = task.get('dependencies', [])
            
            # 确保依赖已处理
            for dep in deps:
                if dep not in processed:
                    merged[dep] = result_map.get(dep, "")
                    processed.add(dep)
            
            # 合并当前结果与依赖结果
            if deps:
                dep_results = [merged[d] for d in deps if d in merged]
                current_result = result_map.get(i, "")
                
                # 构建合并提示
                if summary_model:
                    merged_result = self._merge_with_context(
                        current_result, dep_results, task, summary_model
                    )
                else:
                    merged_result = f"{current_result}\n\n基于前面的结果：\n" + "\n".join(dep_results)
                
                merged[i] = merged_result
            else:
                merged[i] = result_map.get(i, "")
            
            processed.add(i)
        
        # 按顺序组合最终结果
        final_parts = [merged[i] for i in range(len(subtasks)) if i in merged]
        return "\n\n".join(final_parts)
    
    def _merge_with_context(self, current: str, dep_results: List[str],
                           task: Dict, summary_model) -> str:
        """带上下文的合并"""
        prompt = f"""当前任务：{task['description']}
当前结果：{current}

相关上下文：
{chr(10).join(dep_results)}

请将当前结果与上下文结合，生成一个连贯的回答："""

        try:
            response = summary_model.generate(prompt)
            if isinstance(response, tuple):
                response = response[0]
            return response
        except Exception as e:
            logger.error(f"上下文合并失败: {e}")
            return current
    
    def _save_fusion(self, task_id: str, strategy: str,
                    subtask_count: int, input_results: List[str],
                    fused_result: str):
        """保存融合记录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO fusions
                (task_id, strategy, subtask_count, input_results, fused_result, quality_score, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_id,
                strategy,
                subtask_count,
                json.dumps(input_results, ensure_ascii=False)[:1000],
                fused_result[:2000],
                self._estimate_quality(fused_result),
                datetime.now().isoformat()
            ))
            conn.commit()
    
    def get_fusion_stats(self) -> Dict:
        """获取融合统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT COUNT(*) FROM fusions')
            total = cursor.fetchone()[0]
            
            cursor = conn.execute('SELECT strategy, COUNT(*) FROM fusions GROUP BY strategy')
            strategy_counts = dict(cursor.fetchall())
            
            return {
                'total_fusions': total,
                'strategies': strategy_counts
            }


result_fusion = ResultFusion()