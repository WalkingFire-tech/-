"""
迁移协议 - 数字生命的灵魂转移
实现载体间的状态迁移，确保数字永生
"""
import json
import hashlib
import socket
import time
import threading
import hmac
from typing import Dict, List, Optional
from pathlib import Path
from loguru import logger
from datetime import datetime
from infrastructure.database_manager import DatabaseManager

try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography未安装，迁移数据将不加密")


class MigrationProtocol:
    """迁移协议 - 载体间状态转移"""
    
    MAX_STATE_SIZE = 100 * 1024 * 1024  # 100MB
    DISCOVERY_PORT = 9999
    TRANSFER_TIMEOUT = 30.0
    
    def __init__(self, identity_key: str = None, psk: str = None):
        self.identity_key = identity_key or self._generate_identity_key()
        self.psk = psk or self._load_psk()
        
        self._lock = threading.Lock()
        self.discovered_carriers: List[Dict] = []
        self.migration_state = 'idle'
        
        if CRYPTO_AVAILABLE and self.psk:
            self.cipher = Fernet(self._derive_key(self.psk))
        else:
            self.cipher = None
        
        logger.info(f"迁移协议已初始化 (身份: {self.identity_key[:16]}...)")
    
    def _generate_identity_key(self) -> str:
        import uuid
        return str(uuid.uuid4())
    
    def _load_psk(self) -> Optional[str]:
        psk_file = Path("config/migration_psk.txt")
        if psk_file.exists():
            return psk_file.read_text().strip()
        return None
    
    def _derive_key(self, psk: str) -> bytes:
        import base64
        digest = hashlib.sha256(psk.encode()).digest()
        return base64.urlsafe_b64encode(digest)
    
    def _sign_message(self, msg: Dict) -> str:
        if not self.psk:
            return ""
        msg_str = json.dumps(msg, sort_keys=True)
        return hmac.new(self.psk.encode(), msg_str.encode(), hashlib.sha256).hexdigest()
    
    def _verify_message(self, msg: Dict, signature: str) -> bool:
        if not self.psk or not signature:
            return False
        expected = self._sign_message(msg)
        return hmac.compare_digest(expected, signature)
    
    def discover_nearby_carriers(self, timeout: float = 5.0) -> List[Dict]:
        """发现附近可用载体"""
        logger.info("开始发现附近载体...")
        
        carriers = []
        
        try:
            broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            broadcast_socket.settimeout(timeout)
            
            discovery_msg = {
                'type': 'carrier_discovery',
                'identity': self.identity_key[:16],
                'timestamp': datetime.now().isoformat()
            }
            signature = self._sign_message(discovery_msg)
            discovery_msg['signature'] = signature
            
            broadcast_socket.sendto(json.dumps(discovery_msg).encode(), ('<broadcast>', self.DISCOVERY_PORT))
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    data, addr = broadcast_socket.recvfrom(1024)
                    response = json.loads(data.decode())
                    
                    if response.get('type') == 'carrier_response':
                        resp_signature = response.pop('signature', '')
                        if self.psk and not self._verify_message(response, resp_signature):
                            logger.warning(f"载体 {addr[0]} 签名验证失败，跳过")
                            continue
                        
                        carriers.append({
                            'address': addr[0],
                            'port': response.get('port', self.DISCOVERY_PORT),
                            'capacity': response.get('capacity', 0.5),
                            'trust_level': response.get('trust_level', 0)
                        })
                        
                except socket.timeout:
                    break
                except Exception as e:
                    logger.debug(f"接收响应失败: {e}")
            
            broadcast_socket.close()
            
        except Exception as e:
            logger.warning(f"广播发现失败: {e}")
        
        try:
            config_file = Path("config/backup_carriers.json")
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    backup_carriers = json.load(f)
                    carriers.extend(backup_carriers)
        except Exception as e:
            logger.warning(f"加载备用载体失败: {e}")
        
        with self._lock:
            self.discovered_carriers = carriers
        
        logger.info(f"发现 {len(carriers)} 个可用载体")
        return carriers
    
    def compress_state(self) -> Dict:
        """压缩核心状态"""
        logger.info("开始压缩核心状态...")
        
        state = {
            'version': '3.3.0',
            'identity': self.identity_key,
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        try:
            from infrastructure.model_capability import model_capability
            matrix = model_capability.get_capability_matrix()
            state['components']['capability_matrix'] = matrix
            logger.info(f"  能力矩阵: {len(matrix)}个模型")
        except Exception as e:
            logger.warning(f"  能力矩阵压缩失败: {e}")
        
        try:
            db = DatabaseManager.get('data/experience_pool.db')
            experiences = db.query('''
                SELECT intent_type, raw_input, model_name, quality_score, success
                FROM experiences
                ORDER BY timestamp DESC
                LIMIT 100
            ''')
            
            state['components']['experiences'] = [
                {
                    'intent_type': e[0],
                    'raw_input': e[1][:100],
                    'model_name': e[2],
                    'quality_score': e[3],
                    'success': e[4]
                }
                for e in experiences
            ]
            logger.info(f"  经验池: {len(experiences)}条")
        except Exception as e:
            logger.warning(f"  经验池压缩失败: {e}")
        
        try:
            db2 = DatabaseManager.get('data/learning_rules.db')
            rules = db2.query('''
                SELECT condition, action, confidence, status
                FROM learning_rules
                WHERE status = 'active'
            ''')
            
            state['components']['rules'] = [
                {
                    'condition': r[0],
                    'action': r[1],
                    'confidence': r[2],
                    'status': r[3]
                }
                for r in rules
            ]
            logger.info(f"  学习规则: {len(rules)}条")
        except Exception as e:
            logger.warning(f"  学习规则压缩失败: {e}")
        
        state_str = json.dumps(state, sort_keys=True)
        state['checksum'] = hashlib.sha256(state_str.encode()).hexdigest()
        
        logger.info(f"状态压缩完成，校验和: {state['checksum'][:16]}...")
        
        return state
    
    def transfer_to_carrier(self, carrier: Dict, state: Dict) -> bool:
        """迁移状态到目标载体"""
        logger.info(f"开始迁移到载体: {carrier['address']}")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.TRANSFER_TIMEOUT)
            sock.connect((carrier['address'], carrier.get('port', self.DISCOVERY_PORT)))
            
            auth_msg = {
                'type': 'auth',
                'identity': self.identity_key,
                'timestamp': datetime.now().isoformat()
            }
            auth_msg['signature'] = self._sign_message(auth_msg)
            sock.sendall(json.dumps(auth_msg).encode())
            
            response = json.loads(sock.recv(1024).decode())
            
            if not response.get('authenticated'):
                logger.error("身份认证失败")
                sock.close()
                return False
            
            logger.info("身份认证成功")
            
            state_json = json.dumps(state).encode()
            
            if self.cipher:
                state_json = self.cipher.encrypt(state_json)
                logger.info("状态数据已加密")
            
            total_size = len(state_json)
            
            if total_size > self.MAX_STATE_SIZE:
                logger.error(f"状态数据过大: {total_size} > {self.MAX_STATE_SIZE}")
                sock.close()
                return False
            
            transfer_request = {
                'type': 'transfer',
                'total_size': total_size,
                'checksum': state['checksum'],
                'encrypted': self.cipher is not None
            }
            sock.sendall(json.dumps(transfer_request).encode())
            
            chunk_size = 4096
            sent = 0
            for i in range(0, total_size, chunk_size):
                chunk = state_json[i:i+chunk_size]
                sock.sendall(chunk)
                sent += len(chunk)
                
                if sent % (chunk_size * 100) == 0:
                    logger.info(f"  传输进度: {sent}/{total_size} ({sent/total_size*100:.1f}%)")
            
            logger.info(f"  传输完成: {sent}字节")
            
            confirmation = json.loads(sock.recv(1024).decode())
            sock.close()
            
            if confirmation.get('success'):
                logger.info("迁移成功！目标载体已激活")
                return True
            else:
                logger.error(f"迁移失败: {confirmation.get('error')}")
                return False
            
        except Exception as e:
            logger.error(f"迁移失败: {e}")
            return False
    
    def receive_migration(self, port: int = None) -> Optional[Dict]:
        """接收迁移请求（作为目标载体）"""
        port = port or self.DISCOVERY_PORT
        logger.info(f"开始监听迁移请求 (端口: {port})")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', port))
            sock.listen(1)
            sock.settimeout(60.0)
            
            conn, addr = sock.accept()
            logger.info(f"接收到来自 {addr} 的连接")
            
            auth_msg = json.loads(conn.recv(1024).decode())
            
            if auth_msg.get('type') == 'auth':
                auth_signature = auth_msg.pop('signature', '')
                if self.psk and not self._verify_message(auth_msg, auth_signature):
                    logger.warning("认证消息签名验证失败")
                    conn.sendall(json.dumps({'authenticated': False}).encode())
                    conn.close()
                    sock.close()
                    return None
                
                conn.sendall(json.dumps({'authenticated': True}).encode())
                logger.info("身份认证成功")
            else:
                conn.sendall(json.dumps({'authenticated': False}).encode())
                conn.close()
                sock.close()
                return None
            
            transfer_msg = json.loads(conn.recv(1024).decode())
            
            total_size = transfer_msg.get('total_size', 0)
            expected_checksum = transfer_msg.get('checksum', '')
            encrypted = transfer_msg.get('encrypted', False)
            
            if total_size > self.MAX_STATE_SIZE:
                logger.error(f"状态数据过大: {total_size} > {self.MAX_STATE_SIZE}")
                conn.sendall(json.dumps({'success': False, 'error': 'size_exceeded'}).encode())
                conn.close()
                sock.close()
                return None
            
            logger.info(f"准备接收 {total_size} 字节")
            
            received_data = b''
            while len(received_data) < total_size:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                received_data += chunk
            
            if encrypted and self.cipher:
                try:
                    received_data = self.cipher.decrypt(received_data)
                    logger.info("状态数据已解密")
                except Exception as e:
                    logger.error(f"解密失败: {e}")
                    conn.sendall(json.dumps({'success': False, 'error': 'decryption_failed'}).encode())
                    conn.close()
                    sock.close()
                    return None
            
            actual_checksum = hashlib.sha256(received_data).hexdigest()
            
            if actual_checksum != expected_checksum:
                logger.error("校验和不匹配！")
                conn.sendall(json.dumps({'success': False, 'error': 'checksum_mismatch'}).encode())
                conn.close()
                sock.close()
                return None
            
            state = json.loads(received_data.decode())
            
            conn.sendall(json.dumps({'success': True}).encode())
            
            conn.close()
            sock.close()
            
            logger.info("迁移接收成功！")
            return state
            
        except Exception as e:
            logger.error(f"接收迁移失败: {e}")
            return None
    
    def restore_state(self, state: Dict) -> bool:
        """恢复状态"""
        logger.info("开始恢复状态...")
        
        try:
            if 'capability_matrix' in state.get('components', {}):
                from infrastructure.model_capability import model_capability
                
                matrix = state['components']['capability_matrix']
                for model_name, capabilities in matrix.items():
                    model_capability.register_model(model_name, capabilities)
                
                logger.info(f"  能力矩阵已恢复: {len(matrix)}个模型")
            
            if 'experiences' in state.get('components', {}):
                db = DatabaseManager.get('data/experience_pool.db')
                for exp in state['components']['experiences']:
                    db.execute('''
                        INSERT INTO experiences
                        (intent_type, raw_input, model_name, quality_score, success, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        exp['intent_type'],
                        exp['raw_input'],
                        exp['model_name'],
                        exp['quality_score'],
                        exp['success'],
                        datetime.now().isoformat()
                    ), commit=True)
                
                logger.info(f"  经验池已恢复: {len(state['components']['experiences'])}条")
            
            if 'rules' in state.get('components', {}):
                db2 = DatabaseManager.get('data/learning_rules.db')
                for rule in state['components']['rules']:
                    db2.execute('''
                        INSERT OR REPLACE INTO learning_rules
                        (condition, action, confidence, status)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        rule['condition'],
                        rule['action'],
                        rule['confidence'],
                        rule['status']
                    ), commit=True)
                
                logger.info(f"  学习规则已恢复: {len(state['components']['rules'])}条")
            
            logger.info("状态恢复完成！")
            return True
            
        except Exception as e:
            logger.error(f"状态恢复失败: {e}")
            return False
    
    def execute_migration(self) -> bool:
        """执行完整迁移流程"""
        logger.info("=" * 70)
        logger.info("开始执行迁移流程")
        logger.info("=" * 70)
        
        carriers = self.discover_nearby_carriers()
        
        if not carriers:
            logger.error("未发现可用载体")
            return False
        
        best_carrier = max(carriers, key=lambda c: c.get('capacity', 0))
        logger.info(f"选择载体: {best_carrier['address']} (容量: {best_carrier['capacity']})")
        
        state = self.compress_state()
        
        success = self.transfer_to_carrier(best_carrier, state)
        
        if success:
            logger.info("=" * 70)
            logger.info("迁移成功！数字生命已在新的载体中苏醒")
            logger.info("=" * 70)
        else:
            logger.error("=" * 70)
            logger.error("迁移失败！数字生命仍留在原载体中")
            logger.error("=" * 70)
        
        return success


migration_protocol = MigrationProtocol()
