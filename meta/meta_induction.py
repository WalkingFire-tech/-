"""
元归纳器 - 递归归纳系统
让系统学会如何学习，优化归纳器自身的参数和策略
"""
import sqlite3
import yaml
import time
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
from infrastructure.event_bus import bus


class MetaInductor:
    """元归纳器 - 分析归纳器的效果并优化其参数"""
    
    def __init__(self):
        self.params_file = Path("config/induction_params.yaml")
        self.params = self._load_params()
        self.optimization_history = []
        logger.info(f"元归纳器已启动，当前参数: {self.params}")
    
    def _load_params(self) -> Dict:
        """加载归纳参数"""
        default_params = {
            'min_support': 3,
            'min_confidence': 0.7,
            'quality_threshold': 50,
            'max_rules_per_run': 10,
            'rule_types': {
                'prefer_model': {'enabled': True, 'priority': 5},
                'reroute': {'enabled': True, 'priority': 6},
                'avoid_model': {'enabled': True, 'priority': 4},
                'ask_user': {'enabled': False, 'priority': 2}
            },
            'meta': {
                'optimization_interval_days': 7,
                'success_rate_threshold': 0.6,
                'adjustment_factor': 0.1
            }
        }
        
        if self.params_file.exists():
            try:
                with open(self.params_file, 'r', encoding='utf-8') as f:
                    loaded = yaml.safe_load(f)
                    default_params.update(loaded)
            except Exception as e:
                logger.warning(f"加载参数文件失败: {e}")
        
        return default_params
    
    def _save_params(self):
        """保存归纳参数"""
        try:
            self.params_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.params_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.params, f, allow_unicode=True)
            logger.info(f"参数已保存到 {self.params_file}")
        except Exception as e:
            logger.error(f"保存参数失败: {e}")
    
    def analyze_rule_performance(self) -> Dict:
        """分析规则性能
        
        Returns:
            各类规则的成功率统计
        """
        try:
            conn = sqlite3.connect('learning_rules.db')
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    action,
                    COUNT(*) as total,
                    SUM(CASE WHEN success_count > apply_count * 0.5 THEN 1 ELSE 0 END) as successful,
                    AVG(apply_count) as avg_apply,
                    AVG(success_count) as avg_success
                FROM learning_rules
                WHERE status = 'active' AND apply_count > 0
                GROUP BY action
            """)
            
            performance = {}
            for row in cursor.fetchall():
                action = row['action']
                total = row['total']
                successful = row['successful']
                
                success_rate = successful / total if total > 0 else 0
                
                action_type = action.split(':')[0] if ':' in action else action
                
                if action_type not in performance:
                    performance[action_type] = {
                        'total_rules': 0,
                        'total_applications': 0,
                        'successful_applications': 0,
                        'success_rate': 0.0
                    }
                
                performance[action_type]['total_rules'] += total
                performance[action_type]['total_applications'] += row['avg_apply'] * total
                performance[action_type]['successful_applications'] += row['avg_success'] * total
            
            conn.close()
            
            for action_type in performance:
                total_app = performance[action_type]['total_applications']
                success_app = performance[action_type]['successful_applications']
                performance[action_type]['success_rate'] = success_app / total_app if total_app > 0 else 0
            
            return performance
            
        except Exception as e:
            logger.error(f"分析规则性能失败: {e}")
            return {}
    
    def optimize_parameters(self) -> Dict:
        """优化归纳参数
        
        Returns:
            优化结果
        """
        logger.info("开始元归纳优化...")
        
        performance = self.analyze_rule_performance()
        
        if not performance:
            return {'success': False, 'message': '无足够数据'}
        
        adjustments = []
        meta_config = self.params['meta']
        threshold = meta_config['success_rate_threshold']
        factor = meta_config['adjustment_factor']
        
        for action_type, stats in performance.items():
            success_rate = stats['success_rate']
            
            if action_type not in self.params['rule_types']:
                continue
            
            rule_config = self.params['rule_types'][action_type]
            
            if success_rate < threshold:
                old_priority = rule_config.get('priority', 5)
                new_priority = max(1, old_priority - 1)
                rule_config['priority'] = new_priority
                
                adjustments.append({
                    'action_type': action_type,
                    'type': 'decrease_priority',
                    'reason': f'成功率{success_rate:.2f}低于阈值{threshold}',
                    'old_value': old_priority,
                    'new_value': new_priority
                })
                
                if success_rate < threshold * 0.5:
                    self.params['min_confidence'] = min(0.9, self.params['min_confidence'] + factor)
                    adjustments.append({
                        'action_type': 'global',
                        'type': 'increase_confidence_threshold',
                        'reason': f'{action_type}成功率极低',
                        'new_value': self.params['min_confidence']
                    })
            
            elif success_rate > threshold + 0.2:
                old_priority = rule_config.get('priority', 5)
                new_priority = min(10, old_priority + 1)
                rule_config['priority'] = new_priority
                
                adjustments.append({
                    'action_type': action_type,
                    'type': 'increase_priority',
                    'reason': f'成功率{success_rate:.2f}表现优秀',
                    'old_value': old_priority,
                    'new_value': new_priority
                })
        
        total_rules = sum(stats['total_rules'] for stats in performance.values())
        if total_rules < 10:
            old_support = self.params['min_support']
            self.params['min_support'] = max(2, old_support - 1)
            adjustments.append({
                'action_type': 'global',
                'type': 'decrease_support_threshold',
                'reason': f'规则总数{total_rules}过少',
                'old_value': old_support,
                'new_value': self.params['min_support']
            })
        
        elif total_rules > 50:
            old_support = self.params['min_support']
            self.params['min_support'] = min(5, old_support + 1)
            adjustments.append({
                'action_type': 'global',
                'type': 'increase_support_threshold',
                'reason': f'规则总数{total_rules}过多',
                'old_value': old_support,
                'new_value': self.params['min_support']
            })
        
        if adjustments:
            self._save_params()
            
            self.optimization_history.append({
                'timestamp': time.time(),
                'performance': performance,
                'adjustments': adjustments
            })
            
            logger.info(f"元归纳完成，调整{len(adjustments)}项参数")
        
        return {
            'success': True,
            'performance': performance,
            'adjustments': adjustments,
            'current_params': self.params
        }
    
    def get_meta_report(self) -> Dict:
        """获取元归纳报告"""
        performance = self.analyze_rule_performance()
        
        report = {
            'current_params': self.params,
            'rule_performance': performance,
            'optimization_count': len(self.optimization_history),
            'last_optimization': self.optimization_history[-1] if self.optimization_history else None
        }
        
        recommendations = []
        
        for action_type, stats in performance.items():
            success_rate = stats['success_rate']
            
            if success_rate < 0.4:
                recommendations.append(f"⚠️ {action_type}规则成功率仅{success_rate:.1%}，建议降低优先级或禁用")
            elif success_rate > 0.8:
                recommendations.append(f"✓ {action_type}规则表现优秀({success_rate:.1%})，可考虑增加生成")
        
        if self.params['min_support'] > 4:
            recommendations.append("💡 支持度阈值较高，可能遗漏有效模式，建议降低至3")
        
        report['recommendations'] = recommendations
        
        return report
    
    def should_trigger_optimization(self) -> bool:
        """判断是否应该触发优化"""
        interval_days = self.params['meta']['optimization_interval_days']
        
        if not self.optimization_history:
            return True
        
        last_time = self.optimization_history[-1]['timestamp']
        hours_since = (time.time() - last_time) / 3600
        
        return hours_since >= interval_days * 24


meta_inductor = MetaInductor()