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


class ConfigWatcher:
    """配置文件监控器"""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config_path = Path(config_path)
        self.last_mtime: Optional[float] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.check_interval = 2
        
        logger.info(f"配置监控器初始化: {config_path}")
    
    def start(self):
        """启动监控"""
        if not self.config_path.exists():
            logger.warning(f"配置文件不存在: {self.config_path}")
            return
        
        self.last_mtime = self.config_path.stat().st_mtime
        self.running = True
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()
        
        logger.info(f"配置文件监控已启动: {self.config_path}")
    
    def stop(self):
        """停止监控"""
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        
        logger.info("配置文件监控已停止")
    
    def _watch_loop(self):
        """监控循环"""
        while self.running:
            try:
                if not self.config_path.exists():
                    time.sleep(self.check_interval)
                    continue
                
                current_mtime = self.config_path.stat().st_mtime
                
                if current_mtime != self.last_mtime:
                    self.last_mtime = current_mtime
                    self._reload_config()
            
            except Exception as e:
                logger.error(f"监控配置文件失败: {e}")
            
            time.sleep(self.check_interval)
    
    def _reload_config(self):
        """重新加载配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                new_config = yaml.safe_load(f) or {}
            
            from infrastructure.config_manager import config
            config.reload(new_config)
            
            bus.publish(Events.CONFIG_UPDATED, {"config": new_config})
            
            logger.info("配置文件已热加载")
        
        except Exception as e:
            logger.error(f"重新加载配置失败: {e}")


config_watcher = ConfigWatcher()