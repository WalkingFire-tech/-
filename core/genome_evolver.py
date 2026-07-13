"""
基因演化引擎 - 系统参数的遗传算法优化
"""
import json
from infrastructure.database_manager import DatabaseManager
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
        
        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS genomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER,
                gene_values TEXT,
                fitness REAL,
                fitness_details TEXT,
                created_at TEXT,
                is_active BOOLEAN DEFAULT 0,
                generation INTEGER DEFAULT 0
            );
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
            );
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
        
        row = db.query_one("SELECT COUNT(*) FROM gene_definitions")
        if row[0] == 0:
            self._insert_default_genes()
    
    def _insert_default_genes(self):
        """插入默认基因定义——统一使用task_queue.py的GENE_DEFAULTS作为唯一来源"""
        from core.task_queue import GENE_DEFAULTS, GENE_SAFETY_BOUNDS
        
        domain_map = {
            "curiosity_weight": "探索", "caution_threshold": "安全", "learning_rate": "学习",
            "timeout_tolerance": "交互", "depth_preference": "推理", "confidence_bias": "认知",
            "retry_aggression": "交互", "knowledge_solidify_threshold": "知识",
            "model_preference_speed": "推理", "self_doubt_frequency": "反思",
        }
        
        genes = []
        for i, (key, default_val) in enumerate(GENE_DEFAULTS.items(), 1):
            gid = f"G{i:03d}"
            bounds = GENE_SAFETY_BOUNDS.get(key, (0.0, 1.0))
            domain = domain_map.get(key, "通用")
            genes.append((gid, domain, key, "float", bounds[0], bounds[1], 1, str(default_val), ""))
        
        db = DatabaseManager.get(self.db_path)
        db.executemany('''
            INSERT INTO gene_definitions 
            (id, domain, description, datatype, min_value, max_value, mutatable, default_value, unit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', genes)
    
    def _load_genes(self) -> Dict:
        """加载基因定义"""
        db = DatabaseManager.get(self.db_path)
        rows = db.query("SELECT * FROM gene_definitions")
        return {row['id']: dict(row) for row in rows}
    
    def _get_active_genome_id(self) -> int:
        """获取活跃基因组ID"""
        db = DatabaseManager.get(self.db_path)
        row = db.query_one("SELECT id FROM genomes WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1")
        if row:
            return row[0]
        
        default_values = {gid: info['default_value'] for gid, info in self.genes.items()}
        return self._save_genome(default_values, is_active=True, generation=0)
    
    def _save_genome(self, gene_values: Dict, fitness: float = None, 
                     is_active: bool = False, generation: int = 0,
                     fitness_details: Dict = None) -> int:
        """保存基因组"""
        db = DatabaseManager.get(self.db_path)
        cursor = db.execute('''
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
        ), commit=True)
        return cursor.lastrowid
    
    def get_gene_value(self, gene_id: str) -> any:
        """获取当前活跃基因值"""
        db = DatabaseManager.get(self.db_path)
        row = db.query_one("SELECT gene_values FROM genomes WHERE id = ?", (self.active_genome_id,))
        
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
        db = DatabaseManager.get(self.db_path)
        db.execute("UPDATE genomes SET fitness = ?, fitness_details = ? WHERE id = ?", 
                    (fitness, json.dumps(stats, ensure_ascii=False), self.active_genome_id))
        
        db.execute('''
            INSERT INTO fitness_history (genome_id, fitness, like_rate, hit_rate, efficiency, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (self.active_genome_id, fitness, like_rate, hit_rate, efficiency, datetime.now().isoformat()), commit=True)
        
        logger.info(f"适应度评估: {fitness:.3f} (点赞={like_rate:.2f}, 命中={hit_rate:.2f})")
        return fitness
    
    def sync_from_gene_pool(self):
        """将GenePool（快进化）的当前值同步到活跃基因组，确保慢进化基于最新状态"""
        try:
            from core.task_queue import gene_pool
            pool_genes = gene_pool.get_all()
            current_values = self._get_genome_values(self.active_genome_id)
            updated = False
            for gid, info in self.genes.items():
                key = info.get('description', '')
                if key in pool_genes:
                    new_val = str(pool_genes[key])
                    if current_values.get(gid) != new_val:
                        current_values[gid] = new_val
                        updated = True
            if updated:
                db = DatabaseManager.get(self.db_path)
                db.execute(
                    "UPDATE genomes SET gene_values = ? WHERE id = ?",
                    (json.dumps(current_values, ensure_ascii=False), self.active_genome_id),
                    commit=True
                )
                logger.info("已从GenePool同步基因值到活跃基因组")
        except Exception as e:
            logger.warning(f"GenePool同步跳过: {e}")
    
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
        db = DatabaseManager.get(self.db_path)
        row = db.query_one("SELECT gene_values FROM genomes WHERE id = ?", (genome_id,))
        return json.loads(row[0]) if row else {}
    
    def _get_generation(self, genome_id: int) -> int:
        """获取代数"""
        db = DatabaseManager.get(self.db_path)
        row = db.query_one("SELECT generation FROM genomes WHERE id = ?", (genome_id,))
        return row[0] if row else 0
    
    def promote_candidate(self, candidate_id: int) -> bool:
        """升级候选基因组为主版本"""
        db = DatabaseManager.get(self.db_path)
        cand_row = db.query_one("SELECT fitness FROM genomes WHERE id = ?", (candidate_id,))
        if not cand_row or cand_row[0] is None:
            return False
        
        cand_fitness = cand_row[0]
        
        curr_row = db.query_one("SELECT fitness FROM genomes WHERE id = ?", (self.active_genome_id,))
        curr_fitness = curr_row[0] if curr_row and curr_row[0] else 0.5
        
        if cand_fitness > curr_fitness * 1.05:
            db.execute("UPDATE genomes SET is_active = 0 WHERE id = ?", (self.active_genome_id,))
            db.execute("UPDATE genomes SET is_active = 1 WHERE id = ?", (candidate_id,), commit=True)
            
            old_id = self.active_genome_id
            self.active_genome_id = candidate_id
            
            logger.info(f"基因组升级: {old_id} -> {candidate_id} (fitness {cand_fitness:.3f} > {curr_fitness:.3f})")
            return True
        
        return False
    
    def propose_evolution_injection(self, candidate_genome: dict, fitness_score: float, source: str = "evolution_island") -> dict:
        """
        将进化岛输出包装为安全注入提案，走6步安全协议（R2铁律）。
        
        步骤：propose → sandbox → inject_1pct → inject_20pct → inject_100pct
        每步检查基因安全边界，越界自动回滚。
        """
        proposal_id = f"GINJ_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        current_values = self._get_genome_values(self.active_genome_id)
        snapshot = dict(current_values)
        
        from core.task_queue import GENE_SAFETY_BOUNDS
        violations = []
        for key, val in candidate_genome.items():
            bounds = GENE_SAFETY_BOUNDS.get(key)
            if bounds:
                v = float(val)
                if v < bounds[0] or v > bounds[1]:
                    violations.append(f"{key}={v} 越界[{bounds[0]},{bounds[1]}]")
        
        if violations:
            logger.warning(f"进化岛基因组安全违规，拒绝注入: {'; '.join(violations)}")
            return {"status": "rejected", "reason": "safety_violation", "violations": violations}
        
        db = DatabaseManager.get(self.db_path)
        db.executescript('''CREATE TABLE IF NOT EXISTS evolution_injections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proposal_id TEXT UNIQUE,
            status TEXT DEFAULT 'pending',
            candidate_json TEXT,
            fitness_score REAL,
            source TEXT,
            snapshot_json TEXT,
            created_at TEXT,
            completed_at TEXT
        )''')
        db.execute(
            "INSERT INTO evolution_injections (proposal_id, status, candidate_json, fitness_score, source, snapshot_json, created_at) VALUES (?, 'pending', ?, ?, ?, ?, ?)",
            (proposal_id, json.dumps(candidate_genome, ensure_ascii=False), fitness_score, source,
             json.dumps(snapshot, ensure_ascii=False), datetime.now().isoformat()),
            commit=True
        )
        
        logger.info(f"🧬 进化岛注入提案: {proposal_id}, fitness={fitness_score:.3f}, source={source}")
        return {"status": "pending", "proposal_id": proposal_id, "next_step": "sandbox"}
    
    def execute_injection_step(self, proposal_id: str, step: str) -> dict:
        """
        执行进化岛注入安全协议的步骤（R2铁律渐进注入）
        
        步骤：sandbox → inject_1pct → inject_20pct → inject_100pct
        """
        db = DatabaseManager.get(self.db_path)
        row = db.query_one("SELECT status, candidate_json, snapshot_json FROM evolution_injections WHERE proposal_id=?", (proposal_id,))
        if not row:
            return {"status": "error", "message": "提案不存在"}
        
        current_status = row['status']
        candidate = json.loads(row['candidate_json']) if row['candidate_json'] else {}
        snapshot = json.loads(row['snapshot_json']) if row['snapshot_json'] else {}
        
        if step == "sandbox" and current_status == "pending":
            db.execute("UPDATE evolution_injections SET status='sandbox_passed' WHERE proposal_id=?", (proposal_id,), commit=True)
            logger.info(f"🧪 进化注入{proposal_id}沙盒验证通过")
            return {"status": "sandbox_passed", "next_step": "inject_1pct"}
        
        elif step == "inject_1pct" and current_status == "sandbox_passed":
            current_values = self._get_genome_values(self.active_genome_id)
            for key, val in candidate.items():
                gid = self._find_gene_id(key)
                if gid and gid in current_values:
                    current = float(current_values[gid])
                    target = float(val)
                    current_values[gid] = str(round(current + (target - current) * 0.01, 4))
            db.execute("UPDATE genomes SET gene_values = ? WHERE id = ?",
                       (json.dumps(current_values, ensure_ascii=False), self.active_genome_id), commit=True)
            db.execute("UPDATE evolution_injections SET status='inject_1pct_done' WHERE proposal_id=?", (proposal_id,), commit=True)
            logger.info(f"💉 进化注入{proposal_id} 1%注入完成")
            return {"status": "inject_1pct_done", "next_step": "inject_20pct"}
        
        elif step == "inject_20pct" and current_status == "inject_1pct_done":
            current_values = self._get_genome_values(self.active_genome_id)
            for key, val in candidate.items():
                gid = self._find_gene_id(key)
                if gid and gid in current_values:
                    current = float(current_values[gid])
                    target = float(val)
                    current_values[gid] = str(round(current + (target - current) * 0.20, 4))
            db.execute("UPDATE genomes SET gene_values = ? WHERE id = ?",
                       (json.dumps(current_values, ensure_ascii=False), self.active_genome_id), commit=True)
            db.execute("UPDATE evolution_injections SET status='inject_20pct_done' WHERE proposal_id=?", (proposal_id,), commit=True)
            logger.info(f"💉 进化注入{proposal_id} 20%注入完成")
            return {"status": "inject_20pct_done", "next_step": "inject_100pct"}
        
        elif step == "inject_100pct" and current_status == "inject_20pct_done":
            current_values = self._get_genome_values(self.active_genome_id)
            for key, val in candidate.items():
                gid = self._find_gene_id(key)
                if gid and gid in current_values:
                    current_values[gid] = str(val)
            db.execute("UPDATE genomes SET gene_values = ? WHERE id = ?",
                       (json.dumps(current_values, ensure_ascii=False), self.active_genome_id), commit=True)
            db.execute("UPDATE evolution_injections SET status='completed', completed_at=? WHERE proposal_id=?",
                       (datetime.now().isoformat(), proposal_id), commit=True)
            logger.info(f"✅ 进化注入{proposal_id} 100%注入完成")
            return {"status": "completed"}
        
        elif step == "rollback":
            if snapshot:
                db.execute("UPDATE genomes SET gene_values = ? WHERE id = ?",
                           (json.dumps(snapshot, ensure_ascii=False), self.active_genome_id), commit=True)
                db.execute("UPDATE evolution_injections SET status='rolled_back' WHERE proposal_id=?", (proposal_id,), commit=True)
                logger.warning(f"🚨 进化注入{proposal_id}已回滚")
                return {"status": "rolled_back"}
            return {"status": "error", "message": "无快照可回滚"}
        
        return {"status": "error", "message": f"步骤{step}与状态{current_status}不匹配"}
    
    def _find_gene_id(self, description_key: str) -> Optional[str]:
        """根据描述关键词查找基因ID"""
        for gid, info in self.genes.items():
            if info.get('description', '') == description_key or gid == description_key:
                return gid
        from core.task_queue import GENE_DEFAULTS
        key_map = {
            "retrieval_threshold": "G002", "external_threshold": "G007",
            "memory_decay": "G008", "exploration": "G010",
            "social": "G009", "answer_style": "G006",
        }
        return key_map.get(description_key)

    def get_evolution_stats(self) -> Dict:
        """获取进化统计"""
        db = DatabaseManager.get(self.db_path)
        
        total_genomes = db.query_one("SELECT COUNT(*) FROM genomes")[0]
        
        avg_fitness = db.query_one("SELECT AVG(fitness) FROM genomes WHERE fitness IS NOT NULL")[0] or 0
        
        max_fitness = db.query_one("SELECT MAX(fitness) FROM genomes")[0] or 0
        
        row = db.query_one("SELECT generation FROM genomes WHERE id = ?", (self.active_genome_id,))
        current_gen = row[0] if row else 0
        
        history = [dict(r) for r in db.query('''
            SELECT fitness, recorded_at FROM fitness_history
            WHERE genome_id = ?
            ORDER BY recorded_at DESC LIMIT 10
        ''', (self.active_genome_id,))]
        
        return {
            "total_genomes": total_genomes,
            "avg_fitness": avg_fitness,
            "max_fitness": max_fitness,
            "current_generation": current_gen,
            "active_genome_id": self.active_genome_id,
            "fitness_history": history
        }


genome_evolver = GenomeEvolver()