"""
智能任务分解器 - 将复杂任务分解为子任务
支持依赖管理、类型推断、并行度分析
"""
import json
import re
from typing import List, Dict, Optional, Tuple
from loguru import logger
from datetime import datetime
from pathlib import Path
from infrastructure.database_manager import DatabaseManager


class TaskDecomposer:
    """智能任务分解器"""
    
    TASK_PATTERNS = {
        'code': [
            r'写.*代码', r'实现.*功能', r'编写.*程序',
            r'函数', r'类', r'算法', r'模块'
        ],
        'analysis': [
            r'分析', r'比较', r'对比', r'评估',
            r'优缺点', r'差异', r'区别'
        ],
        'explanation': [
            r'解释', r'说明', r'介绍', r'什么是',
            r'为什么', r'如何工作'
        ],
        'calculation': [
            r'计算', r'求解', r'得出.*结果',
            r'\d+.*[\+\-\*/]', r'公式'
        ],
        'creative': [
            r'创作', r'设计', r'构思', r'想象',
            r'写.*故事', r'写.*文章'
        ]
    }
    
    CONNECTIVE_KEYWORDS = [
        '并且', '同时', '另外', '此外', '还有',
        '先', '然后', '再', '接着', '最后',
        '既要', '又要', '不仅', '而且',
        '一方面', '另一方面', '分别'
    ]
    
    def __init__(self, db_path: str = "data/task_decomposition.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(exist_ok=True)
        self._init_db()
        logger.info("任务分解器已初始化")
    
    def _init_db(self):
        """初始化数据库"""
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS decompositions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_task TEXT,
                subtasks TEXT,
                decomposition_strategy TEXT,
                success BOOLEAN,
                quality_score REAL,
                timestamp TEXT
            )
        ''')
        conn.commit()
    
    def detect_subtasks(self, user_input: str) -> List[Dict]:
        """检测子任务（基于规则）
        
        Args:
            user_input: 用户输入
        
        Returns:
            子任务列表
        """
        subtasks = []
        
        # 1. 基于连接词分割
        segments = self._split_by_connectives(user_input)
        
        if len(segments) > 1:
            for i, segment in enumerate(segments):
                task_type = self._infer_task_type(segment)
                subtasks.append({
                    'id': i,
                    'type': task_type,
                    'description': segment.strip(),
                    'dependencies': [],
                    'parallel': True
                })
        else:
            # 2. 基于任务模式检测
            detected_types = self._detect_multiple_types(user_input)
            
            if len(detected_types) > 1:
                for i, task_type in enumerate(detected_types):
                    subtasks.append({
                        'id': i,
                        'type': task_type,
                        'description': self._extract_description(user_input, task_type),
                        'dependencies': [],
                        'parallel': True
                    })
            else:
                # 无法分解，返回原任务
                subtasks.append({
                    'id': 0,
                    'type': self._infer_task_type(user_input),
                    'description': user_input,
                    'dependencies': [],
                    'parallel': False
                })
        
        # 3. 分析依赖关系
        subtasks = self._analyze_dependencies(subtasks)
        
        return subtasks
    
    def _split_by_connectives(self, text: str) -> List[str]:
        """基于连接词分割文本"""
        segments = [text]
        
        for keyword in self.CONNECTIVE_KEYWORDS:
            new_segments = []
            for segment in segments:
                if keyword in segment:
                    parts = segment.split(keyword)
                    new_segments.extend([p.strip() for p in parts if p.strip()])
                else:
                    new_segments.append(segment)
            segments = new_segments
        
        return [s for s in segments if len(s) > 5]
    
    def _infer_task_type(self, text: str) -> str:
        """推断任务类型"""
        text_lower = text.lower()
        
        type_scores = {}
        for task_type, patterns in self.TASK_PATTERNS.items():
            score = sum(1 for p in patterns if re.search(p, text_lower))
            if score > 0:
                type_scores[task_type] = score
        
        if type_scores:
            return max(type_scores.items(), key=lambda x: x[1])[0]
        
        return 'general'
    
    def _detect_multiple_types(self, text: str) -> List[str]:
        """检测多种任务类型"""
        detected = []
        
        for task_type, patterns in self.TASK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text.lower()):
                    if task_type not in detected:
                        detected.append(task_type)
                    break
        
        return detected
    
    def _extract_description(self, text: str, task_type: str) -> str:
        """提取特定类型的描述"""
        patterns = self.TASK_PATTERNS.get(task_type, [])
        
        for pattern in patterns:
            match = re.search(f'(.{{0,50}}{pattern}.{{0,50}})', text)
            if match:
                return match.group(1).strip()
        
        return text
    
    def _analyze_dependencies(self, subtasks: List[Dict]) -> List[Dict]:
        """分析子任务依赖关系"""
        if len(subtasks) <= 1:
            return subtasks
        
        # 简单规则：后续任务依赖前面的code任务
        code_indices = [i for i, t in enumerate(subtasks) if t['type'] == 'code']
        
        for i, task in enumerate(subtasks):
            if task['type'] in ['analysis', 'explanation']:
                # 分析/解释任务依赖前面的代码任务
                task['dependencies'] = [j for j in code_indices if j < i]
                if task['dependencies']:
                    task['parallel'] = False
        
        return subtasks
    
    def decompose_with_llm(self, user_input: str, llm_adapter=None) -> List[Dict]:
        """使用LLM分解任务
        
        Args:
            user_input: 用户输入
            llm_adapter: LLM适配器（可选）
        
        Returns:
            子任务列表
        """
        if not llm_adapter:
            logger.warning("未提供LLM适配器，使用规则分解")
            return self.detect_subtasks(user_input)
        
        prompt = f"""分析以下用户请求，将其分解为独立的子任务。

用户请求：{user_input}

请输出JSON数组，每个元素包含：
- type: 任务类型（code/analysis/explanation/calculation/creative/general）
- description: 任务描述
- dependencies: 依赖的任务索引列表
- parallel: 是否可并行执行

示例输出：
[
  {{"type": "code", "description": "实现快速排序算法", "dependencies": [], "parallel": true}},
  {{"type": "explanation", "description": "解释时间复杂度", "dependencies": [0], "parallel": false}}
]

请直接输出JSON数组，不要包含其他文字。"""

        try:
            response = llm_adapter.generate(prompt)
            
            if isinstance(response, tuple):
                response = response[0]
            
            # 提取JSON
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                subtasks = json.loads(json_match.group())
                
                # 添加ID
                for i, task in enumerate(subtasks):
                    task['id'] = i
                
                logger.info(f"LLM分解成功: {len(subtasks)}个子任务")
                return subtasks
            
        except Exception as e:
            logger.warning(f"LLM分解失败: {e}，使用规则分解")
        
        return self.detect_subtasks(user_input)
    
    def save_decomposition(self, original_task: str, subtasks: List[Dict],
                          strategy: str = 'rule', success: bool = True,
                          quality_score: float = 0.0):
        """保存分解记录"""
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        conn.execute('''
            INSERT INTO decompositions
            (original_task, subtasks, decomposition_strategy, success, quality_score, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            original_task,
            json.dumps(subtasks, ensure_ascii=False),
            strategy,
            success,
            quality_score,
            datetime.now().isoformat()
        ))
        conn.commit()
    
    def get_decomposition_stats(self) -> Dict:
        """获取分解统计"""
        db = DatabaseManager.get(self.db_path)
        conn = db._get_conn()
        cursor = conn.execute('SELECT COUNT(*) FROM decompositions')
        total = cursor.fetchone()[0]
        
        cursor = conn.execute('SELECT AVG(quality_score) FROM decompositions WHERE success = 1')
        avg_quality = cursor.fetchone()[0] or 0.0
        
        return {
            'total_decompositions': total,
            'avg_quality': avg_quality
        }


task_decomposer = TaskDecomposer()
