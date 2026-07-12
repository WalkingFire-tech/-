"""
主动学习调度器 - 置信度驱动提问与用户确认
当系统不确定时主动向用户提问,收集正确信息
"""
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from loguru import logger
from infrastructure.event_bus import bus
from infrastructure.config_manager import config
from infrastructure.database_manager import DatabaseManager


@dataclass
class ClarificationQuestion:
    """澄清问题"""
    question_id: str
    question: str
    context: Dict
    options: List[str]
    priority: int
    timestamp: str


class ActiveLearner:
    """主动学习调度器"""
    
    def __init__(self, adapters: dict):
        self.adapters = adapters
        self.pending_questions: Dict[str, ClarificationQuestion] = {}
        self.confidence_threshold = config.get("active_learning.confidence_threshold", 0.6)
        self.max_pending = config.get("active_learning.max_pending_questions", 5)
        
        logger.info("主动学习调度器初始化完成")
    
    def should_ask_user(self, intent_type: str, confidence: float,
                       context: Dict) -> bool:
        """判断是否应该向用户提问"""
        
        if confidence < self.confidence_threshold:
            return True
        
        if intent_type == "unknown" or confidence < 0.4:
            return True
        
        failure_count = context.get("recent_failures", 0)
        if failure_count >= 2:
            return True
        
        if len(self.pending_questions) >= self.max_pending:
            return False
        
        return False
    
    def generate_clarification(self, user_input: str, intent_type: str,
                              confidence: float, context: Dict = None) -> Optional[ClarificationQuestion]:
        """生成澄清问题"""
        
        if not self.should_ask_user(intent_type, confidence, context or {}):
            return None
        
        question_id = f"q_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        if confidence < 0.4:
            question = "抱歉,我不太理解您的需求。能否详细描述一下您想要做什么?"
            options = ["重新描述", "取消"]
        
        elif intent_type == "code" and confidence < 0.7:
            question = "您是希望我帮您生成代码,还是解释某段代码?"
            options = ["生成代码", "解释代码", "优化代码", "其他"]
        
        elif intent_type == "question" and confidence < 0.7:
            question = "您是希望获得详细解释,还是快速回答?"
            options = ["详细解释", "快速回答", "举例说明", "其他"]
        
        elif intent_type == "document" and confidence < 0.7:
            question = "您希望我对这份文档做什么?"
            options = ["总结摘要", "提取关键信息", "分析结构", "其他"]
        
        else:
            light_llm = self._get_light_llm()
            if light_llm:
                question, options = self._llm_generate_question(
                    light_llm, user_input, intent_type, confidence
                )
            else:
                question = f"我对您的需求理解置信度为{confidence:.0%},是否正确识别为【{intent_type}】任务?"
                options = ["正确", "错误-请重新识别", "跳过"]
        
        clarification = ClarificationQuestion(
            question_id=question_id,
            question=question,
            context={
                "user_input": user_input,
                "intent_type": intent_type,
                "confidence": confidence
            },
            options=options,
            priority=1 if confidence < 0.4 else 2,
            timestamp=datetime.now().isoformat()
        )
        
        self.pending_questions[question_id] = clarification
        
        bus.publish("clarification_needed", {
            "question_id": question_id,
            "question": question,
            "options": options
        })
        
        logger.info(f"生成澄清问题: {question_id}")
        
        return clarification
    
    def handle_user_response(self, question_id: str, response: str,
                            user_input: str) -> Dict:
        """处理用户响应"""
        
        if question_id not in self.pending_questions:
            logger.warning(f"未知问题ID: {question_id}")
            return {"success": False, "error": "未知问题"}
        
        clarification = self.pending_questions[question_id]
        
        del self.pending_questions[question_id]
        
        learning_data = self._extract_learning_data(
            clarification, response, user_input
        )
        
        if learning_data:
            self._save_learning_data(learning_data)
        
        bus.publish("clarification_resolved", {
            "question_id": question_id,
            "response": response,
            "learning_data": learning_data
        })
        
        logger.info(f"用户响应已处理: {question_id} -> {response}")
        
        return {
            "success": True,
            "learning_data": learning_data,
            "action": learning_data.get("action", "continue")
        }
    
    def _extract_learning_data(self, clarification: ClarificationQuestion,
                               response: str, user_input: str) -> Optional[Dict]:
        """从用户响应中提取学习数据"""
        
        context = clarification.context
        original_intent = context.get("intent_type")
        original_confidence = context.get("confidence")
        
        if response == "正确":
            return {
                "type": "confirmation",
                "intent_type": original_intent,
                "user_input": user_input,
                "action": "proceed",
                "confidence_boost": 0.2
            }
        
        elif "重新" in response or "错误" in response:
            return {
                "type": "correction",
                "original_intent": original_intent,
                "user_input": user_input,
                "action": "reparse",
                "suggested_intent": self._infer_intent_from_response(response)
            }
        
        elif response in ["生成代码", "解释代码", "优化代码"]:
            return {
                "type": "refinement",
                "intent_type": "code",
                "sub_type": response,
                "user_input": user_input,
                "action": "proceed"
            }
        
        elif response in ["详细解释", "快速回答", "举例说明"]:
            return {
                "type": "refinement",
                "intent_type": "question",
                "sub_type": response,
                "user_input": user_input,
                "action": "proceed"
            }
        
        else:
            return {
                "type": "general",
                "response": response,
                "user_input": user_input,
                "action": "continue"
            }
    
    def _infer_intent_from_response(self, response: str) -> str:
        """从用户响应推断正确意图"""
        
        if "代码" in response:
            return "code"
        elif "问题" in response or "解释" in response:
            return "question"
        elif "文档" in response:
            return "document"
        elif "计算" in response:
            return "calculation"
        else:
            return "chat"
    
    def _save_learning_data(self, data: Dict):
        """保存学习数据到规则库"""
        db_path = config.get("learning_rules.db_path", "data/learning_rules.db")
        
        try:
            db = DatabaseManager.get(db_path)
            if data["type"] == "correction":
                escaped_input = data['user_input'][:30].replace("'", "''")
                condition = f"raw_input LIKE '%{escaped_input}%'"
                action = f"correct_intent:{data.get('suggested_intent', 'chat')}"
                
                db.execute('''
                    INSERT INTO learning_rules
                    (condition, action, priority, created_at, status, source)
                    VALUES (?, ?, 5, ?, 'pending', 'user_correction')
                ''', (condition, action, datetime.now().isoformat()), commit=True)
            
            elif data["type"] == "confirmation":
                pass
            
            logger.debug(f"学习数据已保存: {data['type']}")
        
        except Exception as e:
            logger.error(f"保存学习数据失败: {e}")
    
    def _get_light_llm(self):
        """获取轻量LLM"""
        for model_name in ["qwen2.5-coder:1.5b", "mindchat"]:
            if model_name in self.adapters:
                return self.adapters[model_name]
        return None
    
    def _llm_generate_question(self, llm, user_input: str, 
                               intent_type: str, confidence: float) -> Tuple[str, List[str]]:
        """使用LLM生成澄清问题"""
        
        prompt = f"""用户输入: "{user_input}"
系统识别意图: {intent_type} (置信度: {confidence:.0%})

请生成一个澄清问题和3-4个选项,帮助理解用户真实需求。

输出JSON格式:
{{
  "question": "问题内容",
  "options": ["选项1", "选项2", "选项3"]
}}

只输出JSON,不要解释。"""

        try:
            response = llm.generate(prompt, task_type="clarification")
            
            if isinstance(response, tuple):
                response = response[0]
            
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return data["question"], data["options"]
        
        except Exception as e:
            logger.warning(f"LLM生成问题失败: {e}")
        
        return f"我对您的需求理解置信度为{confidence:.0%},是否正确?", ["正确", "错误", "跳过"]
    
    def get_pending_questions(self) -> List[ClarificationQuestion]:
        """获取待处理问题"""
        return sorted(
            self.pending_questions.values(),
            key=lambda q: q.priority,
            reverse=True
        )
    
    def clear_expired_questions(self, max_age_minutes: int = 5):
        """清理过期问题"""
        from datetime import timedelta
        
        threshold = datetime.now() - timedelta(minutes=max_age_minutes)
        
        expired = [
            qid for qid, q in self.pending_questions.items()
            if datetime.fromisoformat(q.timestamp) < threshold
        ]
        
        for qid in expired:
            del self.pending_questions[qid]
        
        if expired:
            logger.info(f"清理{len(expired)}个过期问题")


active_learner = ActiveLearner({})
