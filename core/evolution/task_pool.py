"""
任务池构建器 - 从主系统历史对话构建进化任务
"""
from infrastructure.database_manager import DatabaseManager
import json
import re
from typing import List, Dict
from loguru import logger


def build_task_pool(main_db_path: str, 
                   min_confidence: float = 0.5,
                   max_tasks: int = 200,
                   include_keywords: bool = True) -> List[Dict]:
    """
    从主知识库中抽取高质量问答对作为任务池
    
    Args:
        main_db_path: 主数据库路径
        min_confidence: 最低置信度
        max_tasks: 最大任务数
        include_keywords: 是否提取关键词
    
    Returns:
        [
            {
                'question': str,
                'expected_answer': str,
                'keywords': List[str],
                'difficulty': float  # 0-1, 1最难
            }
        ]
    """
    tasks = []
    
    try:
        conn = DatabaseManager.get(main_db_path)._get_conn()
        
        # 查询高质量问答
        cur = conn.execute('''
            SELECT question, answer, salience, access_count, quality_score
            FROM knowledge_items
            WHERE knowledge_type = 'qa' 
            AND answer IS NOT NULL
            AND LENGTH(answer) > 10
            AND (salience >= ? OR quality_score >= 50)
            ORDER BY salience DESC, access_count DESC
            LIMIT ?
        ''', (min_confidence, max_tasks * 2))
        
        rows = cur.fetchall()
        
        for row in rows:
            question = row['question']
            answer = row['answer']
            
            if not question or not answer:
                continue
            
            keywords = []
            if include_keywords:
                keywords = self._extract_keywords_advanced(answer, question)
            
            difficulty = self._calculate_difficulty_advanced(question, answer)
            
            tasks.append({
                'question': question,
                'expected_answer': answer[:300],
                'keywords': keywords,
                'difficulty': difficulty,
                'original_salience': row['salience'] or 0.5
            })
        
        # 去重（基于问题相似度）
        unique_tasks = []
        seen_questions = set()
        
        for task in tasks:
            q_key = task['question'][:30]
            if q_key not in seen_questions:
                seen_questions.add(q_key)
                unique_tasks.append(task)
        
        tasks = unique_tasks[:max_tasks]
        
        logger.info(f"任务池构建完成: {len(tasks)}个任务")
            
    except Exception as e:
        logger.error(f"构建任务池失败: {e}")
    
    return tasks


def load_existing_skills(main_db_path: str) -> List[Dict]:
    """
    从主系统加载现有技能
    
    Returns:
        [
            {
                'name': str,
                'code': str,
                'trigger': str,
                'usage_count': int
            }
        ]
    """
    skills = []
    
    try:
        conn = DatabaseManager.get(main_db_path)._get_conn()
        
        cur = conn.execute('''
            SELECT name, code, description, triggers, usage_count
            FROM tools
            WHERE code IS NOT NULL
            ORDER BY usage_count DESC
            LIMIT 20
        ''')
        
        for row in cur.fetchall():
            triggers = json.loads(row['triggers']) if row['triggers'] else []
            trigger = triggers[0] if triggers else row['name']
            
            skills.append({
                'name': row['name'],
                'code': row['code'][:500],
                'trigger': trigger,
                'usage_count': row['usage_count']
            })
        
        logger.info(f"加载技能: {len(skills)}个")
            
    except Exception as e:
        logger.error(f"加载技能失败: {e}")
    
    return skills


def create_sample_tasks() -> List[Dict]:
    """创建示例任务（当主库为空时）"""
    return [
        {
            'question': '什么是深度学习？',
            'expected_answer': '深度学习是机器学习的一个分支，使用多层神经网络进行特征学习和模式识别。',
            'keywords': ['神经网络', '机器学习', '特征'],
            'difficulty': 0.3
        },
        {
            'question': '如何优化Python代码性能？',
            'expected_answer': '可以使用列表推导式、生成器、避免全局变量、使用内置函数、考虑Cython或Numba加速。',
            'keywords': ['列表推导式', '生成器', 'Cython'],
            'difficulty': 0.5
        },
        {
            'question': '什么是向量检索？',
            'expected_answer': '向量检索是将文本转换为向量后，通过计算向量相似度来查找相关内容的技术。',
            'keywords': ['向量', '相似度', '文本'],
            'difficulty': 0.4
        },
        {
            'question': '如何处理内存泄漏？',
            'expected_answer': '可以使用内存分析工具检测、检查循环引用、使用弱引用、及时释放资源、避免全局变量累积。',
            'keywords': ['内存分析', '循环引用', '弱引用'],
            'difficulty': 0.6
        },
        {
            'question': '什么是三层记忆模型？',
            'expected_answer': '三层记忆模型包括L1核心记忆（永久）、L2框架记忆（长期）、L3情境碎片（可遗忘）。',
            'keywords': ['L1', 'L2', 'L3', '记忆'],
            'difficulty': 0.4
        }
    ]
    
    def _extract_keywords_advanced(self, answer: str, question: str = "") -> List[str]:
        """
        高级关键词提取
        
        使用多策略提取：
        1. TF-IDF风格的重要词提取
        2. 领域特定词识别
        3. 问题-答案关联词提取
        """
        import re
        from collections import Counter
        
        stopwords = {
            '的', '是', '在', '有', '和', '了', '不', '这', '那', '就', '也',
            '都', '会', '能', '要', '可以', '应该', '需要', '一个', '这个',
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'can', 'to', 'of',
            'in', 'for', 'on', 'with', 'at', 'by', 'from', 'as'
        }
        
        domain_keywords = {
            '系统', '架构', '模块', '组件', '接口', '配置', '参数',
            '函数', '方法', '类', '对象', '变量', '类型',
            '数据', '存储', '缓存', '队列', '栈', '堆',
            '算法', '优化', '性能', '效率', '复杂度',
            '学习', '训练', '模型', '特征', '预测', '推理',
            '记忆', '知识', '经验', '规则', '策略',
            '层', '级', '维度', '向量', '矩阵'
        }
        
        text = f"{question} {answer}"
        words = re.findall(r'\w+', text.lower())
        
        word_freq = Counter(w for w in words if len(w) > 2 and w not in stopwords)
        
        scored_words = []
        for word, freq in word_freq.items():
            score = freq
            
            if word in domain_keywords:
                score *= 2.0
            
            if word in answer and word in question:
                score *= 1.5
            
            if re.match(r'^[A-Z]{2,}$', word.upper()):
                score *= 1.3
            
            if re.match(r'.*化$', word):
                score *= 1.2
            
            scored_words.append((word, score))
        
        scored_words.sort(key=lambda x: x[1], reverse=True)
        
        keywords = [word for word, score in scored_words[:8]]
        
        return keywords
    
    def _calculate_difficulty_advanced(self, question: str, answer: str) -> float:
        """
        高级难度计算
        
        多维度难度评估：
        1. 内容长度和复杂度
        2. 概念密度
        3. 抽象程度
        4. 逻辑复杂度
        5. 领域专业度
        """
        difficulty = 0.0
        
        length = len(answer)
        if length < 100:
            difficulty += 0.2
        elif length < 300:
            difficulty += 0.3
        elif length < 600:
            difficulty += 0.5
        elif length < 1000:
            difficulty += 0.7
        else:
            difficulty += 0.9
        
        import re
        sentences = re.split(r'[。！？\n]', answer)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) > 5:
            difficulty += 0.1
        if len(sentences) > 10:
            difficulty += 0.1
        
        technical_patterns = [
            r'\w+系统', r'\w+架构', r'\w+层', r'\w+模块',
            r'\w+机制', r'\w+算法', r'\w+模型',
            r'L\d+', r'\d+维度', r'\d+个'
        ]
        
        tech_count = sum(
            1 for pattern in technical_patterns
            if re.search(pattern, answer)
        )
        difficulty += min(0.2, tech_count * 0.05)
        
        abstract_indicators = [
            '抽象', '泛化', '归纳', '推理', '推断',
            '原理', '本质', '机制', '规律', '模式'
        ]
        if any(ind in answer for ind in abstract_indicators):
            difficulty += 0.15
        
        logic_indicators = [
            '如果', '那么', '因此', '因为', '所以',
            '首先', '然后', '最后', '步骤', '流程'
        ]
        logic_count = sum(1 for ind in logic_indicators if ind in answer)
        difficulty += min(0.15, logic_count * 0.03)
        
        code_indicators = ['```', 'def ', 'class ', 'import ', 'return ']
        if any(ind in answer for ind in code_indicators):
            difficulty += 0.2
        
        math_indicators = [r'\d+\.\d+', r'\d+%', r'=', r'\+', r'-', r'\*', r'/']
        math_count = sum(
            1 for pattern in math_indicators
            if re.search(pattern, answer)
        )
        difficulty += min(0.1, math_count * 0.02)
        
        return min(1.0, difficulty)