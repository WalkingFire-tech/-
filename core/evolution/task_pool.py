"""
任务池构建器 - 从主系统历史对话构建进化任务
"""
import sqlite3
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
        with sqlite3.connect(main_db_path) as conn:
            conn.row_factory = sqlite3.Row
            
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
                
                # 提取关键词
                keywords = []
                if include_keywords:
                    # 从答案中提取关键词
                    words = re.findall(r'\w+', answer.lower())
                    keywords = [w for w in words if len(w) > 3][:5]
                
                # 计算难度（基于长度和复杂度）
                difficulty = min(1.0, len(answer) / 500.0)
                
                tasks.append({
                    'question': question,
                    'expected_answer': answer[:300],  # 截取前300字符
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
        with sqlite3.connect(main_db_path) as conn:
            conn.row_factory = sqlite3.Row
            
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
                    'code': row['code'][:500],  # 限制代码长度
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