"""
自动学习触发器 - 基于学习目标列表自动触发学习
"""
import yaml
import sqlite3
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger


class AutoLearningTrigger:
    """自动学习触发器 - 根据学习目标自动触发学习"""
    
    def __init__(self, config_path: str = "config/learning_targets.yaml",
                 db_path: str = "data/knowledge_store.db"):
        self.config_path = Path(config_path)
        self.db_path = db_path
        self.config = None
        self.learning_targets = None
        self.running = False
        self.thread = None
        self.learning_history = []
        
        # 加载配置
        self._load_config()
        
        # 初始化数据库
        self._init_db()
        
        logger.info(f"自动学习触发器已初始化，目标数: {len(self.learning_targets.get('topics', []))}主题 + {len(self.learning_targets.get('skills', []))}技能")
    
    def _load_config(self):
        """加载学习目标配置"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
                self.learning_targets = self.config.get('learning_targets', {})
                logger.info(f"学习目标配置已加载: {self.config_path}")
            else:
                logger.warning(f"学习目标配置不存在: {self.config_path}")
                self.config = {}
                self.learning_targets = {}
        except Exception as e:
            logger.error(f"加载学习目标配置失败: {e}")
            self.config = {}
            self.learning_targets = {}
    
    def _init_db(self):
        """初始化学习进度数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS learning_progress (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        target_name TEXT NOT NULL,
                        target_type TEXT NOT NULL,
                        progress INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'pending',
                        last_learning TIMESTAMP,
                        success_count INTEGER DEFAULT 0,
                        failure_count INTEGER DEFAULT 0,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(target_name, target_type)
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS learning_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        target_name TEXT NOT NULL,
                        target_type TEXT NOT NULL,
                        action TEXT,
                        result TEXT,
                        knowledge_gained INTEGER DEFAULT 0,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("学习进度数据库已初始化")
        except Exception as e:
            logger.error(f"初始化学习进度数据库失败: {e}")
    
    def start(self):
        """启动自动学习触发器"""
        if self.running:
            logger.warning("自动学习触发器已在运行")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._background_loop, daemon=True)
        self.thread.start()
        logger.info("自动学习触发器已启动")
    
    def stop(self):
        """停止自动学习触发器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("自动学习触发器已停止")
    
    def _background_loop(self):
        """后台循环检查学习目标"""
        auto_config = self.config.get('auto_learning', {})
        check_interval = auto_config.get('check_interval', 3600)
        
        while self.running:
            try:
                logger.info("检查学习目标进度...")
                self._check_and_trigger_learning()
            except Exception as e:
                logger.error(f"检查学习目标失败: {e}")
            
            # 等待下次检查
            for _ in range(check_interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def _check_and_trigger_learning(self):
        """检查学习目标并触发学习"""
        auto_config = self.config.get('auto_learning', {})
        
        if not auto_config.get('enabled', True):
            logger.info("自动学习已禁用")
            return
        
        # 获取需要学习的目标
        pending_targets = self._get_pending_targets()
        
        if not pending_targets:
            logger.info("所有学习目标已完成")
            return
        
        # 按优先级排序
        pending_targets.sort(key=lambda x: x.get('priority', 0), reverse=True)
        
        # 限制并行学习数
        max_parallel = auto_config.get('max_parallel', 3)
        targets_to_learn = pending_targets[:max_parallel]
        
        logger.info(f"触发学习 {len(targets_to_learn)} 个目标")
        
        for target in targets_to_learn:
            try:
                self._trigger_target_learning(target)
            except Exception as e:
                logger.error(f"学习目标 {target['name']} 失败: {e}")
    
    def _get_pending_targets(self) -> List[Dict]:
        """获取待学习的目标"""
        pending = []
        auto_config = self.config.get('auto_learning', {})
        trigger_threshold = auto_config.get('trigger_threshold', 0.5)
        
        # 检查主题学习目标
        for topic in self.learning_targets.get('topics', []):
            progress = self._get_topic_progress(topic['name'])
            topic['progress'] = progress
            topic['type'] = 'topic'
            
            # 计算完成度
            completion = progress / topic.get('min_knowledge', 10)
            
            # 判断是否需要学习
            if completion < trigger_threshold or topic.get('status') == 'pending':
                pending.append(topic)
        
        # 检查技能学习目标
        for skill in self.learning_targets.get('skills', []):
            success_rate = self._get_skill_success_rate(skill['name'])
            skill['success_rate'] = success_rate
            skill['type'] = 'skill'
            
            # 判断是否需要学习
            min_rate = skill.get('min_success_rate', 0.8)
            if success_rate < min_rate or skill.get('status') == 'pending':
                pending.append(skill)
        
        return pending
    
    def _get_topic_progress(self, topic_name: str) -> int:
        """获取主题学习进度（知识条数）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 查询相关知识的数量
                cursor.execute('''
                    SELECT COUNT(*) FROM knowledge_items
                    WHERE question LIKE ? OR answer LIKE ?
                ''', (f'%{topic_name}%', f'%{topic_name}%'))
                
                count = cursor.fetchone()[0]
                return count
        except Exception as e:
            logger.error(f"获取主题进度失败: {topic_name}, 错误: {str(e)}")
            return 0
    
    def _get_skill_success_rate(self, skill_name: str) -> float:
        """获取技能成功率"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 查询技能成功记录
                cursor.execute('''
                    SELECT 
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                        COUNT(*) as total_count
                    FROM experiences
                    WHERE intent_type = ?
                ''', (skill_name,))
                
                result = cursor.fetchone()
                success_count = result[0] or 0
                total_count = result[1] or 0
                
                if total_count == 0:
                    return 0.0
                
                return success_count / total_count
        except Exception as e:
            logger.error(f"获取技能成功率失败: {skill_name}, 错误: {str(e)}")
            return 0.0
    
    def _trigger_target_learning(self, target: Dict):
        """触发单个目标的学习"""
        target_name = target['name']
        target_type = target['type']
        
        logger.info(f"触发学习: {target_name} ({target_type})")
        
        # 记录学习开始
        self._record_learning_history(target_name, target_type, 'start', 'triggered')
        
        try:
            if target_type == 'topic':
                result = self._learn_topic(target)
            else:
                result = self._learn_skill(target)
            
            # 记录学习结果
            self._record_learning_history(
                target_name, target_type, 'complete', 
                'success', result.get('knowledge_gained', 0)
            )
            
            # 更新进度
            self._update_progress(target_name, target_type, result)
            
            logger.info(f"学习完成: {target_name}, 获得知识: {result.get('knowledge_gained', 0)}条")
            
        except Exception as e:
            # 记录失败
            self._record_learning_history(target_name, target_type, 'fail', str(e))
            logger.error(f"学习失败: {target_name} - {e}")
    
    def _learn_topic(self, topic: Dict) -> Dict:
        """学习主题"""
        from core.learning import enhanced_learner
        
        topic_name = topic['name']
        keywords = topic.get('keywords', [])
        sources = topic.get('sources', [])
        
        knowledge_gained = 0
        
        # 为每个关键词触发学习
        for keyword in keywords:
            try:
                # 触发外部学习
                result = enhanced_learner.learn_with_external(
                    user_input=f"请详细解释{topic_name}中的{keyword}概念",
                    context=f"主题学习: {topic_name}",
                    response_text="",
                    confidence=0.5,
                    auto_trigger=True
                )
                
                if result.get('new_knowledge_count', 0) > 0:
                    knowledge_gained += result['new_knowledge_count']
                    
            except Exception as e:
                logger.warning(f"学习关键词 {keyword} 失败: {e}")
        
        return {
            'knowledge_gained': knowledge_gained,
            'keywords_learned': len(keywords)
        }
    
    def _learn_skill(self, skill: Dict) -> Dict:
        """学习技能（通过实践改进）"""
        skill_name = skill['name']
        indicators = skill.get('indicators', [])
        
        # 技能学习主要通过实践积累，这里记录学习意图
        # 实际改进由系统运行时的经验积累完成
        
        return {
            'knowledge_gained': 0,
            'skill_practiced': skill_name,
            'indicators': indicators
        }
    
    def _record_learning_history(self, target_name: str, target_type: str,
                                 action: str, result: str, knowledge_gained: int = 0):
        """记录学习历史"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO learning_history 
                    (target_name, target_type, action, result, knowledge_gained, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (target_name, target_type, action, result, knowledge_gained, datetime.now()))
                
                conn.commit()
        except Exception as e:
            logger.error(f"记录学习历史失败: {e}")
    
    def _update_progress(self, target_name: str, target_type: str, result: Dict):
        """更新学习进度"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 获取当前进度
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT progress, success_count FROM learning_progress
                    WHERE target_name = ? AND target_type = ?
                ''', (target_name, target_type))
                
                row = cursor.fetchone()
                
                if row:
                    new_progress = row[0] + result.get('knowledge_gained', 0)
                    new_success = row[1] + 1
                    
                    conn.execute('''
                        UPDATE learning_progress
                        SET progress = ?, success_count = ?, 
                            last_learning = ?, updated_at = ?
                        WHERE target_name = ? AND target_type = ?
                    ''', (new_progress, new_success, datetime.now(), datetime.now(),
                          target_name, target_type))
                else:
                    conn.execute('''
                        INSERT INTO learning_progress
                        (target_name, target_type, progress, status, success_count, last_learning, updated_at)
                        VALUES (?, ?, ?, 'in_progress', 1, ?, ?)
                    ''', (target_name, target_type, result.get('knowledge_gained', 0),
                          datetime.now(), datetime.now()))
                
                conn.commit()
        except Exception as e:
            logger.error(f"更新学习进度失败: {e}")
    
    def get_learning_status(self) -> Dict:
        """获取学习状态报告"""
        status = {
            'topics': [],
            'skills': [],
            'total_progress': 0,
            'pending_count': 0
        }
        
        # 主题状态
        for topic in self.learning_targets.get('topics', []):
            progress = self._get_topic_progress(topic['name'])
            completion = progress / topic.get('min_knowledge', 10)
            
            status['topics'].append({
                'name': topic['name'],
                'progress': progress,
                'target': topic.get('min_knowledge', 10),
                'completion': f"{completion * 100:.1f}%",
                'status': 'completed' if completion >= 1.0 else 'in_progress',
                'priority': topic.get('priority', 0)
            })
            
            status['total_progress'] += min(completion, 1.0)
            if completion < 1.0:
                status['pending_count'] += 1
        
        # 技能状态
        for skill in self.learning_targets.get('skills', []):
            success_rate = self._get_skill_success_rate(skill['name'])
            min_rate = skill.get('min_success_rate', 0.8)
            
            status['skills'].append({
                'name': skill['name'],
                'success_rate': f"{success_rate * 100:.1f}%",
                'target': f"{min_rate * 100:.1f}%",
                'status': 'completed' if success_rate >= min_rate else 'in_progress',
                'priority': skill.get('priority', 0)
            })
            
            if success_rate < min_rate:
                status['pending_count'] += 1
        
        # 总体进度
        total_targets = len(status['topics']) + len(status['skills'])
        if total_targets > 0:
            status['overall_completion'] = f"{(status['total_progress'] / len(status['topics'])) * 100:.1f}%"
        
        return status
    
    def force_learn_target(self, target_name: str, target_type: str = 'topic') -> Dict:
        """强制学习指定目标"""
        # 查找目标
        targets = self.learning_targets.get(f'{target_type}s', [])
        target = next((t for t in targets if t['name'] == target_name), None)
        
        if not target:
            return {'success': False, 'error': f'目标不存在: {target_name}'}
        
        target['type'] = target_type
        
        try:
            self._trigger_target_learning(target)
            return {'success': True, 'message': f'已触发学习: {target_name}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# 全局实例
auto_learning_trigger = AutoLearningTrigger()