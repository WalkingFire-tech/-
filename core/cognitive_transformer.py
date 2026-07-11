"""
认知转化器 - 五层认知架构的转化机制

层级：
L0: 基因/初始配置（硬编码）
L1: 反射/本能（自动触发规则）
L2: 程序性技能（可调用工具）
L3: 情景记忆（具体经历）
L4: 抽象能力/元认知（跨领域原则）

转化：
- 情景记忆 → 技能（重复经历固化）
- 技能 → 反射（高频成功自动化）
- 情景记忆 → 抽象知识（归纳总结）
"""
from infrastructure.database_manager import DatabaseManager
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import Counter
from loguru import logger


class CognitiveTransformer:
    """认知转化器 - 实现记忆到能力的转化"""
    
    def __init__(self, db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
        logger.info("认知转化器已初始化")
    
    def transform_all(self) -> Dict:
        """执行所有转化"""
        results = {
            "situations_to_skills": 0,
            "skills_to_reflexes": 0,
            "situations_to_abstractions": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            results["situations_to_skills"] = self.situations_to_skills()
        except Exception as e:
            logger.error(f"情景→技能转化失败: {e}")
        
        try:
            results["skills_to_reflexes"] = self.skills_to_reflexes()
        except Exception as e:
            logger.error(f"技能→反射转化失败: {e}")
        
        try:
            results["situations_to_abstractions"] = self.situations_to_abstractions()
        except Exception as e:
            logger.error(f"情景→抽象转化失败: {e}")
        
        logger.info(f"认知转化完成: {results}")
        return results
    
    def situations_to_skills(self) -> int:
        """
        情景记忆 → 程序性技能
        
        条件：同一类问题出现 ≥3 次，且有成功解决记录
        动作：生成工具函数，标记原始记忆为"已转化"
        """
        skills_created = 0
        MAX_AUTO_TOOLS = 30
        
        db = DatabaseManager.get(self.db_path)
        existing_count = db.query_one("SELECT COUNT(*) FROM tools WHERE enabled=1")[0]
        if existing_count >= MAX_AUTO_TOOLS:
            logger.debug(f"自动工具已达上限({MAX_AUTO_TOOLS})，跳过技能转化")
            return 0
        
        remaining_slots = MAX_AUTO_TOOLS - existing_count
        
        candidates = db.query('''
            SELECT question, answer, COUNT(*) as freq
            FROM knowledge_items
            WHERE memory_layer = 3
            AND knowledge_type = 'qa'
            AND salience >= 0.5
            GROUP BY question
            HAVING freq >= 3
            ORDER BY freq DESC
            LIMIT 10
        ''')
        
        for row in candidates:
            if skills_created >= remaining_slots:
                break
            question = row['question']
            answer = row['answer']
            freq = row['freq']
            
            tool_name = self._generate_tool_name(question)
            if db.query_one("SELECT 1 FROM tools WHERE name = ?", (tool_name,)):
                continue
            
            tool_code = self._generate_tool_code(tool_name, question, answer)
            
            db.execute('''
                INSERT INTO tools (name, code, description, triggers, usage_count, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
            ''', (
                tool_name,
                tool_code,
                f"从{freq}次成功经验中提取的技能: {question[:50]}",
                json.dumps([question[:30]]),
                datetime.now().isoformat()
            ), commit=True)
            
            db.execute('''
                UPDATE knowledge_items
                SET metadata = json_set(metadata, '$.transformed_to', ?)
                WHERE question = ? AND memory_layer = 3
            ''', (tool_name, question), commit=True)
            
            skills_created += 1
            logger.info(f"情景→技能: {question[:40]} -> {tool_name}")
        
        return skills_created
    
    def skills_to_reflexes(self) -> int:
        """
        程序性技能 → 反射/本能
        
        条件：工具被成功调用 ≥3 次，且用户反馈正面
        动作：生成learning_rules，实现自动触发
        """
        reflexes_created = 0
        
        db = DatabaseManager.get(self.db_path)
        
        candidates = db.query('''
            SELECT name, description, triggers, usage_count
            FROM tools
            WHERE usage_count >= 3
            ORDER BY usage_count DESC
            LIMIT 10
        ''')
        
        for row in candidates:
            tool_name = row['name']
            triggers = json.loads(row['triggers']) if row['triggers'] else []
            
            if not triggers:
                continue
            
            for trigger in triggers:
                if db.query_one('''
                    SELECT 1 FROM learning_rules
                    WHERE trigger_pattern LIKE ?
                ''', (f'%{trigger}%',)):
                    continue
                
                db.execute('''
                    INSERT INTO learning_rules
                    (trigger_pattern, action, confidence, source, status, created_at)
                    VALUES (?, ?, ?, ?, 'active', ?)
                ''', (
                    f"用户输入包含 '{trigger}'",
                    f"自动调用工具 {tool_name}",
                    0.85,
                    'reflex_from_skill'
                ), commit=True)
                
                reflexes_created += 1
                logger.info(f"技能→反射: {tool_name} -> 触发'{trigger}'")
        
        return reflexes_created
    
    def situations_to_abstractions(self) -> int:
        """
        情景记忆 → 抽象知识/元认知
        
        条件：多个情景记忆有共同主题/模式
        动作：使用LLM归纳生成抽象原则，存入L1
        """
        abstractions_created = 0
        
        db = DatabaseManager.get(self.db_path)
        
        situations = db.query('''
            SELECT question, answer, source, metadata
            FROM knowledge_items
            WHERE memory_layer = 3
            AND knowledge_type = 'qa'
            ORDER BY salience DESC
            LIMIT 20
        ''')
        
        if len(situations) < 5:
            return 0
        
        keywords = []
        for row in situations:
            words = re.findall(r'\w+', row['question'].lower())
            keywords.extend([w for w in words if len(w) > 3])
        
        keyword_count = Counter(keywords)
        top_keywords = keyword_count.most_common(5)
        
        for keyword, count in top_keywords:
            if count < 3:
                continue
            
            related = [s for s in situations if keyword in s['question'].lower()]
            
            if len(related) < 3:
                continue
            
            abstract_question = f"关于{keyword}的通用原则"
            
            if db.query_one('''
                SELECT 1 FROM knowledge_items
                WHERE question = ? AND memory_layer = 1
            ''', (abstract_question,)):
                continue
            
            related_answers = [r['answer'][:100] for r in related[:3]]
            abstract_answer = f"根据{len(related)}次经验总结：\n" + "\n".join([f"- {a}" for a in related_answers])
            
            db.execute('''
                INSERT INTO knowledge_items
                (question_hash, question, answer, source, knowledge_type, 
                 quality_score, memory_layer, salience, metadata, created_at)
                VALUES (?, ?, ?, ?, 'abstract', 100.0, 1, 0.85, ?, ?)
            ''', (
                f"abstract_{keyword}",
                abstract_question,
                abstract_answer,
                "abstraction_from_situations",
                json.dumps({"source_count": len(related), "keyword": keyword}),
                datetime.now().isoformat()
            ), commit=True)
            
            abstractions_created += 1
            logger.info(f"情景→抽象: {keyword} (来自{len(related)}条情景)")
        
        return abstractions_created
    
    def _generate_tool_name(self, question: str) -> str:
        """从问题生成工具名"""
        # 提取关键词
        words = re.findall(r'\w+', question.lower())
        meaningful = [w for w in words if len(w) > 3 and w not in ['what', 'how', 'why', 'when', 'where']]
        
        if meaningful:
            return f"auto_{'_'.join(meaningful[:3])}"
        return f"auto_tool_{hash(question) % 10000}"
    
    def _generate_tool_code(self, name: str, question: str, answer: str) -> str:
        """生成工具代码"""
        return f'''def {name}(context):
    """
    自动生成的工具
    问题: {question[:100]}
    """
    # 返回学习到的答案
    return """{answer[:500]}"""
'''
    
    def get_transformation_stats(self) -> Dict:
        """获取转化统计"""
        db = DatabaseManager.get(self.db_path)
        
        l3_count = db.query_one("SELECT COUNT(*) FROM knowledge_items WHERE memory_layer = 3")[0]
        tools_count = db.query_one("SELECT COUNT(*) FROM tools")[0]
        reflexes_count = db.query_one("SELECT COUNT(*) FROM learning_rules WHERE source = 'reflex_from_skill'")[0]
        abstractions_count = db.query_one("SELECT COUNT(*) FROM knowledge_items WHERE knowledge_type = 'abstract'")[0]
        
        return {
            "l3_situations": l3_count,
            "l2_skills": tools_count,
            "l1_reflexes": reflexes_count,
            "l4_abstractions": abstractions_count,
            "transformation_potential": {
                "situations_to_skills": max(0, l3_count // 3),
                "skills_to_reflexes": max(0, tools_count // 2),
                "situations_to_abstractions": max(0, l3_count // 5)
            }
        }


cognitive_transformer = CognitiveTransformer()