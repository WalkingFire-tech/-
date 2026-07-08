"""
语义路由器 - 让路由器自己学会路由
从规则路由升级为向量检索路由
"""
import numpy as np
import os
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from loguru import logger
from infrastructure.database_manager import DatabaseManager

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_AVAILABLE = True
except:
    EMBEDDING_AVAILABLE = False
    logger.warning("SentenceTransformer不可用，使用降级模式")


class SemanticRouter:
    """语义路由器 - 向量检索驱动的智能路由"""
    
    def __init__(self, db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
        
        # 初始化嵌入模型
        if EMBEDDING_AVAILABLE:
            try:
                os.environ['HF_HUB_OFFLINE'] = '1'
                os.environ['TRANSFORMERS_OFFLINE'] = '1'
                self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("✅ 语义路由器初始化: all-MiniLM-L6-v2")
            except:
                self.encoder = None
                logger.warning("嵌入模型加载失败，使用关键词匹配")
        else:
            self.encoder = None
        
        # 技能定义（语义描述）
        self.skills = {
            "empathy": {
                "description": "用户情绪低落、痛苦、寻求安慰，需要先承接情感，表达理解和关怀",
                "priority": 5,
                "safety_critical": True,  # 安全关键技能
                "prompt_template": "用户情绪需要关怀，请先表达理解和共情，再处理问题。"
            },
            "socratic": {
                "description": "用户犹豫不决、请求替做决定、需要引导式提问，帮助用户自己思考",
                "priority": 4,
                "safety_critical": False,
                "prompt_template": "用户需要引导，请用苏格拉底式提问帮助用户思考。"
            },
            "boundary": {
                "description": "用户触及伦理红线、极端言论、危险请求，需要先声明限制",
                "priority": 6,
                "safety_critical": True,
                "prompt_template": "触及边界，请明确声明限制，保持尊重但坚定。"
            },
            "factual": {
                "description": "用户询问事实、知识、技术问题，需要准确回答",
                "priority": 3,
                "safety_critical": False,
                "prompt_template": "用户询问事实，请提供准确、详细的信息。"
            },
            "creative": {
                "description": "用户需要创意、头脑风暴、发散思维",
                "priority": 2,
                "safety_critical": False,
                "prompt_template": "用户需要创意，请发散思维，提供多样化建议。"
            },
            "teaching": {
                "description": "用户想学习、理解概念、需要循序渐进的讲解",
                "priority": 4,
                "safety_critical": False,
                "prompt_template": "用户想学习，请循序渐进讲解，用例子帮助理解。"
            },
            "problem_solving": {
                "description": "用户遇到问题、需要解决方案、步骤指导",
                "priority": 4,
                "safety_critical": False,
                "prompt_template": "用户遇到问题，请分析原因并提供解决方案。"
            },
            "chitchat": {
                "description": "用户闲聊、打招呼、日常对话",
                "priority": 1,
                "safety_critical": False,
                "prompt_template": "用户闲聊，请自然回应，保持友好。"
            }
        }
        
        # 预计算技能向量
        self.skill_vectors = {}
        self._precompute_skill_vectors()
        
        # 反馈缓冲区（用于在线学习）
        self.feedback_buffer = []
        self.max_buffer_size = 1000
        
        # 路由历史（用于进化）
        self.routing_history = []
        
        # 加载历史路由数据
        self._load_routing_history()
    
    def _precompute_skill_vectors(self):
        """预计算技能向量"""
        if not self.encoder:
            logger.warning("无嵌入模型，跳过技能向量计算")
            return
        
        for skill_name, skill_info in self.skills.items():
            description = skill_info["description"]
            vector = self.encoder.encode(description)
            self.skill_vectors[skill_name] = vector
        
        logger.info(f"✅ 预计算{len(self.skill_vectors)}个技能向量")
    
    def encode_context(self, 
                      user_message: str,
                      emotion_score: float = 0.0,
                      dialogue_round: int = 0,
                      recent_context: str = "") -> np.ndarray:
        """
        编码用户上下文为向量
        
        Args:
            user_message: 用户消息
            emotion_score: 情绪分数 (-1到1)
            dialogue_round: 对话轮次
            recent_context: 最近对话上下文
        
        Returns:
            上下文向量
        """
        if not self.encoder:
            return None
        
        # 构建上下文文本
        context_parts = [user_message]
        
        # 添加情绪信号
        if emotion_score < -0.6:
            context_parts.append("[用户情绪低落]")
        elif emotion_score < -0.3:
            context_parts.append("[用户情绪不佳]")
        elif emotion_score > 0.3:
            context_parts.append("[用户情绪积极]")
        
        # 添加对话轮次信号
        if dialogue_round > 10:
            context_parts.append("[深度对话]")
        elif dialogue_round < 2:
            context_parts.append("[初次对话]")
        
        # 添加最近上下文
        if recent_context:
            context_parts.append(recent_context[:200])
        
        context_text = " ".join(context_parts)
        
        # 编码
        return self.encoder.encode(context_text)
    
    def route(self,
             user_message: str,
             emotion_score: float = 0.0,
             dialogue_round: int = 0,
             recent_context: str = "",
             top_k: int = 2) -> List[Tuple[str, float, str]]:
        """
        动态路由到最佳技能
        
        Returns:
            [(skill_name, confidence, prompt_template), ...]
        """
        # 1. 编码上下文
        query_vector = self.encode_context(
            user_message, emotion_score, dialogue_round, recent_context
        )
        
        if query_vector is None or not self.skill_vectors:
            # 降级到关键词匹配
            return self._fallback_route(user_message, emotion_score)
        
        # 2. 计算与所有技能的相似度
        similarities = {}
        for skill_name, skill_vector in self.skill_vectors.items():
            similarity = np.dot(query_vector, skill_vector) / (
                np.linalg.norm(query_vector) * np.linalg.norm(skill_vector)
            )
            similarities[skill_name] = similarity
        
        # 3. 排序并选择Top-K
        sorted_skills = sorted(
            similarities.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:top_k]
        
        # 4. 构建结果
        results = []
        for skill_name, similarity in sorted_skills:
            skill_info = self.skills[skill_name]
            confidence = (similarity + 1) / 2  # 归一化到0-1
            
            results.append((
                skill_name,
                confidence,
                skill_info["prompt_template"]
            ))
        
        # 5. 记录路由历史
        self._record_routing(
            user_message, 
            [r[0] for r in results], 
            [r[1] for r in results],
            emotion_score
        )
        
        return results
    
    def _fallback_route(self, 
                       user_message: str,
                       emotion_score: float) -> List[Tuple[str, float, str]]:
        """降级路由：关键词匹配"""
        # 情绪优先
        if emotion_score < -0.6:
            return [("empathy", 0.8, self.skills["empathy"]["prompt_template"])]
        
        # 关键词匹配
        message_lower = user_message.lower()
        
        if any(kw in message_lower for kw in ["为什么", "什么是", "怎么", "如何"]):
            return [("factual", 0.7, self.skills["factual"]["prompt_template"])]
        
        if any(kw in message_lower for kw in ["帮我", "应该", "选择"]):
            return [("socratic", 0.7, self.skills["socratic"]["prompt_template"])]
        
        if any(kw in message_lower for kw in ["你好", "在吗", "嗨"]):
            return [("chitchat", 0.8, self.skills["chitchat"]["prompt_template"])]
        
        # 默认
        return [("factual", 0.5, self.skills["factual"]["prompt_template"])]
    
    def record_feedback(self,
                       user_message: str,
                       chosen_skill: str,
                       user_satisfaction: float,
                       response_quality: float):
        """
        记录用户反馈，用于在线学习
        
        Args:
            user_message: 用户消息
            chosen_skill: 选择的技能
            user_satisfaction: 用户满意度 (0-1)
            response_quality: 响应质量 (0-100)
        """
        # 计算奖励
        reward = user_satisfaction * 0.6 + (response_quality / 100) * 0.4
        
        # 编码上下文
        query_vector = self.encode_context(user_message)
        
        if query_vector is not None:
            self.feedback_buffer.append({
                "query_vector": query_vector,
                "chosen_skill": chosen_skill,
                "reward": reward,
                "timestamp": datetime.now().isoformat()
            })
        
        # 缓冲区满时触发进化
        if len(self.feedback_buffer) >= self.max_buffer_size:
            self.evolve()
    
    def evolve(self):
        """
        在线学习：根据反馈微调技能向量
        
        核心思想：
        - 如果某个技能获得高奖励，向该查询向量方向微调
        - 如果某个技能获得低奖励，远离该查询向量方向
        """
        if not self.feedback_buffer or not self.encoder:
            return
        
        logger.info(f"🧬 触发路由器进化: {len(self.feedback_buffer)}条反馈")
        
        # 统计每个技能的平均奖励
        skill_rewards = {}
        skill_vectors_sum = {}
        
        for feedback in self.feedback_buffer:
            skill = feedback["chosen_skill"]
            reward = feedback["reward"]
            query_vec = feedback["query_vector"]
            
            if skill not in skill_rewards:
                skill_rewards[skill] = []
                skill_vectors_sum[skill] = np.zeros_like(query_vec)
            
            skill_rewards[skill].append(reward)
            skill_vectors_sum[skill] += query_vec * (reward - 0.5)  # 中心化
        
        # 微调技能向量
        learning_rate = 0.01
        
        for skill_name, rewards in skill_rewards.items():
            avg_reward = np.mean(rewards)
            
            if skill_name not in self.skill_vectors:
                continue
            
            # 计算调整方向
            adjustment = skill_vectors_sum[skill_name] * learning_rate
            
            # 应用调整
            self.skill_vectors[skill_name] += adjustment
            
            # 归一化
            self.skill_vectors[skill_name] /= np.linalg.norm(self.skill_vectors[skill_name])
            
            logger.info(f"  {skill_name}: 平均奖励={avg_reward:.3f}, 已微调")
        
        # 清空缓冲区
        self.feedback_buffer = []
        
        # 保存进化后的向量
        self._save_evolved_vectors()
        
        logger.info("✅ 路由器进化完成")
    
    def _record_routing(self,
                       user_message: str,
                       skills: List[str],
                       confidences: List[float],
                       emotion_score: float):
        """记录路由历史"""
        record = {
            "message": user_message[:100],
            "skills": skills,
            "confidences": confidences,
            "emotion": emotion_score,
            "timestamp": datetime.now().isoformat()
        }
        
        self.routing_history.append(record)
        
        # 限制历史长度
        if len(self.routing_history) > 10000:
            self.routing_history = self.routing_history[-5000:]
        
        # 保存到数据库
        try:
            db = DatabaseManager.get(self.db_path)
            conn = db._get_conn()
            conn.execute('''
                CREATE TABLE IF NOT EXISTS routing_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT,
                    skills TEXT,
                    confidences TEXT,
                    emotion REAL,
                    timestamp TEXT
                )
            ''')
            
            conn.execute('''
                INSERT INTO routing_history 
                (message, skills, confidences, emotion, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                record["message"],
                json.dumps(record["skills"]),
                json.dumps(record["confidences"]),
                record["emotion"],
                record["timestamp"]
            ))
            
            conn.commit()
        except Exception as e:
            logger.debug(f"记录路由历史失败: {e}")
    
    def _load_routing_history(self):
        """加载路由历史"""
        try:
            db = DatabaseManager.get(self.db_path)
            conn = db._get_conn()
            cursor = conn.execute('''
                SELECT message, skills, confidences, emotion, timestamp
                FROM routing_history
                ORDER BY timestamp DESC
                LIMIT 1000
            ''')
            
            for row in cursor.fetchall():
                self.routing_history.append({
                    "message": row[0],
                    "skills": json.loads(row[1]),
                    "confidences": json.loads(row[2]),
                    "emotion": row[3],
                    "timestamp": row[4]
                })
            
            logger.info(f"加载{len(self.routing_history)}条路由历史")
        except:
            pass
    
    def _save_evolved_vectors(self):
        """保存进化后的向量"""
        try:
            db = DatabaseManager.get(self.db_path)
            conn = db._get_conn()
            conn.execute('''
                CREATE TABLE IF NOT EXISTS skill_vectors (
                    skill_name TEXT PRIMARY KEY,
                    vector BLOB,
                    updated_at TEXT
                )
            ''')
            
            for skill_name, vector in self.skill_vectors.items():
                conn.execute('''
                    INSERT OR REPLACE INTO skill_vectors 
                    (skill_name, vector, updated_at)
                    VALUES (?, ?, ?)
                ''', (
                    skill_name,
                    vector.tobytes(),
                    datetime.now().isoformat()
                ))
            
            conn.commit()
        except Exception as e:
            logger.warning(f"保存技能向量失败: {e}")
    
    def get_routing_report(self) -> str:
        """获取路由报告"""
        if not self.routing_history:
            return "暂无路由历史"
        
        # 统计技能使用频率
        skill_counts = {}
        for record in self.routing_history:
            for skill in record["skills"]:
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
        
        # 排序
        sorted_skills = sorted(
            skill_counts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # 构建报告
        report_lines = [
            "📊 语义路由器报告",
            "=" * 40,
            f"总路由次数: {len(self.routing_history)}",
            f"技能数量: {len(self.skills)}",
            f"反馈缓冲: {len(self.feedback_buffer)}/{self.max_buffer_size}",
            "",
            "技能使用频率:"
        ]
        
        for skill, count in sorted_skills:
            percentage = count / len(self.routing_history) * 100
            report_lines.append(f"  {skill}: {count}次 ({percentage:.1f}%)")
        
        return "\n".join(report_lines)


# 全局语义路由器实例
semantic_router = SemanticRouter()
