"""
模型发现器 - 自动发现本地和远程模型
扫描Ollama服务、外部API等
"""
import asyncio
from typing import List, Dict, Optional
from loguru import logger
from datetime import datetime
from pathlib import Path
from infrastructure.database_manager import DatabaseManager

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logger.warning("aiohttp未安装，模型发现功能受限")


class ModelDiscovery:
    """模型发现服务"""
    
    def __init__(self, db_path: str = "data/discovered_models.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(exist_ok=True)
        self._init_db()
        
        self.ollama_urls = [
            "http://localhost:11434",
            "http://127.0.0.1:11434"
        ]
        
        logger.info("模型发现器已初始化")
    
    def _init_db(self):
        """初始化数据库"""
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            CREATE TABLE IF NOT EXISTS discovered_models (
                name TEXT PRIMARY KEY,
                source TEXT,
                model_type TEXT,
                size_gb REAL,
                parameters TEXT,
                capabilities TEXT,
                last_seen TEXT,
                available BOOLEAN
            )
        ''', commit=True)
    
    async def discover_ollama_models(self, url: str = None) -> List[Dict]:
        """发现Ollama模型
        
        Args:
            url: Ollama服务地址，None则尝试默认地址
        
        Returns:
            模型列表
        """
        if not AIOHTTP_AVAILABLE:
            logger.warning("aiohttp未安装，无法发现Ollama模型")
            return []
        
        urls = [url] if url else self.ollama_urls
        models = []
        
        for ollama_url in urls:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{ollama_url}/api/tags", 
                                          timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            
                            for model in data.get('models', []):
                                model_info = {
                                    'name': model['name'],
                                    'source': 'ollama',
                                    'model_type': 'local',
                                    'size_gb': model.get('size', 0) / (1024**3),
                                    'parameters': model.get('details', {}).get('parameter_size', 'unknown'),
                                    'capabilities': self._infer_capabilities(model['name']),
                                    'last_seen': datetime.now().isoformat(),
                                    'available': True
                                }
                                models.append(model_info)
                            
                            logger.info(f"从 {ollama_url} 发现 {len(models)} 个模型")
                            break
                            
            except asyncio.TimeoutError:
                logger.warning(f"Ollama服务超时: {ollama_url}")
            except Exception as e:
                logger.error(f"连接Ollama失败: {ollama_url}, {e}")
        
        return models
    
    def _infer_capabilities(self, model_name: str) -> Dict[str, float]:
        """从模型名推断能力
        
        Args:
            model_name: 模型名称
        
        Returns:
            能力字典
        """
        name_lower = model_name.lower()
        
        capabilities = {
            'reasoning': 0.7,
            'coding': 0.6,
            'math': 0.6,
            'creative': 0.6,
            'knowledge': 0.7,
            'speed': 0.7
        }
        
        if 'coder' in name_lower or 'code' in name_lower:
            capabilities['coding'] = 0.9
            capabilities['reasoning'] = 0.8
        
        if 'math' in name_lower:
            capabilities['math'] = 0.9
            capabilities['reasoning'] = 0.8
        
        if '7b' in name_lower:
            capabilities['speed'] = 0.9
            capabilities['context_length'] = 0.7
        elif '13b' in name_lower or '14b' in name_lower:
            capabilities['speed'] = 0.7
            capabilities['reasoning'] = 0.85
        elif '70b' in name_lower:
            capabilities['speed'] = 0.4
            capabilities['reasoning'] = 0.95
            capabilities['knowledge'] = 0.9
        
        if 'llama' in name_lower or 'qwen' in name_lower:
            capabilities['reasoning'] = min(0.9, capabilities['reasoning'] + 0.1)
            capabilities['knowledge'] = min(0.9, capabilities['knowledge'] + 0.1)
        
        if 'deepseek' in name_lower:
            capabilities['coding'] = 0.95
            capabilities['reasoning'] = 0.85
        
        return capabilities
    
    async def discover_all_models(self) -> List[Dict]:
        """发现所有可用模型"""
        models = []
        
        ollama_models = await self.discover_ollama_models()
        models.extend(ollama_models)
        
        self._save_discovered_models(models)
        
        return models
    
    def _save_discovered_models(self, models: List[Dict]):
        """保存发现的模型"""
        db = DatabaseManager.get(self.db_path)
        for model in models:
            import json
            db.execute('''
                INSERT OR REPLACE INTO discovered_models
                (name, source, model_type, size_gb, parameters, 
                 capabilities, last_seen, available)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                model['name'],
                model['source'],
                model['model_type'],
                model.get('size_gb', 0),
                model.get('parameters', 'unknown'),
                json.dumps(model.get('capabilities', {})),
                model['last_seen'],
                model['available']
            ), commit=True)
        
        logger.info(f"已保存 {len(models)} 个发现的模型")
    
    def get_discovered_models(self) -> List[Dict]:
        """获取已发现的模型"""
        db = DatabaseManager.get(self.db_path)
        rows = db.query('''
            SELECT name, source, model_type, size_gb, parameters, 
                   capabilities, last_seen, available
            FROM discovered_models
            WHERE available = 1
        ''')
        
        models = []
        for row in rows:
            import json
            models.append({
                'name': row[0],
                'source': row[1],
                'model_type': row[2],
                'size_gb': row[3],
                'parameters': row[4],
                'capabilities': json.loads(row[5]) if row[5] else {},
                'last_seen': row[6],
                'available': row[7]
            })
        
        return models
    
    def get_model_info(self, model_name: str) -> Optional[Dict]:
        """获取特定模型信息"""
        db = DatabaseManager.get(self.db_path)
        row = db.query_one('''
            SELECT name, source, model_type, size_gb, parameters, 
                   capabilities, last_seen, available
            FROM discovered_models
            WHERE name = ?
        ''', (model_name,))
        
        if row:
            import json
            return {
                'name': row[0],
                'source': row[1],
                'model_type': row[2],
                'size_gb': row[3],
                'parameters': row[4],
                'capabilities': json.loads(row[5]) if row[5] else {},
                'last_seen': row[6],
                'available': row[7]
            }
        
        return None
    
    async def refresh(self) -> Dict:
        """刷新模型发现"""
        models = await self.discover_all_models()
        
        from infrastructure.model_capability import model_capability
        for model in models:
            capabilities = model.get('capabilities', {})
            if capabilities:
                model_capability.register_model(model['name'], capabilities)
        
        return {
            'discovered': len(models),
            'sources': list(set(m['source'] for m in models)),
            'timestamp': datetime.now().isoformat()
        }
    
    def discover_all_models_sync(self) -> List[Dict]:
        """同步版本，供现有同步代码调用"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.discover_all_models())
                return future.result()
        else:
            return asyncio.run(self.discover_all_models())
    
    def refresh_sync(self) -> Dict:
        """同步刷新版本"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.refresh())
                return future.result()
        else:
            return asyncio.run(self.refresh())
    
    def mark_unavailable(self, model_name: str):
        """标记模型不可用"""
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            UPDATE discovered_models
            SET available = 0, last_seen = ?
            WHERE name = ?
        ''', (datetime.now().isoformat(), model_name), commit=True)
        
        logger.info(f"已标记模型不可用: {model_name}")


model_discovery = ModelDiscovery()
