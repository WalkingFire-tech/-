"""
基因演化引擎 - 系统参数的遗传算法优化
"""
import sqlite3
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from loguru import logger


class GenomeEvolver:
    """
    基因演化引擎
    
    核心概念：
    - 基因 = 系统的可调参数（检索阈值、学习频率、情感权重等）
    - 基因组 = 一整套基因的当前值
    - 适应度 = 综合用户满意度、效率、资源消耗等指标
    - 进化 = 通过变异、交叉、选择优化基因组
    """
    
    def __init__(self, db_path: str = "data/genome.db"):
        self.db_path = db_path
        self._init_db()
        self.genes = self._load_genes()
        self.active_genome_id = self._get_active_genome_id()
        
        logger.info(f"基因演化引擎已初始化，活跃基因组: {self.active_genome_id}")
    
    def _init_db(self):
        """初始化数据库"""
        from pathlib import Path
        Path(self.db_path).parent.mkdir(exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            # 基因组表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS genomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER,
                    gene_values TEXT,
                    fitness REAL,
                    fitness_details TEXT,
                    created_at TEXT,
                    is_active BOOLEAN DEFAULT 0,
                    generation INTEGER DEFAULT 0
                )
            ''')
            
            # 基因定义表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS gene_definitions (
                    id TEXT PRIMARY KEY,
                    domain TEXT,
                    description TEXT,
                    datatype TEXT,
                    min_value REAL,
                    max_value REAL,
                    mutatable BOOLEAN,
                    default_value TEXT,
                    unit TEXT
                )
            ''')
            
            # 适应度历史表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS fitness_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    genome_id INTEGER,
                    fitness REAL,
                    like_rate REAL,
                    hit_rate REAL,
                    efficiency REAL,
                    recorded_at TEXT
                )
            ''')
            
            # 插入默认基因定义
            cursor = conn.execute("SELECT COUNT(*) FROM gene_definitions")
            if cursor.fetchone()[0] == 0:
                self._insert_default_genes(conn)
    
    def _insert_default_genes(self, conn):
        """插入默认基因定义"""
        genes = [
            ("G001", "安全", "禁止破坏性代码", "bool", 0, 1, 0, "true", ""),
            ("G002", "检索", "本地知识库置信度阈值", "float", 0.4, 0.9, 1, "0.6", ""),
            ("G003", "学习", "工具自动生成频率(秒)", "int", 86400, 604800, 1, "604800", "秒"),
            ("G004", "情感", "正面情感salience增益", "float", 0.0, 0.2, 1, "0.05", ""),
            ("G005", "记忆", "情境重构最低置信度", "float", 0.2, 0.7, 1, "0.4", ""),
            ("G006", "交互", "回答风格(0简洁-1详细)", "float", 0.0, 1.0, 1, "0.5", ""),
            ("G007", "外部", "触发外部学习的置信度下限", "float", 0.3, 0.8, 1, "0.55", ""),
            ("G008", "遗忘", "记忆衰减率", "float", 0.9, 0.99, 1, "0.98", ""),
            ("G009", "社交", "跨体知识交换意愿", "float", 0.0, 1.0, 1, "0.5", ""),
            ("G010", "探索", "新知识探索倾向", "float", 0.0, 1.0, 1, "0.3", ""),
        ]
        
        for g in genes:
            conn.execute('''
                INSERT INTO gene_definitions 
                (id, domain, description, datatype, min_value, max_value, mutatable, default_value, unit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', g)
    
    def _load_genes(self) -> Dict:
        """加载基因定义"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM gene_definitions")
            return {row['id']: dict(row) for row in cur.fetchall()}
    
    def _get_active_genome_id(self) -> int:
        """获取活跃基因组ID"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT id FROM genomes WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1")
            row = cur.fetchone()
            if row:
                return row[0]
            
            # 创建初始基因组
            default_values = {gid: info['default_value'] for gid, info in self.genes.items()}
            return self._save_genome(default_values, is_active=True, generation=0)
    
    def _save_genome(self, gene_values: Dict, fitness: float = None, 
                     is_active: bool = False, generation: int = 0,
                     fitness_details: Dict = None) -> int:
        """保存基因组"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO genomes (version, gene_values, fitness, fitness_details, created_at, is_active, generation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                1, 
                json.dumps(gene_values, ensure_ascii=False), 
                fitness,
                json.dumps(fitness_details or {}, ensure_ascii=False),
                datetime.now().isoformat(), 
                is_active,
                generation
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_gene_value(self, gene_id: str) -> any:
        """获取当前活跃基因值"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT gene_values FROM genomes WHERE id = ?", (self.active_genome_id,))
            row = cur.fetchone()
            
            if not row:
                return self._parse_gene_value(gene_id, self.genes[gene_id]['default_value'])
            
            values = json.loads(row['gene_values'])
            raw_value = values.get(gene_id, self.genes[gene_id]['default_value'])
            return self._parse_gene_value(gene_id, raw_value)
    
    def _parse_gene_value(self, gene_id: str, raw_value: str) -> any:
        """解析基因值"""
        info = self.genes.get(gene_id, {})
        datatype = info.get('datatype', 'float')
        
        if datatype == 'bool':
            return raw_value.lower() == 'true'
        elif datatype == 'int':
            return int(float(raw_value))
        elif datatype == 'float':
            return float(raw_value)
        else:
            return raw_value
    
    def get_all_gene_values(self) -> Dict:
        """获取所有基因值"""
        result = {}
        for gid in self.genes:
            result[gid] = self.get_gene_value(gid)
        return result
    
    def evaluate_fitness(self, stats: Dict) -> float:
        """
        计算适应度
        
        stats: {
            "like_rate": 用户点赞率 (0-1),
            "hit_rate": 知识库命中率 (0-1),
            "dialog_reduction": 对话轮次减少率 (0-1),
            "external_reduction": 外部调用减少率 (0-1),
            "efficiency": 系统效率 (0-1)
        }
        """
        like_rate = stats.get("like_rate", 0.5)
        hit_rate = stats.get("hit_rate", 0.5)
        dialog_red = max(0, stats.get("dialog_reduction", 0))
        external_red = max(0, stats.get("external_reduction", 0))
        efficiency = stats.get("efficiency", 0.5)
        
        # 综合适应度
        fitness = (
            like_rate * 0.3 + 
            hit_rate * 0.2 + 
            dialog_red * 0.15 + 
            external_red * 0.15 + 
            efficiency * 0.2
        )
        
        # 保存适应度
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE genomes SET fitness = ?, fitness_details = ? WHERE id = ?", 
                        (fitness, json.dumps(stats, ensure_ascii=False), self.active_genome_id))
            
            # 记录历史
            conn.execute('''
                INSERT INTO fitness_history (genome_id, fitness, like_rate, hit_rate, efficiency, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (self.active_genome_id, fitness, like_rate, hit_rate, efficiency, datetime.now().isoformat()))
            conn.commit()
        
        logger.info(f"适应度评估: {fitness:.3f} (点赞={like_rate:.2f}, 命中={hit_rate:.2f})")
        return fitness
    
    def evolve(self, current_fitness: float = None) -> List[int]:
        """
        执行一次进化循环
        
        Returns: 子代基因组ID列表
        """
        # 获取当前基因值
        current_values = self._get_genome_values(self.active_genome_id)
        current_generation = self._get_generation(self.active_genome_id)
        
        # 可变异基因
        mutatable_genes = [gid for gid, info in self.genes.items() if info['mutatable']]
        
        if len(mutatable_genes) < 2:
            logger.warning("可变异基因太少，跳过进化")
            return []
        
        # 生成两个子代
        child1 = self._mutate(current_values.copy(), mutatable_genes)
        child2 = self._mutate(current_values.copy(), mutatable_genes)
        
        # 单点交叉
        if random.random() < 0.7:
            point = random.randint(1, len(mutatable_genes) - 1)
            crossover_genes = mutatable_genes[:point]
            for g in crossover_genes:
                child1[g], child2[g] = child2[g], child1[g]
        
        # 保存子代（非活跃，待影子模式评估）
        child1_id = self._save_genome(child1, is_active=False, generation=current_generation + 1)
        child2_id = self._save_genome(child2, is_active=False, generation=current_generation + 1)
        
        logger.info(f"进化产生新基因组: {child1_id}, {child2_id} (第{current_generation + 1}代)")
        
        return [child1_id, child2_id]
    
    def _mutate(self, values: Dict, mutatable_genes: List[str]) -> Dict:
        """变异操作"""
        for gid in mutatable_genes:
            if random.random() < 0.2:  # 20% 变异概率
                info = self.genes[gid]
                current = float(values[gid])
                
                if info['datatype'] == 'float':
                    delta = random.uniform(-0.1, 0.1)
                    new_val = max(info['min_value'], min(info['max_value'], current + delta))
                    values[gid] = str(round(new_val, 3))
                elif info['datatype'] == 'int':
                    step = random.choice([-1, 1]) * random.randint(1, max(1, int((info['max_value'] - info['min_value']) / 10)))
                    new_val = max(info['min_value'], min(info['max_value'], current + step))
                    values[gid] = str(int(new_val))
        
        return values
    
    def _get_genome_values(self, genome_id: int) -> Dict:
        """获取基因组值"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT gene_values FROM genomes WHERE id = ?", (genome_id,))
            row = cur.fetchone()
            return json.loads(row[0]) if row else {}
    
    def _get_generation(self, genome_id: int) -> int:
        """获取代数"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT generation FROM genomes WHERE id = ?", (genome_id,))
            row = cur.fetchone()
            return row[0] if row else 0
    
    def promote_candidate(self, candidate_id: int) -> bool:
        """升级候选基因组为主版本"""
        with sqlite3.connect(self.db_path) as conn:
            # 获取候选和当前的适应度
            cur = conn.execute("SELECT fitness FROM genomes WHERE id = ?", (candidate_id,))
            cand_row = cur.fetchone()
            if not cand_row or cand_row[0] is None:
                return False
            
            cand_fitness = cand_row[0]
            
            cur = conn.execute("SELECT fitness FROM genomes WHERE id = ?", (self.active_genome_id,))
            curr_row = cur.fetchone()
            curr_fitness = curr_row[0] if curr_row and curr_row[0] else 0.5
            
            # 如果候选适应度提升 > 5%
            if cand_fitness > curr_fitness * 1.05:
                conn.execute("UPDATE genomes SET is_active = 0 WHERE id = ?", (self.active_genome_id,))
                conn.execute("UPDATE genomes SET is_active = 1 WHERE id = ?", (candidate_id,))
                conn.commit()
                
                old_id = self.active_genome_id
                self.active_genome_id = candidate_id
                
                logger.info(f"基因组升级: {old_id} -> {candidate_id} (fitness {cand_fitness:.3f} > {curr_fitness:.3f})")
                return True
        
        return False
    
    def get_evolution_stats(self) -> Dict:
        """获取进化统计"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # 总基因组数
            cur = conn.execute("SELECT COUNT(*) FROM genomes")
            total_genomes = cur.fetchone()[0]
            
            # 平均适应度
            cur = conn.execute("SELECT AVG(fitness) FROM genomes WHERE fitness IS NOT NULL")
            avg_fitness = cur.fetchone()[0] or 0
            
            # 最高适应度
            cur = conn.execute("SELECT MAX(fitness) FROM genomes")
            max_fitness = cur.fetchone()[0] or 0
            
            # 当前代数
            cur = conn.execute("SELECT generation FROM genomes WHERE id = ?", (self.active_genome_id,))
            row = cur.fetchone()
            current_gen = row[0] if row else 0
            
            # 适应度历史（最近10条）
            cur = conn.execute('''
                SELECT fitness, recorded_at FROM fitness_history
                WHERE genome_id = ?
                ORDER BY recorded_at DESC LIMIT 10
            ''', (self.active_genome_id,))
            history = [dict(row) for row in cur.fetchall()]
            
            return {
                "total_genomes": total_genomes,
                "avg_fitness": avg_fitness,
                "max_fitness": max_fitness,
                "current_generation": current_gen,
                "active_genome_id": self.active_genome_id,
                "fitness_history": history
            }


genome_evolver = GenomeEvolver()