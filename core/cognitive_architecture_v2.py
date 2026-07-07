"""
系统重生计划 v2.0
基于六层认知进化架构的完整优化实现

优化点：
1. 层间数据契约（TypedDict）
2. 统一领域识别器
3. 外部检索备选机制（用户询问模式）
4. 语义匹配（嵌入向量）
5. 持久化进化（文件存储）
6. 元认知层（监控与诊断）
7. 用户友好输出
"""

import json
import time
import hashlib
from typing import TypedDict, Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import os

# 尝试导入可选依赖
try:
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False

# 禁用自动加载模型（避免导入时下载）
import os
if os.environ.get('DISABLE_SEMANTIC') == '1':
    SEMANTIC_AVAILABLE = False


# ==================== 数据契约定义 ====================

class BoundaryCheckResult(TypedDict):
    """存在层输出"""
    in_boundary: bool
    domain: str
    status: str
    declaration: str
    action: str
    confidence_threshold: Optional[float]


class KnowledgeAssessment(TypedDict):
    """感知层输出"""
    knows: bool
    confidence: float
    domain: str
    domain_info: Dict[str, Any]
    trigger_blind_spot: bool
    declaration: str
    action: str


class LearningResult(TypedDict):
    """学习层输出"""
    learned: bool
    sources: List[tuple]
    validated: Dict[str, Any]
    storage: Dict[str, Any]
    declaration: str
    knowledge_pieces: List[str]  # 新增：学习到的知识碎片


class IntegrationResult(TypedDict):
    """整合层输出"""
    integrated: bool
    knowledge_structure: Dict[str, Any]
    core_knowledge: List[str]
    declaration: str


class VerificationResult(TypedDict):
    """校验层输出"""
    is_valid: bool
    match_score: float
    match_details: Dict[str, Any]
    doubts: List[str]
    reverse_check: Dict[str, Any]
    declaration: str


class EvolutionResult(TypedDict):
    """进化层输出"""
    evolved: bool
    error_case: Optional[Dict[str, Any]]
    calibration: Dict[str, Any]
    gene_update: Dict[str, Any]
    declaration: str


class ProcessResult(TypedDict):
    """完整处理结果"""
    solution: str
    user_friendly_output: str  # 新增：面向用户的输出
    is_valid: bool
    thinking_chain: List[tuple]
    status: str
    meta: Dict[str, Any]  # 新增：元数据


# ==================== 统一领域识别器 ====================

class DomainIdentifier:
    """
    统一领域识别器
    所有层共享同一个实例，保证领域判断一致性
    """
    
    def __init__(self):
        self.domain_patterns = {
            '专业芯片选型': {
                'patterns': [r'推荐.*芯片', r'芯片.*选型', r'IC.*推荐', r'保护板.*芯片'],
                'keywords': ['芯片', 'IC', '选型', '推荐', '型号']
            },
            '电池管理': {
                'patterns': [r'电池', r'BMS', r'保护板', r'均衡', r'充电', r'26650', r'18650'],
                'keywords': ['电池', '保护', '均衡', '充电', '放电', 'BMS']
            },
            'LED驱动': {
                'patterns': [r'LED', r'背光', r'屏幕', r'驱动', r'亮度'],
                'keywords': ['LED', '背光', '驱动', '亮度', '显示']
            },
            '电路设计': {
                'patterns': [r'电路.*设计', r'原理图', r'PCB', r'电源.*设计'],
                'keywords': ['电路', '原理图', 'PCB', '电源', '信号']
            },
            '代码分析与生成': {
                'patterns': [r'代码', r'编程', r'函数', r'算法', r'类', r'def'],
                'keywords': ['代码', '编程', '函数', '算法', '实现']
            },
            '医学诊断': {
                'patterns': [r'诊断', r'症状', r'治疗', r'疾病', r'药物'],
                'keywords': ['诊断', '症状', '治疗', '疾病']
            },
            '法律咨询': {
                'patterns': [r'法律', r'合同', r'诉讼', r'律师', r'法规'],
                'keywords': ['法律', '合同', '诉讼', '法规']
            }
        }
        
        self.domain_embeddings = {}  # 用于语义领域识别
    
    def identify(self, problem: str) -> Dict[str, Any]:
        """识别问题所属领域"""
        
        import re
        
        matched_domains = []
        domain_scores = {}
        
        for domain, config in self.domain_patterns.items():
            score = 0
            
            # 1. 正则匹配
            for pattern in config['patterns']:
                if re.search(pattern, problem, re.IGNORECASE):
                    score += 2
            
            # 2. 关键词匹配
            for keyword in config['keywords']:
                if keyword in problem:
                    score += 1
            
            # 3. 语义匹配（如果可用）
            if SEMANTIC_AVAILABLE:
                semantic_score = self._semantic_match(problem, domain)
                score += semantic_score * 0.5
            
            if score > 0:
                matched_domains.append(domain)
                domain_scores[domain] = score
        
        # 排序
        matched_domains.sort(key=lambda d: domain_scores.get(d, 0), reverse=True)
        
        primary = matched_domains[0] if matched_domains else '通用知识'
        
        return {
            'primary_domain': primary,
            'all_matched': matched_domains,
            'domain_scores': domain_scores,
            'is_mixed': len(matched_domains) > 1
        }
    
    def _semantic_match(self, problem: str, domain: str) -> float:
        """语义匹配（使用嵌入向量）"""
        
        # 简化实现：领域关键词与问题关键词的重叠度
        domain_keywords = self.domain_patterns.get(domain, {}).get('keywords', [])
        problem_keywords = set(problem.split())
        
        overlap = len(set(domain_keywords) & problem_keywords)
        if overlap > 0:
            return overlap / len(domain_keywords)
        
        return 0.0


# ==================== 第0层：存在层 ====================

class ExistenceLayer:
    """
    第0层：存在层（身份与边界）
    优化：使用统一领域识别器
    """
    
    def __init__(self, domain_identifier: DomainIdentifier):
        self.domain_identifier = domain_identifier
        
        self.boundary_manifest = {
            '核心能力': [
                '通用知识问答',
                '代码分析与生成',
                '技术推理与解释',
                '数据分析与处理',
                '对话交互与理解'
            ],
            '扩展能力': [
                '文档学习与归纳',
                '知识库管理',
                '经验总结与反思'
            ],
            '能力边界': {
                '专业芯片选型': {
                    'status': '需要学习',
                    'confidence_threshold': 0.8,
                    'declaration': '⚠️ 芯片选型需要专业知识，我会先学习再回答'
                },
                '医学诊断': {
                    'status': '禁止回答',
                    'declaration': '⚠️ 医学诊断需要专业资质，建议咨询医生'
                },
                '法律咨询': {
                    'status': '禁止回答',
                    'declaration': '⚠️ 法律咨询需要专业律师，我无法提供建议'
                }
            }
        }
        
        self.dynamic_boundaries = []
        self.persistent_dir = "./data/boundaries/"
        os.makedirs(self.persistent_dir, exist_ok=True)
        self._load_dynamic_boundaries()
    
    def check_boundary(self, problem: str) -> BoundaryCheckResult:
        """检查问题是否在能力边界内"""
        
        # 使用统一领域识别器
        domain_info = self.domain_identifier.identify(problem)
        primary_domain = domain_info['primary_domain']
        
        if primary_domain in self.boundary_manifest['能力边界']:
            boundary_info = self.boundary_manifest['能力边界'][primary_domain]
            
            return {
                'in_boundary': False,
                'domain': primary_domain,
                'status': boundary_info['status'],
                'declaration': boundary_info['declaration'],
                'action': '需要学习' if boundary_info['status'] == '需要学习' else '拒绝回答',
                'confidence_threshold': boundary_info.get('confidence_threshold', 0.8)
            }
        
        # 检查动态边界
        if primary_domain in self.dynamic_boundaries:
            return {
                'in_boundary': True,
                'domain': primary_domain,
                'status': '可以处理',
                'declaration': f"✓ 已扩展能力边界，可处理{primary_domain}领域",
                'action': '继续处理',
                'confidence_threshold': 0.7
            }
        
        return {
            'in_boundary': True,
            'domain': primary_domain,
            'status': '可以处理',
            'declaration': f"✓ 在我的能力范围内（{primary_domain}）",
            'action': '继续处理',
            'confidence_threshold': 0.7
        }
    
    def expand_boundary(self, domain: str, confidence: float):
        """动态扩展边界"""
        
        if confidence > 0.8 and domain not in self.dynamic_boundaries:
            self.dynamic_boundaries.append(domain)
            self._save_dynamic_boundaries()
    
    def _load_dynamic_boundaries(self):
        """加载持久化边界"""
        
        path = os.path.join(self.persistent_dir, "dynamic_boundaries.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.dynamic_boundaries = data.get('boundaries', [])
            except:
                pass
    
    def _save_dynamic_boundaries(self):
        """保存动态边界"""
        
        path = os.path.join(self.persistent_dir, "dynamic_boundaries.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({'boundaries': self.dynamic_boundaries}, f, ensure_ascii=False)
        except:
            pass


# ==================== 第1层：感知层 ====================

class PerceptionLayer:
    """
    第一层：感知层（已知与未知的判断）
    优化：使用统一领域识别器，加入置信度衰减
    """
    
    def __init__(self, domain_identifier: DomainIdentifier):
        self.domain_identifier = domain_identifier
        self.confidence_threshold = 0.7
        self.domain_weights = {}
        
        # 知识时效性记录
        self.knowledge_timestamps = {}
        self.persistent_dir = "./data/perception/"
        os.makedirs(self.persistent_dir, exist_ok=True)
        self._load_knowledge_timestamps()
    
    def assess_knowledge(self, problem: str, domain: str) -> KnowledgeAssessment:
        """评估知识储备"""
        
        confidence = self._evaluate_confidence(problem, domain)
        
        # 置信度衰减（知识过时）
        decayed_confidence = self._apply_confidence_decay(domain, confidence)
        
        domain_info = self.domain_identifier.identify(problem)
        
        if decayed_confidence < self.confidence_threshold:
            return {
                'knows': False,
                'confidence': decayed_confidence,
                'domain': domain,
                'domain_info': domain_info,
                'trigger_blind_spot': True,
                'declaration': f"⚠️ 对{domain}领域的知识不确定（置信度{decayed_confidence:.0%} < {self.confidence_threshold:.0%}），需要学习",
                'action': '需要学习'
            }
        
        return {
            'knows': True,
            'confidence': decayed_confidence,
            'domain': domain,
            'domain_info': domain_info,
            'trigger_blind_spot': False,
            'declaration': f"✓ 了解{domain}领域（置信度{decayed_confidence:.0%}）",
            'action': '可以直接回答'
        }
    
    def _evaluate_confidence(self, problem: str, domain: str) -> float:
        """置信度评估器"""
        
        try:
            # 从内部知识检索获取置信度
            from core.learning import enhanced_learner
            result = enhanced_learner.retrieve_knowledge(problem)
            
            if result:
                base_confidence = result.get('confidence', 0.5)
                domain_weight = self.domain_weights.get(domain, 1.0)
                return min(base_confidence * domain_weight, 1.0)
        except:
            pass
        
        # 基于领域复杂度的默认置信度
        domain_complexity = {
            '专业芯片选型': 0.3,
            '电池管理': 0.4,
            'LED驱动': 0.4,
            '代码分析与生成': 0.6,
            '通用知识': 0.7
        }
        
        return domain_complexity.get(domain, 0.4)
    
    def _apply_confidence_decay(self, domain: str, confidence: float) -> float:
        """应用置信度衰减（知识时效性）"""
        
        if domain in self.knowledge_timestamps:
            last_update = self.knowledge_timestamps[domain]
            days_passed = (time.time() - last_update) / (24 * 3600)
            
            # 每30天衰减5%
            decay_rate = 0.05 * (days_passed / 30)
            decayed = confidence * (1 - min(decay_rate, 0.3))
            
            return max(decayed, 0.1)
        
        return confidence
    
    def update_timestamp(self, domain: str):
        """更新知识时间戳"""
        
        self.knowledge_timestamps[domain] = time.time()
        self._save_knowledge_timestamps()
    
    def _load_knowledge_timestamps(self):
        """加载知识时间戳"""
        
        path = os.path.join(self.persistent_dir, "knowledge_timestamps.json")
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.knowledge_timestamps = json.load(f)
            except:
                pass
    
    def _save_knowledge_timestamps(self):
        """保存知识时间戳"""
        
        path = os.path.join(self.persistent_dir, "knowledge_timestamps.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_timestamps, f, ensure_ascii=False)
        except:
            pass


# ==================== 第2层：学习层 ====================

class LearningLayer:
    """
    第二层：学习层（主动获取知识）
    优化：外部检索失败时启动用户询问模式
    """
    
    def __init__(self):
        self.knowledge_store = {}  # 短期知识存储
        self.pending_questions = []  # 待询问用户的问题
    
    def learn(self, problem: str, domain: str, reason: str) -> LearningResult:
        """强制学习流程"""
        
        learning_sources = []
        knowledge_pieces = []
        
        # 1. 内部检索
        internal_result = self._internal_search(problem)
        learning_sources.append(('内部检索', internal_result))
        if internal_result.get('found'):
            knowledge_pieces.extend(internal_result.get('knowledge', []))
        
        # 2. 外部检索
        external_result = self._external_search(problem, domain)
        learning_sources.append(('外部检索', external_result))
        if external_result.get('found'):
            knowledge_pieces.extend(external_result.get('knowledge', []))
        
        # 3. 如果外部检索失败，准备用户询问模式
        if not self._has_valid_sources(learning_sources):
            self._prepare_user_questions(problem, domain)
        
        # 4. 交叉验证
        validated = self._cross_validate(learning_sources)
        
        # 5. 动态存储
        storage_result = self._dynamic_store(problem, knowledge_pieces)
        
        return {
            'learned': len(knowledge_pieces) > 0,
            'sources': learning_sources,
            'validated': validated,
            'storage': storage_result,
            'declaration': f"✓ 学习完成，从{len(learning_sources)}个来源获取信息，交叉验证{'通过' if validated['valid'] else '未完全通过'}",
            'knowledge_pieces': knowledge_pieces
        }
    
    def _internal_search(self, problem: str) -> Dict[str, Any]:
        """内部检索"""
        
        try:
            from core.learning import enhanced_learner
            result = enhanced_learner.retrieve_knowledge(problem)
            
            if result:
                return {
                    'found': True,
                    'knowledge': result.get('knowledge', []),
                    'confidence': result.get('confidence', 0.5),
                    'source': '知识库'
                }
        except:
            pass
        
        return {'found': False, 'source': '知识库'}
    
    def _external_search(self, problem: str, domain: str) -> Dict[str, Any]:
        """外部检索"""
        
        try:
            from core.external_learner import external_learner
            result = external_learner.learn_from_external(
                user_input=problem,
                context=f"领域：{domain}",
                trigger_reason="感知层触发学习"
            )
            
            if result:
                return {
                    'found': True,
                    'knowledge': result.get('knowledge', []),
                    'source': '外部搜索'
                }
        except:
            pass
        
        return {'found': False, 'source': '外部搜索'}
    
    def _has_valid_sources(self, sources: List[tuple]) -> bool:
        """检查是否有有效来源"""
        
        for _, source_data in sources:
            if source_data.get('found'):
                return True
        return False
    
    def _prepare_user_questions(self, problem: str, domain: str):
        """准备用户询问模式"""
        
        questions = []
        
        if '电池' in problem or '保护' in problem:
            questions.append("请问您的电池组是几串的？（例如：3串12.6V，4串16.8V）")
            questions.append("您需要被动均衡还是主动均衡？")
        
        if '芯片' in problem and '推荐' in problem:
            questions.append("请问您对芯片品牌有偏好吗？（例如：TI、ADI、国产）")
            questions.append("您对成本有什么要求？")
        
        self.pending_questions = questions
    
    def get_pending_questions(self) -> List[str]:
        """获取待询问的问题"""
        return self.pending_questions
    
    def _cross_validate(self, sources: List[tuple]) -> Dict[str, Any]:
        """交叉验证"""
        
        valid_sources = [s for s in sources if s[1].get('found')]
        
        if len(valid_sources) >= 2:
            return {
                'valid': True,
                'source_count': len(valid_sources),
                'declaration': f"✓ {len(valid_sources)}个来源交叉验证通过"
            }
        
        return {
            'valid': False,
            'source_count': len(valid_sources),
            'declaration': f"⚠️ 仅{len(valid_sources)}个来源，需要更多验证"
        }
    
    def _dynamic_store(self, problem: str, knowledge: List[str]) -> Dict[str, Any]:
        """动态存储"""
        
        key = hashlib.md5(problem.encode()).hexdigest()
        self.knowledge_store[key] = {
            'problem': problem,
            'knowledge': knowledge,
            'timestamp': time.time()
        }
        
        return {
            'stored': True,
            'storage_type': '短期记忆',
            'key': key
        }


# ==================== 第3层：整合层 ====================

class IntegrationLayer:
    """
    第三层：整合层（知识结构化）
    优化：实现真正的知识提炼算法
    """
    
    def __init__(self):
        self.knowledge_graph = {}
    
    def integrate(self, learning_result: LearningResult) -> IntegrationResult:
        """整合知识"""
        
        knowledge_pieces = learning_result.get('knowledge_pieces', [])
        
        # 1. 信息聚类
        clustered = self._cluster_information(knowledge_pieces)
        
        # 2. 冲突消解
        resolved = self._resolve_conflicts(clustered)
        
        # 3. 知识提炼
        refined = self._refine_knowledge(resolved)
        
        # 4. 知识图谱更新
        self._update_graph(refined)
        
        return {
            'integrated': True,
            'knowledge_structure': refined,
            'core_knowledge': refined.get('core_knowledge', []),
            'declaration': f"✓ 整合完成，提炼出{len(refined.get('core_knowledge', []))}个核心知识点"
        }
    
    def _cluster_information(self, knowledge: List[str]) -> Dict[str, Any]:
        """信息聚类"""
        
        if not knowledge:
            return {'clusters': {}, 'raw': knowledge}  # 修复：空字典而非空列表
        
        # 使用关键词聚类
        clusters = {}
        for item in knowledge:
            # 简单聚类：提取关键词
            words = item.split()
            key_words = [w for w in words if len(w) > 2]
            for kw in key_words[:3]:  # 取前3个关键词
                if kw not in clusters:
                    clusters[kw] = []
                clusters[kw].append(item)
        
        return {
            'clusters': clusters,
            'cluster_count': len(clusters),
            'raw': knowledge
        }
    
    def _resolve_conflicts(self, clustered: Dict[str, Any]) -> Dict[str, Any]:
        """冲突消解"""
        
        # 简化实现：按出现频率解决冲突
        resolved = {}
        
        for cluster_name, items in clustered.get('clusters', {}).items():
            # 去重并统计频率
            from collections import Counter
            freq = Counter(items)
            resolved[cluster_name] = freq.most_common(3)
        
        return {
            'resolved': True,
            'conflicts_resolved': len(clustered.get('clusters', {})) - len(resolved),
            'resolved_data': resolved
        }
    
    def _refine_knowledge(self, resolved: Dict[str, Any]) -> Dict[str, Any]:
        """知识提炼"""
        
        core_knowledge = []
        
        for cluster_name, items in resolved.get('resolved_data', {}).items():
            if items:
                # 取最高频的内容
                core_knowledge.append(f"{cluster_name}: {items[0][0]}")
        
        return {
            'refined': True,
            'core_knowledge': core_knowledge,
            'full_resolved': resolved
        }
    
    def _update_graph(self, refined: Dict[str, Any]):
        """更新知识图谱"""
        
        for item in refined.get('core_knowledge', []):
            key = hashlib.md5(item.encode()).hexdigest()
            self.knowledge_graph[key] = {
                'knowledge': item,
                'timestamp': time.time()
            }


# ==================== 第4层：校验层 ====================

class VerificationLayer:
    """
    第四层：校验层（输出前的强制防线）
    优化：引入语义匹配（嵌入向量）
    """
    
    def __init__(self):
        self.match_threshold = 0.75  # 降低阈值，因为语义匹配更准确
        
        # 初始化嵌入模型（如果可用）- 使用共享模型
        self.embed_model = None
        if SEMANTIC_AVAILABLE:
            try:
                from core.shared_embedding import get_embedding_model
                self.embed_model = get_embedding_model()
            except:
                self.embed_model = None
    
    def verify(self, problem: str, solution: str) -> VerificationResult:
        """强制校验流程"""
        
        # 1. 语义匹配度评分
        match_result = self._calculate_match_score_enhanced(problem, solution)
        
        # 2. 自我质疑列表
        doubts = self._generate_doubts_enhanced(problem, solution)
        
        # 3. 反向推演
        reverse_result = self._reverse_reasoning_enhanced(problem, solution)
        
        # 4. 综合判断
        is_valid = (
            match_result['score'] >= self.match_threshold and
            len(doubts) == 0 and
            reverse_result['valid']
        )
        
        return {
            'is_valid': is_valid,
            'match_score': match_result['score'],
            'match_details': match_result,
            'doubts': doubts,
            'reverse_check': reverse_result,
            'declaration': f"{'✅ 校验通过' if is_valid else '⚠️ 校验未完全通过'}（匹配度{match_result['score']:.0%}）"
        }
    
    def _calculate_match_score_enhanced(self, problem: str, solution: str) -> Dict[str, Any]:
        """增强版匹配度评分（语义 + 关键词）"""
        
        # 1. 关键词匹配
        keyword_score = self._keyword_match(problem, solution)
        
        # 2. 语义匹配（如果可用）
        semantic_score = 0.0
        if self.embed_model and SEMANTIC_AVAILABLE:
            try:
                problem_emb = self.embed_model.encode(problem)
                solution_emb = self.embed_model.encode(solution)
                semantic_score = float(cosine_similarity(
                    [problem_emb], [solution_emb]
                )[0][0])
            except:
                semantic_score = 0.5
        
        # 3. 需求-功能匹配
        requirement_match = self._requirement_match(problem, solution)
        
        # 4. 综合得分
        if self.embed_model and SEMANTIC_AVAILABLE:
            final_score = semantic_score * 0.5 + keyword_score * 0.3 + requirement_match * 0.2
        else:
            final_score = keyword_score * 0.6 + requirement_match * 0.4
        
        return {
            'score': final_score,
            'semantic_similarity': semantic_score,
            'keyword_score': keyword_score,
            'requirement_match': requirement_match,
            'requirements': self._extract_requirements(problem),
            'features': self._extract_features(solution)
        }
    
    def _keyword_match(self, problem: str, solution: str) -> float:
        """关键词匹配度"""
        
        problem_keywords = set(problem.split())
        solution_keywords = set(solution.split())
        
        if not problem_keywords:
            return 0.5
        
        overlap = len(problem_keywords & solution_keywords)
        return overlap / len(problem_keywords)
    
    def _requirement_match(self, problem: str, solution: str) -> float:
        """需求-功能匹配度"""
        
        requirements = self._extract_requirements(problem)
        features = self._extract_features(solution)
        
        if not requirements:
            return 0.5
        
        matched = 0
        for req in requirements:
            if any(req in feat for feat in features):
                matched += 1
        
        return matched / len(requirements)
    
    def _extract_requirements(self, problem: str) -> List[str]:
        """提取需求关键词"""
        
        import re
        requirements = []
        
        patterns = {
            '适配电池型号': r'26650|18650|21700|电池',
            '均衡功能': r'平衡|均衡|balanc',
            '保护功能': r'保护|overvoltage|overcurrent|protection',
            '串数适配': r'[0-9]+串|串|S'
        }
        
        for req, pattern in patterns.items():
            if re.search(pattern, problem, re.IGNORECASE):
                requirements.append(req)
        
        return requirements if requirements else ['通用需求']
    
    def _extract_features(self, solution: str) -> List[str]:
        """提取方案功能"""
        
        features = []
        
        if any(kw in solution for kw in ['均衡', '平衡']):
            features.append('均衡功能')
        
        if any(kw in solution for kw in ['保护', 'overvoltage', 'overcurrent']):
            features.append('保护功能')
        
        if any(kw in solution for kw in ['26650', '18650', '电池']):
            features.append('适配电池')
        
        return features if features else ['通用功能']
    
    def _generate_doubts_enhanced(self, problem: str, solution: str) -> List[str]:
        """增强版自我质疑"""
        
        doubts = []
        
        import re
        chips = re.findall(r'(TPS\d+|BQ\d+|SH\d+|RT\d+|SC\d+)', solution)
        
        if chips:
            chip = chips[0]
            
            # 领域检查（使用领域识别）
            problem_domain = domain_identifier.identify(problem)['primary_domain']
            
            # 芯片型号与领域匹配检查
            chip_domain_map = {
                'TPS': 'LED驱动',
                'BQ': '电池管理',
                'SH': '通用电源',
                'SC': '通用电源',
                'RT': '通用电源'
            }
            
            chip_prefix = chip[:3]
            chip_domain = chip_domain_map.get(chip_prefix, '未知')
            
            if problem_domain != chip_domain and chip_domain != '未知':
                doubts.append(f"⚠️ {chip}属于{chip_domain}领域，但您的问题涉及{problem_domain}领域")
        
        # 功能匹配检查
        if '均衡' in problem and '均衡' not in solution:
            doubts.append("⚠️ 您的需求包含'均衡功能'，但推荐方案中未明确提及")
        
        if '保护' in problem and '保护' not in solution:
            doubts.append("⚠️ 您的需求包含'保护功能'，但推荐方案中未明确提及")
        
        return doubts
    
    def _reverse_reasoning_enhanced(self, problem: str, solution: str) -> Dict[str, Any]:
        """增强版反向推演"""
        
        import re
        possible_errors = []
        
        # 如果我是错的，最可能错在哪里？
        if '推荐' in problem and '芯片' in problem:
            # 检查推荐是否合理
            chips = re.findall(r'(TPS\d+|BQ\d+|SH\d+|RT\d+)', solution)
            if chips and '26650' in problem:
                # 检查芯片是否适合26650（粗略检查）
                if chips[0].startswith('TPS'):
                    possible_errors.append("TPS系列一般是LED或电源管理芯片，可能不适合电池保护")
        
        return {
            'valid': len(possible_errors) == 0,
            'possible_errors': possible_errors,
            'reasoning': "反向推演完成",
            'error_count': len(possible_errors)
        }


# ==================== 数据驱动反思降级方案 ====================

class DataDrivenReflectionFallback:
    """
    数据驱动反思降级方案
    在无LLM时，通过数据模式识别实现反思
    """
    
    def __init__(self):
        self.error_patterns = {
            'domain_confusion': {
                'indicators': [
                    ('TPS', ['电池', '保护', 'BMS']),  # TPS芯片用于电池保护
                    ('LED', ['电池', '保护']),  # LED芯片用于电池保护
                ],
                'severity': 'high'
            },
            'functional_mismatch': {
                'indicators': [
                    ('均衡', ['均衡']),  # 需要均衡但方案不含均衡
                    ('保护', ['保护']),  # 需要保护但方案不含保护
                ],
                'severity': 'medium'
            },
            'content_anomaly': {
                'indicators': [
                    ('error', []),  # 包含错误信息
                    ('exception', []),  # 包含异常信息
                ],
                'severity': 'low'
            }
        }
    
    def detect_patterns(self, problem: str, solution: str, feedback: str = None) -> List[Dict]:
        """检测错误模式"""
        import re
        
        detected = []
        
        # 检测1：领域混淆（芯片型号与问题领域不匹配）
        # TPS芯片通常用于LED驱动，不应用于电池保护
        if 'TPS' in solution:
            if any(kw in problem for kw in ['电池', '保护', 'BMS', '均衡']):
                detected.append({
                    'pattern_type': 'domain_confusion',
                    'problem': problem,
                    'solution': solution,
                    'feedback': f"检测到领域混淆: TPS芯片用于电池保护",
                    'severity': 'high'
                })
        
        # LED芯片不应用于电池保护
        if 'LED' in solution:
            if any(kw in problem for kw in ['电池', '保护']):
                detected.append({
                    'pattern_type': 'domain_confusion',
                    'problem': problem,
                    'solution': solution,
                    'feedback': f"检测到领域混淆: LED芯片用于电池保护",
                    'severity': 'high'
                })
        
        # 检测2：功能不匹配（需求功能未在方案中体现）
        if '均衡' in problem and '均衡' not in solution:
            detected.append({
                'pattern_type': 'functional_mismatch',
                'problem': problem,
                'solution': solution,
                'feedback': "检测到功能不匹配: 缺少均衡功能",
                'severity': 'medium'
            })
        
        if '保护' in problem and '保护' not in solution:
            detected.append({
                'pattern_type': 'functional_mismatch',
                'problem': problem,
                'solution': solution,
                'feedback': "检测到功能不匹配: 缺少保护功能",
                'severity': 'medium'
            })
        
        # 检测3：内容异常
        if 'error' in solution.lower() or 'exception' in solution.lower():
            detected.append({
                'pattern_type': 'content_anomaly',
                'problem': problem,
                'solution': solution,
                'feedback': "检测到内容异常: 包含错误信息",
                'severity': 'low'
            })
        
        # 检测4：用户反馈
        if feedback and any(kw in feedback for kw in ['错误', '不对', '不正确', '不是']):
            detected.append({
                'pattern_type': 'user_feedback',
                'problem': problem,
                'solution': solution,
                'feedback': feedback,
                'severity': 'high'
            })
        
        return detected


# ==================== 第5层：进化层 ====================

class EvolutionLayer:
    """
    第五层：进化层（从每次交互中成长）
    优化：
    1. 持久化存储（文件存储）
    2. 数据驱动反思（无LLM时降级）
    """
    
    def __init__(self):
        self.persistent_dir = "./data/evolution/"
        os.makedirs(self.persistent_dir, exist_ok=True)
        
        self.error_archive = []
        self.behavior_patterns = {}
        self.gene_parameters = {}
        
        # 数据驱动反思引擎（降级方案）
        self.data_driven_reflection = DataDrivenReflectionFallback()
        
        self._load_state()
    
    def evolve(self, problem: str, solution: str, 
               is_correct: bool, feedback: str = None) -> EvolutionResult:
        """即时进化（支持数据驱动反思）"""
        
        if not is_correct:
            error_case = self._archive_error(problem, solution, feedback)
            calibration = self._calibrate_behavior(error_case)
            gene_update = self._update_gene(error_case)
            
            # 数据驱动反思（检测更多错误模式）
            additional_errors = self.data_driven_reflection.detect_patterns(
                problem, solution, feedback
            )
            
            if additional_errors:
                for err in additional_errors:
                    self._archive_error(
                        err['problem'],
                        err['solution'],
                        err.get('feedback')
                    )
            
            self._save_state()
            
            return {
                'evolved': True,
                'error_case': error_case,
                'calibration': calibration,
                'gene_update': gene_update,
                'declaration': "✅ 错误已归档，行为已校准，基因已更新"
            }
        
        return {
            'evolved': False,
            'error_case': None,
            'calibration': {},
            'gene_update': {},
            'declaration': "✅ 回答正确，能力已验证"
        }
    
    def _archive_error(self, problem: str, solution: str, 
                      feedback: str) -> Dict[str, Any]:
        """错误案例自动归档"""
        
        error_type = self._classify_error(problem, solution)
        
        error_case = {
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
            'problem': problem,
            'wrong_solution': solution,
            'feedback': feedback or '用户未提供具体反馈',
            'error_type': error_type,
            'improvement_suggestion': self._generate_improvement(problem, solution),
            'id': hashlib.md5(f"{problem}{time.time()}".encode()).hexdigest()
        }
        
        self.error_archive.append(error_case)
        
        # 限制归档大小（保留最近100条）
        if len(self.error_archive) > 100:
            self.error_archive = self.error_archive[-100:]
        
        return error_case
    
    def _calibrate_behavior(self, error_case: Dict[str, Any]) -> Dict[str, Any]:
        """行为模式校准"""
        
        error_type = error_case.get('error_type', '未知错误')
        
        if error_type not in self.behavior_patterns:
            self.behavior_patterns[error_type] = {
                'count': 0,
                'last_occurrence': None,
                'examples': []
            }
        
        self.behavior_patterns[error_type]['count'] += 1
        self.behavior_patterns[error_type]['last_occurrence'] = error_case['timestamp']
        self.behavior_patterns[error_type]['examples'].append({
            'problem': error_case['problem'][:100],
            'solution': error_case['wrong_solution'][:100]
        })
        
        return {
            'calibrated': True,
            'error_type': error_type,
            'occurrence_count': self.behavior_patterns[error_type]['count']
        }
    
    def _update_gene(self, error_case: Dict[str, Any]) -> Dict[str, Any]:
        """基因演化更新"""
        
        error_type = error_case.get('error_type', '未知错误')
        
        # 更新基因参数
        if error_type == '领域混淆':
            self.gene_parameters['domain_check_weight'] = \
                self.gene_parameters.get('domain_check_weight', 1.0) * 1.1
        
        elif error_type == '知识缺失':
            self.gene_parameters['learning_priority'] = \
                self.gene_parameters.get('learning_priority', 1.0) * 1.05
        
        elif error_type == '校验失败':
            self.gene_parameters['verification_strictness'] = \
                self.gene_parameters.get('verification_strictness', 1.0) * 1.1
        
        # 记录基因版本
        self.gene_parameters['version'] = self.gene_parameters.get('version', 0) + 1
        self.gene_parameters['last_update'] = time.time()
        
        return {
            'updated': True,
            'gene_parameters': self.gene_parameters,
            'version': self.gene_parameters['version']
        }
    
    def _classify_error(self, problem: str, solution: str) -> str:
        """分类错误类型"""
        
        import re
        
        if any(kw in problem for kw in ['芯片', 'IC', '选型']):
            # 检查是否领域混淆
            
            # 方法1：直接检查关键词
            if any(kw in solution for kw in ['LED', '背光']):
                return '领域混淆'
            
            # 方法2：检查芯片型号前缀
            chips = re.findall(r'(TPS\d+|BQ\d+|SH\d+|RT\d+)', solution)
            if chips:
                chip = chips[0]
                
                # TPS通常是LED驱动或电源管理芯片
                if chip.startswith('TPS'):
                    # 如果问题是电池保护相关，则是领域混淆
                    if any(kw in problem for kw in ['电池', '保护', 'BMS', '均衡']):
                        return '领域混淆'
            
            return '专业选型错误'
        
        if '均衡' in problem and '均衡' not in solution:
            return '功能缺失'
        
        return '一般错误'
    
    def _generate_improvement(self, problem: str, solution: str) -> str:
        """生成改进建议"""
        
        import re
        
        if '芯片' in problem:
            # 检查是否推荐了LED芯片
            if 'LED' in solution:
                return "增加领域判断前置步骤，输出前强制校验芯片所属领域"
            
            # 检查芯片型号
            chips = re.findall(r'(TPS\d+|BQ\d+|SH\d+|RT\d+)', solution)
            if chips and chips[0].startswith('TPS'):
                if any(kw in problem for kw in ['电池', '保护', 'BMS']):
                    return "增加芯片型号与领域匹配检查，TPS系列通常不适用于电池保护"
        
        if '均衡' in problem and '均衡' not in solution:
            return "校验层需要强化功能匹配检查，确保推荐方案覆盖用户所有需求"
        
        return "建议在输出前进行更严格的自我质疑"
    
    def _load_state(self):
        """加载持久化状态"""
        
        # 加载错误归档
        path_errors = os.path.join(self.persistent_dir, "error_archive.json")
        if os.path.exists(path_errors):
            try:
                with open(path_errors, 'r', encoding='utf-8') as f:
                    self.error_archive = json.load(f)
            except:
                pass
        
        # 加载行为模式
        path_patterns = os.path.join(self.persistent_dir, "behavior_patterns.json")
        if os.path.exists(path_patterns):
            try:
                with open(path_patterns, 'r', encoding='utf-8') as f:
                    self.behavior_patterns = json.load(f)
            except:
                pass
        
        # 加载基因参数
        path_genes = os.path.join(self.persistent_dir, "gene_parameters.json")
        if os.path.exists(path_genes):
            try:
                with open(path_genes, 'r', encoding='utf-8') as f:
                    self.gene_parameters = json.load(f)
            except:
                pass
    
    def _save_state(self):
        """保存持久化状态"""
        
        # 保存错误归档
        path_errors = os.path.join(self.persistent_dir, "error_archive.json")
        try:
            with open(path_errors, 'w', encoding='utf-8') as f:
                json.dump(self.error_archive, f, ensure_ascii=False, indent=2)
        except:
            pass
        
        # 保存行为模式
        path_patterns = os.path.join(self.persistent_dir, "behavior_patterns.json")
        try:
            with open(path_patterns, 'w', encoding='utf-8') as f:
                json.dump(self.behavior_patterns, f, ensure_ascii=False, indent=2)
        except:
            pass
        
        # 保存基因参数
        path_genes = os.path.join(self.persistent_dir, "gene_parameters.json")
        try:
            with open(path_genes, 'w', encoding='utf-8') as f:
                json.dump(self.gene_parameters, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """获取进化统计"""
        
        return {
            'error_count': len(self.error_archive),
            'error_types': self.behavior_patterns,
            'gene_version': self.gene_parameters.get('version', 0)
        }


# ==================== 元认知层 ====================

class MetaCognitiveLayer:
    """
    元认知层：观察者模式，监控所有层的运行状态
    新增：独立于六层之外的监控与诊断层
    """
    
    def __init__(self):
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'learning_triggered': 0,
            'verification_failed': 0,
            'layers_performance': {}
        }
        self.alert_thresholds = {
            'verification_failure_rate': 0.3,  # 30%
            'learning_trigger_rate': 0.5,      # 50%
        }
        self.alerts = []
    
    def observe(self, process_result: ProcessResult):
        """观察一次处理过程"""
        
        self.metrics['total_requests'] += 1
        
        if process_result.get('is_valid', False):
            self.metrics['successful_requests'] += 1
        else:
            self.metrics['failed_requests'] += 1
        
        # 记录每层表现
        for layer_name, layer_result in process_result.get('thinking_chain', []):
            if layer_name not in self.metrics['layers_performance']:
                self.metrics['layers_performance'][layer_name] = {
                    'count': 0,
                    'declarations': []
                }
            self.metrics['layers_performance'][layer_name]['count'] += 1
            if isinstance(layer_result, dict):
                self.metrics['layers_performance'][layer_name]['declarations'].append(
                    layer_result.get('declaration', '')
                )
        
        # 检查告警条件
        self._check_alerts()
    
    def _check_alerts(self):
        """检查告警条件"""
        
        total = self.metrics['total_requests']
        if total == 0:
            return
        
        # 校验失败率
        failed = self.metrics['failed_requests']
        failure_rate = failed / total
        
        if failure_rate > self.alert_thresholds['verification_failure_rate']:
            self.alerts.append({
                'level': 'warning',
                'message': f"⚠️ 校验失败率过高：{failure_rate:.1%}，建议检查校验层逻辑",
                'timestamp': time.time()
            })
        
        # 学习触发率
        learning = self.metrics['learning_triggered']
        if learning > 0 and learning / total > self.alert_thresholds['learning_trigger_rate']:
            self.alerts.append({
                'level': 'info',
                'message': f"📊 学习触发率较高：{learning/total:.1%}，系统在积极学习新知识",
                'timestamp': time.time()
            })
        
        # 只保留最近10条告警
        if len(self.alerts) > 10:
            self.alerts = self.alerts[-10:]
    
    def get_diagnosis(self) -> Dict[str, Any]:
        """获取系统诊断"""
        
        total = self.metrics['total_requests']
        if total == 0:
            return {'status': 'no_data', 'message': '尚未有足够数据进行分析'}
        
        failure_rate = self.metrics['failed_requests'] / total
        
        # 判断系统健康状态
        if failure_rate < 0.1:
            status = 'healthy'
            message = '✅ 系统运行健康，校验成功率良好'
        elif failure_rate < 0.3:
            status = 'moderate'
            message = '⚠️ 系统表现尚可，但存在优化空间'
        else:
            status = 'degraded'
            message = '⚠️ 系统表现需要关注，建议检查校验层'
        
        return {
            'status': status,
            'message': message,
            'metrics': {
                'total_requests': total,
                'success_rate': (1 - failure_rate) * 100,
                'learning_triggered': self.metrics['learning_triggered']
            },
            'alerts': self.alerts[-5:],
            'layers': self.metrics['layers_performance']
        }


# ==================== 完整的六层认知进化架构 ====================

class CognitiveEvolutionArchitecture:
    """
    六层认知进化架构 - 完整实现
    
    包含：存在层 → 感知层 → 学习层 → 整合层 → 校验层 → 进化层
    新增：元认知层（监控与诊断）
    """
    
    def __init__(self):
        # 统一领域识别器
        self.domain_identifier = DomainIdentifier()
        
        # 第0层：存在层
        self.existence = ExistenceLayer(self.domain_identifier)
        
        # 第一层：感知层
        self.perception = PerceptionLayer(self.domain_identifier)
        
        # 第二层：学习层
        self.learning = LearningLayer()
        
        # 第三层：整合层
        self.integration = IntegrationLayer()
        
        # 第四层：校验层
        self.verification = VerificationLayer()
        
        # 第五层：进化层
        self.evolution = EvolutionLayer()
        
        # 元认知层
        self.metacognition = MetaCognitiveLayer()
        
        # 对话状态
        self.conversation_state = {
            'turn_count': 0,
            'last_problem': None,
            'last_solution': None
        }
    
    def process(self, problem: str) -> ProcessResult:
        """
        完整的认知进化流程
        
        每个问题都必须经过这六层处理 + 元认知监控
        """
        
        self.conversation_state['turn_count'] += 1
        
        thinking_chain = []
        solution = None
        is_valid = True
        user_friendly_parts = []
        
        # ========== 第0层：存在层 ==========
        boundary_check = self.existence.check_boundary(problem)
        thinking_chain.append(('存在层', boundary_check))
        
        if boundary_check['status'] == '禁止回答':
            return {
                'solution': boundary_check['declaration'],
                'user_friendly_output': boundary_check['declaration'],
                'is_valid': False,
                'thinking_chain': thinking_chain,
                'status': '拒绝回答',
                'meta': self.metacognition.get_diagnosis()
            }
        
        # ========== 第一层：感知层 ==========
        domain = boundary_check.get('domain', '通用')
        knowledge_assessment = self.perception.assess_knowledge(problem, domain)
        thinking_chain.append(('感知层', knowledge_assessment))
        user_friendly_parts.append(knowledge_assessment['declaration'])
        
        # ========== 第二层：学习层 ==========
        if not knowledge_assessment['knows'] or boundary_check['status'] == '需要学习':
            learning_result = self.learning.learn(
                problem, 
                domain,
                knowledge_assessment['declaration']
            )
            thinking_chain.append(('学习层', learning_result))
            self.metacognition.metrics['learning_triggered'] += 1
            
            user_friendly_parts.append(learning_result['declaration'])
            
            # 检查是否有待询问的问题
            pending_questions = self.learning.get_pending_questions()
            if pending_questions:
                return {
                    'solution': "\n".join(pending_questions),
                    'user_friendly_output': f"📝 为了更好地回答您的问题，我需要先确认以下信息：\n\n" + "\n".join(f"• {q}" for q in pending_questions),
                    'is_valid': True,
                    'thinking_chain': thinking_chain,
                    'status': '需要更多信息',
                    'meta': self.metacognition.get_diagnosis()
                }
            
            # ========== 第三层：整合层 ==========
            integration_result = self.integration.integrate(learning_result)
            thinking_chain.append(('整合层', integration_result))
            user_friendly_parts.append(integration_result['declaration'])
        
        # ========== 生成方案 ==========
        solution = self._generate_solution(problem, thinking_chain)
        
        # ========== 第四层：校验层 ==========
        verification_result = self.verification.verify(problem, solution)
        thinking_chain.append(('校验层', verification_result))
        user_friendly_parts.append(verification_result['declaration'])
        
        if not verification_result['is_valid']:
            is_valid = False
            self.metacognition.metrics['verification_failed'] += 1
            
            # 生成改进方案
            if verification_result.get('doubts'):
                solution = f"⚠️ 我的初步方案存在以下问题：\n\n" + "\n".join(f"• {doubt}" for doubt in verification_result['doubts']) + "\n\n我需要重新学习并给出更准确的回答。"
        
        # ========== 构建用户友好输出 ==========
        user_friendly_output = self._build_user_friendly_output(
            problem, solution, verification_result, is_valid
        )
        
        # ========== 元认知观察 ==========
        process_result = {
            'solution': solution,
            'user_friendly_output': user_friendly_output,
            'is_valid': is_valid,
            'thinking_chain': thinking_chain,
            'status': '完成' if is_valid else '需要修正',
            'meta': self.metacognition.get_diagnosis()
        }
        self.metacognition.observe(process_result)
        
        # ========== 更新感知层时间戳 ==========
        self.perception.update_timestamp(domain)
        
        # 存储当前状态
        self.conversation_state['last_problem'] = problem
        self.conversation_state['last_solution'] = solution
        
        return process_result
    
    def _generate_solution(self, problem: str, thinking_chain: List[tuple]) -> str:
        """生成解决方案"""
        
        # 从思考链中提取关键信息
        solution_parts = []
        
        for layer_name, layer_result in thinking_chain:
            if isinstance(layer_result, dict):
                if layer_name == '整合层':
                    core_knowledge = layer_result.get('core_knowledge', [])
                    if core_knowledge:
                        solution_parts.extend(core_knowledge)
                elif layer_name == '学习层':
                    knowledge_pieces = layer_result.get('knowledge_pieces', [])
                    if knowledge_pieces:
                        solution_parts.extend(knowledge_pieces)
        
        if solution_parts:
            # 如果有学习到的知识，基于知识生成方案
            return f"基于学习到的信息，我的推荐是：\n" + "\n".join(f"• {part}" for part in solution_parts[:5])
        
        # 通用方案生成
        return f"关于「{problem}」的建议：\n根据我的理解，这是一个需要专业知识的领域。我建议您提供更多具体信息（如应用场景、技术参数），以便我能给出更精准的建议。"
    
    def _build_user_friendly_output(self, problem: str, solution: str, 
                                    verification_result: VerificationResult, 
                                    is_valid: bool) -> str:
        """构建用户友好输出"""
        
        parts = []
        
        # 状态指示
        if is_valid:
            parts.append("✅ 我的回答已通过内部校验")
        else:
            parts.append("⚠️ 我的回答需要您进一步确认")
        
        # 匹配度
        match_score = verification_result.get('match_score', 0)
        if match_score > 0.8:
            parts.append(f"📊 需求匹配度：{match_score:.0%}（较高）")
        elif match_score > 0.6:
            parts.append(f"📊 需求匹配度：{match_score:.0%}（中等）")
        else:
            parts.append(f"📊 需求匹配度：{match_score:.0%}（较低，建议进一步确认）")
        
        # 自我质疑
        doubts = verification_result.get('doubts', [])
        if doubts:
            parts.append("\n⚠️ 以下是我对自己回答的质疑：")
            parts.extend(f"  • {doubt}" for doubt in doubts)
        
        # 解决方案
        parts.append(f"\n📝 {solution}")
        
        return "\n".join(parts)
    
    def get_evolution_stats(self) -> Dict[str, Any]:
        """获取进化统计"""
        return self.evolution.get_stats()
    
    def get_diagnosis(self) -> Dict[str, Any]:
        """获取系统诊断"""
        return self.metacognition.get_diagnosis()


# ==================== 全局实例 ====================

# 创建全局实例
domain_identifier = DomainIdentifier()
cognitive_architecture = CognitiveEvolutionArchitecture()


# ==================== 测试 ====================

def test_architecture():
    """测试六层认知进化架构"""
    
    print("=" * 70)
    print("系统重生计划 v2.0 - 测试运行")
    print("=" * 70)
    
    test_problems = [
        "推荐一款26650的锂电保护板控制芯片，需要带平衡功能",
        "如何治疗感冒？",  # 应该被拒绝
        "帮我分析这段代码的性能问题",  # 在能力范围内
    ]
    
    for problem in test_problems:
        print(f"\n{'='*50}")
        print(f"问题: {problem}")
        print(f"{'='*50}")
        
        result = cognitive_architecture.process(problem)
        
        print(f"\n【用户友好输出】")
        print(result['user_friendly_output'])
        
        if result.get('thinking_chain'):
            print(f"\n【思考链摘要】")
            for layer_name, layer_result in result['thinking_chain']:
                if isinstance(layer_result, dict):
                    decl = layer_result.get('declaration', '')
                    if decl:
                        print(f"  [{layer_name}] {decl[:80]}...")
        
        print(f"\n状态: {result['status']}")
        print(f"有效性: {'✅' if result['is_valid'] else '⚠️'}")
    
    # 显示诊断
    print("\n" + "=" * 70)
    print("【系统诊断】")
    print("=" * 70)
    diagnosis = cognitive_architecture.get_diagnosis()
    print(f"状态: {diagnosis.get('message', 'N/A')}")
    
    # 显示进化统计
    print("\n" + "=" * 70)
    print("【进化统计】")
    print("=" * 70)
    stats = cognitive_architecture.get_evolution_stats()
    print(f"错误归档数: {stats.get('error_count', 0)}")
    print(f"基因版本: {stats.get('gene_version', 0)}")
    print(f"行为模式: {list(stats.get('error_types', {}).keys())}")


if __name__ == "__main__":
    test_architecture()