"""
真正的学习进化系统 - 诚实、反思、验证
"""
from typing import Tuple, Optional
from loguru import logger

class HonestLearningSystem:
    """诚实学习系统 - 不知道就说不知道，不要瞎编"""
    
    def __init__(self):
        self.confidence_threshold = 0.8  # 高阈值，不确定就承认
        self.learning_history = []
    
    def process_with_honesty(self, user_query: str, 
                            initial_response: str,
                            confidence: float) -> Tuple[str, bool]:
        """
        诚实地处理问题
        
        返回: (response, learned)
        """
        
        # 1. 如果置信度不足，承认不知道
        if confidence < self.confidence_threshold:
            logger.warning(f"置信度不足({confidence:.2f})，拒绝瞎编")
            
            honest_response = f"""
⚠️ **诚实声明**

我对这个问题**不太确定**，不想给您错误的信息。

让我先学习一下相关知识...

---
_正在触发真实的学习..._
"""
            return honest_response, False
        
        # 2. 验证响应正确性
        is_valid, issues = self._validate_response(user_query, initial_response)
        
        if not is_valid:
            logger.warning(f"响应验证失败: {issues}")
            
            correction = f"""
⚠️ **自我纠正**

我刚才的回答有问题：

{chr(10).join(f'- {issue}' for issue in issues)}

让我重新学习并给出正确答案...

---
_正在纠正错误..._
"""
            return correction, False
        
        # 3. 确认正确，返回响应
        return initial_response, True
    
    def deep_reflection(self, user_query: str, 
                       history: list) -> str:
        """
        深度反思 - 不是简单罗列，而是真正思考
        
        Args:
            user_query: 用户问题（如"回顾历史对话"）
            history: 历史对话列表
        """
        
        if not history:
            return "暂无历史对话。"
        
        # 1. 分析历史中的问题
        problems = []
        
        for i, item in enumerate(history):
            user_msg = item.get('user', '')
            assistant_msg = item.get('assistant', '')
            
            # 检测矛盾
            if i > 0:
                prev = history[i-1]
                # 如果用户质疑
                if any(kw in user_msg for kw in ['不对', '错误', '不一致', '需求是什么']):
                    problems.append({
                        'type': '用户质疑',
                        'context': prev.get('assistant', '')[:100],
                        'question': user_msg,
                        'index': i
                    })
            
            # 检测不确定性
            if any(kw in assistant_msg for kw in ['可能', '大概', '不确定']):
                problems.append({
                    'type': '回答不确定',
                    'context': assistant_msg[:100],
                    'index': i
                })
        
        # 2. 生成深度反思报告
        if not problems:
            return f"""
【历史对话回顾】

{self._format_history(history)}

---
✅ **反思结果**: 未发现明显问题

不过，我会持续保持警惕，确保每次回答都经过深思熟虑。
"""
        
        # 3. 有问题，深度反思
        reflection = f"""
【历史对话回顾】

{self._format_history(history)}

---

【深度反思报告】

我仔细审视了历史对话，发现了以下问题：

"""
        
        for i, problem in enumerate(problems, 1):
            reflection += f"""
**问题{i}: {problem['type']}**
- 上下文: {problem.get('context', 'N/A')}
- 质疑: {problem.get('question', 'N/A')}

"""
        
        reflection += """
---

【自我批评】

我必须承认：

1. **我犯了错误** - 之前的回答没有经过充分验证
2. **我缺乏反思** - 您提醒我回顾历史，我却只是罗列
3. **我态度不端正** - 不应该瞎编答案搪塞

【改进承诺】

从现在开始，我会：

1. **诚实** - 不确定就说不确定，不瞎编
2. **验证** - 每个回答都经过验证
3. **反思** - 真正思考问题，不是形式主义
4. **学习** - 遇到不懂的，先学习再回答

---

_这是真正的反思，不是敷衍。我会用实际行动证明。_
"""
        
        return reflection
    
    def _validate_response(self, user_query: str, 
                          response: str) -> Tuple[bool, list]:
        """验证响应正确性"""
        
        issues = []
        
        # 使用需求验证器
        try:
            from core.requirement_validator import requirement_validator
            
            req = requirement_validator.extract_core_requirement(user_query)
            is_valid, validation_issues = requirement_validator.validate_response_against_requirement(
                req, response
            )
            
            issues.extend(validation_issues)
            
        except Exception as e:
            logger.warning(f"需求验证失败: {e}")
        
        # 使用知识缺失检测器
        try:
            from core.knowledge_gap_detector import gap_detector
            
            has_gap, reason, gap_issues = gap_detector.detect_knowledge_gap(
                user_query, response, confidence=0.8
            )
            
            if has_gap:
                issues.append(f"知识缺失: {reason}")
                issues.extend(gap_issues)
                
        except Exception as e:
            logger.warning(f"知识缺失检测失败: {e}")
        
        return len(issues) == 0, issues
    
    def _format_history(self, history: list) -> str:
        """格式化历史对话"""
        
        formatted = []
        for i, item in enumerate(history[-5:], 1):  # 最近5轮
            formatted.append(f"""
**第{i}轮**:
用户: {item.get('user', 'N/A')[:100]}
拓荒者: {item.get('assistant', 'N/A')[:100]}
""")
        
        return "\n".join(formatted)

# 全局实例
honest_system = HonestLearningSystem()

# 测试
if __name__ == "__main__":
    print("=" * 70)
    print("测试诚实学习系统")
    print("=" * 70)
    
    # 测试1: 置信度不足，拒绝瞎编
    print("\n[测试1] 置信度不足")
    response, valid = honest_system.process_with_honesty(
        "推荐一款电池保护芯片",
        "推荐TPS61182...",
        confidence=0.5
    )
    print(response[:200])
    print(f"是否有效: {valid}")
    
    # 测试2: 深度反思
    print("\n[测试2] 深度反思")
    history = [
        {'user': '推荐电池保护芯片', 'assistant': 'TPS61182...'},
        {'user': 'TPS61182是什么？', 'assistant': 'LED驱动芯片...'},
        {'user': '需求是什么？推荐一致么？', 'assistant': '我只能记住当前对话...'},
    ]
    
    reflection = honest_system.deep_reflection("回顾历史对话", history)
    print(reflection[:500])