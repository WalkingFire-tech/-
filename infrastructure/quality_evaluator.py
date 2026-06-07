import re
from loguru import logger

class QualityEvaluator:
    """简单的任务结果评估器（基于规则）"""
    
    @staticmethod
    def evaluate_code(response: str) -> int:
        """评估代码质量：0-100分"""
        score = 0
        
        # 检查是否包含代码块
        if "```" in response:
            score += 20
        else:
            score += 5  # 没有代码块但可能有代码
        
        # 检查是否有函数定义
        if re.search(r'def\s+\w+\s*\(', response):
            score += 20
        if re.search(r'class\s+\w+', response):
            score += 10
        
        # 检查常见语法完整性（避免明显不完整）
        if re.search(r'return\s+\w+', response):
            score += 15
        
        # 检查是否有明显错误（如空的 left/middle/right）
        if re.search(r'left\s*=\s*$', response, re.MULTILINE):
            score -= 20
        if re.search(r'middle\s*=\s*$', response, re.MULTILINE):
            score -= 20
        
        # 长度惩罚（如果太短，可能不完整）
        if len(response) < 100:
            score -= 10
        
        # 限制在 0-100 范围
        return max(0, min(100, score))
    
    @staticmethod
    def evaluate_chat(response: str) -> int:
        """评估对话质量（回答是否连贯、相关）"""
        score = 50  # 基础分
        
        # 如果回答太短
        if len(response) < 20:
            score -= 20
        
        # 如果包含 "抱歉" 或 "无法" 等负面词，可能回答质量低
        if re.search(r'抱歉|无法|不能|不知道', response):
            score -= 15
        
        # 如果回答看起来是完整句子，加分
        if response.endswith(('。', '.', '！', '?', '？')):
            score += 10
        
        # 如果回答包含换行（结构化），加分
        if '\n' in response:
            score += 5
        
        return max(0, min(100, score))
    
    @classmethod
    def evaluate(cls, response: str, task_type: str) -> int:
        """统一入口"""
        if task_type == "code":
            return cls.evaluate_code(response)
        else:
            return cls.evaluate_chat(response)
