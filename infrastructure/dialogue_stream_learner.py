"""
对话流学习器 - 实时在线学习系统
从每次对话中主动吸收养分，无需等待显式反馈
"""
import re
import time
import sqlite3
import threading
import json
from collections import deque
from typing import Dict, List, Optional, Tuple
from loguru import logger
from infrastructure.event_bus import bus


class SemanticShiftDetector:
    """语义漂移检测器 - 检测用户是否重复同一问题但换说法"""
    
    def __init__(self):
        self.recent_questions = deque(maxlen=20)
        self.similarity_threshold = 0.7
    
    def detect(self, user_input: str) -> Optional[Dict]:
        """检测语义漂移
        
        Returns:
            如果检测到漂移，返回 {'type': 'semantic_shift', 'previous': str, 'current': str}
        """
        current_time = time.time()
        
        for prev_q, prev_time in self.recent_questions:
            if current_time - prev_time > 300:
                continue
            
            similarity = self._calculate_similarity(prev_q, user_input)
            
            if similarity > self.similarity_threshold and prev_q != user_input:
                logger.info(f"检测到语义漂移: '{prev_q[:30]}' → '{user_input[:30]}' (相似度: {similarity:.2f})")
                return {
                    'type': 'semantic_shift',
                    'previous': prev_q,
                    'current': user_input,
                    'similarity': similarity
                }
        
        self.recent_questions.append((user_input, current_time))
        return None
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简化版：基于词重叠）"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)


class ImplicitNegationDetector:
    """隐式否定检测器 - 从用户措辞中检测不满"""
    
    def __init__(self):
        self.negation_patterns = [
            r"不太对",
            r"还是不对",
            r"不对[，。]",
            r"不是这样",
            r"错了",
            r"没.*理解",
            r"没.*明白",
            r"不准确",
            r"不自然",
            r"处理不了",
            r"你.*不懂",
            r"你.*不明白",
            r"我.*不想听",
            r"算了",
            r"算了[，。]",
        ]
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.negation_patterns]
    
    def detect(self, user_input: str) -> Optional[Dict]:
        """检测隐式否定
        
        Returns:
            如果检测到否定，返回 {'type': 'implicit_negation', 'text': str, 'pattern': str}
        """
        for pattern in self.compiled_patterns:
            match = pattern.search(user_input)
            if match:
                logger.info(f"检测到隐式否定: '{user_input[:50]}' (模式: {pattern.pattern})")
                return {
                    'type': 'implicit_negation',
                    'text': user_input,
                    'pattern': pattern.pattern,
                    'matched': match.group()
                }
        
        return None


class EmotionAnalyzer:
    """情绪分析器 - 推断用户满意度"""
    
    def __init__(self):
        self.negative_keywords = [
            "沮丧", "失望", "不满", "生气", "愤怒", "烦躁", "不耐烦",
            "无语", "崩溃", "绝望", "难过", "伤心", "焦虑", "担心"
        ]
        self.positive_keywords = [
            "满意", "开心", "高兴", "感谢", "谢谢", "很好", "不错",
            "完美", "棒", "厉害", "聪明", "有用", "有帮助"
        ]
    
    def analyze(self, user_input: str) -> Dict:
        """分析情绪
        
        Returns:
            {'emotion': str, 'score': float, 'confidence': float}
        """
        text_lower = user_input.lower()
        
        neg_count = sum(1 for kw in self.negative_keywords if kw in text_lower)
        pos_count = sum(1 for kw in self.positive_keywords if kw in text_lower)
        
        total = neg_count + pos_count
        if total == 0:
            return {
                'emotion': 'neutral',
                'score': 0.5,
                'confidence': 0.3
            }
        
        score = pos_count / total
        
        if score < 0.3:
            emotion = 'negative'
        elif score > 0.7:
            emotion = 'positive'
        else:
            emotion = 'neutral'
        
        return {
            'emotion': emotion,
            'score': score,
            'confidence': min(total * 0.2, 1.0)
        }


class CorrectionDetector:
    """修正检测器 - 检测用户明确纠正"""
    
    def __init__(self):
        self.correction_patterns = [
            r"不是.*应该是(.+)",
            r"不对[，。].*应该是(.+)",
            r"你记错了[，。].*是(.+)",
            r"错了[，。].*是(.+)",
            r"其实.*是(.+)",
            r"实际上.*是(.+)",
        ]
        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.correction_patterns]
    
    def detect(self, user_input: str) -> Optional[Dict]:
        """检测修正
        
        Returns:
            如果检测到修正，返回 {'type': 'correction', 'correct_content': str, 'original': str}
        """
        for pattern in self.compiled_patterns:
            match = pattern.search(user_input)
            if match:
                correct_content = match.group(1).strip()
                logger.info(f"检测到用户修正: '{correct_content}'")
                return {
                    'type': 'correction',
                    'correct_content': correct_content,
                    'original': user_input,
                    'pattern': pattern.pattern
                }
        
        return None


class DialogueStreamLearner:
    """对话流学习器 - 主控制器"""
    
    def __init__(self):
        self.semantic_detector = SemanticShiftDetector()
        self.negation_detector = ImplicitNegationDetector()
        self.emotion_analyzer = EmotionAnalyzer()
        self.correction_detector = CorrectionDetector()
        
        self.dialogue_window = deque(maxlen=50)
        self.recent_emotions = deque(maxlen=10)
        
        self._db_lock = threading.Lock()
        self._listeners_initialized = False
        
        self._setup_event_listeners()
        logger.info("对话流学习器已启动")
    
    def _setup_event_listeners(self):
        """设置事件监听"""
        if self._listeners_initialized:
            return
        
        bus.subscribe("intent_parsed", self._on_intent_parsed)
        bus.subscribe("plan_executed", self._on_plan_executed)
        self._listeners_initialized = True
    
    def _on_intent_parsed(self, intent):
        """意图解析事件处理"""
        self.dialogue_window.append({
            'type': 'user_input',
            'text': intent.raw_text,
            'intent_type': intent.type,
            'timestamp': time.time()
        })
        
        self._analyze_user_input(intent.raw_text)
    
    def _on_plan_executed(self, response):
        """计划执行事件处理"""
        self.dialogue_window.append({
            'type': 'system_response',
            'text': response if isinstance(response, str) else str(response),
            'timestamp': time.time()
        })
    
    def _analyze_user_input(self, user_input: str):
        """分析用户输入，检测学习机会"""
        
        # 1. 检测语义漂移
        shift = self.semantic_detector.detect(user_input)
        if shift:
            self._handle_semantic_shift(shift)
        
        # 2. 检测隐式否定
        negation = self.negation_detector.detect(user_input)
        if negation:
            self._handle_implicit_negation(negation)
        
        # 3. 检测修正
        correction = self.correction_detector.detect(user_input)
        if correction:
            self._handle_correction(correction)
        
        # 4. 情绪分析
        emotion = self.emotion_analyzer.analyze(user_input)
        self.recent_emotions.append(emotion)
        self._check_emotion_pattern()
    
    def _handle_semantic_shift(self, shift: Dict):
        """处理语义漂移 - 用户重复提问但换说法"""
        logger.warning(f"语义漂移检测: 用户可能对之前回答不满意")
        
        bus.publish("learning_opportunity", {
            'type': 'semantic_shift',
            'data': shift,
            'action': 'consider_clarification'
        })
    
    def _handle_implicit_negation(self, negation: Dict):
        """处理隐式否定 - 标记低质量交互"""
        try:
            with self._db_lock:
                with sqlite3.connect('data/experience_pool.db') as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        UPDATE experiences
                        SET quality_score = 20,
                            user_feedback = -1
                        WHERE id = (
                            SELECT id FROM experiences
                            ORDER BY timestamp DESC
                            LIMIT 1
                        )
                    """)
                    
                    conn.commit()
            
            logger.info("已标记最近交互为低质量（隐式否定）")
            
            bus.publish("learning_opportunity", {
                'type': 'implicit_negation',
                'data': negation,
                'action': 'trigger_induction'
            })
            
        except Exception as e:
            logger.error(f"处理隐式否定失败: {e}")
    
    def _handle_correction(self, correction: Dict):
        """处理用户修正 - 生成即时规则"""
        try:
            correct_content = correction['correct_content']
            
            safe_content = correct_content[:20].replace("'", "''").replace('"', '""')
            
            condition_data = json.dumps({
                "type": "text_contains",
                "content": correct_content[:20]
            }, ensure_ascii=False)
            
            with self._db_lock:
                with sqlite3.connect('data/learning_rules.db') as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        INSERT INTO learning_rules
                        (condition, action, priority, confidence, status, source, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        condition_data,
                        "prefer_context:user_correction",
                        5,
                        0.8,
                        'active',
                        'correction',
                        time.time()
                    ))
                    
                    conn.commit()
            
            logger.info(f"从用户修正生成规则: '{correct_content[:30]}'")
            
            bus.publish("learning_opportunity", {
                'type': 'correction',
                'data': correction,
                'action': 'rule_generated'
            })
            
        except Exception as e:
            logger.error(f"处理修正失败: {e}")
    
    def _check_emotion_pattern(self):
        """检查情绪模式 - 连续负面情绪触发反思"""
        if len(self.recent_emotions) < 3:
            return
        
        recent_three = list(self.recent_emotions)[-3:]
        negative_count = sum(1 for e in recent_three if e['emotion'] == 'negative')
        
        if negative_count >= 3:
            logger.warning("检测到连续负面情绪，触发反思")
            
            bus.publish("learning_opportunity", {
                'type': 'negative_emotion_pattern',
                'data': {
                    'emotions': recent_three,
                    'count': negative_count
                },
                'action': 'force_induction'
            })
    
    def get_dialogue_summary(self) -> Dict:
        """获取对话摘要"""
        return {
            'total_dialogues': len(self.dialogue_window),
            'recent_emotions': list(self.recent_emotions),
            'emotion_trend': self._calculate_emotion_trend()
        }
    
    def _calculate_emotion_trend(self) -> str:
        """计算情绪趋势"""
        if len(self.recent_emotions) < 2:
            return 'stable'
        
        scores = [e['score'] for e in self.recent_emotions]
        
        if scores[-1] > scores[-2] + 0.1:
            return 'improving'
        elif scores[-1] < scores[-2] - 0.1:
            return 'declining'
        else:
            return 'stable'


dialogue_learner = DialogueStreamLearner()