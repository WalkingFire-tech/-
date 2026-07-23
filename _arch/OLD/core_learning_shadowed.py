"""
增强学习模块 - 主动学习、规则生成、工具自动生成
"""
import json
import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import Counter
from loguru import logger
from core.ports.adapters import get_storage_port


class EnhancedLearner:
    """增强学习器 - 实现主动学习、规则生成、工具生成"""
    
    def __init__(self, db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(exist_ok=True)
        self._init_db()
        
        try:
            from core.vector_store import VectorStore
            self.vector_store = VectorStore()
            logger.info("向量存储已集成")
        except Exception as e:
            self.vector_store = None
            logger.warning(f"向量存储集成失败: {e}")
        
        logger.info("增强学习器已初始化")
    
    def _init_db(self):
        """初始化数据库"""
        db = get_storage_port(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS knowledge_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_hash TEXT UNIQUE,
                question TEXT,
                answer TEXT,
                source TEXT,
                intent_type TEXT,
                knowledge_type TEXT DEFAULT 'qa',
                quality_score REAL DEFAULT 100.0,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                created_at TEXT,
                metadata TEXT
            );
            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                code TEXT,
                description TEXT,
                triggers TEXT,
                usage_count INTEGER DEFAULT 0,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS learning_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trigger_pattern TEXT,
                action TEXT,
                confidence REAL DEFAULT 0.7,
                source TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_question_hash ON knowledge_items(question_hash);
            CREATE INDEX IF NOT EXISTS idx_knowledge_type ON knowledge_items(knowledge_type)
        ''')
        
        try:
            db.execute('ALTER TABLE knowledge_items ADD COLUMN memory_layer INTEGER DEFAULT 2')
        except Exception:
            logger.warning("操作降级跳过")
        
        try:
            db.execute('ALTER TABLE knowledge_items ADD COLUMN salience REAL DEFAULT 0.5')
        except Exception:
            logger.warning("操作降级跳过")
        
        try:
            db.execute('ALTER TABLE knowledge_items ADD COLUMN emotional_valence REAL DEFAULT 0.0')
        except Exception:
            logger.warning("操作降级跳过")
        
        try:
            db.execute('ALTER TABLE knowledge_items ADD COLUMN context_snapshot TEXT')
        except Exception:
            logger.warning("操作降级跳过")
        
        try:
            db.execute('ALTER TABLE knowledge_items ADD COLUMN environmental_triggers TEXT')
        except Exception:
            logger.warning("操作降级跳过")
    
    def learn_from_file(self, filename: str, content: str, context: Dict = None, environmental_triggers: str = None) -> int:
        """从文件学习 - 提取结构化知识"""
        
        knowledge_count = 0
        env_trigger = environmental_triggers or filename
        
        # 1. 提取文件整体摘要
        summary = self._extract_file_summary(filename, content)
        if summary:
            self._save_knowledge(
                question=f"{filename} 的主要内容",
                answer=summary,
                source=f"file:{filename}",
                knowledge_type="code_file",
                metadata={
                    'filename': filename,
                    'language': self._detect_language(filename),
                    'type': 'file_summary',
                    'environmental_triggers': env_trigger
                }
            )
            knowledge_count += 1
        
        # 2. 提取函数知识点
        functions = self._extract_functions(content, filename)
        for func in functions:
            self._save_knowledge(
                question=f"函数 {func['name']} 的作用是什么？",
                answer=func['description'],
                source=f"file:{filename}",
                knowledge_type="function",
                metadata={
                    'function_name': func['name'],
                    'filename': filename,
                    'code': func['code'][:500]
                }
            )
            knowledge_count += 1
        
        # 3. 提取类知识点
        classes = self._extract_classes(content, filename)
        for cls in classes:
            self._save_knowledge(
                question=f"类 {cls['name']} 的作用是什么？",
                answer=cls['description'],
                source=f"file:{filename}",
                knowledge_type="class",
                metadata={
                    'class_name': cls['name'],
                    'filename': filename
                }
            )
            knowledge_count += 1
        
        # 4. 提取代码片段作为潜在工具
        self._extract_code_snippets(content, filename)
        
        logger.info(f"从文件 {filename} 学习到 {knowledge_count} 条知识")
        return knowledge_count
    
    def learn_from_conversation(self, question: str, answer: str, feedback: int = 0) -> bool:
        """从对话学习"""
        
        # 只有正面反馈才保存
        if feedback > 0:
            return self._save_knowledge(
                question=question,
                answer=answer[:1000],
                source="user_feedback_positive",
                knowledge_type="qa",
                metadata={
                    'feedback': feedback,
                    'type': 'conversation_learning'
                }
            )
        return False
    
    def learn_with_external(self, user_input: str, context: str = "", 
                            response_text: str = None, confidence: float = 1.0,
                            auto_trigger: bool = True) -> Dict[str, Any]:
        """
        智能学习：自动判断是否需要外部学习
        
        Args:
            user_input: 用户输入
            context: 对话上下文
            response_text: 系统回复（用于置信度判断）
            confidence: 置信度（0-1）
            auto_trigger: 是否自动触发外部学习
        
        Returns:
            {
                "external_triggered": bool,
                "reason": str,
                "new_knowledge_count": int,
                "items": List[Dict]
            }
        """
        from core.external_learner import external_learner, should_trigger_external_learning
        
        result = {
            "external_triggered": False,
            "reason": "",
            "new_knowledge_count": 0,
            "items": []
        }
        
        if not auto_trigger:
            return result
        
        knowledge_count = 0
        try:
            db = get_storage_port(self.db_path)
            row = db.query_one(
                'SELECT COUNT(*) FROM knowledge_items WHERE question LIKE ?',
                (f'%{user_input[:20]}%',)
            )
            knowledge_count = row[0] if row else 0
        except Exception:
            logger.warning("操作降级跳过")
        
        should_trigger, reason = should_trigger_external_learning(
            user_input, response_text, confidence, knowledge_count
        )
        
        if should_trigger:
            result["external_triggered"] = True
            result["reason"] = reason
            
            try:
                items = external_learner.learn_from_external(user_input, context, reason)
                saved_count = external_learner.save_to_knowledge_base(items)
                
                result["new_knowledge_count"] = saved_count
                result["items"] = items
                
                logger.info(f"外部学习完成: {reason}, 新增{saved_count}条知识")
            except Exception as e:
                logger.error(f"外部学习失败: {e}")
        
        return result
    
    def detect_and_create_rules(self):
        """检测重复模式并生成规则"""
        
        rules_created = 0
        db = get_storage_port(self.db_path)
        
        try:
            rows = db.query('SELECT question FROM knowledge_items WHERE knowledge_type = "qa"')
            questions = [row['question'] for row in rows]
        except Exception:
            questions = []
        
        keyword_count = Counter()
        for q in questions:
            words = re.findall(r'\w+', q.lower())
            for word in words:
                if len(word) > 3:
                    keyword_count[word] += 1
        
        for keyword, count in keyword_count.most_common(20):
            if count >= 2:
                try:
                    row = db.query_one(
                        'SELECT 1 FROM learning_rules WHERE trigger_pattern LIKE ?',
                        (f'%{keyword}%',)
                    )
                    if not row:
                        db.execute('''
                            INSERT INTO learning_rules 
                            (trigger_pattern, action, confidence, source, created_at)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            f"用户问题包含关键词 '{keyword}'",
                            f"优先从知识库检索关于'{keyword}'的知识",
                            min(0.9, 0.5 + count * 0.1),
                            'auto_generated',
                            datetime.now().isoformat()
                        ), commit=True)
                        rules_created += 1
                except Exception:
                    continue
        
        if rules_created > 0:
            logger.info(f"自动生成 {rules_created} 条学习规则")
        
        return rules_created
    
    def feedback_on_knowledge(self, question: str, positive: bool):
        """用户反馈影响记忆重要性"""
        delta = 0.1 if positive else -0.15
        question_hash = hashlib.md5(question.lower().encode()).hexdigest()
        
        db = get_storage_port(self.db_path)
        db.execute('''
            UPDATE knowledge_items
            SET salience = MIN(1.0, MAX(0.0, salience + ?))
            WHERE question_hash = ?
        ''', (delta, question_hash), commit=True)
        
        logger.info(f"用户反馈: {question[:30]}... ({'正面' if positive else '负面'})")
    
    def mark_as_important(self, question: str) -> bool:
        """刻骨铭心 - 手动标记为永久记忆"""
        question_hash = hashlib.md5(question.lower().strip().encode()).hexdigest()
        
        db = get_storage_port(self.db_path)
        db.execute('''
            UPDATE knowledge_items
            SET memory_layer = 1,
                salience = 0.9,
                emotional_valence = 1.0
            WHERE question_hash = ?
        ''', (question_hash,), commit=True)
        
        row = db.query_one('SELECT changes()')
        changes = row[0] if row else 0
        
        if changes > 0:
            logger.info(f"刻骨铭心: {question[:30]}...")
            return True
        return False
    
    def get_last_qa(self, limit: int = 1) -> List[Dict]:
        """获取最近学习的问答对（用于 :important 命令）"""
        db = get_storage_port(self.db_path)
        rows = db.query('''
            SELECT question, answer, source, created_at
            FROM knowledge_items
            WHERE knowledge_type = 'qa'
            ORDER BY created_at DESC LIMIT ?
        ''', (limit,))
        return [dict(row) for row in rows]
    
    def match_environmental_triggers(self, current_file: str = None, current_topic: str = None) -> List[tuple]:
        """根据当前环境（文件路径、话题）检索相关记忆，返回 (答案, 相似度)"""
        if not current_file and not current_topic:
            return []
        
        query_parts = []
        if current_file:
            query_parts.append(current_file)
        if current_topic:
            query_parts.append(current_topic)
        query = " ".join(query_parts)
        
        # 使用向量检索匹配
        if self.vector_store:
            try:
                vector_results = self.vector_store.search(query, top_k=3, threshold=0.7)
                matches = []
                for dist, meta in vector_results:
                    layer = meta.get('layer', 2)
                    salience = meta.get('salience', 0)
                    if layer <= 2 and salience > 0.4:
                        matches.append((meta.get('answer', ''), 1-dist))
                return matches
            except Exception as e:
                logger.error(f"环境触发器匹配失败: {e}")
        
        return []
    
    def get_recently_forgotten(self, days: int = 7) -> List[Dict]:
        """获取最近遗忘的记忆（用于回忆通知）"""
        db = get_storage_port(self.db_path)
        rows = db.query('''
            SELECT question, answer, source, created_at
            FROM knowledge_items
            WHERE salience < 0.2
            AND memory_layer = 3
            AND julianday('now') - julianday(last_accessed) <= ?
            ORDER BY last_accessed DESC
            LIMIT 5
        ''', (days,))
        
        return [dict(row) for row in rows]
    
    def get_memory_review(self) -> Dict:
        """获取记忆回顾报告"""
        db = get_storage_port(self.db_path)
        
        row = db.query_one('''
            SELECT COUNT(*) as count
            FROM knowledge_items
            WHERE memory_layer = 1
        ''')
        l1_count = row['count'] if row else 0
        
        row = db.query_one('''
            SELECT COUNT(*) as count
            FROM knowledge_items
            WHERE memory_layer = 2
        ''')
        l2_count = row['count'] if row else 0
        
        row = db.query_one('''
            SELECT COUNT(*) as count
            FROM knowledge_items
            WHERE memory_layer = 3 AND salience < 0.3
        ''')
        l3_fading = row['count'] if row else 0
        
        rows = db.query('''
            SELECT question, access_count, last_accessed
            FROM knowledge_items
            WHERE access_count > 0
            ORDER BY access_count DESC
            LIMIT 5
        ''')
        hot_memories = [dict(row) for row in rows]
        
        return {
            "l1_core": l1_count,
            "l2_framework": l2_count,
            "l3_fading": l3_fading,
            "hot_memories": hot_memories
        }
    
    def get_retrieval_confidence(self, query: str) -> float:
        """返回检索到的知识最高置信度，若无返回0"""
        result = self.retrieve_knowledge(query, min_quality=0)
        if result:
            return result[1]
        return 0.0
    
    def add_knowledge_item(self, item: dict) -> bool:
        """通用添加知识条目，用于外部学习导入"""
        question = item.get('question')
        answer = item.get('answer')
        source = item.get('source', 'external')
        knowledge_type = item.get('type', 'qa')
        metadata = item.get('metadata', {})
        
        return self._save_knowledge(question, answer, source, knowledge_type, metadata)
    
    def register_tool_from_code(self, name: str, code: str, description: str, triggers: list) -> bool:
        """注册工具到数据库，同时写入可执行文件"""
        db = get_storage_port(self.db_path)
        try:
            db.execute('''
                INSERT OR REPLACE INTO tools (name, code, description, triggers, usage_count, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
            ''', (name, code, description, json.dumps(triggers), datetime.now().isoformat()), commit=True)
            
            tools_dir = Path("data/auto_tools")
            tools_dir.mkdir(exist_ok=True)
            tool_file = tools_dir / f"{name}.py"
            tool_file.write_text(code)
            
            logger.info(f"工具已注册: {name}")
            return True
        except Exception as e:
            logger.error(f"注册工具失败: {e}")
            return False
    
    def get_tool(self, name: str) -> Optional[Dict]:
        """获取工具"""
        db = get_storage_port(self.db_path)
        row = db.query_one('SELECT * FROM tools WHERE name = ?', (name,))
        
        if row:
            return {
                "name": row['name'],
                "code": row['code'],
                "description": row['description'],
                "triggers": json.loads(row['triggers']) if row['triggers'] else [],
                "usage_count": row['usage_count']
            }
        return None
    
    def increment_tool_usage(self, name: str):
        """增加工具使用计数"""
        db = get_storage_port(self.db_path)
        db.execute('''
            UPDATE tools SET usage_count = usage_count + 1 
            WHERE name = ?
        ''', (name,), commit=True)
    
    def get_all_tools(self) -> List[Dict]:
        """获取所有工具"""
        db = get_storage_port(self.db_path)
        rows = db.query('SELECT * FROM tools ORDER BY usage_count DESC')
        
        tools = []
        for row in rows:
            tools.append({
                "name": row['name'],
                "code": row['code'],
                "description": row['description'],
                "triggers": json.loads(row['triggers']) if row['triggers'] else [],
                "usage_count": row['usage_count']
            })
        
        return tools
    
    def auto_generate_tools(self):
        """自动生成工具函数"""
        
        tools_created = 0
        db = get_storage_port(self.db_path)
        
        try:
            rows = db.query('''
                SELECT metadata FROM knowledge_items 
                WHERE knowledge_type = 'function' 
                AND metadata LIKE '%code%'
            ''')
            
            snippets = []
            for row in rows:
                try:
                    metadata = json.loads(row['metadata'])
                    if 'code' in metadata:
                        snippets.append(metadata['code'])
                except Exception:
                    continue
            
            snippet_counter = Counter(snippets)
            
            for snippet, count in snippet_counter.most_common(10):
                if count >= 1 and len(snippet) > 20:
                    tool_name = self._generate_tool_name(snippet)
                    
                    try:
                        check = db.query_one('SELECT 1 FROM tools WHERE name = ?', (tool_name,))
                        if not check:
                            db.execute('''
                                INSERT INTO tools (name, code, description, triggers, usage_count, created_at)
                                VALUES (?, ?, ?, ?, 0, ?)
                            ''', (
                                tool_name,
                                snippet,
                                f"自动生成的工具函数",
                                json.dumps([snippet[:30]]),
                                datetime.now().isoformat()
                            ), commit=True)
                            tools_created += 1
                    except Exception:
                        continue
            
        except Exception:
            logger.warning("操作降级跳过")
        
        if tools_created > 0:
            logger.info(f"自动生成 {tools_created} 个工具函数")
        
        return tools_created
    
    def retrieve_knowledge(self, query: str, min_quality: float = 50.0) -> Optional[Dict]:
        """
        检索知识（支持情境重构）
        
        返回: {"answer": str, "confidence": float, "source": str, "reconstructed": bool}
        source: 'vector', 'fuzzy', 'reconstruction'
        """
        
        # 1. 向量检索
        if self.vector_store:
            try:
                vector_results = self.vector_store.search(query, top_k=1, threshold=0.6)
                if vector_results:
                    distance, meta = vector_results[0]
                    confidence = 1.0 - distance
                    answer = meta.get("answer", "")
                    layer = meta.get('layer', 2)
                    if answer and confidence > 0.6 and layer in (1, 2):
                        logger.info(f"向量检索命中: {confidence:.2f}")
                        return {
                            "answer": answer,
                            "confidence": confidence,
                            "source": "vector",
                            "reconstructed": False
                        }
            except Exception as e:
                logger.error(f"向量检索失败: {e}")
        
        # 2. 情境重构（低置信度时）
        reconstruction = self.retrieve_with_context_reconstruction(query)
        if reconstruction:
            answer, conf = reconstruction
            return {
                "answer": answer,
                "confidence": conf,
                "source": "reconstruction",
                "reconstructed": True
            }
        
        # 3. SQL精确匹配
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()
        
        db = get_storage_port(self.db_path)
        
        row = db.query_one('''
            SELECT answer, quality_score, memory_layer, salience
            FROM knowledge_items 
            WHERE question_hash = ? AND quality_score >= ?
        ''', (query_hash, min_quality))
        
        if row:
            db.execute('''
                UPDATE knowledge_items 
                SET access_count = access_count + 1, last_accessed = ?
                WHERE question_hash = ?
            ''', (datetime.now().isoformat(), query_hash), commit=True)
            return {
                "answer": row['answer'],
                "confidence": row['quality_score'] / 100.0,
                "source": "exact",
                "reconstructed": False
            }
        
        keywords = re.findall(r'\w+', query.lower())
        for keyword in keywords:
            if len(keyword) > 3:
                row = db.query_one('''
                    SELECT answer, quality_score, memory_layer, salience
                    FROM knowledge_items 
                    WHERE question LIKE ? AND quality_score >= ?
                    AND memory_layer IN (1, 2)
                    ORDER BY quality_score DESC, access_count DESC
                    LIMIT 1
                ''', (f'%{keyword}%', min_quality))
                
                if row:
                    salience = row['salience'] if row['salience'] else 0.5
                    return {
                        "answer": row['answer'],
                        "confidence": row['quality_score'] / 100.0 * 0.8,
                        "source": "fuzzy",
                        "reconstructed": False
                    }
        
        return None
    
    def retrieve_with_context_reconstruction(self, query: str, min_salience: float = 0.3) -> Optional[tuple]:
        """情境重构检索"""
        
        db = get_storage_port(self.db_path)
        candidates = db.query('''
            SELECT question, answer, context_snapshot, source
            FROM knowledge_items
            WHERE memory_layer = 3 AND salience >= ?
            ORDER BY salience DESC
            LIMIT 3
        ''', (min_salience,))
        
        if not candidates:
            return None
        
        prompt = f"""用户问：{query}

我回忆起之前学习过的情境：
"""
        for idx, row in enumerate(candidates):
            prompt += f"\n【情境{idx+1}】\n来源: {row['source']}\n问题: {row['question']}\n答案: {row['answer'][:200]}\n"
            if row['context_snapshot']:
                prompt += f"上下文: {row['context_snapshot'][:200]}\n"
        
        prompt += "\n请结合这些情境，给出完整回答。"
        
        try:
            from core.external_learner import external_learner
            new_answer = external_learner.ask_llm(prompt)
            
            if new_answer and not new_answer.startswith("[ERROR]") and not new_answer.startswith("[模拟]"):
                # 添加回忆感
                recalled = f"💭 让我想想... 啊，我想起来了！\n\n{new_answer}\n\n（这是我从之前的情境中回忆起来的）"
                
                self._save_knowledge(
                    question=query,
                    answer=new_answer,
                    source="context_reconstruction",
                    knowledge_type="qa",
                    memory_layer=2
                )
                
                return (recalled, 0.65)
        except Exception as e:
            logger.error(f"情境重构失败: {e}")
        
        return None

    
    def _save_knowledge(self, question: str, answer: str, source: str, 
                       knowledge_type: str = 'qa', metadata: Dict = None) -> bool:
        """保存知识"""
        
        question_hash = hashlib.md5(question.lower().strip().encode()).hexdigest()
        
        try:
            db = get_storage_port(self.db_path)
            db.execute('''
                INSERT OR REPLACE INTO knowledge_items
                (question_hash, question, answer, source, knowledge_type, 
                 quality_score, access_count, last_accessed, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                question_hash,
                question,
                answer,
                source,
                knowledge_type,
                100.0,
                0,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                json.dumps(metadata or {}, ensure_ascii=False)
            ), commit=True)
            
            if self.vector_store:
                try:
                    self.vector_store.add(question, answer, {
                        "source": source,
                        "type": knowledge_type,
                        "quality": 100.0
                    })
                except Exception as e:
                    logger.error(f"向量存储失败: {e}")
            
            return True
        except Exception as e:
            logger.error(f"保存知识失败: {e}")
            return False
    
    def _extract_file_summary(self, filename: str, content: str) -> str:
        """提取文件摘要"""
        
        language = self._detect_language(filename)
        
        if language == 'python':
            imports = re.findall(r'^(?:from|import)\s+([\w\.]+)', content, re.MULTILINE)
            functions = re.findall(r'^def\s+(\w+)\s*\(', content, re.MULTILINE)
            classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
            
            summary = f"文件 {filename} (Python)\n"
            if imports:
                summary += f"导入: {', '.join(imports[:5])}\n"
            if functions:
                summary += f"函数: {', '.join(functions[:5])}\n"
            if classes:
                summary += f"类: {', '.join(classes[:5])}\n"
            
            return summary
        
        elif language == 'markdown':
            headers = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
            if headers:
                return f"文档 {filename}\n主要章节: {', '.join(headers[:5])}"
        
        return content[:500]
    
    def _extract_functions(self, content: str, filename: str) -> List[Dict]:
        """提取函数"""
        
        functions = []
        
        # 匹配函数定义和文档字符串
        pattern = r'def\s+(\w+)\s*\([^)]*\):\s*"""([^"]+)"""'
        for match in re.finditer(pattern, content, re.DOTALL):
            func_name = match.group(1)
            docstring = match.group(2).strip()
            
            functions.append({
                'name': func_name,
                'description': f"{func_name}: {docstring}",
                'code': match.group(0)
            })
        
        # 如果没有文档字符串，提取函数签名
        if not functions:
            pattern = r'def\s+(\w+)\s*\([^)]*\):'
            for match in re.finditer(pattern, content):
                func_name = match.group(1)
                functions.append({
                    'name': func_name,
                    'description': f"函数 {func_name} (定义在 {filename})",
                    'code': match.group(0)
                })
        
        return functions[:10]  # 最多10个函数
    
    def _extract_classes(self, content: str, filename: str) -> List[Dict]:
        """提取类"""
        
        classes = []
        
        # 匹配类定义和文档字符串
        pattern = r'class\s+(\w+).*?:\s*"""([^"]+)"""'
        for match in re.finditer(pattern, content, re.DOTALL):
            class_name = match.group(1)
            docstring = match.group(2).strip()
            
            classes.append({
                'name': class_name,
                'description': f"{class_name}: {docstring}"
            })
        
        return classes[:10]
    
    def _extract_code_snippets(self, content: str, filename: str):
        """提取代码片段"""
        
        # 提取可能重复使用的代码模式
        patterns = [
            r'sum\(p\.numel\(\) for p in .*?\.parameters\(\)\)',
            r'model\.parameters\(\)',
            r'torch\.cuda\.is_available\(\)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                self._save_knowledge(
                    question=f"代码片段: {match[:50]}",
                    answer=match,
                    source=f"snippet:{filename}",
                    knowledge_type="snippet",
                    metadata={'code': match}
                )
    
    def _detect_language(self, filename: str) -> str:
        """检测文件语言"""
        
        ext = Path(filename).suffix.lower()
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.md': 'markdown',
            '.txt': 'text',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
        }
        return language_map.get(ext, 'unknown')
    
    def _generate_tool_name(self, snippet: str) -> str:
        """生成工具名"""
        
        if 'parameters()' in snippet:
            return 'count_parameters'
        elif 'cuda' in snippet:
            return 'check_cuda'
        else:
            return f'auto_tool_{hash(snippet) % 10000}'


# 全局实例
enhanced_learner = EnhancedLearner()
