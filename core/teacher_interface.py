"""
DeepSeek老师接口
让外部模型作为"思维教练"评估系统的思考过程
"""
from typing import Dict, List, Optional
from datetime import datetime
import json
import time

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class TeacherInterface:
    """
    与DeepSeek的交互接口
    
    老师角色：
    - 评估思维过程（不是答案对不对，而是思考好不好）
    - 提炼方法论
    - 指出盲点
    - 建议学习方向
    """
    
    def __init__(
        self,
        api_key: str = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        max_tokens: int = 2000
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.call_history = []
        self.last_call_time = 0
        self.min_interval = 300  # 最少间隔5秒
    
    def request_feedback(
        self,
        question: str,
        response: str,
        self_reflection: Dict,
        objective_score: float = 0.0,
        context: Dict = None
    ) -> Dict:
        """
        请求DeepSeek评估学生的思维过程
        
        Args:
            question: 用户问题
            response: 系统回答
            self_reflection: 自我复盘结果
            objective_score: 客观分
            context: 上下文
        
        Returns:
            结构化反馈
        """
        # 速率限制
        current_time = time.time()
        if current_time - self.last_call_time < self.min_interval:
            logger.warning("老师调用过于频繁，使用本地评估")
            return self._local_evaluation(question, response, self_reflection)
        
        logger.info(f"👨‍🏫 请求老师评估: {question[:50]}...")
        
        # 构建提示词
        prompt = self._build_teacher_prompt(
            question, response, self_reflection, objective_score
        )
        
        # 尝试调用API
        try:
            feedback = self._call_deepseek_api(prompt)
            self.last_call_time = current_time
            
            # 记录历史
            self.call_history.append({
                'question': question,
                'timestamp': datetime.now().isoformat(),
                'success': True
            })
            
            logger.info("✅ 老师评估完成")
            return feedback
            
        except Exception as e:
            logger.warning(f"老师API调用失败: {e}，使用本地评估")
            return self._local_evaluation(question, response, self_reflection)
    
    def _build_teacher_prompt(
        self,
        question: str,
        response: str,
        self_reflection: Dict,
        objective_score: float
    ) -> str:
        """构建老师评估提示词"""
        
        what_i_did_well = self_reflection.get('what_i_did_well', [])
        what_i_could_improve = self_reflection.get('what_i_could_improve', [])
        alternative_approaches = self_reflection.get('alternative_approaches', [])
        uncertainties = self_reflection.get('uncertainties', [])
        
        prompt = f"""你是一位高级思维教练。请评估以下学生的思考过程：

【问题】
{question}

【学生回答】
{response}

【客观评分】
{objective_score:.1f}分

【学生自我复盘】
- 做得好的地方：
{chr(10).join(f'  • {item}' for item in what_i_did_well) if what_i_did_well else '  （未识别）'}

- 可改进的地方：
{chr(10).join(f'  • {item}' for item in what_i_could_improve) if what_i_could_improve else '  （未识别）'}

- 替代方案思考：
{chr(10).join(f'  • {item}' for item in alternative_approaches) if alternative_approaches else '  （未思考）'}

- 不确定性：
{chr(10).join(f'  • {item}' for item in uncertainties) if uncertainties else '  （未识别）'}

请从以下维度给出反馈：

1. **问题拆解能力**（1-10分）：学生是否准确识别了问题的核心？是否将复杂问题合理拆解？

2. **分析框架**（1-10分）：学生的思考结构是否清晰、有层次？是否建立了有效的分析框架？

3. **假设检验**（1-10分）：学生是否识别并检验了关键假设？是否考虑了边界情况？

4. **知识运用**（1-10分）：学生是否正确运用了已有知识？知识来源是否可靠？

5. **改进建议**：具体、可操作的建议（列出2-3条）

6. **推荐的学习方向**：建议补充哪些领域的知识或能力

7. **方法论提炼**：从这个案例中可以提炼出什么可复用的思维方法？

请以JSON格式返回结果。"""
        
        return prompt
    
    def _call_deepseek_api(self, prompt: str) -> Dict:
        """调用DeepSeek API"""
        if not self.api_key:
            raise ValueError("未配置API Key")
        
        try:
            import requests
        except ImportError:
            raise ImportError("需要安装requests库")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.7
        }
        
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"API调用失败: {response.status_code}")
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # 解析JSON
        try:
            # 尝试提取JSON部分
            if '```json' in content:
                json_str = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                json_str = content.split('```')[1].split('```')[0]
            else:
                json_str = content
            
            feedback = json.loads(json_str)
        except Exception:
            # 如果解析失败，返回基本结构
            feedback = {
                "problem_decomposition": 7,
                "analysis_framework": 7,
                "hypothesis_testing": 7,
                "knowledge_application": 7,
                "improvement_suggestions": ["继续提升思考深度"],
                "learning_directions": ["加强逻辑思维训练"],
                "methodology": "保持系统化思考",
                "raw_response": content
            }
        
        return feedback
    
    def _local_evaluation(
        self,
        question: str,
        response: str,
        self_reflection: Dict
    ) -> Dict:
        """本地评估（当API不可用时）"""
        
        what_i_did_well = self_reflection.get('what_i_did_well', [])
        what_i_could_improve = self_reflection.get('what_i_could_improve', [])
        
        # 基于自我复盘生成本地评估
        problem_decomposition = 7 if len(what_i_did_well) > 1 else 5
        analysis_framework = 7 if len(response) > 100 else 5
        hypothesis_testing = 6
        knowledge_application = 7 if len(what_i_did_well) > 0 else 5
        
        return {
            "problem_decomposition": problem_decomposition,
            "analysis_framework": analysis_framework,
            "hypothesis_testing": hypothesis_testing,
            "knowledge_application": knowledge_application,
            "improvement_suggestions": what_i_could_improve[:3] if what_i_could_improve else ["继续提升"],
            "learning_directions": ["加强知识储备", "提升思考深度"],
            "methodology": "系统化分析问题",
            "source": "local_evaluation"
        }
    
    def get_call_statistics(self) -> Dict:
        """获取调用统计"""
        total = len(self.call_history)
        successful = sum(1 for c in self.call_history if c.get('success', False))
        
        return {
            'total_calls': total,
            'successful_calls': successful,
            'success_rate': successful / max(1, total)
        }


teacher_interface = TeacherInterface()