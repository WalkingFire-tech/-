"""
决策日志记录器 - 让用户了解系统为何做出某个决策
"""
from collections import deque
from datetime import datetime
from typing import Dict, Optional
from loguru import logger


class DecisionLogger:
    """决策日志记录器"""
    
    def __init__(self, max_records: int = 100):
        self.decisions = deque(maxlen=max_records)
        self.request_id = None
    
    def start_request(self, request_id: str):
        """开始新请求"""
        self.request_id = request_id
    
    def log_decision(
        self,
        decision_type: str,
        choice: str,
        reason: str,
        alternatives: list = None,
        score: float = None,
        metadata: Dict = None
    ):
        """记录决策
        
        Args:
            decision_type: 决策类型（model_selection, tool_selection, route等）
            choice: 选择结果
            reason: 选择原因
            alternatives: 备选方案
            score: 得分
            metadata: 其他元数据
        """
        record = {
            "type": decision_type,
            "choice": choice,
            "reason": reason,
            "alternatives": alternatives or [],
            "score": score,
            "metadata": metadata or {},
            "request_id": self.request_id,
            "timestamp": datetime.now().isoformat()
        }
        
        self.decisions.append(record)
        logger.debug(f"决策记录: {decision_type} -> {choice} ({reason})")
    
    def get_last_decision(self) -> Optional[Dict]:
        """获取最近决策"""
        return self.decisions[-1] if self.decisions else None
    
    def get_decisions_by_type(self, decision_type: str) -> list:
        """按类型获取决策"""
        return [d for d in self.decisions if d["type"] == decision_type]
    
    def explain_last_decision(self) -> str:
        """解释最近决策（供用户查看）"""
        last = self.get_last_decision()
        if not last:
            return "暂无决策记录"
        
        decision_type = last["type"]
        choice = last["choice"]
        reason = last["reason"]
        score = last.get("score")
        alternatives = last.get("alternatives", [])
        
        if decision_type == "model_selection":
            explanation = f"""
╔══════════════════════════════════════════════════════════╗
║              决策解释：模型选择                            ║
╚══════════════════════════════════════════════════════════╝

🎯 选择模型: {choice}

📊 选择原因:
  {reason}

📈 得分: {score:.2f if score else 'N/A'}

🔄 备选模型:
"""
            for i, alt in enumerate(alternatives[:3], 1):
                explanation += f"  {i}. {alt}\n"
        
        elif decision_type == "tool_selection":
            score_str = f"{score:.2%}" if score else "N/A"
            explanation = f"""
╔══════════════════════════════════════════════════════════╗
║              决策解释：工具选择                            ║
╚══════════════════════════════════════════════════════════╝

🛠️ 选择工具: {choice}

📊 选择原因:
  {reason}

📈 成功率: {score_str}
"""
        
        elif decision_type == "route":
            explanation = f"""
╔══════════════════════════════════════════════════════════╗
║              决策解释：路由决策                            ║
╚══════════════════════════════════════════════════════════╝

🔀 路由路径: {choice}

📊 选择原因:
  {reason}
"""
        
        else:
            explanation = f"""
决策类型: {decision_type}
选择: {choice}
原因: {reason}
"""
        
        return explanation
    
    def get_decision_summary(self, recent_n: int = 10) -> str:
        """获取决策摘要"""
        if not self.decisions:
            return "暂无决策记录"
        
        recent = list(self.decisions)[-recent_n:]
        
        summary = f"""
╔══════════════════════════════════════════════════════════╗
║              最近 {len(recent)} 次决策摘要                   ║
╚══════════════════════════════════════════════════════════╝
"""
        
        for i, decision in enumerate(recent, 1):
            summary += f"\n{i}. [{decision['type']}] {decision['choice']}\n"
            summary += f"   原因: {decision['reason'][:50]}\n"
        
        return summary


decision_logger = DecisionLogger()