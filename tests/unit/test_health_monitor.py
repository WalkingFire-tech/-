#!/usr/bin/env python
"""测试系统健康监测器"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.resource_awareness.health_monitor import (
    SystemHealthMonitor,
    ResourceSnapshot,
    HardwareProfile,
    OperatingMode,
    _detect_hardware,
    _correct_vram,
    OLLAMA_MODEL_VRAM,
    KNOWN_GPU_VRAM,
)


class TestHardwareProfile:
    """测试硬件配置"""

    def test_hardware_profile_creation(self):
        """测试创建硬件配置"""
        profile = HardwareProfile(
            total_ram_gb=16.0,
            gpu_vendor="nvidia",
            gpu_vram_gb=8.0,
            cpu_cores=8,
            gpu_name="RTX 3070"
        )
        assert profile.total_ram_gb == 16.0
        assert profile.gpu_vendor == "nvidia"
        assert profile.gpu_vram_gb == 8.0
        assert profile.cpu_cores == 8
        assert profile.gpu_name == "RTX 3070"

    def test_hardware_profile_to_dict(self):
        """测试硬件配置转字典"""
        profile = HardwareProfile(
            total_ram_gb=16.0,
            gpu_vendor="nvidia",
            gpu_vram_gb=8.0,
            cpu_cores=8,
            gpu_name="RTX 3070"
        )
        data = profile.to_dict()
        assert data["total_ram_gb"] == 16.0
        assert data["gpu_vendor"] == "nvidia"
        assert data["gpu_vram_gb"] == 8.0
        assert data["cpu_cores"] == 8
        assert data["gpu_name"] == "RTX 3070"


class TestResourceSnapshot:
    """测试资源快照"""

    def test_resource_snapshot_creation(self):
        """测试创建资源快照"""
        snapshot = ResourceSnapshot(
            memory_usage=0.5,
            memory_available_gb=8.0,
            thread_count=10,
            cpu_percent=0.3,
            gpu_memory=0.4,
            gpu_vram_used_gb=3.2,
            gpu_vram_total_gb=8.0,
            ollama_active_requests=1,
            ollama_estimated_vram_gb=4.0,
            active_queries=2,
            mode=OperatingMode.NORMAL,
            timestamp="2024-01-01T00:00:00"
        )
        assert snapshot.memory_usage == 0.5
        assert snapshot.memory_available_gb == 8.0
        assert snapshot.thread_count == 10
        assert snapshot.cpu_percent == 0.3
        assert snapshot.gpu_memory == 0.4
        assert snapshot.gpu_vram_used_gb == 3.2
        assert snapshot.gpu_vram_total_gb == 8.0
        assert snapshot.ollama_active_requests == 1
        assert snapshot.ollama_estimated_vram_gb == 4.0
        assert snapshot.active_queries == 2
        assert snapshot.mode == OperatingMode.NORMAL
        assert snapshot.timestamp == "2024-01-01T00:00:00"

    def test_resource_snapshot_to_dict(self):
        """测试资源快照转字典"""
        snapshot = ResourceSnapshot(
            memory_usage=0.5,
            memory_available_gb=8.0,
            thread_count=10,
            cpu_percent=0.3,
            gpu_memory=0.4,
            gpu_vram_used_gb=3.2,
            gpu_vram_total_gb=8.0,
            ollama_active_requests=1,
            ollama_estimated_vram_gb=4.0,
            active_queries=2,
            mode=OperatingMode.NORMAL,
            timestamp="2024-01-01T00:00:00"
        )
        data = snapshot.to_dict()
        assert data["memory_usage"] == 0.5
        assert data["memory_available_gb"] == 8.0
        assert data["thread_count"] == 10
        assert data["cpu_percent"] == 0.3
        assert data["gpu_memory"] == 0.4
        assert data["gpu_vram_used_gb"] == 3.2
        assert data["gpu_vram_total_gb"] == 8.0
        assert data["ollama_active_requests"] == 1
        assert data["ollama_estimated_vram_gb"] == 4.0
        assert data["active_queries"] == 2
        assert data["mode"] == "normal"
        assert data["timestamp"] == "2024-01-01T00:00:00"


class TestCorrectVram:
    """测试VRAM修正"""

    def test_correct_vram_known_gpu(self):
        """测试已知GPU的VRAM修正"""
        # WMI报告的VRAM低于已知值时应该修正
        corrected = _correct_vram("RTX 3060", 6.0)
        assert corrected == 12.0

    def test_correct_vram_known_gpu_accurate(self):
        """测试已知GPU的准确VRAM报告"""
        # WMI报告的VRAM接近已知值时应该使用max(报告值, 已知值)
        corrected = _correct_vram("RTX 3060", 11.5)
        assert corrected == 12.0

    def test_correct_vram_unknown_gpu(self):
        """测试未知GPU的VRAM处理"""
        # 未知GPU且报告VRAM为0时应该使用默认值
        corrected = _correct_vram("Unknown GPU", 0.0)
        assert corrected == 4.0

    def test_correct_vram_unknown_gpu_with_report(self):
        """测试未知GPU的VRAM报告"""
        # 未知GPU且有报告VRAM时应该使用报告值
        corrected = _correct_vram("Unknown GPU", 8.0)
        assert corrected == 8.0


class TestSystemHealthMonitor:
    """测试系统健康监测器"""

    @pytest.fixture
    def monitor(self):
        """创建监测器实例"""
        return SystemHealthMonitor()

    def test_monitor_initialization(self, monitor):
        """测试监测器初始化"""
        assert monitor is not None
        assert monitor._snapshot is not None
        assert monitor.hardware is not None
        assert monitor.thresholds is not None
        assert "memory_warn" in monitor.thresholds
        assert "memory_critical" in monitor.thresholds

    def test_compute_thresholds_32gb_ram(self, monitor):
        """测试32GB RAM的阈值计算"""
        monitor.hardware.total_ram_gb = 32.0
        thresholds = monitor._compute_thresholds()
        assert thresholds["memory_warn"] == 0.80
        assert thresholds["memory_critical"] == 0.90
        assert thresholds["available_memory_min_gb"] == 3.0

    def test_compute_thresholds_16gb_ram(self, monitor):
        """测试16GB RAM的阈值计算"""
        monitor.hardware.total_ram_gb = 16.0
        thresholds = monitor._compute_thresholds()
        assert thresholds["memory_warn"] == 0.75
        assert thresholds["memory_critical"] == 0.88
        assert thresholds["available_memory_min_gb"] == 2.0

    def test_compute_thresholds_8gb_ram(self, monitor):
        """测试8GB RAM的阈值计算"""
        monitor.hardware.total_ram_gb = 8.0
        thresholds = monitor._compute_thresholds()
        assert thresholds["memory_warn"] == 0.70
        assert thresholds["memory_critical"] == 0.85
        assert thresholds["available_memory_min_gb"] == 1.5

    def test_compute_thresholds_4gb_ram(self, monitor):
        """测试4GB RAM的阈值计算"""
        monitor.hardware.total_ram_gb = 4.0
        thresholds = monitor._compute_thresholds()
        assert thresholds["memory_warn"] == 0.65
        assert thresholds["memory_critical"] == 0.80
        assert thresholds["available_memory_min_gb"] == 1.0

    def test_compute_thresholds_small_vram(self, monitor):
        """测试小VRAM的阈值计算"""
        monitor.hardware.gpu_vram_gb = 4.0
        thresholds = monitor._compute_thresholds()
        assert thresholds["gpu_memory_warn"] == 0.70
        assert thresholds["gpu_memory_critical"] == 0.85

    def test_compute_thresholds_medium_vram(self, monitor):
        """测试中等VRAM的阈值计算"""
        monitor.hardware.gpu_vram_gb = 6.0
        thresholds = monitor._compute_thresholds()
        assert thresholds["gpu_memory_warn"] == 0.75
        assert thresholds["gpu_memory_critical"] == 0.88

    def test_compute_thresholds_large_vram(self, monitor):
        """测试大VRAM的阈值计算"""
        monitor.hardware.gpu_vram_gb = 12.0
        thresholds = monitor._compute_thresholds()
        assert thresholds["gpu_memory_warn"] == 0.80
        assert thresholds["gpu_memory_critical"] == 0.90

    def test_check_with_cache(self, monitor):
        """测试带缓存的检查"""
        # 第一次检查
        snapshot1 = monitor.check()
        # 第二次检查应该返回缓存的结果
        snapshot2 = monitor.check()
        assert snapshot1 is snapshot2

    def test_compute_mode_normal(self, monitor):
        """测试正常模式计算"""
        monitor._snapshot.memory_usage = 0.5
        monitor._snapshot.memory_available_gb = 8.0
        monitor._snapshot.thread_count = 30
        monitor._snapshot.cpu_percent = 0.5
        monitor._snapshot.gpu_memory = 0.5
        mode = monitor._compute_mode()
        assert mode == OperatingMode.NORMAL

    def test_compute_mode_conservative_memory(self, monitor):
        """测试保守模式计算（内存警告）"""
        monitor._snapshot.memory_usage = 0.78
        monitor._snapshot.memory_available_gb = 8.0
        monitor._snapshot.thread_count = 30
        monitor._snapshot.cpu_percent = 0.5
        monitor._snapshot.gpu_memory = 0.5
        mode = monitor._compute_mode()
        assert mode == OperatingMode.CONSERVATIVE

    def test_compute_mode_emergency_memory(self, monitor):
        """测试紧急模式计算（内存危急）"""
        monitor._snapshot.memory_usage = 0.92
        monitor._snapshot.memory_available_gb = 8.0
        monitor._snapshot.thread_count = 30
        monitor._snapshot.cpu_percent = 0.5
        monitor._snapshot.gpu_memory = 0.5
        mode = monitor._compute_mode()
        assert mode == OperatingMode.EMERGENCY

    def test_compute_mode_emergency_low_memory(self, monitor):
        """测试紧急模式计算（可用内存不足）"""
        monitor._snapshot.memory_usage = 0.7
        monitor._snapshot.memory_available_gb = 0.8
        monitor._snapshot.thread_count = 30
        monitor._snapshot.cpu_percent = 0.5
        monitor._snapshot.gpu_memory = 0.5
        mode = monitor._compute_mode()
        assert mode == OperatingMode.EMERGENCY

    def test_compute_mode_conservative_threads(self, monitor):
        """测试保守模式计算（线程数警告）"""
        monitor._snapshot.memory_usage = 0.5
        monitor._snapshot.memory_available_gb = 8.0
        monitor._snapshot.thread_count = 65
        monitor._snapshot.cpu_percent = 0.5
        monitor._snapshot.gpu_memory = 0.5
        mode = monitor._compute_mode()
        assert mode == OperatingMode.CONSERVATIVE

    def test_compute_mode_emergency_threads(self, monitor):
        """测试紧急模式计算（线程数危急）"""
        monitor._snapshot.memory_usage = 0.5
        monitor._snapshot.memory_available_gb = 8.0
        monitor._snapshot.thread_count = 85
        monitor._snapshot.cpu_percent = 0.5
        monitor._snapshot.gpu_memory = 0.5
        mode = monitor._compute_mode()
        assert mode == OperatingMode.EMERGENCY

    def test_compute_mode_conservative_cpu(self, monitor):
        """测试保守模式计算（CPU警告）"""
        monitor._snapshot.memory_usage = 0.5
        monitor._snapshot.memory_available_gb = 8.0
        monitor._snapshot.thread_count = 30
        monitor._snapshot.cpu_percent = 0.88
        monitor._snapshot.gpu_memory = 0.5
        mode = monitor._compute_mode()
        assert mode == OperatingMode.CONSERVATIVE

    def test_compute_mode_emergency_cpu(self, monitor):
        """测试紧急模式计算（CPU危急）"""
        monitor._snapshot.memory_usage = 0.5
        monitor._snapshot.memory_available_gb = 8.0
        monitor._snapshot.thread_count = 30
        monitor._snapshot.cpu_percent = 0.98
        monitor._snapshot.gpu_memory = 0.5
        mode = monitor._compute_mode()
        assert mode == OperatingMode.EMERGENCY

    def test_is_memory_rising_fast(self, monitor):
        """测试内存快速上升检测"""
        monitor._memory_trend = [0.5, 0.55, 0.6, 0.65, 0.75]
        assert monitor._is_memory_rising_fast() == True

    def test_is_memory_not_rising_fast(self, monitor):
        """测试内存非快速上升检测"""
        monitor._memory_trend = [0.5, 0.52, 0.51, 0.53, 0.52]
        assert monitor._is_memory_rising_fast() == False

    def test_is_memory_rising_fast_insufficient_data(self, monitor):
        """测试内存快速上升检测（数据不足）"""
        monitor._memory_trend = [0.5, 0.52, 0.51]
        assert monitor._is_memory_rising_fast() == False

    def test_ollama_activity_tracking(self, monitor):
        """测试Ollama活动跟踪"""
        monitor.register_ollama_request()
        monitor.register_ollama_request()

        with monitor._ollama_lock:
            assert monitor._ollama_active == 2

        monitor.unregister_ollama_request()

        with monitor._ollama_lock:
            assert monitor._ollama_active == 1

        monitor.unregister_ollama_request()

        with monitor._ollama_lock:
            assert monitor._ollama_active == 0

    def test_active_queries_tracking(self, monitor):
        """测试活动查询跟踪"""
        monitor.register_query()
        monitor.register_query()

        with monitor._query_lock:
            assert monitor._active_queries == 2

        monitor.unregister_query()

        with monitor._query_lock:
            assert monitor._active_queries == 1

        monitor.unregister_query()

        with monitor._query_lock:
            assert monitor._active_queries == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])