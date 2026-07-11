"""
反思驱动的无模型进化系统
在无LLM环境下，通过数据驱动方式实现：
1. 错误感知（通过模式异常检测）
2. 假设检验（通过一致性验证）
3. 认知闭环（通过反馈整合）
4. 进化校准（通过元监控）
"""

import sys
import time
import threading

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
from loguru import logger
import math
from infrastructure.database_manager import DatabaseManager

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


# ==================== 数据契约 ====================

@dataclass
class KnowledgeItem:
    """知识条目"""
    id: str
    question: str
    answer: str
    source: str
    knowledge_type: str
    quality_score: float
    confidence: float  # 新增：置信度
    verification_status: str  # 'pending', 'verified', 'disputed', 'refuted'
    created_at: str
    last_accessed: str
    access_count: int
    error_count: int  # 新增：被指正的次数
    version: int  # 新增：版本号（每次修正递增）


@dataclass
class ErrorCase:
    """错误案例"""
    id: str
    problem: str
    wrong_answer: str
    correct_answer: Optional[str]
    error_type: str  # 'domain_confusion', 'functional_mismatch', 'source_unreliable'
    detected_at: str
    resolved_at: Optional[str]
    resolution_status: str  # 'pending', 'resolved', 'invalid'
    reflection: Optional[str]  # 反思结论


@dataclass
class BehaviorPattern:
    """行为模式"""
    pattern_id: str
    pattern_type: str
    description: str
    confidence: float
    triggered_count: int
    success_count: int
    failure_count: int
    last_triggered: str
    evolution_stage: int  # 演化代际


# ==================== 第0层：数据驱动的反思引擎 ====================

class DataDrivenReflectionEngine:
    """
    数据驱动的反思引擎
    不依赖LLM，通过数据模式识别实现"自我审视"
    """
    
    def __init__(self, db_path: str = "data/reflection_store.db"):
        self.db_path = db_path
        self._init_database()
        
        # 内存中的模式缓存
        self.pattern_cache = {}
        
        # 反思阈值
        self.thresholds = {
            'error_rate_threshold': 0.15,  # 错误率超过15%触发反思
            'confidence_drop_threshold': 0.3,  # 置信度下降超过30%触发
            'inconsistency_threshold': 0.4,  # 不一致率达到40%触发
            'knowledge_decay_rate': 0.02,  # 每次衰减2%
        }
        
        logger.info("🧠 数据驱动反思引擎已初始化")
    
    def _init_database(self):
        """初始化反思数据库"""
        
        Path(self.db_path).parent.mkdir(exist_ok=True)
        
        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS error_cases (
                id TEXT PRIMARY KEY,
                problem TEXT,
                wrong_answer TEXT,
                correct_answer TEXT,
                error_type TEXT,
                detected_at TEXT,
                resolved_at TEXT,
                resolution_status TEXT,
                reflection TEXT
            );
            CREATE TABLE IF NOT EXISTS behavior_patterns (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT,
                description TEXT,
                confidence REAL,
                triggered_count INTEGER,
                success_count INTEGER,
                failure_count INTEGER,
                last_triggered TEXT,
                evolution_stage INTEGER
            );
            CREATE TABLE IF NOT EXISTS knowledge_confidence (
                knowledge_id TEXT PRIMARY KEY,
                current_confidence REAL,
                initial_confidence REAL,
                highest_confidence REAL,
                lowest_confidence REAL,
                confidence_history TEXT,
                last_updated TEXT,
                verification_count INTEGER,
                dispute_count INTEGER
            );
            CREATE TABLE IF NOT EXISTS metacognition_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                metric_name TEXT,
                metric_value REAL,
                context TEXT,
                triggered_reflection BOOLEAN
            )
        ''')

    
    def detect_errors(self, knowledge_items: List[Dict]) -> List[ErrorCase]:
        """
        错误感知：通过多种模式检测潜在错误
        
        无需LLM，纯数据驱动
        """
        errors = []
        
        for item in knowledge_items:
            # 模式1：置信度异常下降
            if self._detect_confidence_collapse(item):
                errors.append(self._create_error_case(
                    item, 'confidence_collapse',
                    f"置信度从{item.get('initial_confidence', 0.8):.2f}下降至{item.get('confidence', 0.3):.2f}"
                ))
            
            # 模式2：高频错误反馈
            if item.get('error_count', 0) > 3:
                errors.append(self._create_error_case(
                    item, 'frequent_errors',
                    f"被指正{item.get('error_count', 0)}次"
                ))
            
            # 模式3：与其他知识的不一致
            inconsistent_items = self._find_inconsistencies(item)
            if inconsistent_items:
                errors.append(self._create_error_case(
                    item, 'inconsistency',
                    f"与{len(inconsistent_items)}条其他知识不一致"
                ))
            
            # 模式4：内容异常（长度、格式等）
            if self._detect_anomalous_content(item):
                errors.append(self._create_error_case(
                    item, 'content_anomaly',
                    "内容格式或结构异常"
                ))
        
        return errors
    
    def _detect_confidence_collapse(self, item: Dict) -> bool:
        """检测置信度崩溃"""
        current = item.get('confidence', 0.5)
        initial = item.get('initial_confidence', current)
        
        if initial == 0:
            return False
        
        drop_rate = (initial - current) / initial
        return drop_rate > self.thresholds['confidence_drop_threshold']
    
    def _find_inconsistencies(self, item: Dict) -> List[str]:
        """查找不一致的知识"""
        # 简化实现：基于关键词冲突
        inconsistencies = []
        
        # 从数据库中获取相关知识
        try:
            db = DatabaseManager.get(self.db_path)
            results = db.query('''
                SELECT id, answer, confidence 
                FROM knowledge_confidence 
                WHERE knowledge_id != ?
            ''', (item.get('id', ''),))

            
            for result in results:
                # 简化的一致性检查：长度差异过大提示可能不一致
                if abs(len(item.get('answer', '')) - len(result[1])) > 100:
                    inconsistencies.append(result[0])
                    
        except Exception as e:
            logger.debug(f"一致性检查失败: {e}")
        
        return inconsistencies
    
    def _detect_anomalous_content(self, item: Dict) -> bool:
        """检测异常内容"""
        answer = item.get('answer', '')
        
        # 异常模式
        anomalies = [
            len(answer) < 10,  # 太短
            'error' in answer.lower() and 'exception' in answer.lower(),  # 包含错误信息
            len(answer.split()) > 500,  # 太长
        ]
        
        return any(anomalies)
    
    def _create_error_case(self, item: Dict, error_type: str, description: str) -> ErrorCase:
        """创建错误案例"""
        import hashlib
        
        error_id = hashlib.md5(
            f"{item.get('id', '')}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        return ErrorCase(
            id=error_id,
            problem=item.get('question', ''),
            wrong_answer=item.get('answer', ''),
            correct_answer=None,
            error_type=error_type,
            detected_at=datetime.now().isoformat(),
            resolved_at=None,
            resolution_status='pending',
            reflection=description
        )
    
    def perform_hypothesis_check(self, new_knowledge: Dict, existing_knowledge: List[Dict]) -> Dict:
        """
        假设检验：验证新知识是否可靠
        
        通过对比已有知识进行一致性验证
        """
        result = {
            'passed': True,
            'checks': [],
            'warnings': [],
            'confidence_adjustment': 0.0
        }
        
        # 检查1：与已有知识的一致性
        inconsistencies = self._find_inconsistencies(new_knowledge)
        if inconsistencies:
            result['checks'].append({
                'name': '一致性检查',
                'passed': False,
                'details': f"与{len(inconsistencies)}条知识不一致"
            })
            result['confidence_adjustment'] -= 0.2 * len(inconsistencies)
            result['warnings'].append(f"与已有知识存在{len(inconsistencies)}处不一致")
        
        # 检查2：知识完整性
        completeness_score = self._check_completeness(new_knowledge)
        if completeness_score < 0.5:
            result['checks'].append({
                'name': '完整性检查',
                'passed': False,
                'details': f"完整度{completeness_score:.1%}"
            })
            result['confidence_adjustment'] -= 0.15
            result['warnings'].append("知识内容不完整")
        
        # 检查3：来源可靠性（如果有）
        source_score = self._assess_source_reliability(new_knowledge.get('source', ''))
        if source_score < 0.3:
            result['checks'].append({
                'name': '来源可信度检查',
                'passed': False,
                'details': f"来源可信度{source_score:.1%}"
            })
            result['confidence_adjustment'] -= 0.1
        
        # 综合判断
        result['passed'] = result['confidence_adjustment'] > -0.3
        
        # 置信度调整后，保证在0.1-0.95之间
        result['confidence_adjustment'] = max(-0.5, min(0.2, result['confidence_adjustment']))
        
        return result
    
    def _check_completeness(self, knowledge: Dict) -> float:
        """检查知识完整性"""
        score = 0.0
        content = knowledge.get('answer', '')
        
        # 长度评分
        if len(content) > 50:
            score += 0.3
        if len(content) > 200:
            score += 0.3
        
        # 结构评分（是否有分点、标题等）
        if '\n' in content:
            score += 0.2
        if any(marker in content for marker in ['•', '-', '1.', '2.', '首先', '其次']):
            score += 0.2
        
        return min(score, 1.0)
    
    def _assess_source_reliability(self, source: str) -> float:
        """评估来源可信度"""
        reliable_sources = {
            'official_documentation': 0.9,
            'known_manufacturer': 0.85,
            'academic_paper': 0.8,
            'technical_forum': 0.6,
            'blog': 0.5,
            'external_search': 0.4,
            'unknown': 0.2
        }
        
        for key, score in reliable_sources.items():
            if key in source.lower():
                return score
        
        return 0.3
    
    def record_reflection(self, error_case: ErrorCase, resolution: str):
        """记录反思结果"""
        
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            UPDATE error_cases
            SET correct_answer = ?, resolved_at = ?, resolution_status = ?, reflection = ?
            WHERE id = ?
        ''', (
            error_case.correct_answer,
            datetime.now().isoformat(),
            'resolved',
            f"原错误: {error_case.reflection}\n处理方式: {resolution}",
            error_case.id
        ), commit=True)

        
        logger.info(f"✅ 反思已记录: {error_case.id[:8]}...")


# ==================== 第1层：认知闭环管理器 ====================

class CognitiveLoopManager:
    """
    认知闭环管理器
    管理完整的 学习 → 验证 → 反思 → 修正 循环
    """
    
    def __init__(self, reflection_engine: DataDrivenReflectionEngine):
        self.reflection_engine = reflection_engine
        self.db_path = "data/cognitive_loop.db"
        self._init_database()
        
        # 闭环状态
        self.loop_status = {
            'current_phase': 'idle',
            'last_completed_cycle': None,
            'cycle_count': 0,
            'pending_verifications': []
        }
        
        logger.info("🔄 认知闭环管理器已初始化")
    
    def _init_database(self):
        """初始化闭环数据库"""
        
        Path(self.db_path).parent.mkdir(exist_ok=True)
        
        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS cognitive_cycles (
                cycle_id TEXT PRIMARY KEY,
                start_time TEXT,
                end_time TEXT,
                knowledge_learned INTEGER,
                errors_detected INTEGER,
                errors_resolved INTEGER,
                confidence_change REAL,
                status TEXT
            );
            CREATE TABLE IF NOT EXISTS verification_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                knowledge_id TEXT,
                question TEXT,
                answer TEXT,
                created_at TEXT,
                status TEXT,
                retry_count INTEGER
            )
        ''')

    
    def run_complete_cycle(self, new_knowledge: List[Dict]) -> Dict:
        """
        运行完整的认知闭环
        
        流程：学习 → 假设检验 → 存储 → 验证 → 反思 → 修正
        """
        
        cycle_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:12]
        start_time = datetime.now().isoformat()
        
        logger.info(f"🔄 认知闭环 #{self.loop_status['cycle_count'] + 1} 开始")
        
        # Phase 1: 假设检验（学习后立即执行）
        logger.info("  📋 Phase 1: 假设检验...")
        verified_knowledge = []
        pending_verification = []
        
        for item in new_knowledge:
            # 获取已有知识进行对比
            existing = self._get_existing_knowledge(item.get('question', ''))
            
            # 执行假设检验
            check_result = self.reflection_engine.perform_hypothesis_check(item, existing)
            
            if check_result['passed']:
                # 通过检验，可以存储
                item['confidence'] = min(0.9, 
                    0.6 + check_result['confidence_adjustment'])
                verified_knowledge.append(item)
            else:
                # 未通过，加入待验证队列
                pending_verification.append({
                    'knowledge': item,
                    'checks': check_result['checks'],
                    'warnings': check_result['warnings']
                })
        
        logger.info(f"      ✅ 通过: {len(verified_knowledge)}, 待验证: {len(pending_verification)}")
        
        # Phase 2: 存储已通过的知识
        logger.info("  💾 Phase 2: 存储知识...")
        for item in verified_knowledge:
            self._store_verified_knowledge(item)
        
        # Phase 3: 错误感知（检查已有知识中的错误）
        logger.info("  🔍 Phase 3: 错误感知...")
        all_knowledge = self._get_all_knowledge()
        detected_errors = self.reflection_engine.detect_errors(all_knowledge)
        
        logger.info(f"      发现 {len(detected_errors)} 个潜在错误")
        
        # Phase 4: 处理待验证项
        if pending_verification:
            logger.info("  ⏳ Phase 4: 处理待验证项...")
            for pv in pending_verification:
                # 加入验证队列
                self._add_to_verification_queue(pv)
        
        # Phase 5: 反思
        logger.info("  🤔 Phase 5: 执行反思...")
        if detected_errors:
            self._perform_reflection(detected_errors)
        
        # 更新循环状态
        self.loop_status['cycle_count'] += 1
        self.loop_status['last_completed_cycle'] = datetime.now().isoformat()
        
        # 记录循环
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            INSERT INTO cognitive_cycles 
            (cycle_id, start_time, end_time, knowledge_learned, errors_detected, errors_resolved, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            cycle_id,
            start_time,
            datetime.now().isoformat(),
            len(verified_knowledge),
            len(detected_errors),
            0,
            'completed'
        ), commit=True)

        
        return {
            'cycle_id': cycle_id,
            'knowledge_learned': len(verified_knowledge),
            'pending_verification': len(pending_verification),
            'errors_detected': len(detected_errors),
            'status': 'completed'
        }
    
    def _get_existing_knowledge(self, question: str) -> List[Dict]:
        """从主系统知识库获取已有知识"""
        try:
            db = DatabaseManager.get("data/knowledge_store.db")
            rows = db.query('''
                SELECT id, question, answer, quality_score as confidence
                FROM knowledge_items
                WHERE question LIKE ?
                ORDER BY quality_score DESC
                LIMIT 10
            ''', (f'%{question[:30]}%',))
            results = [dict(row) for row in rows]
            return results
        except Exception as e:
            logger.debug(f"获取已有知识失败: {e}")
            return []
    
    def _get_all_knowledge(self) -> List[Dict]:
        """从主系统知识库获取所有知识"""
        try:
            db = DatabaseManager.get("data/knowledge_store.db")
            rows = db.query('''
                SELECT id, question, answer, quality_score as confidence, 
                       source, created_at
                FROM knowledge_items
                ORDER BY created_at DESC
                LIMIT 100
            ''')
            results = [dict(row) for row in rows]
            return results
        except Exception as e:
            logger.debug(f"获取所有知识失败: {e}")
            return []
    
    def _store_verified_knowledge(self, item: Dict):
        """存储通过验证的知识到主系统知识库"""
        try:
            db = DatabaseManager.get("data/knowledge_store.db")
            
            question_hash = hashlib.md5(item.get('question', '').lower().encode()).hexdigest()
            
            db.execute('''
                INSERT OR REPLACE INTO knowledge_items 
                (id, question, answer, source, knowledge_type, quality_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                question_hash,
                item.get('question', ''),
                item.get('answer', ''),
                item.get('source', 'reflection'),
                item.get('knowledge_type', 'learned'),
                item.get('confidence', 0.7),
                datetime.now().isoformat()
            ), commit=True)

            logger.debug(f"✓ 知识已存储: {item.get('question', '')[:30]}...")
        except Exception as e:
            logger.warning(f"存储知识失败: {e}")
    
    def _add_to_verification_queue(self, pending_item: Dict):
        """添加到验证队列"""
        try:
            knowledge = pending_item.get('knowledge', {})
            
            db = DatabaseManager.get(self.db_path)
            db.execute('''
                INSERT INTO verification_queue 
                (knowledge_id, question, answer, created_at, status, retry_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                hashlib.md5(knowledge.get('question', '').encode()).hexdigest()[:12],
                knowledge.get('question', ''),
                knowledge.get('answer', ''),
                datetime.now().isoformat(),
                'pending',
                0
            ), commit=True)

            logger.info(f"  ✓ 已加入验证队列: {knowledge.get('question', '')[:30]}...")
        except Exception as e:
            logger.warning(f"添加验证队列失败: {e}")
    
    def _perform_reflection(self, errors: List[ErrorCase]):
        """执行反思"""
        for error in errors:
            # 记录反思
            self.reflection_engine.record_reflection(
                error,
                f"通过数据驱动反思发现: {error.reflection}"
            )
            
            # 根据错误类型触发不同的修正策略
            if error.error_type == 'confidence_collapse':
                # 置信度崩溃 → 重新学习该知识
                self._trigger_relearning(error)
            elif error.error_type == 'inconsistency':
                # 不一致 → 标记冲突
                self._mark_conflict(error)
            elif error.error_type == 'frequent_errors':
                # 频繁错误 → 高优先级修正
                self._prioritize_correction(error)
    
    def _trigger_relearning(self, error: ErrorCase):
        """触发重新学习"""
        logger.warning(f"  🔄 触发重新学习: {error.problem[:50]}...")
        
        try:
            from core.external_learner import external_learner
            
            result = external_learner.learn_and_integrate(
                user_input=error.problem,
                context=f"置信度崩溃，需要重新学习",
                trigger_reason="confidence_collapse"
            )
            
            if result.get("saved_count", 0) > 0:
                logger.info(f"    ✅ 重新学习成功，获取{result['saved_count']}条新知识")
        except Exception as e:
            logger.debug(f"重新学习失败: {e}")
    
    def _mark_conflict(self, error: ErrorCase):
        """标记冲突"""
        logger.warning(f"  ⚠️ 标记冲突: {error.problem[:50]}...")
        
        try:
            db = DatabaseManager.get(self.db_path)
            db.executescript('''
                CREATE TABLE IF NOT EXISTS knowledge_conflicts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_id TEXT,
                    problem TEXT,
                    detected_at TEXT,
                    resolution_status TEXT,
                    resolution TEXT
                )
            ''')
            db.execute('''
                INSERT INTO knowledge_conflicts 
                (error_id, problem, detected_at, resolution_status)
                VALUES (?, ?, ?, ?)
            ''', (
                error.id,
                error.problem,
                datetime.now().isoformat(),
                'pending'
            ), commit=True)

        except Exception as e:
            logger.debug(f"标记冲突失败: {e}")
    
    def _prioritize_correction(self, error: ErrorCase):
        """高优先级修正"""
        logger.warning(f"  🚨 高优先级修正: {error.problem[:50]}...")
        
        try:
            db = DatabaseManager.get(self.db_path)
            db.executescript('''
                CREATE TABLE IF NOT EXISTS high_priority_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    error_id TEXT,
                    problem TEXT,
                    wrong_answer TEXT,
                    priority INTEGER,
                    created_at TEXT,
                    status TEXT
                )
            ''')
            db.execute('''
                INSERT INTO high_priority_corrections 
                (error_id, problem, wrong_answer, priority, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                error.id,
                error.problem,
                error.wrong_answer,
                10,
                datetime.now().isoformat(),
                'pending'
            ), commit=True)

            
            from core.external_learner import external_learner
            external_learner.learn_and_integrate(
                user_input=error.problem,
                context=f"频繁错误，需要正确答案",
                trigger_reason="frequent_errors"
            )
        except Exception as e:
            logger.debug(f"高优先级修正失败: {e}")


# ==================== 第2层：元认知监控器 ====================

class MetacognitionMonitor:
    """
    元认知监控器
    监控系统自身表现，动态调整行为
    """
    
    def __init__(self, db_path: str = "data/metacognition.db"):
        self.db_path = db_path
        self._init_database()
        
        # 系统表现指标
        self.metrics = {
            'knowledge_quality': [],
            'error_rate': [],
            'learning_efficiency': [],
            'confidence_trend': [],
            'adaptation_speed': []
        }
        
        # 警报状态
        self.alerts = []
        
        logger.info("📊 元认知监控器已初始化")
    
    def _init_database(self):
        """初始化元认知数据库"""
        
        Path(self.db_path).parent.mkdir(exist_ok=True)
        
        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                metric_type TEXT,
                value REAL,
                context TEXT
            );
            CREATE TABLE IF NOT EXISTS behavior_adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                adjustment_type TEXT,
                previous_value REAL,
                new_value REAL,
                reason TEXT,
                effectiveness REAL
            )
        ''')

    
    def monitor_and_adjust(self, system_state: Dict) -> Dict:
        """
        监控系统状态并自动调整
        
        核心：通过检测系统表现异常，触发自我调整
        """
        
        adjustments = []
        
        # 1. 监控错误率
        error_rate = system_state.get('error_rate', 0)
        if error_rate > 0.15:  # 超过15%
            adjustments.append({
                'type': 'increase_verification',
                'reason': f'错误率过高: {error_rate:.1%}',
                'action': '强化校验层'
            })
        
        # 2. 监控学习效率
        learning_efficiency = system_state.get('learning_efficiency', 0.5)
        if learning_efficiency < 0.3:
            adjustments.append({
                'type': 'adjust_learning',
                'reason': f'学习效率低: {learning_efficiency:.1%}',
                'action': '调整学习策略'
            })
        
        # 3. 监控置信度趋势
        confidence_trend = system_state.get('confidence_trend', 0)
        if confidence_trend < -0.1:  # 持续下降
            adjustments.append({
                'type': 'review_knowledge',
                'reason': f'置信度持续下降: {confidence_trend:.1%}',
                'action': '审查知识质量'
            })
        
        # 4. 监控适应速度
        adaptation_speed = system_state.get('adaptation_speed', 0)
        if adaptation_speed < 0.1:
            adjustments.append({
                'type': 'accelerate_evolution',
                'reason': f'适应速度慢: {adaptation_speed:.2f}',
                'action': '加速基因演化'
            })
        
        # 记录调整
        for adj in adjustments:
            self._record_adjustment(adj)
        
        # 更新指标
        self._update_metrics(system_state)
        
        return {
            'adjustments': adjustments,
            'system_health': self._assess_health(),
            'recommendations': self._generate_recommendations(adjustments)
        }
    
    def _record_adjustment(self, adjustment: Dict):
        """记录行为调整"""
        
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            INSERT INTO behavior_adjustments 
            (timestamp, adjustment_type, reason)
            VALUES (?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            adjustment['type'],
            adjustment['reason']
        ), commit=True)

    
    def _update_metrics(self, system_state: Dict):
        """更新系统指标"""
        
        for key, value in system_state.items():
            if key in self.metrics:
                self.metrics[key].append(value)
                # 保持最近100个数据点
                if len(self.metrics[key]) > 100:
                    self.metrics[key] = self.metrics[key][-100:]
    
    def _assess_health(self) -> str:
        """评估系统健康状态"""
        
        if not self.metrics['error_rate']:
            return 'unknown'
        
        avg_error = sum(self.metrics['error_rate'][-10:]) / 10
        
        if avg_error < 0.05:
            return 'healthy'
        elif avg_error < 0.15:
            return 'moderate'
        else:
            return 'degraded'
    
    def _generate_recommendations(self, adjustments: List[Dict]) -> List[str]:
        """生成建议"""
        
        recommendations = []
        
        for adj in adjustments:
            if adj['type'] == 'increase_verification':
                recommendations.append("加强校验层：在输出前增加2轮自我质疑")
            elif adj['type'] == 'adjust_learning':
                recommendations.append("优化学习策略：增加外部搜索的深度和广度")
            elif adj['type'] == 'review_knowledge':
                recommendations.append("审查知识库：对低置信度知识进行重新验证")
            elif adj['type'] == 'accelerate_evolution':
                recommendations.append("加速进化：缩短基因演化周期，增加变异率")
        
        return recommendations


# ==================== 第3层：进化参数自适应器 ====================

class AdaptiveEvolutionController:
    """
    进化参数自适应器
    根据系统表现动态调整进化参数
    """
    
    def __init__(self):
        # 可调参数
        self.params = {
            'learning_rate': 0.3,
            'verification_strictness': 0.7,
            'evolution_speed': 0.5,
            'mutation_rate': 0.05,
            'memory_retention': 0.8,
            'exploration_ratio': 0.2
        }
        
        # 参数历史
        self.param_history = []
        self.performance_history = []
        
        logger.info("🧬 进化参数自适应器已初始化")
    
    def adjust_params(self, performance_feedback: Dict) -> Dict:
        """
        根据性能反馈调整参数
        
        核心：当系统表现偏离预期时，自动调整参数
        """
        
        changes = {}
        
        # 根据错误率调整验证严格度
        error_rate = performance_feedback.get('error_rate', 0)
        if error_rate > 0.15:
            change = min(0.1, error_rate - 0.15)
            self.params['verification_strictness'] = min(1.0, 
                self.params['verification_strictness'] + change)
            changes['verification_strictness'] = change
        
        # 根据学习效率调整学习率
        learning_efficiency = performance_feedback.get('learning_efficiency', 0.5)
        if learning_efficiency < 0.3:
            self.params['learning_rate'] = min(0.8,
                self.params['learning_rate'] + 0.05)
            changes['learning_rate'] = 0.05
        
        # 根据适应速度调整进化速度
        adaptation_speed = performance_feedback.get('adaptation_speed', 0)
        if adaptation_speed < 0.1:
            self.params['evolution_speed'] = min(1.0,
                self.params['evolution_speed'] + 0.05)
            changes['evolution_speed'] = 0.05
        
        # 记录参数变化
        self.param_history.append({
            'timestamp': datetime.now().isoformat(),
            'params': self.params.copy(),
            'changes': changes,
            'reason': performance_feedback.get('reason', 'adaptive_adjustment')
        })
        
        return changes


# ==================== 整合：反思驱动的无模型进化 ====================

class ReflectiveModelFreeEvolution:
    """
    反思驱动的无模型进化系统
    整合了：反思引擎 + 认知闭环 + 元认知监控 + 自适应进化
    """
    
    def __init__(self):
        self.running = False
        self.evolution_thread = None
        
        # 核心组件
        self.reflection_engine = DataDrivenReflectionEngine()
        self.cognitive_loop = CognitiveLoopManager(self.reflection_engine)
        self.metacognition = MetacognitionMonitor()
        self.adaptive_controller = AdaptiveEvolutionController()
        
        # 统计
        self.stats = {
            'start_time': datetime.now().isoformat(),
            'cycles': 0,
            'errors_detected': 0,
            'errors_resolved': 0,
            'parameters_adjusted': 0,
            'reflections_performed': 0
        }
        
        logger.info("🧬 反思驱动的无模型进化系统已初始化")
        logger.info("  核心特征:")
        logger.info("    ✅ 数据驱动的反思引擎")
        logger.info("    ✅ 完整的认知闭环 (学习→验证→反思→修正)")
        logger.info("    ✅ 元认知监控与自我调整")
        logger.info("    ✅ 自适应进化参数")
    
    def run_evolution_cycle(self, new_knowledge: List[Dict] = None) -> Dict:
        """运行一次完整的进化周期"""
        new_knowledge = new_knowledge or []
        
        cycle_result = self.cognitive_loop.run_complete_cycle(new_knowledge)
        
        system_state = self._collect_system_state()
        
        monitor_result = self.metacognition.monitor_and_adjust(system_state)
        
        param_changes = self.adaptive_controller.adjust_params({
            'error_rate': system_state.get('error_rate', 0),
            'learning_efficiency': system_state.get('learning_efficiency', 0.5),
            'adaptation_speed': system_state.get('adaptation_speed', 0)
        })
        
        if param_changes:
            self._apply_evolution_to_main_system(param_changes)
        
        self.stats['cycles'] += 1
        self.stats['errors_detected'] += cycle_result.get('errors_detected', 0)
        self.stats['parameters_adjusted'] += len(param_changes)
        
        return {
            'cycle_result': cycle_result,
            'monitor_result': monitor_result,
            'param_changes': param_changes,
            'stats': self.stats
        }
    
    def _collect_system_state(self) -> Dict:
        """从主系统状态收集器获取系统状态"""
        try:
            from core.reporting.state_collector import get_state_collector
            collector = get_state_collector()
            snapshot = collector.get_snapshot()
            
            return {
                'error_rate': self._calculate_error_rate(),
                'learning_efficiency': self._calculate_learning_efficiency(),
                'confidence_trend': self._calculate_confidence_trend(),
                'adaptation_speed': self._calculate_adaptation_speed()
            }
        except Exception as e:
            logger.debug(f"收集系统状态失败: {e}")
            return {
                'error_rate': 0.1,
                'learning_efficiency': 0.4,
                'confidence_trend': 0.0,
                'adaptation_speed': 0.1
            }
    
    def _calculate_error_rate(self) -> float:
        """计算错误率"""
        try:
            db = DatabaseManager.get(self.reflection_engine.db_path)
            total_errors = db.query_one("SELECT COUNT(*) FROM error_cases")[0]
            resolved = db.query_one("SELECT COUNT(*) FROM error_cases WHERE resolution_status='resolved'")[0]
            
            return total_errors / max(resolved + 1, 1) * 0.1
        except:
            return 0.1
    
    def _calculate_learning_efficiency(self) -> float:
        """计算学习效率"""
        try:
            db = DatabaseManager.get("data/knowledge_store.db")
            result = db.query_one("SELECT AVG(quality_score) FROM knowledge_items")[0]
            return result if result else 0.5
        except:
            return 0.5
    
    def _calculate_confidence_trend(self) -> float:
        """计算置信度趋势"""
        try:
            db = DatabaseManager.get(self.reflection_engine.db_path)
            rows = db.query('''
                SELECT metric_value FROM metacognition_log
                WHERE metric_name='confidence'
                ORDER BY timestamp DESC
                LIMIT 10
            ''')
            values = [row[0] for row in rows]
            
            if len(values) >= 2:
                return values[-1] - values[0]
            return 0.0
        except:
            return 0.0
    
    def _calculate_adaptation_speed(self) -> float:
        """计算适应速度"""
        try:
            db = DatabaseManager.get(self.metacognition.db_path)
            adjustments = db.query_one('''
                SELECT COUNT(*) FROM behavior_adjustments
                WHERE timestamp > datetime('now', '-1 day')
            ''')[0]
            return min(1.0, adjustments / 10)
        except:
            return 0.1
    
    def _apply_evolution_to_main_system(self, changes: Dict):
        """将进化结果应用到主系统"""
        try:
            if 'learning_rate' in changes:
                from core.config.unified_config import get_config
                config = get_config()
                if hasattr(config, 'set'):
                    config.set('evolution.learning_rate', changes['learning_rate'])
            
            if 'verification_strictness' in changes:
                try:
                    from core.layers.l4_validation import get_l4_validation
                    l4 = get_l4_validation()
                    if hasattr(l4, 'thresholds'):
                        l4.thresholds['pass'] = 0.7 + (changes['verification_strictness'] - 0.7) * 0.2
                except:
                    pass
            
            logger.info(f"✅ 进化参数已应用: {changes}")
        except Exception as e:
            logger.debug(f"应用进化结果失败: {e}")
    
    def get_status(self) -> Dict:
        """获取系统状态"""
        return {
            'running': self.running,
            'stats': self.stats,
            'params': self.adaptive_controller.params,
            'metrics': self.metacognition.metrics
        }


# ==================== 全局实例 ====================

reflective_evolution = ReflectiveModelFreeEvolution()