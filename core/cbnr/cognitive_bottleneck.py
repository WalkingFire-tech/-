"""
L2: 认知瓶颈层 (Cognitive Bottleneck)

对应Bottleneck Block：压缩 → 处理 → 重构
先压缩到核心要素，在低维空间中高效推理，再重构为完整输出。

CBNR-AGI 2.0增强：
- 双模型架构：因果(前向)模型 + 反事实(逆向)模型
- 模型冲突管理：干涉态(建设性融合) vs 局域态(离散投影)
  ΔF < 阈值 → 干涉态：两个模型输出建设性融合
  ΔF ≥ 阈值 → 局域态：通过离散投影解决冲突

关键问句："这个问题的本质是什么？我可以安全地忽略什么？"
"""

import time
import math
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ConflictMode(Enum):
    INTERFERENCE = "interference"
    LOCALIZED = "localized"


@dataclass
class BottleneckResult:
    core_essence: Dict[str, Any] = field(default_factory=dict)
    causal_result: Optional[Dict] = None
    counterfactual_result: Optional[Dict] = None
    conflict_delta: float = 0.0
    conflict_mode: ConflictMode = ConflictMode.INTERFERENCE
    compression_ratio: float = 0.0
    reconstructed_output: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


class CausalModel:
    """
    因果(前向)模型：从原因推导结果
    "如果A发生，B会怎样？"
    CBNR-AGI 2.1: 接入world_model因果图进行真实因果推理
    """
    
    def infer(self, core: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(core)
        entities = core.get("entities", [])
        topic = core.get("topic", "")
        
        causal_chain = []
        wm_confidence = 0.0
        try:
            from core.world_model import get_world_model
            wm = get_world_model()
            for entity in entities[:3]:
                pred = wm.predict({"entity": entity, "intent": core.get("intent", "general")}, core.get("intent", "general"))
                if pred and pred.get("predicted_outcome"):
                    causal_chain.append({
                        "cause": entity,
                        "effect": pred["predicted_outcome"],
                        "confidence": pred.get("confidence", 0.6),
                        "source": "world_model",
                    })
                    wm_confidence = max(wm_confidence, pred.get("confidence", 0.6))
                else:
                    causal_chain.append({
                        "cause": entity,
                        "effect": f"{entity}的因果后果",
                        "confidence": 0.5,
                        "source": "fallback",
                    })
            if wm_confidence > 0:
                result["world_model_used"] = True
        except Exception:
            for entity in entities[:3]:
                if not any(c["cause"] == entity for c in causal_chain):
                    causal_chain.append({
                        "cause": entity,
                        "effect": f"{entity}的因果后果",
                        "confidence": 0.5,
                        "source": "fallback",
                    })
        
        result["causal_chain"] = causal_chain
        result["reasoning_direction"] = "forward"
        result["confidence"] = wm_confidence if wm_confidence > 0 else 0.5
        return result


class CounterfactualModel:
    """
    反事实(逆向)模型：从结果反推原因
    "如果要达到B，需要什么条件？"
    CBNR-AGI 2.1: 接入world_model反事实推理
    """
    
    def infer(self, core: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(core)
        entities = core.get("entities", [])
        topic = core.get("topic", "")
        
        counterfactuals = []
        wm_confidence = 0.0
        try:
            from core.world_model import get_world_model
            wm = get_world_model()
            for entity in entities[:3]:
                cf = wm.counterfactual(
                    {"entity": entity, "intent": core.get("intent", "general")},
                    core.get("intent", "general"),
                    f"不{core.get('intent', 'general')}" if core.get("intent") else "alternative",
                    core.get("intent", "general")
                )
                if cf and cf.get("counterfactual", {}).get("predicted_outcome"):
                    cf_data = cf["counterfactual"]
                    counterfactuals.append({
                        "target": entity,
                        "required_conditions": str(cf_data.get("predicted_outcome", "")),
                        "confidence": min(cf_data.get("score", 0.4), 1.0),
                        "source": "world_model",
                        "lesson": cf.get("lesson", ""),
                    })
                    wm_confidence = max(wm_confidence, min(cf_data.get("score", 0.4), 1.0))
                else:
                    counterfactuals.append({
                        "target": entity,
                        "required_conditions": f"实现{entity}的前提条件",
                        "confidence": 0.4,
                        "source": "fallback",
                    })
            if wm_confidence > 0:
                result["world_model_used"] = True
        except Exception:
            for entity in entities[:3]:
                if not any(c["target"] == entity for c in counterfactuals):
                    counterfactuals.append({
                        "target": entity,
                        "required_conditions": f"实现{entity}的前提条件",
                        "confidence": 0.4,
                        "source": "fallback",
                    })
        
        result["counterfactuals"] = counterfactuals
        result["reasoning_direction"] = "backward"
        result["confidence"] = wm_confidence if wm_confidence > 0 else 0.4
        return result


class CognitiveBottleneck:
    """
    认知瓶颈层
    
    三步瓶颈处理：
    1. 压缩 - 从海量信息中提取核心要素（骨架、关键实体、意图）
    2. 推理 - 在压缩后的核心空间中进行高密度推理（双模型架构）
    3. 重构 - 将推理结果展开为完整、结构化的表达
    """

    CONFLICT_THRESHOLD = 0.4

    def __init__(self):
        self._causal_model = CausalModel()
        self._counterfactual_model = CounterfactualModel()
        self._compression_history: List[float] = []
        self._process_count = 0

    def process(self, normalized_input: Dict[str, Any]) -> BottleneckResult:
        self._process_count += 1
        
        attention = normalized_input.get("_attention_weights", {})
        prediction_error = attention.get("prediction_error", 0.5)
        focus_boost = attention.get("focus_boost", 1.0)
        high_surprise = attention.get("high_surprise", False)
        
        target_compression = self._compute_target_compression(prediction_error, focus_boost, high_surprise)
        
        core = self._compress_to_essence(normalized_input, target_compression)
        
        causal_result = self._causal_model.infer(core)
        counterfactual_result = self._counterfactual_model.infer(core)
        
        conflict_delta = self._compute_conflict(causal_result, counterfactual_result)
        conflict_mode = ConflictMode.INTERFERENCE if conflict_delta < self.CONFLICT_THRESHOLD else ConflictMode.LOCALIZED
        
        core_result = self._resolve_conflict(causal_result, counterfactual_result, conflict_mode, conflict_delta)
        
        full_result = self._expand_to_full(core_result, normalized_input)
        
        original_size = len(str(normalized_input.get("user_input", "")))
        core_size = len(str(core.get("topic", ""))) + sum(len(str(e)) for e in core.get("entities", []))
        compression_ratio = core_size / max(original_size, 1)
        self._compression_history.append(compression_ratio)
        
        result = BottleneckResult(
            core_essence=core,
            causal_result=causal_result,
            counterfactual_result=counterfactual_result,
            conflict_delta=conflict_delta,
            conflict_mode=conflict_mode,
            compression_ratio=compression_ratio,
            reconstructed_output=full_result,
            timestamp=time.time(),
        )
        
        logger.debug(f"认知瓶颈: 压缩比={compression_ratio:.1%}(目标{target_compression:.1%}), 冲突ΔF={conflict_delta:.2f}, 模式={conflict_mode.value}")
        
        return result

    def _compute_target_compression(self, prediction_error: float, focus_boost: float, high_surprise: bool) -> float:
        base = 0.3
        pe_factor = max(0.1, 1.0 - prediction_error * 0.6)
        focus_factor = 1.0 / max(focus_boost, 0.5)
        surprise_factor = 0.7 if high_surprise else 1.0
        return min(0.9, max(0.1, base * pe_factor * focus_factor * surprise_factor))

    def _compress_to_essence(self, input_data: Dict, target_compression: float = 0.3) -> Dict[str, Any]:
        user_input = input_data.get("user_input", "")
        intent = input_data.get("intent", "")
        attention = input_data.get("_attention_weights", {})
        focus_boost = attention.get("focus_boost", 1.0)
        high_surprise = attention.get("high_surprise", False)
        
        topic = self._extract_topic(user_input)
        entities = self._extract_entities(user_input)
        question_type = self._classify_question(user_input)
        core_sentences = self._extract_core_sentences(user_input, focus_boost)
        
        max_entities = max(2, min(8, int(3 / max(target_compression, 0.1))))
        max_sentences = max(2, min(6, int(4 / max(target_compression, 0.1))))
        
        core = {
            "topic": topic,
            "entities": entities[:max_entities],
            "question_type": question_type,
            "core_sentences": core_sentences[:max_sentences],
            "intent": intent,
            "original_length": len(user_input),
            "_essence_mode": input_data.get("_essence_mode", False),
            "_require_verification": input_data.get("_require_verification", False),
            "_attention_focus_boost": focus_boost,
            "_target_compression": target_compression,
        }
        
        try:
            from core.knowledge_graph import get_knowledge_graph
            kg = get_knowledge_graph()
            related = kg.search(topic, top_k=3)
            if related:
                core["related_knowledge"] = [r.content[:80] if hasattr(r, 'content') else str(r)[:80] for r in related]
        except Exception:
            logger.warning("操作降级跳过")
        
        try:
            from infrastructure.fact_store import get_fact_store
            fs = get_fact_store()
            conflicts = fs.search_by_keywords(entities[:3])
            if conflicts:
                core["fact_conflicts"] = [c[:80] for c in conflicts[:2]]
        except Exception:
            logger.warning("操作降级跳过")
        
        return core

    def _extract_topic(self, text: str) -> str:
        sentences = text.replace("。", ".").replace("？", "?").replace("！", "!").split(".")
        if sentences:
            first = sentences[0].strip()
            return first[:60] if len(first) > 60 else first
        return text[:60]

    def _extract_entities(self, text: str) -> List[str]:
        entities = []
        import re
        patterns = [
            r'"([^"]+)"',
            r"'([^']+)'",
            r'「([^」]+)」',
            r'【([^】]+)】',
        ]
        for p in patterns:
            for m in re.finditer(p, text):
                entities.append(m.group(1))
        
        if not entities:
            words = text.split()
            for w in words:
                if len(w) >= 2 and w[0].isupper():
                    entities.append(w)
        
        _skip_re = re.compile(r'^(?:如何|怎么|为什么|什么|哪里|哪些|的|和|与|或|在|到|从|对|是|不|没|被|把|让|给|为|及|何|之|其|此|该|这|那|一|个|种|些|上|下|中|内|外|前|后|里|间)+')
        
        zh_tech_patterns = [
            r'([A-Z][a-z]*(?:JS|js|TS|ts|API|api|SDK|sdk|URL|url|GPU|gpu|CPU|cpu|SQL|sql|DB|db|ML|ml|AI|ai|LLM|llm))\b',
            r'((?:ollama|deepseek|qwen|gemma|pytorch|tensorflow|fastapi|flask|django|react|vue|node|python|rust|golang|java|docker|kubernetes|redis|mongodb|postgres|mysql|sqlite|git|github|uvicorn|streamlit|gradio|langchain|transformers|huggingface))',
            r'([\u4e00-\u9fff]{2,4}(?:模型|架构|系统|引擎|框架|模块|服务|组件|接口|协议|算法|管线|管道|配置|监控|调度|推理|训练|优化|验证|测试|部署|容器|集群|数据库|缓存|队列|网关|代理|负载|路由|枢纽|瓶颈|残差|规范化|感知|记忆|进化|门控|适应度|经验池|向量|检索器|嵌入|编码器|解码器|注意力|变换器|生成器|判别器|分类器|回归器|聚合器|分发器|协调器|执行器|观察器|评估器|验证器|学习器|预测器|规划器|反思器|调度器|监控器|守护器|修复器|适配器|转换器|过滤器|排序器|归约器|映射器|收集器|广播器|订阅器|发布器|处理器|解析器|渲染器|编译器|解释器|调试器|分析器|优化器|序列化|反序列化))',
        ]
        for p in zh_tech_patterns:
            for m in re.finditer(p, text, re.IGNORECASE):
                entity = _skip_re.sub('', m.group(1))
                if entity not in entities and len(entity) >= 2:
                    entities.append(entity)
        
        zh_domain_patterns = [
            r'((?:CBNR|cbnr|AGI|agi|SSE|sse|REST|rest|HTTP|http|JSON|json|YAML|yaml|TCP|tcp|UDP|udp|IPC|ipc|RPC|rpc|GRPC|grpc|WebSocket|websocket|SSE|MQTT|mqtt|Kafka|kafka|RabbitMQ|AMQP))\b',
            r'([\u4e00-\u9fff]{2,6}(?:偏差|不确定性|预测编码|注意力权重|因果链|反事实|搜索树|工作记忆|棘轮|门控|适应度|经验池|精神内核|同行者|存在层|感知层|执行层|元认知层|认知规范化|认知瓶颈|认知残差|世界模型|贡献归因|主动感知|情绪检测|硬件监控|动态节流|自我评估|分层记忆|睡眠巩固|间隙生长|存在框架|五层存在|元宪法|铁律))',
        ]
        for p in zh_domain_patterns:
            for m in re.finditer(p, text, re.IGNORECASE):
                entity = _skip_re.sub('', m.group(1))
                if entity not in entities and len(entity) >= 2:
                    entities.append(entity)
        
        zh_noun_chunks = re.findall(r'[\u4e00-\u9fff]{2,8}(?:的[^\s，。？！、]{1,6})?', text)
        _stop_words = {'你好','谢谢','请问','但是','因为','所以','如果','虽然','不过','然而','而且','或者','以及','关于','对于','通过','根据','按照','需要','可以','应该','可能','已经','正在','将会','没有','不是','就是','还是','这个','那个','什么','怎么','如何','为什么','哪里','哪个','哪些','多少','几个','一下','一点','一些','这些','那些','每个','所有','任何','其他','另外','此外','同时','然后','接着','最后','首先','其次','再次','最终','目前','现在','之前','之后','以后','以前','刚才','刚刚','最近','今天','明天','昨天'}
        for chunk in zh_noun_chunks:
            chunk = _skip_re.sub('', chunk)
            if chunk in _stop_words or len(chunk) < 2:
                continue
            if any(e in chunk or chunk in e for e in entities):
                continue
            if re.match(r'^[\u4e00-\u9fff]{2,6}$', chunk) and not re.match(r'^(?:的|了|着|过|是|在|有|和|与|或|但|而|就|都|也|还|再|又|才|只|已|将|被|把|让|给|为|到|从|对|向|往|比|跟|同|与|及|或|且|则|而|因|故|遂|乃|故|遂)$', chunk):
                entities.append(chunk)
        
        return entities[:8] if entities else [text[:20]]

    def _classify_question(self, text: str) -> str:
        if any(kw in text for kw in ["为什么", "为何", "why", "原因"]):
            return "why"
        elif any(kw in text for kw in ["如何", "怎么", "how", "方法"]):
            return "how"
        elif any(kw in text for kw in ["是什么", "什么是", "what", "定义"]):
            return "what"
        elif any(kw in text for kw in ["是否", "能不能", "can", "是否可以"]):
            return "yes_no"
        elif any(kw in text for kw in ["修复", "解决", "fix", "bug"]):
            return "fix"
        else:
            return "general"

    def _extract_core_sentences(self, text: str, focus_boost: float = 1.0) -> List[str]:
        sentences = text.replace("。", ".").replace("？", "?").replace("！", "!").split(".")
        scored = []
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            score = 0
            if any(kw in s for kw in ["关键", "核心", "本质", "重要", "必须"]):
                score += 2
            if any(kw in s for kw in ["但是", "然而", "不过", "but", "however"]):
                score += 1
            if "?" in s or "？" in s:
                score += 1
            scored.append((s, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored[:3]]

    def _compute_conflict(self, result_a: Dict, result_b: Dict) -> float:
        conf_a = result_a.get("confidence", 0.5)
        conf_b = result_b.get("confidence", 0.5)
        
        chain_a = set(str(item) for item in result_a.get("causal_chain", []))
        chain_b = set(str(item) for item in result_b.get("counterfactuals", []))
        
        overlap = len(chain_a & chain_b) / max(len(chain_a | chain_b), 1)
        
        delta = abs(conf_a - conf_b) + (1.0 - overlap)
        return max(0.0, min(1.0, delta))

    def _resolve_conflict(self, causal: Dict, counterfactual: Dict, mode: ConflictMode, delta: float) -> Dict:
        if mode == ConflictMode.INTERFERENCE:
            merged = dict(causal)
            merged["counterfactuals"] = counterfactual.get("counterfactuals", [])
            merged["resolution_mode"] = "interference_fusion"
            merged["fusion_confidence"] = (causal.get("confidence", 0.5) + counterfactual.get("confidence", 0.5)) / 2
            return merged
        else:
            if causal.get("confidence", 0.5) >= counterfactual.get("confidence", 0.5):
                primary = causal
                secondary = counterfactual
            else:
                primary = counterfactual
                secondary = causal
            
            result = dict(primary)
            result["alternative_perspective"] = secondary
            result["resolution_mode"] = "localized_projection"
            result["projection_confidence"] = primary.get("confidence", 0.5)
            return result

    def _expand_to_full(self, core_result: Dict, original_input: Dict) -> Dict[str, Any]:
        output = dict(core_result)
        output["_original_intent"] = original_input.get("intent", "")
        output["_cognitive_resolution"] = original_input.get("_cognitive_resolution", "high")
        output["_max_reasoning_depth"] = original_input.get("_max_reasoning_depth", 6)
        output["_require_verification"] = original_input.get("_require_verification", False)
        output["_express_uncertainty"] = original_input.get("_express_uncertainty", False)
        output["_fallback_enabled"] = original_input.get("_fallback_enabled", False)
        return output

    def get_stats(self) -> Dict[str, Any]:
        avg_compression = sum(self._compression_history) / max(len(self._compression_history), 1)
        return {
            "process_count": self._process_count,
            "avg_compression_ratio": avg_compression,
            "conflict_threshold": self.CONFLICT_THRESHOLD,
        }