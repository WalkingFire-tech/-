"""
情绪推断模块 - 理解用户状态
基于文本、标点、上下文推断用户情绪、耐心、紧迫度
"""
import re
from typing import Dict, List, Tuple
from datetime import datetime
from loguru import logger


class EmotionInferencer:
    """情绪推断器"""
    
    # 情绪关键词词典（增强版）
    EMOTION_KEYWORDS = {
        "urgent": ["快", "急", "马上", "立刻", "赶紧", "紧急", "快点", "快点啊", "等不及", "现在就要", "马上要", " ASAP", "asap", "紧急情况"],
        "frustrated": ["烦", "气死", "无语", "算了", "不玩了", "什么鬼", "怎么又", "老是", "受不了", "崩溃", "抓狂", "郁闷", "烦躁", "真难用", "怎么这么难"],
        "angry": ["滚", "闭嘴", "别说了", "够了", "讨厌", "可恶", "混蛋", "垃圾", "废物", "什么破系统", "太烂了", "气死我了"],
        "happy": ["谢谢", "太好了", "棒", "厉害", "完美", "优秀", "喜欢", "赞", "好棒", "真棒", "太棒了", "爱了", "给力", "牛逼", "666", "感谢", "多谢"],
        "confused": ["不懂", "不明白", "什么意思", "怎么用", "为什么", "搞不懂", "看不懂", "不理解", "啥意思", "这是啥", "怎么操作", "如何使用"],
        "disappointed": ["唉", "失望", "不行", "不好", "差劲", "一般", "就这", "也就这样", "没什么用", "不太行", "不太满意", "还可以吧"],
        "neutral": ["好的", "嗯", "哦", "明白", "了解", "收到", "知道了", "好的呢"],
    }
    
    # 情绪强度修饰词
    INTENSITY_MODIFIERS = {
        "very": ["太", "非常", "特别", "超级", "极其", "真的", "实在"],
        "somewhat": ["有点", "稍微", "略微", "还算"],
        "negative": ["不", "没", "别", "不要"],
    }
    
    # 标点符号强度
    PUNCTUATION_WEIGHTS = {
        "！": 1.5,  # 感叹号增强情绪
        "？": 1.2,  # 问号表示困惑
        "。。。": 1.3,  # 省略号表示无奈
        "！！": 2.0,  # 多个感叹号强烈情绪
    }
    
    def __init__(self):
        self.history: List[Dict] = []
        logger.info("情绪推断器已初始化")
    
    def infer(self, text: str, context: Dict = None) -> Dict:
        """推断情绪
        
        Args:
            text: 用户输入文本
            context: 上下文（历史对话、失败次数等）
        
        Returns:
            情绪推断结果
        """
        result = {
            "emotion": "neutral",
            "urgency": 0.0,
            "patience": 1.0,
            "frustration": 0.0,
            "confidence": 0.5,
            "signals": []
        }
        
        # 1. 关键词检测
        emotion_scores = {}
        for emotion, keywords in self.EMOTION_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                emotion_scores[emotion] = score
                result["signals"].append(f"关键词: {emotion}")
        
        # 2. 标点符号分析
        punct_multiplier = 1.0
        for punct, weight in self.PUNCTUATION_WEIGHTS.items():
            if punct in text:
                punct_multiplier = max(punct_multiplier, weight)
                result["signals"].append(f"标点: {punct}")
        
        # 3. 确定主要情绪
        if emotion_scores:
            primary_emotion = max(emotion_scores, key=emotion_scores.get)
            result["emotion"] = primary_emotion
            result["confidence"] = min(0.9, 0.5 + emotion_scores[primary_emotion] * 0.1)
        
        # 4. 计算紧迫度
        if result["emotion"] == "urgent":
            result["urgency"] = 0.9 * punct_multiplier
        elif result["emotion"] == "angry":
            result["urgency"] = 0.8 * punct_multiplier
        elif result["emotion"] == "frustrated":
            result["urgency"] = 0.6 * punct_multiplier
        
        # 5. 计算耐心（增强版）
        base_patience = 1.0
        
        # 根据情绪调整基础耐心
        emotion_patience_map = {
            "frustrated": 0.3,
            "angry": 0.1,
            "disappointed": 0.4,
            "urgent": 0.5,  # 紧急但不是没耐心
            "confused": 0.6,  # 困惑需要更多耐心解释
            "happy": 1.0,
            "neutral": 0.8,
        }
        
        if result["emotion"] in emotion_patience_map:
            base_patience = emotion_patience_map[result["emotion"]]
        
        # 检查强度修饰词
        for modifier in self.INTENSITY_MODIFIERS.get("very", []):
            if modifier in text:
                if result["emotion"] in ["frustrated", "angry", "disappointed"]:
                    base_patience *= 0.7  # 更强烈的负面情绪
                break
        
        result["patience"] = base_patience
        
        # 6. 计算挫折度
        if context:
            recent_failures = context.get("recent_failures", 0)
            result["frustration"] = min(1.0, recent_failures * 0.2)
            
            # 如果连续失败，降低耐心
            if recent_failures >= 3:
                result["patience"] = min(result["patience"], 0.3)
                result["signals"].append(f"连续失败: {recent_failures}次")
        
        # 7. 响应时间分析（如果有）
        if context and "response_time" in context:
            response_time = context["response_time"]
            if response_time > 10.0:  # 超过10秒
                result["patience"] *= 0.8
                result["signals"].append(f"响应慢: {response_time:.1f}s")
        
        # 8. 记录历史
        self._record_inference(text, result)
        
        return result
    
    def _record_inference(self, text: str, result: Dict):
        """记录推断历史"""
        self.history.append({
            "text": text[:50],
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
        
        # 保留最近100条
        if len(self.history) > 100:
            self.history = self.history[-100:]
    
    def get_user_state(self, recent_n: int = 5) -> Dict:
        """获取用户整体状态（基于最近N次交互）"""
        if not self.history:
            return {"state": "unknown", "trend": "stable"}
        
        recent = self.history[-recent_n:]
        
        # 计算平均情绪
        emotions = [r["result"]["emotion"] for r in recent]
        patience_avg = sum(r["result"]["patience"] for r in recent) / len(recent)
        frustration_avg = sum(r["result"]["frustration"] for r in recent) / len(recent)
        
        # 判断趋势
        if len(recent) >= 3:
            patience_trend = recent[-1]["result"]["patience"] - recent[0]["result"]["patience"]
            if patience_trend < -0.2:
                trend = "deteriorating"  # 恶化
            elif patience_trend > 0.2:
                trend = "improving"  # 改善
            else:
                trend = "stable"  # 稳定
        else:
            trend = "unknown"
        
        # 确定状态
        if patience_avg < 0.3:
            state = "critical"  # 用户很不耐烦
        elif patience_avg < 0.6:
            state = "concerning"  # 需要关注
        elif frustration_avg > 0.5:
            state = "frustrated"  # 用户受挫
        else:
            state = "healthy"  # 正常
        
        return {
            "state": state,
            "trend": trend,
            "patience_avg": round(patience_avg, 2),
            "frustration_avg": round(frustration_avg, 2),
            "recent_emotions": emotions
        }
    
    def should_simplify_response(self, emotion_result: Dict) -> bool:
        """判断是否应该简化响应"""
        return (
            emotion_result["patience"] < 0.4 or
            emotion_result["frustration"] > 0.6 or
            emotion_result["urgency"] > 0.7
        )
    
    def get_response_tone(self, emotion_result: Dict) -> str:
        """获取响应语调建议"""
        emotion = emotion_result["emotion"]
        patience = emotion_result["patience"]
        
        if emotion == "angry":
            return "apologetic"  # 道歉语调
        elif emotion == "frustrated":
            return "empathetic"  # 共情语调
        elif emotion == "urgent":
            return "concise"  # 简洁语调
        elif emotion == "confused":
            return "explanatory"  # 解释语调
        elif patience < 0.5:
            return "brief"  # 简短语调
        else:
            return "normal"  # 正常语调


emotion_inferencer = EmotionInferencer()