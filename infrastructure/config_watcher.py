"""
配置文件热加载监控
自动检测配置文件变化并重新加载
"""
import os
import time
import yaml
import threading
from pathlib import Path
from typing import Optional
from loguru import logger
from infrastructure.event_bus import bus
from infrastructure.events import Events

MAX_CONFIG_SIZE = 1 * 1024 * 1024  # 1MB


class ConfigWatcher:
    """配置文件监控器"""
    
    def __init__(self, config_path: str = "config/settings.yaml", check_interval: int = 2):
        self.config_path = Path(config_path).resolve()
        self.last_mtime: Optional[float] = None
        self._stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.check_interval = check_interval
        
        logger.info(f"配置监控器初始化: {self.config_path}")
    
    def start(self):
        """启动监控"""
        if not self.config_path.exists():
            logger.warning(f"配置文件不存在: {self.config_path}")
            return
        
        if self.config_path.is_symlink():
            logger.warning(f"配置路径是符号链接: {self.config_path}")
        
        self.last_mtime = self.config_path.stat().st_mtime
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        
        logger.info(f"配置文件监控已启动: {self.config_path}")
    
    def stop(self):
        """停止监控"""
        self._stop_event.set()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        
        logger.info("配置文件监控已停止")
    
    def _watch_loop(self):
        """监控循环"""
        while not self._stop_event.is_set():
            try:
                if not self.config_path.exists():
                    self._stop_event.wait(self.check_interval)
                    continue
                
                current_mtime = self.config_path.stat().st_mtime
                
                if current_mtime != self.last_mtime:
                    self.last_mtime = current_mtime
                    self._reload_config()
            
            except Exception as e:
                logger.error(f"监控配置文件失败: {e}")
            
            self._stop_event.wait(self.check_interval)
    
    def _reload_config(self):
        """重新加载配置"""
        try:
            file_size = self.config_path.stat().st_size
            if file_size > MAX_CONFIG_SIZE:
                logger.error(f"配置文件过大 ({file_size}字节)，超过限制 {MAX_CONFIG_SIZE}字节，跳过加载")
                return
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                new_config = yaml.safe_load(f) or {}
            
            from infrastructure.config_manager import config
            config.reload(new_config)
            
            bus.publish(Events.CONFIG_UPDATED, {"config": new_config})
            
            logger.info(f"配置文件已热加载 (大小: {file_size}字节)")
        
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")


config_watcher = ConfigWatcher()