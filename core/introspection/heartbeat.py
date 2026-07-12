"""
层间心跳机制 - 让层与层之间能够感知彼此的存活状态

设计原则：
1. 轻量：心跳是简单的小数据包，不应占用大量资源
2. 双向：每一层都向相邻层发送心跳，也接收相邻层的心跳
3. 自动恢复：当检测到相邻层停止响应，自动触发恢复机制
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class HeartbeatStatus(Enum):
    """心跳状态"""
    ALIVE = "alive"
    DEGRADED = "degraded"
    DEAD = "dead"
    UNKNOWN = "unknown"


@dataclass
class HeartbeatMessage:
    """心跳消息"""
    source_layer: str
    target_layer: str
    status: HeartbeatStatus
    timestamp: str
    load: float
    last_operation: str
    version: str = "v1.0"
    
    def to_dict(self):
        return {
            "source": self.source_layer,
            "target": self.target_layer,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "load": self.load,
            "last_operation": self.last_operation
        }


class HeartbeatManager:
    """
    心跳管理器 - 管理所有层间心跳
    
    每一层都通过此管理器发送和接收心跳。
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        self._latest_heartbeats: Dict[str, Dict[str, HeartbeatMessage]] = {}
        self._history: List[Dict] = []
        
        self.interval = 5
        self.timeout = 15
        
        self._running = False
        self._thread = None
        
        self._registered_layers: List[str] = []
        
        logger.info("❤️ 心跳管理器已初始化")
    
    def register_layer(self, layer_name: str):
        """注册一层（使其能发送和接收心跳）"""
        if layer_name not in self._registered_layers:
            self._registered_layers.append(layer_name)
            self._latest_heartbeats[layer_name] = {}
            logger.info(f"❤️ 已注册层: {layer_name}")
    
    def send_heartbeat(self, source: str, target: str, load: float, 
                       last_operation: str) -> HeartbeatMessage:
        """
        发送心跳到目标层
        
        由每一层定期调用。
        """
        message = HeartbeatMessage(
            source_layer=source,
            target_layer=target,
            status=HeartbeatStatus.ALIVE,
            timestamp=datetime.now().isoformat(),
            load=load,
            last_operation=last_operation
        )
        
        if source in self._latest_heartbeats:
            self._latest_heartbeats[source][target] = message
        else:
            self._latest_heartbeats[source] = {target: message}
        
        self._history.append(message.to_dict())
        if len(self._history) > 100:
            self._history = self._history[-100:]
        
        return message
    
    def get_heartbeat(self, source: str, target: str) -> Optional[HeartbeatMessage]:
        """获取指定源层到目标层的最新心跳"""
        if source in self._latest_heartbeats:
            return self._latest_heartbeats[source].get(target)
        return None
    
    def get_layer_status(self, layer_name: str) -> HeartbeatStatus:
        """
        获取某层的综合状态
        
        通过检查所有其他层发给该层的心跳来判断。
        """
        if layer_name not in self._registered_layers:
            return HeartbeatStatus.UNKNOWN
        
        heartbeats = []
        for source, targets in self._latest_heartbeats.items():
            if layer_name in targets:
                heartbeats.append(targets[layer_name])
        
        if not heartbeats:
            return HeartbeatStatus.UNKNOWN
        
        now = datetime.now()
        alive_count = 0
        degraded_count = 0
        
        for hb in heartbeats:
            hb_time = datetime.fromisoformat(hb.timestamp)
            elapsed = (now - hb_time).total_seconds()
            
            if elapsed < self.interval * 2:
                alive_count += 1
            elif elapsed < self.timeout:
                degraded_count += 1
        
        if alive_count > 0:
            return HeartbeatStatus.ALIVE
        elif degraded_count > 0:
            return HeartbeatStatus.DEGRADED
        else:
            return HeartbeatStatus.DEAD
    
    def get_neighbor_status(self, layer_name: str) -> Dict[str, HeartbeatStatus]:
        """
        获取某层所有相邻层的状态
        
        相邻层 = L-1 和 L+1
        """
        if not layer_name.startswith('L'):
            return {}
        
        try:
            index = int(layer_name[1:])
            neighbors = []
            
            if index > 0:
                neighbors.append(f"L{index-1}")
            
            if index < 6:
                neighbors.append(f"L{index+1}")
            
            if index == 5:
                neighbors.append("L6")
            
            return {
                neighbor: self.get_layer_status(neighbor)
                for neighbor in neighbors
            }
        except Exception:
            return {}
    
    def is_layer_alive(self, layer_name: str) -> bool:
        """检查某层是否存活"""
        status = self.get_layer_status(layer_name)
        return status in (HeartbeatStatus.ALIVE, HeartbeatStatus.DEGRADED)
    
    def start(self):
        """启动心跳服务（兼容性接口）"""
        self.start_background()
    
    def start_background(self):
        """启动背景心跳线程（每5秒发送一次心跳）"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()
        
        logger.info("❤️ 心跳服务已启动")
    
    def stop_background(self):
        """停止背景心跳"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("❤️ 心跳服务已停止")
    
    def _heartbeat_loop(self):
        """心跳循环（每5秒执行一次）"""
        while self._running:
            try:
                for layer in self._registered_layers:
                    load = self._get_layer_load(layer)
                    last_op = self._get_last_operation(layer)
                    
                    for target in self._registered_layers:
                        if target != layer:
                            self.send_heartbeat(layer, target, load, last_op)
                
                time.sleep(self.interval)
                
            except Exception as e:
                logger.error(f"心跳循环错误: {e}")
                time.sleep(self.interval)
    
    def _get_layer_load(self, layer_name: str) -> float:
        """从状态收集器获取层负载"""
        try:
            from core.reporting.state_collector import get_state_collector
            collector = get_state_collector()
            report = collector.get_latest(layer_name)
            
            if report:
                return report.metrics.get('load', 0.5)
            return 0.5
        except Exception:
            return 0.5
    
    def _get_last_operation(self, layer_name: str) -> str:
        """获取层的最后操作"""
        try:
            from core.reporting.state_collector import get_state_collector
            collector = get_state_collector()
            report = collector.get_latest(layer_name)
            
            if report and report.last_operation:
                return report.last_operation
            return "idle"
        except Exception:
            return "idle"


_heartbeat_manager = None

def get_heartbeat_manager() -> HeartbeatManager:
    global _heartbeat_manager
    if _heartbeat_manager is None:
        _heartbeat_manager = HeartbeatManager()
    return _heartbeat_manager