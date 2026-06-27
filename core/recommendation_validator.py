"""
推荐验证机制 - 智能验证推荐正确性

设计原则：
1. 知识库驱动：芯片信息存储在数据库，可动态更新
2. LLM辅助：复杂匹配交给LLM语义理解
3. 规则可配置：验证规则可外部配置
4. 持续学习：从错误中学习，优化推荐
"""
import re
import json
import sqlite3
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class RecommendationValidator:
    """推荐验证器 - 智能版"""
    
    def __init__(self, db_path: str = "data/recommendation_kb.db"):
        self.db_path = db_path
        self._init_database()
        self._load_initial_knowledge()
        
        logger.info("✓ 推荐验证器已初始化")
    
    def _init_database(self):
        """初始化知识库数据库"""
        Path(self.db_path).parent.mkdir(exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS product_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_name TEXT UNIQUE,
                    description TEXT,
                    keywords TEXT,
                    created_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT UNIQUE,
                    product_name TEXT,
                    category TEXT,
                    features TEXT,
                    keywords TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS validation_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name TEXT,
                    condition_pattern TEXT,
                    valid_categories TEXT,
                    priority INTEGER,
                    created_at TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS validation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_hash TEXT,
                    recommendation TEXT,
                    is_valid INTEGER,
                    issues TEXT,
                    validated_at TEXT
                )
            ''')
    
    def _load_initial_knowledge(self):
        """加载初始知识（仅首次）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM product_categories")
            if cursor.fetchone()[0] > 0:
                return
            
            categories = [
                ("电池保护", "电池保护芯片，BMS管理", ["保护板", "BMS", "电池保护", "电池管理"]),
                ("LED驱动", "LED背光驱动芯片", ["LED", "背光", "屏幕驱动", "LED驱动"]),
                ("电源管理", "电源管理芯片", ["电源管理", "PMIC", "电源控制"]),
                ("充电管理", "电池充电管理芯片", ["充电", "充电管理", "充电控制"]),
            ]
            
            for name, desc, keywords in categories:
                conn.execute(
                    "INSERT INTO product_categories (category_name, description, keywords, created_at) VALUES (?, ?, ?, ?)",
                    (name, desc, json.dumps(keywords, ensure_ascii=False), datetime.now().isoformat())
                )
            
            products = [
                ("BQ76940", "TI BQ76940", "电池保护", ["均衡", "保护", "多串"], ["BQ769", "TI"]),
                ("BQ76952", "TI BQ76952", "电池保护", ["均衡", "保护", "高精度"], ["BQ769", "TI"]),
                ("SH36710", "中颖 SH36710", "电池保护", ["均衡", "国产"], ["SH367", "中颖"]),
                ("TPS61182", "TI TPS61182", "LED驱动", ["LED", "背光"], ["TPS611", "TI"]),
                ("BQ24195", "TI BQ24195", "充电管理", ["充电", "电源路径"], ["BQ24", "TI"]),
            ]
            
            for pid, name, category, features, keywords in products:
                conn.execute(
                    "INSERT INTO products (product_id, product_name, category, features, keywords, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (pid, name, category, json.dumps(features, ensure_ascii=False), json.dumps(keywords, ensure_ascii=False), datetime.now().isoformat(), datetime.now().isoformat())
                )
            
            conn.commit()
            logger.info("✓ 初始知识库已加载")
    
    def validate_recommendation(self, user_query: str, recommendation: str,
                               llm_adapter = None) -> Dict:
        """
        验证推荐是否匹配需求
        
        Args:
            user_query: 用户查询
            recommendation: 推荐内容
            llm_adapter: LLM适配器（可选）
        
        Returns:
            验证结果字典
        """
        required_categories = self._identify_requirements(user_query)
        
        recommended_products = self._extract_products(recommendation)
        
        if not required_categories:
            return self._llm_validate(user_query, recommendation, llm_adapter)
        
        if not recommended_products:
            return {
                'is_valid': None,
                'confidence': 0.5,
                'required_categories': required_categories,
                'recommended_products': [],
                'issues': ["无法识别推荐产品"],
                'suggestion': "请提供更明确的推荐"
            }
        
        issues = []
        valid_count = 0
        
        for product in recommended_products:
            product_category = product.get('category')
            is_match = any(
                self._is_category_match(req, product_category)
                for req in required_categories
            )
            
            if is_match:
                valid_count += 1
            else:
                issues.append(
                    f"产品 {product.get('name')} ({product_category}) 不匹配需求 {required_categories}"
                )
        
        is_valid = valid_count > 0 and len(issues) == 0
        confidence = valid_count / max(len(recommended_products), 1)
        
        result = {
            'is_valid': is_valid,
            'confidence': confidence,
            'required_categories': required_categories,
            'recommended_products': [p.get('name') for p in recommended_products],
            'issues': issues,
            'recommendation': recommendation
        }
        
        self._record_validation(user_query, recommendation, is_valid, issues)
        
        return result
    
    def _identify_requirements(self, query: str) -> List[str]:
        """识别需求类别"""
        categories = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT category_name, keywords FROM product_categories")
            for row in cursor:
                category_name, keywords_json = row
                keywords = json.loads(keywords_json)
                if any(kw in query for kw in keywords):
                    categories.append(category_name)
        
        return list(set(categories))
    
    def _extract_products(self, text: str) -> List[Dict]:
        """从文本中提取产品"""
        products = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT product_id, product_name, category, keywords FROM products")
            for row in cursor:
                pid, name, category, keywords_json = row
                keywords = json.loads(keywords_json)
                
                if pid in text or any(kw in text for kw in keywords):
                    products.append({
                        'id': pid,
                        'name': name,
                        'category': category
                    })
        
        return products
    
    def _is_category_match(self, required: str, provided: str) -> bool:
        """判断类别是否匹配"""
        if required == provided:
            return True
        
        compatible = {
            ("电池保护", "电源管理"),
            ("充电管理", "电源管理"),
        }
        
        return (required, provided) in compatible or (provided, required) in compatible
    
    def _llm_validate(self, query: str, recommendation: str, 
                      llm_adapter) -> Dict:
        """使用LLM进行验证"""
        if not llm_adapter:
            return {
                'is_valid': None,
                'confidence': 0.5,
                'issues': ["无法验证，缺少LLM"],
                'recommendation': recommendation
            }
        
        try:
            prompt = f"""验证推荐是否正确：

用户需求：{query}

推荐内容：{recommendation}

请判断：
1. 推荐是否满足需求？
2. 是否存在明显错误？
3. 应该推荐什么？

以JSON格式返回：
{{
  "is_valid": true/false,
  "confidence": 0.0-1.0,
  "issues": ["问题1", "问题2"],
  "suggestion": "建议"
}}
"""
            
            response = llm_adapter.generate(prompt, task_type="validation")
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                result['recommendation'] = recommendation
                return result
        except Exception as e:
            logger.debug(f"LLM验证失败: {e}")
        
        return {
            'is_valid': None,
            'confidence': 0.5,
            'issues': ["验证失败"],
            'recommendation': recommendation
        }
    
    def _record_validation(self, query: str, recommendation: str,
                          is_valid: bool, issues: List[str]):
        """记录验证历史"""
        try:
            query_hash = str(hash(query))[:12]
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO validation_history (query_hash, recommendation, is_valid, issues, validated_at) VALUES (?, ?, ?, ?, ?)",
                    (query_hash, recommendation[:200], int(is_valid) if is_valid is not None else -1, json.dumps(issues, ensure_ascii=False), datetime.now().isoformat())
                )
                conn.commit()
        except:
            pass
    
    def add_product(self, product_id: str, name: str, category: str,
                   features: List[str], keywords: List[str]):
        """添加产品到知识库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO products (product_id, product_name, category, features, keywords, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (product_id, name, category, json.dumps(features, ensure_ascii=False), json.dumps(keywords, ensure_ascii=False), datetime.now().isoformat(), datetime.now().isoformat())
                )
                conn.commit()
                logger.info(f"✓ 添加产品: {name}")
        except Exception as e:
            logger.warning(f"添加产品失败: {e}")
    
    def add_category(self, name: str, description: str, keywords: List[str]):
        """添加产品类别"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO product_categories (category_name, description, keywords, created_at) VALUES (?, ?, ?, ?)",
                    (name, description, json.dumps(keywords, ensure_ascii=False), datetime.now().isoformat())
                )
                conn.commit()
                logger.info(f"✓ 添加类别: {name}")
        except Exception as e:
            logger.warning(f"添加类别失败: {e}")
    
    def get_correct_recommendation(self, user_query: str, llm_adapter = None) -> str:
        """获取正确推荐"""
        required_categories = self._identify_requirements(user_query)
        
        if not required_categories:
            if llm_adapter:
                return self._llm_recommend(user_query, llm_adapter)
            return "请提供更多需求信息"
        
        recommendations = []
        
        with sqlite3.connect(self.db_path) as conn:
            for category in required_categories:
                cursor = conn.execute(
                    "SELECT product_id, product_name, features FROM products WHERE category = ?",
                    (category,)
                )
                for row in cursor:
                    pid, name, features_json = row
                    features = json.loads(features_json)
                    recommendations.append(f"- {name}: {', '.join(features)}")
        
        if recommendations:
            return f"推荐产品（{', '.join(required_categories)}）：\n" + "\n".join(recommendations[:5])
        
        return "暂无匹配产品，请补充知识库"
    
    def _llm_recommend(self, query: str, llm_adapter) -> str:
        """使用LLM生成推荐"""
        try:
            prompt = f"根据需求推荐合适的产品：{query}"
            return llm_adapter.generate(prompt, task_type="recommendation")
        except:
            return "无法生成推荐"


validator = RecommendationValidator()
