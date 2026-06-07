"""
主动学习调度器 - 元控制层核心组件
当系统置信度低时主动向用户提问,加速学习
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger
from infrastructure.event_bus import bus
from infrastructure.config_manager import config


class ActiveLearner:
    """主动学习调度器"""
    
    def __init__(self):
        self.questions_file = Path("active_learning_questions.json")
        self.questions = self._load_questions()
        self.min_confidence = config.get("active_learning.min_confidence", 0.6)
        self.min_experience_count = config.get("active_learning.min_experience_count", 5)
        self.max_pending_questions = config.get("active_learning.max_pending_questions", 10)
        self.question_count = 0
    
    def _load_questions(self) -> List[Dict]:
        """加载待处理问题"""
        if self.questions_file.exists():
            try:
                with open(self.questions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载问题失败: {e}")
        return []
    
    def _save_questions(self):
        """保存问题"""
        try:
            with open(self.questions_file, 'w', encoding='utf-8') as f:
                json.dump(self.questions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存问题失败: {e}")
    
    def should_ask_question(self, context: Dict) -> bool:
        """判断是否应该主动提问"""
        # 检查条件
        confidence = context.get("confidence", 1.0)
        experience_count = context.get("experience_count", 0)
        task_type = context.get("task_type")
        
        # 条件1: 置信度低
        if confidence < self.min_confidence:
            logger.info(f"置信度低({confidence:.2f}),触发主动学习")
            return True
        
        # 条件2: 经验不足
        if experience_count < self.min_experience_count:
            logger.info(f"经验不足({experience_count}),触发主动学习")
            return True
        
        # 条件3: 新任务类型
        if task_type and not self._has_enough_experience(task_type):
            logger.info(f"新任务类型({task_type}),触发主动学习")
            return True
        
        return False
    
    def _has_enough_experience(self, task_type: str) -> bool:
        """检查是否有足够经验"""
        # 从经验池查询(简化实现)
        experience_file = Path("experience_pool.db")
        if not experience_file.exists():
            return False
        
        import sqlite3
        try:
            with sqlite3.connect(experience_file) as conn:
                cur = conn.execute(
                    'SELECT COUNT(*) FROM experiences WHERE intent_type = ?',
                    (task_type,)
                )
                count = cur.fetchone()[0]
                return count >= self.min_experience_count
        except:
            return False
    
    def generate_question(self, context: Dict) -> Optional[Dict]:
        """生成主动学习问题"""
        if not self.should_ask_question(context):
            return None
        
        # 检查待处理问题数量
        pending = [q for q in self.questions if q.get("status") == "pending"]
        if len(pending) >= self.max_pending_questions:
            logger.warning("待处理问题过多,暂停生成新问题")
            return None
        
        task_type = context.get("task_type", "unknown")
        user_input = context.get("user_input", "")
        planned_action = context.get("planned_action", "")
        confidence = context.get("confidence", 0.0)
        
        # 生成问题
        question = {
            "id": f"q_{int(time.time())}_{self.question_count}",
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            "context": context,
            "question_type": self._determine_question_type(context),
            "question": self._format_question(task_type, user_input, planned_action, confidence),
            "options": self._generate_options(task_type)
        }
        
        self.questions.append(question)
        self.question_count += 1
        self._save_questions()
        
        logger.info(f"生成主动学习问题: {question['id']}")
        
        # 发布事件
        bus.publish("active_learning_question", question)
        
        return question
    
    def _determine_question_type(self, context: Dict) -> str:
        """确定问题类型"""
        confidence = context.get("confidence", 1.0)
        experience_count = context.get("experience_count", 0)
        
        if confidence < 0.5:
            return "low_confidence"
        elif experience_count < 3:
            return "new_task_type"
        else:
            return "confirmation"
    
    def _format_question(self, task_type: str, user_input: str, 
                        planned_action: str, confidence: float) -> str:
        """格式化问题"""
        if confidence < 0.5:
            return (
                f"我对这个任务不太确定(置信度: {confidence:.2f})。\n"
                f"用户输入: {user_input[:100]}\n"
                f"我计划: {planned_action[:100]}\n"
                f"这样做对吗?如果不对,请告诉我正确的方法。"
            )
        else:
            return (
                f"这是一个{task_type}类型的任务。\n"
                f"我计划: {planned_action[:100]}\n"
                f"请确认是否正确?"
            )
    
    def _generate_options(self, task_type: str) -> List[Dict]:
        """生成选项"""
        base_options = [
            {"label": "正确", "value": "correct"},
            {"label": "需要调整", "value": "adjust"},
            {"label": "完全错误", "value": "wrong"}
        ]
        
        # 根据任务类型添加特定选项
        if task_type == "code":
            base_options.append({"label": "应该用其他模型", "value": "change_model"})
        elif task_type == "question":
            base_options.append({"label": "需要搜索", "value": "need_search"})
        
        return base_options
    
    def process_answer(self, question_id: str, answer: str, details: str = None):
        """处理用户回答"""
        # 查找问题
        question = None
        for q in self.questions:
            if q["id"] == question_id:
                question = q
                break
        
        if not question:
            logger.warning(f"未找到问题: {question_id}")
            return
        
        # 更新问题状态
        question["status"] = "answered"
        question["answer"] = answer
        question["answer_details"] = details
        question["answer_timestamp"] = datetime.now().isoformat()
        
        self._save_questions()
        
        # 根据回答采取行动
        self._apply_learning(question, answer, details)
        
        logger.info(f"处理回答: {question_id} -> {answer}")
        
        # 发布事件
        bus.publish("active_learning_answer", {
            "question_id": question_id,
            "answer": answer,
            "details": details
        })
    
    def _apply_learning(self, question: Dict, answer: str, details: str):
        """应用学习结果"""
        context = question.get("context", {})
        task_type = context.get("task_type")
        
        if answer == "correct":
            # 标记为成功经验
            self._record_success(context)
        
        elif answer == "wrong":
            # 记录失败并学习
            self._record_failure(context, details)
            
            # 如果有详细说明,更新修正库
            if details:
                self._update_correction_db(task_type, details)
        
        elif answer == "adjust":
            # 记录调整建议
            if details:
                self._record_adjustment(task_type, details)
        
        elif answer == "change_model":
            # 记录模型切换建议
            self._record_model_preference(context, details)
    
    def _record_success(self, context: Dict):
        """记录成功经验"""
        logger.info(f"记录成功经验: {context.get('task_type')}")
        # 可以更新经验池或统计库
    
    def _record_failure(self, context: Dict, details: str):
        """记录失败经验"""
        logger.warning(f"记录失败经验: {context.get('task_type')}, 原因: {details}")
        # 更新修正数据库
    
    def _update_correction_db(self, task_type: str, correct_approach: str):
        """更新修正数据库"""
        correction_file = Path("plan_corrections.db")
        import sqlite3
        
        try:
            with sqlite3.connect(correction_file) as conn:
                conn.execute('''
                    INSERT INTO plan_corrections 
                    (intent_type, correct_approach, context, timestamp)
                    VALUES (?, ?, ?, datetime('now'))
                ''', (task_type, correct_approach, "active_learning"))
        except Exception as e:
            logger.error(f"更新修正库失败: {e}")
    
    def _record_adjustment(self, task_type: str, details: str):
        """记录调整建议"""
        adjustment_file = Path("learning_adjustments.json")
        adjustments = []
        
        if adjustment_file.exists():
            try:
                with open(adjustment_file, 'r', encoding='utf-8') as f:
                    adjustments = json.load(f)
            except:
                pass
        
        adjustments.append({
            "task_type": task_type,
            "adjustment": details,
            "timestamp": datetime.now().isoformat()
        })
        
        with open(adjustment_file, 'w', encoding='utf-8') as f:
            json.dump(adjustments, f, ensure_ascii=False, indent=2)
    
    def _record_model_preference(self, context: Dict, preferred_model: str):
        """记录模型偏好"""
        logger.info(f"记录模型偏好: {context.get('task_type')} -> {preferred_model}")
        # 可以更新统计库或路由配置
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        total = len(self.questions)
        pending = len([q for q in self.questions if q["status"] == "pending"])
        answered = len([q for q in self.questions if q["status"] == "answered"])
        
        # 按类型统计
        by_type = {}
        for q in self.questions:
            qtype = q.get("question_type", "unknown")
            by_type[qtype] = by_type.get(qtype, 0) + 1
        
        return {
            "total_questions": total,
            "pending": pending,
            "answered": answered,
            "by_type": by_type,
            "answer_rate": answered / total if total > 0 else 0
        }
    
    def cleanup_old_questions(self, days: int = 30):
        """清理旧问题"""
        cutoff = datetime.now() - timedelta(days=days)
        
        self.questions = [
            q for q in self.questions
            if datetime.fromisoformat(q["timestamp"]) > cutoff
        ]
        
        self._save_questions()
        logger.info(f"清理了{days}天前的旧问题")


from datetime import timedelta