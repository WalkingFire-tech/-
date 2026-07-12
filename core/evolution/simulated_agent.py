"""
模拟智能体 - 进化岛中的个体

每个智能体拥有：
- 独立的临时数据库（隔离主系统）
- 独立的基因组
- 独立的技能集
- 可评估的适应度
"""
import tempfile
import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
from infrastructure.database_manager import DatabaseManager


class SimulatedGenome:
    """模拟基因组 - 简化版"""
    
    def __init__(self):
        # 核心参数
        self.retrieval_threshold = 0.6      # 检索置信度阈值
        self.external_threshold = 0.55      # 外部学习触发阈值
        self.memory_decay = 0.98            # 记忆衰减率
        self.exploration = 0.3              # 探索倾向
        self.social = 0.5                   # 社交倾向
        self.answer_style = 0.5             # 回答风格（0简洁-1详细）
    
    @classmethod
    def random(cls):
        """随机生成基因组"""
        import random
        g = cls()
        g.retrieval_threshold = random.uniform(0.4, 0.8)
        g.external_threshold = random.uniform(0.3, 0.7)
        g.memory_decay = random.uniform(0.9, 0.99)
        g.exploration = random.uniform(0.0, 1.0)
        g.social = random.uniform(0.0, 1.0)
        g.answer_style = random.uniform(0.0, 1.0)
        return g
    
    @classmethod
    def from_dict(cls, data: Dict):
        """从字典创建"""
        g = cls()
        g.retrieval_threshold = data.get('retrieval_threshold', 0.6)
        g.external_threshold = data.get('external_threshold', 0.55)
        g.memory_decay = data.get('memory_decay', 0.98)
        g.exploration = data.get('exploration', 0.3)
        g.social = data.get('social', 0.5)
        g.answer_style = data.get('answer_style', 0.5)
        return g
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'retrieval_threshold': self.retrieval_threshold,
            'external_threshold': self.external_threshold,
            'memory_decay': self.memory_decay,
            'exploration': self.exploration,
            'social': self.social,
            'answer_style': self.answer_style
        }
    
    def crossover(self, other: 'SimulatedGenome') -> 'SimulatedGenome':
        """基因杂交"""
        import random
        child = SimulatedGenome()
        
        for attr in ['retrieval_threshold', 'external_threshold', 'memory_decay', 
                     'exploration', 'social', 'answer_style']:
            if random.random() < 0.5:
                setattr(child, attr, getattr(self, attr))
            else:
                setattr(child, attr, getattr(other, attr))
        
        return child
    
    def mutate(self, rate: float = 0.2) -> 'SimulatedGenome':
        """变异"""
        import random
        child = SimulatedGenome.from_dict(self.to_dict())
        
        if random.random() < rate:
            child.retrieval_threshold = max(0.4, min(0.8, 
                child.retrieval_threshold + random.uniform(-0.1, 0.1)))
        
        if random.random() < rate:
            child.external_threshold = max(0.3, min(0.7,
                child.external_threshold + random.uniform(-0.1, 0.1)))
        
        if random.random() < rate:
            child.memory_decay = max(0.9, min(0.99,
                child.memory_decay + random.uniform(-0.05, 0.05)))
        
        if random.random() < rate:
            child.exploration = max(0.0, min(1.0,
                child.exploration + random.uniform(-0.2, 0.2)))
        
        if random.random() < rate:
            child.social = max(0.0, min(1.0,
                child.social + random.uniform(-0.2, 0.2)))
        
        if random.random() < rate:
            child.answer_style = max(0.0, min(1.0,
                child.answer_style + random.uniform(-0.2, 0.2)))
        
        return child


class SimulatedAgent:
    """模拟智能体"""
    
    def __init__(self, agent_id: int, genome: SimulatedGenome, 
                 skills: List[Dict], task_pool: List[Dict]):
        self.id = agent_id
        self.genome = genome
        self.skills = skills
        self.task_pool = task_pool
        self.fitness = 0.0
        self.age = 0
        
        # 创建临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self._init_db()
        
        # 预置技能
        for skill in skills:
            self._add_skill(skill)
        
        logger.debug(f"智能体{agent_id}已创建，基因组: {genome.to_dict()}")
    
    def _init_db(self):
        """初始化临时数据库"""
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT,
                answer TEXT,
                confidence REAL DEFAULT 0.5,
                created_at TEXT
            )
        ''')
        
        db.execute('''
            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                code TEXT,
                trigger TEXT
            )
        ''', commit=True)
    
    def _add_skill(self, skill: Dict):
        """添加技能"""
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            INSERT INTO skills (name, code, trigger)
            VALUES (?, ?, ?)
        ''', (skill.get('name', ''), skill.get('code', ''), skill.get('trigger', '')), commit=True)
    
    def learn(self, question: str, answer: str, confidence: float = 0.7):
        """学习知识"""
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            INSERT INTO knowledge (question, answer, confidence, created_at)
            VALUES (?, ?, ?, ?)
        ''', (question, answer, confidence, datetime.now().isoformat()), commit=True)
    
    def retrieve(self, query: str) -> Optional[Dict]:
        """检索知识"""
        db = DatabaseManager.get(self.db_path)
        
        row = db.query_one('''
            SELECT answer, confidence FROM knowledge
            WHERE question = ?
            ORDER BY confidence DESC LIMIT 1
        ''', (query,))
        
        if row and row['confidence'] >= self.genome.retrieval_threshold:
            return {
                'answer': row['answer'],
                'confidence': row['confidence'],
                'source': 'exact'
            }
        
        row = db.query_one('''
            SELECT answer, confidence FROM knowledge
            WHERE question LIKE ?
            ORDER BY confidence DESC LIMIT 1
        ''', (f'%{query[:20]}%',))
        
        if row and row['confidence'] >= self.genome.retrieval_threshold * 0.8:
            return {
                'answer': row['answer'],
                'confidence': row['confidence'] * 0.8,
                'source': 'fuzzy'
            }
        
        return None
    
    def answer(self, question: str) -> str:
        """回答问题"""
        result = self.retrieve(question)
        
        if result:
            answer = result['answer']
            
            # 根据回答风格调整
            if self.genome.answer_style < 0.3:
                # 简洁风格
                answer = answer[:100] + ('...' if len(answer) > 100 else '')
            elif self.genome.answer_style > 0.7:
                # 详细风格（保持原样）
                pass
            
            return answer
        
        # 未找到知识，返回模拟回答
        return "[模拟] 我暂时不知道这个问题的答案"
    
    def evaluate_on_task(self, task: Dict) -> float:
        """
        在任务上评估
        
        task: {
            'question': str,
            'expected_answer': str,
            'keywords': List[str]  # 可选
        }
        
        Returns: 得分 (0-1)
        """
        question = task['question']
        expected = task.get('expected_answer', '')
        keywords = task.get('keywords', [])
        
        response = self.answer(question)
        
        # 计算相似度
        score = 0.0
        
        # 方法1：期望答案包含
        if expected and expected[:50] in response:
            score = 0.8
        elif expected and response[:50] in expected:
            score = 0.6
        
        # 方法2：关键词匹配
        if keywords:
            matched = sum(1 for kw in keywords if kw.lower() in response.lower())
            score = max(score, matched / len(keywords) * 0.7)
        
        # 方法3：长度合理性
        if not score:
            if 10 < len(response) < 500:
                score = 0.3
        
        self.fitness += score
        return score
    
    def learn_from_experience(self):
        """从情景记忆抽象出技能（认知转化：L3情景→L2技能）"""
        db = DatabaseManager.get(self.db_path)
        
        patterns = db.query('''
            SELECT question, answer, COUNT(*) as cnt
            FROM knowledge
            GROUP BY question
            HAVING cnt >= 3
            ORDER BY cnt DESC
            LIMIT 5
        ''')
        
        for row in patterns:
            question = row['question']
            answer = row['answer']
            cnt = row['cnt']
            
            existing = db.query_one('''
                SELECT 1 as found FROM skills
                WHERE trigger LIKE ?
            ''', (f'%{question[:20]}%',))
            
            if not existing:
                skill_name = f"auto_skill_{len(self.skills) + 1}"
                skill = {
                    'name': skill_name,
                    'code': f"# 自动从{cnt}次经验生成\n# 问题: {question[:50]}\n# 答案: {answer[:100]}",
                    'trigger': question[:30]
                }
                
                self._add_skill(skill)
                self.skills.append(skill)
                logger.debug(f"智能体{self.id}从经验中生成技能: {skill_name} (来自{cnt}次经验)")
    
    def cleanup(self):
        """清理临时数据库"""
        try:
            # 先关闭文件句柄
            if hasattr(self, 'temp_db') and self.temp_db:
                try:
                    self.temp_db.close()
                except Exception:
                    logger.warning("操作降级跳过")
            
            # 删除临时文件
            if hasattr(self, 'db_path') and self.db_path and os.path.exists(self.db_path):
                os.unlink(self.db_path)
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")
    
    def __del__(self):
        self.cleanup()