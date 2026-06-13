"""
外部模型配置管理 - 安全加密存储
使用Fernet对称加密保护API密钥
"""
import os
import json
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional, List
from loguru import logger

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography未安装，使用明文存储（不推荐）")


class ExternalModelConfig:
    """外部模型配置管理器"""
    
    def __init__(self, config_dir: str = "data"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        self.key_file = self.config_dir / "fernet.key"
        self.db_file = self.config_dir / "external_models.db"
        
        self.cipher = self._init_cipher()
        self._init_db()
        
        logger.info("外部模型配置管理器已初始化")
    
    def _init_cipher(self) -> Optional[Fernet]:
        """初始化加密器"""
        if not CRYPTO_AVAILABLE:
            return None
        
        # 从环境变量或文件获取密钥
        key = os.getenv("FERNET_KEY")
        
        if not key:
            if self.key_file.exists():
                key = self.key_file.read_bytes()
            else:
                # 生成新密钥
                key = Fernet.generate_key()
                self.key_file.write_bytes(key)
                logger.info("已生成新的加密密钥")
        
        return Fernet(key if isinstance(key, bytes) else key.encode())
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_file)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS external_models (
                name TEXT PRIMARY KEY,
                api_url TEXT,
                api_key_encrypted TEXT,
                daily_limit INTEGER DEFAULT 1000,
                used_today INTEGER DEFAULT 0,
                last_reset TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS api_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT,
                timestamp TEXT,
                tokens_used INTEGER,
                success BOOLEAN,
                error_message TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _encrypt(self, text: str) -> str:
        """加密文本"""
        if self.cipher:
            return self.cipher.encrypt(text.encode()).decode()
        return text  # 降级：明文
    
    def _decrypt(self, encrypted: str) -> str:
        """解密文本"""
        if self.cipher and encrypted:
            try:
                return self.cipher.decrypt(encrypted.encode()).decode()
            except:
                return encrypted
        return encrypted
    
    def add_model(self, name: str, api_url: str, api_key: str, 
                  daily_limit: int = 1000) -> bool:
        """添加或更新外部模型"""
        try:
            encrypted_key = self._encrypt(api_key)
            now = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_file)
            conn.execute('''
                INSERT OR REPLACE INTO external_models
                (name, api_url, api_key_encrypted, daily_limit, used_today, last_reset, created_at, updated_at)
                VALUES (?, ?, ?, ?, 0, ?, ?, ?)
            ''', (name, api_url, encrypted_key, daily_limit, now, now, now))
            conn.commit()
            conn.close()
            
            logger.info(f"已添加外部模型: {name}")
            return True
            
        except Exception as e:
            logger.error(f"添加模型失败: {e}")
            return False
    
    def get_model(self, name: str) -> Optional[Dict]:
        """获取模型配置（含解密后的API密钥）"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.execute('''
            SELECT name, api_url, api_key_encrypted, daily_limit, used_today, last_reset
            FROM external_models
            WHERE name = ?
        ''', (name,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            'name': row[0],
            'api_url': row[1],
            'api_key': self._decrypt(row[2]),
            'daily_limit': row[3],
            'used_today': row[4],
            'last_reset': row[5]
        }
    
    def list_models(self) -> List[Dict]:
        """列出所有模型（不含密钥）"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.execute('''
            SELECT name, api_url, daily_limit, used_today, last_reset
            FROM external_models
        ''')
        
        models = []
        for row in cursor.fetchall():
            models.append({
                'name': row[0],
                'api_url': row[1],
                'daily_limit': row[2],
                'used_today': row[3],
                'last_reset': row[4]
            })
        
        conn.close()
        return models
    
    def delete_model(self, name: str) -> bool:
        """删除模型"""
        try:
            conn = sqlite3.connect(self.db_file)
            conn.execute('DELETE FROM external_models WHERE name = ?', (name,))
            conn.commit()
            conn.close()
            
            logger.info(f"已删除外部模型: {name}")
            return True
            
        except Exception as e:
            logger.error(f"删除模型失败: {e}")
            return False
    
    def record_usage(self, name: str, tokens: int = 0, 
                     success: bool = True, error: str = None):
        """记录API使用"""
        now = datetime.now().isoformat()
        today = date.today().isoformat()
        
        conn = sqlite3.connect(self.db_file)
        
        # 记录使用日志
        conn.execute('''
            INSERT INTO api_usage_log
            (model_name, timestamp, tokens_used, success, error_message)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, now, tokens, success, error))
        
        # 更新每日使用量
        cursor = conn.execute('''
            SELECT last_reset, used_today FROM external_models WHERE name = ?
        ''', (name,))
        row = cursor.fetchone()
        
        if row:
            last_reset, used_today = row
            
            # 检查是否需要重置
            if last_reset != today:
                used_today = 0
            
            conn.execute('''
                UPDATE external_models
                SET used_today = ?, last_reset = ?
                WHERE name = ?
            ''', (used_today + 1, today, name))
        
        conn.commit()
        conn.close()
    
    def check_quota(self, name: str) -> bool:
        """检查是否超出配额"""
        today = date.today().isoformat()
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.execute('''
            SELECT daily_limit, used_today, last_reset
            FROM external_models
            WHERE name = ?
        ''', (name,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return False
        
        daily_limit, used_today, last_reset = row
        
        # 新的一天，重置
        if last_reset != today:
            return True
        
        return used_today < daily_limit
    
    def get_usage_stats(self, name: str, days: int = 7) -> Dict:
        """获取使用统计"""
        conn = sqlite3.connect(self.db_file)
        
        # 总调用次数
        cursor = conn.execute('''
            SELECT COUNT(*), SUM(tokens_used), SUM(CASE WHEN success THEN 1 ELSE 0 END)
            FROM api_usage_log
            WHERE model_name = ?
              AND timestamp >= datetime('now', ?)
        ''', (name, f'-{days} days'))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            'total_calls': row[0] if row[0] else 0,
            'total_tokens': row[1] if row[1] else 0,
            'success_rate': row[2] / row[0] if row[0] and row[0] > 0 else 0
        }


# 全局实例
external_model_config = ExternalModelConfig()