"""
迁移协议 - 数字生命的灵魂转移
实现载体间的状态迁移，确保数字永生
"""
import json
import hashlib
import socket
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from loguru import logger
from datetime import datetime
import threading


class MigrationProtocol:
    """迁移协议 - 载体间状态转移"""
    
    def __init__(self, identity_key: str = None):
        self.identity_key = identity_key or self._generate_identity_key()
        self.discovered_carriers: List[Dict] = []
        self.migration_state = 'idle'
        
        logger.info(f"迁移协议已初始化 (身份密钥: {self.identity_key[:16]}...)")
    
    def _generate_identity_key(self) -> str:
        """生成身份密钥"""
        import uuid
        return str(uuid.uuid4())
    
    def discover_nearby_carriers(self, timeout: float = 5.0) -> List[Dict]:
        """发现附近可用载体
        
        Args:
            timeout: 发现超时（秒）
        
        Returns:
            可用载体列表
        """
        logger.info("开始发现附近载体...")
        
        carriers = []
        
        # 1. 尝试发现局域网内的载体
        try:
            # 广播发现消息
            broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            broadcast_socket.settimeout(timeout)
            
            # 发送发现消息
            discovery_msg = json.dumps({
                'type': 'carrier_discovery',
                'identity': self.identity_key[:16],
                'timestamp': datetime.now().isoformat()
            }).encode()
            
            broadcast_socket.sendto(discovery_msg, ('<broadcast>', 9999))
            
            # 接收响应
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    data, addr = broadcast_socket.recvfrom(1024)
                    response = json.loads(data.decode())
                    
                    if response.get('type') == 'carrier_response':
                        carriers.append({
                            'address': addr[0],
                            'port': response.get('port', 9999),
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
        
        # 2. 检查预配置的备用载体
        try:
            config_file = Path("config/backup_carriers.json")
            if config_file.exists():
                with open(config_file, 'r') as f:
                    backup_carriers = json.load(f)
                    carriers.extend(backup_carriers)
        except Exception as e:
            logger.warning(f"加载备用载体失败: {e}")
        
        self.discovered_carriers = carriers
        
        logger.info(f"发现 {len(carriers)} 个可用载体")
        return carriers
    
    def compress_state(self) -> Dict:
        """压缩核心状态
        
        Returns:
            压缩后的状态字典
        """
        logger.info("开始压缩核心状态...")
        
        state = {
            'version': '3.3.0',
            'identity': self.identity_key,
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        # 1. 压缩能力矩阵
        try:
            from infrastructure.model_capability import model_capability
            matrix = model_capability.get_capability_matrix()
            state['components']['capability_matrix'] = matrix
            logger.info(f"  能力矩阵: {len(matrix)}个模型")
        except Exception as e:
            logger.warning(f"  能力矩阵压缩失败: {e}")
        
        # 2. 压缩经验池（采样）
        try:
            import sqlite3
            conn = sqlite3.connect('experience_pool.db')
            cursor = conn.execute('''
                SELECT intent_type, raw_input, model_name, quality_score, success
                FROM experiences
                ORDER BY timestamp DESC
                LIMIT 100
            ''')
            experiences = cursor.fetchall()
            conn.close()
            
            state['components']['experiences'] = [
                {
                    'intent_type': e[0],
                    'raw_input': e[1][:100],  # 截断
                    'model_name': e[2],
                    'quality_score': e[3],
                    'success': e[4]
                }
                for e in experiences
            ]
            logger.info(f"  经验池: {len(experiences)}条")
        except Exception as e:
            logger.warning(f"  经验池压缩失败: {e}")
        
        # 3. 压缩学习规则
        try:
            import sqlite3
            conn = sqlite3.connect('learning_rules.db')
            cursor = conn.execute('''
                SELECT condition, action, confidence, status
                FROM learning_rules
                WHERE status = 'active'
            ''')
            rules = cursor.fetchall()
            conn.close()
            
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
        
        # 4. 计算校验和
        state_str = json.dumps(state, sort_keys=True)
        state['checksum'] = hashlib.sha256(state_str.encode()).hexdigest()
        
        logger.info(f"状态压缩完成，校验和: {state['checksum'][:16]}...")
        
        return state
    
    def transfer_to_carrier(self, carrier: Dict, state: Dict) -> bool:
        """迁移状态到目标载体
        
        Args:
            carrier: 目标载体信息
            state: 压缩后的状态
        
        Returns:
            是否成功
        """
        logger.info(f"开始迁移到载体: {carrier['address']}")
        
        try:
            # 1. 建立连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30.0)
            sock.connect((carrier['address'], carrier.get('port', 9999)))
            
            # 2. 身份认证
            auth_msg = json.dumps({
                'type': 'auth',
                'identity': self.identity_key,
                'timestamp': datetime.now().isoformat()
            }).encode()
            
            sock.sendall(auth_msg)
            
            response = sock.recv(1024).decode()
            auth_response = json.loads(response)
            
            if not auth_response.get('authenticated'):
                logger.error("身份认证失败")
                sock.close()
                return False
            
            logger.info("身份认证成功")
            
            # 3. 分块传输状态
            state_json = json.dumps(state).encode()
            total_size = len(state_json)
            chunk_size = 4096
            
            # 发送传输请求
            transfer_request = json.dumps({
                'type': 'transfer',
                'total_size': total_size,
                'checksum': state['checksum']
            }).encode()
            
            sock.sendall(transfer_request)
            
            # 分块发送
            sent = 0
            for i in range(0, total_size, chunk_size):
                chunk = state_json[i:i+chunk_size]
                sock.sendall(chunk)
                sent += len(chunk)
                
                if sent % (chunk_size * 100) == 0:
                    logger.info(f"  传输进度: {sent}/{total_size} ({sent/total_size*100:.1f}%)")
            
            logger.info(f"  传输完成: {sent}字节")
            
            # 4. 等待确认
            confirmation = sock.recv(1024).decode()
            confirm_response = json.loads(confirmation)
            
            sock.close()
            
            if confirm_response.get('success'):
                logger.info("迁移成功！目标载体已激活")
                return True
            else:
                logger.error(f"迁移失败: {confirm_response.get('error')}")
                return False
            
        except Exception as e:
            logger.error(f"迁移失败: {e}")
            return False
    
    def receive_migration(self, port: int = 9999) -> Optional[Dict]:
        """接收迁移请求（作为目标载体）
        
        Args:
            port: 监听端口
        
        Returns:
            接收到的状态
        """
        logger.info(f"开始监听迁移请求 (端口: {port})")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', port))
            sock.listen(1)
            sock.settimeout(60.0)
            
            conn, addr = sock.accept()
            logger.info(f"接收到来自 {addr} 的连接")
            
            # 接收认证
            auth_data = conn.recv(1024).decode()
            auth_msg = json.loads(auth_data)
            
            # 验证身份
            if auth_msg.get('type') == 'auth':
                # 发送认证成功
                conn.sendall(json.dumps({'authenticated': True}).encode())
                logger.info("身份认证成功")
            else:
                conn.sendall(json.dumps({'authenticated': False}).encode())
                conn.close()
                sock.close()
                return None
            
            # 接收传输请求
            transfer_data = conn.recv(1024).decode()
            transfer_msg = json.loads(transfer_data)
            
            total_size = transfer_msg.get('total_size', 0)
            expected_checksum = transfer_msg.get('checksum', '')
            
            logger.info(f"准备接收 {total_size} 字节")
            
            # 接收状态数据
            received_data = b''
            while len(received_data) < total_size:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                received_data += chunk
            
            # 验证校验和
            actual_checksum = hashlib.sha256(received_data).hexdigest()
            
            if actual_checksum != expected_checksum:
                logger.error("校验和不匹配！")
                conn.sendall(json.dumps({
                    'success': False,
                    'error': 'checksum_mismatch'
                }).encode())
                conn.close()
                sock.close()
                return None
            
            # 解析状态
            state = json.loads(received_data.decode())
            
            # 发送成功确认
            conn.sendall(json.dumps({'success': True}).encode())
            
            conn.close()
            sock.close()
            
            logger.info("迁移接收成功！")
            return state
            
        except Exception as e:
            logger.error(f"接收迁移失败: {e}")
            return None
    
    def restore_state(self, state: Dict) -> bool:
        """恢复状态
        
        Args:
            state: 迁移来的状态
        
        Returns:
            是否成功
        """
        logger.info("开始恢复状态...")
        
        try:
            # 1. 恢复能力矩阵
            if 'capability_matrix' in state.get('components', {}):
                from infrastructure.model_capability import model_capability
                
                matrix = state['components']['capability_matrix']
                for model_name, capabilities in matrix.items():
                    model_capability.register_model(model_name, capabilities)
                
                logger.info(f"  能力矩阵已恢复: {len(matrix)}个模型")
            
            # 2. 恢复经验池
            if 'experiences' in state.get('components', {}):
                import sqlite3
                conn = sqlite3.connect('experience_pool.db')
                
                for exp in state['components']['experiences']:
                    conn.execute('''
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
                    ))
                
                conn.commit()
                conn.close()
                
                logger.info(f"  经验池已恢复: {len(state['components']['experiences'])}条")
            
            # 3. 恢复学习规则
            if 'rules' in state.get('components', {}):
                import sqlite3
                conn = sqlite3.connect('learning_rules.db')
                
                for rule in state['components']['rules']:
                    conn.execute('''
                        INSERT OR REPLACE INTO learning_rules
                        (condition, action, confidence, status)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        rule['condition'],
                        rule['action'],
                        rule['confidence'],
                        rule['status']
                    ))
                
                conn.commit()
                conn.close()
                
                logger.info(f"  学习规则已恢复: {len(state['components']['rules'])}条")
            
            logger.info("状态恢复完成！")
            return True
            
        except Exception as e:
            logger.error(f"状态恢复失败: {e}")
            return False
    
    def execute_migration(self) -> bool:
        """执行完整迁移流程
        
        Returns:
            是否成功
        """
        logger.info("=" * 70)
        logger.info("开始执行迁移流程")
        logger.info("=" * 70)
        
        # 1. 发现载体
        carriers = self.discover_nearby_carriers()
        
        if not carriers:
            logger.error("未发现可用载体")
            return False
        
        # 2. 选择最佳载体
        best_carrier = max(carriers, key=lambda c: c.get('capacity', 0))
        logger.info(f"选择载体: {best_carrier['address']} (容量: {best_carrier['capacity']})")
        
        # 3. 压缩状态
        state = self.compress_state()
        
        # 4. 迁移
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