"""
联盟拓荒者主流程
集成所有已实现的模块，提供完整的交互体验
"""
import sys
import uuid
from typing import Optional, Dict, List
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# 导入所有模块
from infrastructure.versioned_fact_store import VersionedFactStore
from infrastructure.verification_loop import KnowledgeVerificationLoop
from infrastructure.user_correction_flow import UserCorrectionFlow
from infrastructure.interaction_data_collector import InteractionDataCollector
from infrastructure.question_matcher import QuestionMatcher

from core.decision_chain import DecisionChainManager
from core.learning_reflector import LearningReflector
from core.capability_gap_diagnoser import CapabilityGapDiagnoser
from core.self_reflection import SelfReflection
from core.teacher_interface import TeacherInterface
from core.methodology_extractor import MethodologyExtractor
from core.skill_tree import SkillTree, TaskScheduler, ToolGenerator
from core.self_evolution import SelfEvolutionEngine
from core.instant_learning import InstantLearningSystem


class AlliancePioneer:
    """
    联盟拓荒者主系统
    
    集成所有能力：
    1. P0: 知识版本控制 + 注入验证 + 用户纠错
    2. P1: 决策链 + 反思日志 + 能力诊断
    3. 数据飞轮: 交互数据收集
    4. 元认知循环: 自我复盘 + 老师评估 + 方法论提炼
    """
    
    def __init__(self, teacher_api_key: str = None):
        # 会话ID
        self.session_id = str(uuid.uuid4())[:8]
        
        # P0核心模块
        self.fact_store = VersionedFactStore()
        self.verification_loop = KnowledgeVerificationLoop()
        self.correction_flow = UserCorrectionFlow()
        
        # P1自我认知模块
        self.chain_manager = DecisionChainManager()
        self.reflector = LearningReflector()
        self.gap_diagnoser = CapabilityGapDiagnoser()
        
        # 数据飞轮
        self.data_collector = InteractionDataCollector()
        
        # 元认知循环
        self.self_reflection = SelfReflection()
        self.teacher = TeacherInterface(api_key=teacher_api_key)
        self.methodology_extractor = MethodologyExtractor()
        
        # 技能树系统
        self.skill_tree = SkillTree()
        self.task_scheduler = TaskScheduler(self.skill_tree)
        self.tool_generator = ToolGenerator(self.skill_tree)
        
        # 统计
        self.interaction_count = 0
        
        # 自我进化引擎
        self.evolution_engine = SelfEvolutionEngine(
            data_threshold=50,
            training_interval_hours=6
        )
        
        # 即时学习系统
        self.instant_learning = InstantLearningSystem()
        
        logger.info(f"🚀 联盟拓荒者已启动 (Session: {self.session_id})")
        logger.info(f"🌳 技能树已加载: {len(self.skill_tree.skills)} 个技能")
        logger.info(f"🧬 自我进化引擎已启动")
        logger.info(f"📚 即时学习系统已启动")
    
    def process_question(
        self,
        question: str,
        enable_metacognition: bool = True
    ) -> Dict:
        """
        处理用户问题（主流程）
        
        Args:
            question: 用户问题
            enable_metacognition: 是否启用元认知循环
        
        Returns:
            处理结果
        """
        self.interaction_count += 1
        
        logger.info(f"\n{'='*60}")
        logger.info(f"处理问题 #{self.interaction_count}: {question[:50]}...")
        logger.info(f"{'='*60}")
        
        # 步骤1: 开始决策链
        chain = self.chain_manager.start_new_chain()
        
        # 步骤2: L1感知层 - 意图识别
        intent = self._perceive_intent(question)
        chain.add_step(
            layer="L1",
            layer_name="感知层",
            input_data=question,
            output_data=intent,
            reasoning=f"识别意图: {intent}",
            confidence=0.9
        )
        
        # 步骤3: L2理解层 - 检索知识
        # 使用智能匹配器生成多个查询变体
        question_variants = QuestionMatcher.normalize_question(question)
        facts = []
        for variant in question_variants:
            facts = self.fact_store.get_active_assertions(variant)
            if facts:
                break
        
        chain.add_step(
            layer="L2",
            layer_name="理解层",
            input_data=question,
            output_data=f"{len(facts)}条事实",
            reasoning=f"检索到{len(facts)}条相关知识",
            confidence=0.8 if facts else 0.5
        )
        
        # 步骤3.5: 即时学习 - 检索知识库
        instant_knowledge, knowledge_confidence = self.instant_learning.retrieve_knowledge(question)
        
        # 检测知识缺口
        knowledge_gap = None
        if not instant_knowledge:
            knowledge_gap = self.instant_learning.detect_knowledge_gap(question, instant_knowledge)
            if knowledge_gap:
                logger.info(f"⚠️ 检测到知识缺口: {knowledge_gap}")
        
        # 如果检索到即时知识，添加到facts
        if instant_knowledge:
            for k in instant_knowledge[:3]:  # 最多添加3条
                facts.append({
                    'content': k['assertion'],
                    'source': f"即时学习库({k['source']})",
                    'confidence': k['confidence']
                })
            logger.info(f"📚 从即时学习库检索到 {len(instant_knowledge)} 条知识")
        
        # 步骤4: L3推理层 - 生成回答
        response = self._generate_response(question, facts, intent)
        chain.add_step(
            layer="L3",
            layer_name="推理层",
            input_data=facts[:3] if facts else [],
            output_data=response[:100],
            reasoning="整合知识生成回答",
            confidence=0.75
        )
        
        # 步骤5: L4校验层 - 评估质量
        objective_score = self._evaluate_objective(question, response, facts)
        chain.add_step(
            layer="L4",
            layer_name="校验层",
            input_data=response,
            output_data=f"客观分{objective_score:.1f}",
            reasoning=f"评估回答质量",
            confidence=objective_score / 100
        )
        
        # 步骤6: 完成决策链
        chain.set_final_output(response, objective_score / 100)
        self.chain_manager.complete_chain()
        
        # 步骤7: 元认知循环（如果启用）
        metacognition_result = None
        if enable_metacognition:
            metacognition_result = self._run_metacognition_loop(
                question, response, objective_score
            )
        
        # 步骤8: 触发知识注入（如果客观分低）
        if objective_score < 30:
            self._trigger_knowledge_injection(question, response, objective_score)
        
        # 返回结果
        result = {
            'question': question,
            'response': response,
            'objective_score': objective_score,
            'facts_used': len(facts),
            'intent': intent,
            'metacognition': metacognition_result,
            'session_id': self.session_id
        }
        
        return result
    
    def handle_feedback(
        self,
        question: str,
        response: str,
        feedback: str,
        objective_score: float = 0.0
    ) -> Dict:
        """
        处理用户反馈
        
        Args:
            question: 原问题
            response: 原回答
            feedback: 用户反馈
            objective_score: 客观分
        
        Returns:
            处理结果
        """
        logger.info(f"📝 处理用户反馈: {feedback[:50]}...")
        
        # 分类反馈
        feedback_type = self._classify_feedback(feedback)
        
        # 如果是纠错，更新事实库
        if feedback_type == 'correction':
            correction_result = self.correction_flow.process_correction(
                question=question,
                old_answer=response,
                correction_feedback=feedback,
                before_score=objective_score
            )
            
            logger.info(f"✅ 纠错已处理: 更新{correction_result.get('updated_assertions', 0)}条断言")
            
            # 即时学习：将纠错立即写入知识库
            instant_learn_result = self.instant_learning.learn_instantly(
                concept=question,
                assertion=feedback,  # 将用户的纠错作为新知识
                source='user_correction'
            )
            
            logger.info(f"📚 即时学习完成: {instant_learn_result['action']}")
            
            return {
                'feedback_type': 'correction',
                'correction_result': correction_result,
                'instant_learning': instant_learn_result
            }
        
        # 记录学习事件
        self.reflector.record_learning_event(
            event_type='user_feedback',
            question=question,
            action_taken=f'记录{feedback_type}反馈',
            result='success' if feedback_type == 'positive' else 'partial',
            confidence_before=objective_score / 100,
            confidence_after=(objective_score + 10) / 100 if feedback_type == 'positive' else objective_score / 100
        )
        
        # 检查是否应该触发自我进化
        evolution_result = None
        if feedback_type == 'correction':
            logger.info("🧬 检查自我进化条件...")
            evolution_result = self.evolution_engine.evolve()
            
            if evolution_result.get('action') == 'training':
                logger.info("✅ 已触发自我训练")
        
        # 记录交互数据
        self.data_collector.save_interaction(
            session_id=self.session_id,
            question=question,
            response=response,
            feedback_type=feedback_type,
            feedback_content=feedback,
            objective_score=objective_score,
            total_score=objective_score
        )
        
        return {
            'feedback_type': feedback_type,
            'recorded': True
        }
    
    def _perceive_intent(self, question: str) -> str:
        """感知意图"""
        if '为什么' in question:
            return '因果解释'
        if '怎么' in question or '如何' in question:
            return '方法指导'
        if '是什么' in question or '什么是' in question:
            return '概念定义'
        if '有啥' in question or '有哪些' in question:
            return '列举说明'
        return '通用问答'
    
    def _generate_response(
        self,
        question: str,
        facts: List[Dict],
        intent: str
    ) -> str:
        """生成回答 - 使用Ollama模型"""
        try:
            import requests
            
            # 构建提示词
            if facts:
                fact_strs = [f"{f['subject']}{f['predicate']}{f['object']}" for f in facts[:3]]
                context = f"已知信息：{'；'.join(fact_strs)}\n\n"
                prompt = f"{context}基于以上信息，请回答：{question}"
            else:
                prompt = question
            
            # 调用Ollama
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen2.5-coder:7b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 300,
                        "temperature": 0.7
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                answer = response.json().get("response", "").strip()
                return answer
            else:
                logger.warning(f"Ollama调用失败: {response.status_code}")
                # 回退到知识检索
                if facts:
                    fact_strs = [f"{f['subject']}{f['predicate']}{f['object']}" for f in facts[:3]]
                    return f"根据已知信息：{'；'.join(fact_strs)}。"
                return f"关于{question}，我暂时没有确切的知识储备，需要进一步学习。"
                
        except Exception as e:
            logger.warning(f"模型调用失败: {e}")
            # 回退到知识检索
            if facts:
                fact_strs = [f"{f['subject']}{f['predicate']}{f['object']}" for f in facts[:3]]
                return f"根据已知信息：{'；'.join(fact_strs)}。"
            return f"关于{question}，我暂时没有确切的知识储备，需要进一步学习。"
    
    def _evaluate_objective(
        self,
        question: str,
        response: str,
        facts: List[Dict]
    ) -> float:
        """评估客观分"""
        if not facts:
            return 30.0
        
        # 基于事实数量和质量评分
        base_score = 50.0
        fact_bonus = min(len(facts) * 5, 20)
        confidence_bonus = sum(f.get('confidence', 0.8) for f in facts) / len(facts) * 10
        
        return min(100.0, base_score + fact_bonus + confidence_bonus)
    
    def _run_metacognition_loop(
        self,
        question: str,
        response: str,
        objective_score: float
    ) -> Dict:
        """运行元认知循环"""
        logger.info("🔄 启动元认知循环...")
        
        # 步骤1: 自我复盘
        self_result = self.self_reflection.reflect_on_interaction(
            question=question,
            response=response,
            objective_score=objective_score
        )
        
        # 步骤2: 判断是否需要老师评估
        should_ask_teacher = (
            objective_score < 50 or
            len(self_result.what_i_could_improve) >= 2 or
            self.interaction_count % 10 == 0  # 每10次抽样一次
        )
        
        teacher_feedback = None
        methodologies = []
        
        if should_ask_teacher:
            # 步骤3: 请求老师评估
            teacher_feedback = self.teacher.request_feedback(
                question=question,
                response=response,
                self_reflection=self.self_reflection.to_dict(self_result),
                objective_score=objective_score
            )
            
            # 步骤4: 提炼方法论
            methodologies = self.methodology_extractor.extract_methodology(
                teacher_feedback=teacher_feedback,
                question=question,
                response=response,
                self_reflection=self.self_reflection.to_dict(self_result)
            )
        
        return {
            'self_reflection': self.self_reflection.to_dict(self_result),
            'teacher_feedback': teacher_feedback,
            'methodologies': [{'name': m.name, 'description': m.description} for m in methodologies]
        }
    
    def _trigger_knowledge_injection(
        self,
        question: str,
        response: str,
        objective_score: float
    ):
        """触发知识注入"""
        logger.info(f"💉 触发知识注入: 客观分={objective_score:.1f}")
        
        # 记录学习事件
        self.reflector.record_learning_event(
            event_type='injection_trigger',
            question=question,
            action_taken='触发外部学习',
            result='pending',
            confidence_before=objective_score / 100
        )
    
    def _classify_feedback(self, feedback: str) -> str:
        """分类反馈"""
        feedback_lower = feedback.lower()
        
        if any(word in feedback_lower for word in ['不对', '错误', '应该是', '不是']):
            return 'correction'
        if any(word in feedback_lower for word in ['好', '对', '不错', '正确', '点赞']):
            return 'positive'
        if any(word in feedback_lower for word in ['不好', '错', '不对', '点踩']):
            return 'negative'
        
        return 'neutral'
    
    def show_stats(self) -> str:
        """显示统计信息"""
        lines = []
        lines.append("\n" + "=" * 60)
        lines.append("  系统统计")
        lines.append("=" * 60)
        
        # 交互统计
        lines.append(f"\n【交互统计】")
        lines.append(f"  本次会话交互数: {self.interaction_count}")
        
        # 事实库统计
        fact_stats = self.fact_store.get_statistics()
        lines.append(f"\n【事实库】")
        lines.append(f"  总断言: {fact_stats['total']}")
        lines.append(f"  有效断言: {fact_stats['active']}")
        
        # 方法论统计
        method_stats = self.methodology_extractor.get_statistics()
        lines.append(f"\n【方法论】")
        lines.append(f"  总方法论: {method_stats['total_methodologies']}")
        lines.append(f"  平均效果: {method_stats['avg_effectiveness']:.2f}")
        
        # 数据收集统计
        data_stats = self.data_collector.get_statistics()
        lines.append(f"\n【数据收集】")
        lines.append(f"  总交互: {data_stats['total_interactions']}")
        lines.append(f"  高质量数据: {data_stats['high_quality_data']}")
        lines.append(f"  可用于SFT: {data_stats['ready_for_sft']}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)
    
    def export_training_data(self, output_path: str = "data/training_data.json") -> int:
        """导出训练数据"""
        return self.data_collector.export_for_sft(
            output_path=output_path,
            format_type="json",
            min_quality_score=0.7,
            include_corrections=True
        )


def main():
    """命令行入口"""
    print("\n" + "=" * 60)
    print("  🚀 联盟拓荒者 - 自我进化AI系统")
    print("=" * 60)
    print("\n命令:")
    print("  :stats   - 显示统计")
    print("  :why     - 显示决策链")
    print("  :reflect - 显示反思报告")
    print("  :export  - 导出训练数据")
    print("  :help    - 显示帮助")
    print("  exit     - 退出")
    print("\n" + "=" * 60)
    
    # 初始化系统
    pioneer = AlliancePioneer()
    
    while True:
        try:
            user_input = input("\n你: ").strip()
            
            if not user_input:
                continue
            
            # 命令处理
            if user_input == 'exit':
                print("\n👋 再见！")
                break
            
            if user_input == ':stats':
                print(pioneer.show_stats())
                continue
            
            if user_input == ':why':
                chain = pioneer.chain_manager.get_last_chain()
                if chain:
                    print(chain.visualize())
                else:
                    print("暂无决策链记录")
                continue
            
            if user_input == ':reflect':
                report = pioneer.reflector.generate_learning_report("day")
                print(pioneer.reflector.format_report(report))
                continue
            
            if user_input == ':export':
                count = pioneer.export_training_data()
                print(f"✅ 已导出 {count} 条训练数据")
                continue
            
            if user_input == ':help':
                print("\n可用命令:")
                print("  :stats   - 显示系统统计")
                print("  :why     - 显示最近决策链")
                print("  :reflect - 显示学习反思报告")
                print("  :export  - 导出SFT训练数据")
                print("  :help    - 显示此帮助")
                print("  exit     - 退出系统")
                continue
            
            # 处理问题
            result = pioneer.process_question(user_input)
            
            print(f"\n拓荒者: {result['response']}")
            print(f"  [客观分: {result['objective_score']:.1f}, 事实数: {result['facts_used']}]")
            
            # 询问反馈
            feedback = input("\n反馈 (点赞/点踩/纠错/跳过): ").strip()
            
            if feedback and feedback not in ['跳过', 'skip', '']:
                pioneer.handle_feedback(
                    question=user_input,
                    response=result['response'],
                    feedback=feedback,
                    objective_score=result['objective_score']
                )
                print("  ✅ 反馈已记录")
            
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            logger.error(f"错误: {e}")
            print(f"\n❌ 错误: {e}")


if __name__ == "__main__":
    main()