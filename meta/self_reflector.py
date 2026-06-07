"""
自我反思模块 - 元控制层核心组件
使用LLM分析失败案例,生成修正建议
"""
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from infrastructure.event_bus import bus
from infrastructure.config_manager import config


class SelfReflector:
    """自我反思模块"""
    
    def __init__(self, llm_adapter=None):
        self.llm_adapter = llm_adapter
        self.reflections_file = Path("self_reflections.json")
        self.reflections = self._load_reflections()
        self.reflection_interval = config.get("self_reflection.interval_hours", 24)
        self.min_failures = config.get("self_reflection.min_failures", 5)
    
    def _load_reflections(self) -> List[Dict]:
        """加载反思记录"""
        if self.reflections_file.exists():
            try:
                with open(self.reflections_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载反思记录失败: {e}")
        return []
    
    def _save_reflections(self):
        """保存反思记录"""
        try:
            with open(self.reflections_file, 'w', encoding='utf-8') as f:
                json.dump(self.reflections, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存反思记录失败: {e}")
    
    def should_reflect(self) -> bool:
        """判断是否应该进行反思"""
        # 检查上次反思时间
        if not self.reflections:
            return True
        
        last_reflection = self.reflections[-1]
        last_time = datetime.fromisoformat(last_reflection["timestamp"])
        
        if datetime.now() - last_time < timedelta(hours=self.reflection_interval):
            return False
        
        # 检查失败数量
        failures = self._get_recent_failures()
        if len(failures) < self.min_failures:
            return False
        
        return True
    
    def _get_recent_failures(self, hours: int = 24) -> List[Dict]:
        """获取最近的失败案例"""
        stats_db = Path("model_stats.db")
        if not stats_db.exists():
            return []
        
        cutoff = datetime.now() - timedelta(hours=hours)
        
        try:
            with sqlite3.connect(stats_db) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.execute('''
                    SELECT *
                    FROM model_performance
                    WHERE (quality_score < 50 OR success = 0)
                      AND timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT 50
                ''', (cutoff.isoformat(),))
                
                return [dict(row) for row in cur.fetchall()]
        except:
            return []
    
    def reflect(self) -> Optional[Dict]:
        """执行自我反思"""
        if not self.should_reflect():
            logger.info("不满足反思条件,跳过")
            return None
        
        if not self.llm_adapter:
            logger.warning("未配置LLM适配器,无法进行反思")
            return None
        
        logger.info("开始自我反思...")
        
        # 1. 收集失败案例
        failures = self._get_recent_failures()
        
        if not failures:
            logger.info("无失败案例,跳过反思")
            return None
        
        # 2. 分析失败模式
        failure_patterns = self._analyze_failure_patterns(failures)
        
        # 3. 使用LLM生成反思
        reflection_prompt = self._build_reflection_prompt(failures, failure_patterns)
        
        try:
            reflection_response = self.llm_adapter.generate(
                reflection_prompt,
                task_type="reflection"
            )
            
            # 4. 解析反思结果
            insights = self._parse_reflection(reflection_response)
            
            # 5. 生成修正建议
            corrections = self._generate_corrections(insights, failure_patterns)
            
            # 6. 记录反思
            reflection_record = {
                "timestamp": datetime.now().isoformat(),
                "failure_count": len(failures),
                "failure_patterns": failure_patterns,
                "insights": insights,
                "corrections": corrections,
                "raw_response": reflection_response
            }
            
            self.reflections.append(reflection_record)
            self._save_reflections()
            
            logger.info(f"反思完成,生成{len(corrections)}条修正建议")
            
            # 7. 应用修正(可选)
            self._apply_corrections(corrections)
            
            return reflection_record
        
        except Exception as e:
            logger.error(f"反思失败: {e}")
            return None
    
    def _analyze_failure_patterns(self, failures: List[Dict]) -> Dict:
        """分析失败模式"""
        patterns = {
            "by_task_type": {},
            "by_model": {},
            "by_error_type": {},
            "common_characteristics": []
        }
        
        # 按任务类型统计
        for failure in failures:
            task_type = failure.get("task_type", "unknown")
            patterns["by_task_type"][task_type] = patterns["by_task_type"].get(task_type, 0) + 1
            
            model = failure.get("model_name", "unknown")
            patterns["by_model"][model] = patterns["by_model"].get(model, 0) + 1
            
            # 判断错误类型
            if failure.get("quality_score", 0) < 30:
                error_type = "low_quality"
            elif not failure.get("success", True):
                error_type = "execution_failure"
            else:
                error_type = "suboptimal"
            
            patterns["by_error_type"][error_type] = patterns["by_error_type"].get(error_type, 0) + 1
        
        # 找出最常见的失败模式
        patterns["common_characteristics"] = [
            f"任务类型'{k}'失败{v}次"
            for k, v in sorted(
                patterns["by_task_type"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
        ]
        
        return patterns
    
    def _build_reflection_prompt(self, failures: List[Dict], patterns: Dict) -> str:
        """构建反思提示词"""
        prompt = f"""作为系统自我反思模块,请分析以下失败案例并生成改进建议。

## 失败统计
- 总失败数: {len(failures)}
- 按任务类型: {patterns['by_task_type']}
- 按模型: {patterns['by_model']}
- 按错误类型: {patterns['by_error_type']}

## 典型失败案例
"""
        
        # 添加典型案例
        for i, failure in enumerate(failures[:5], 1):
            prompt += f"""
### 案例{i}
- 任务类型: {failure.get('task_type')}
- 使用模型: {failure.get('model_name')}
- 质量分: {failure.get('quality_score')}
- 是否成功: {failure.get('success')}
- 耗时: {failure.get('duration', 0):.2f}秒
"""
        
        prompt += """

## 请分析并回答
1. **主要问题**: 这些失败有什么共同原因?
2. **改进建议**: 应该如何调整系统以避免这些失败?
3. **参数调整**: 是否需要调整路由权重、质量阈值等参数?
4. **规则修正**: 是否需要修改意图识别规则或提示词模板?

请以JSON格式返回:
{
  "main_issues": ["问题1", "问题2"],
  "improvements": ["建议1", "建议2"],
  "param_adjustments": {"参数名": "调整建议"},
  "rule_corrections": ["规则修正1"]
}
"""
        
        return prompt
    
    def _parse_reflection(self, response: str) -> Dict:
        """解析反思结果"""
        import re
        
        # 尝试提取JSON
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except:
                pass
        
        # 解析失败,返回空结果
        return {
            "main_issues": [],
            "improvements": [],
            "param_adjustments": {},
            "rule_corrections": []
        }
    
    def _generate_corrections(self, insights: Dict, patterns: Dict) -> List[Dict]:
        """生成修正建议"""
        corrections = []
        
        # 基于洞察生成修正
        for improvement in insights.get("improvements", []):
            corrections.append({
                "type": "general",
                "description": improvement,
                "priority": "medium"
            })
        
        # 基于失败模式生成修正
        for task_type, count in patterns["by_task_type"].items():
            if count >= 3:
                corrections.append({
                    "type": "task_specific",
                    "task_type": task_type,
                    "description": f"任务类型'{task_type}'失败率高,需要优化",
                    "priority": "high"
                })
        
        # 参数调整
        for param, suggestion in insights.get("param_adjustments", {}).items():
            corrections.append({
                "type": "parameter",
                "parameter": param,
                "suggestion": suggestion,
                "priority": "medium"
            })
        
        return corrections
    
    def _apply_corrections(self, corrections: List[Dict]):
        """应用修正建议"""
        for correction in corrections:
            if correction["type"] == "parameter":
                logger.info(f"参数修正建议: {correction['parameter']} -> {correction['suggestion']}")
                # 实际应用需要谨慎,可以先记录
            
            elif correction["type"] == "task_specific":
                logger.info(f"任务修正建议: {correction['description']}")
                # 可以更新任务特定配置
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        if not self.reflections:
            return {
                "total_reflections": 0,
                "last_reflection": None,
                "total_corrections": 0
            }
        
        total_corrections = sum(
            len(r.get("corrections", []))
            for r in self.reflections
        )
        
        return {
            "total_reflections": len(self.reflections),
            "last_reflection": self.reflections[-1]["timestamp"],
            "total_corrections": total_corrections,
            "avg_failures_per_reflection": sum(
                r["failure_count"] for r in self.reflections
            ) / len(self.reflections)
        }