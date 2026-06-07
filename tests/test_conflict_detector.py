"""
核心模块单元测试 - 冲突检测器
"""
import pytest
import sqlite3
import tempfile
import os
from meta.conflict_detector import ConflictDetector


class TestConflictDetector:
    """冲突检测器测试类"""
    
    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        with sqlite3.connect(path) as conn:
            conn.execute('''
                CREATE TABLE learning_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    condition TEXT NOT NULL,
                    action TEXT NOT NULL,
                    priority INTEGER DEFAULT 3,
                    confidence REAL DEFAULT 0.5,
                    status TEXT DEFAULT 'active',
                    source TEXT,
                    created_at TEXT,
                    metadata TEXT
                )
            ''')
            
            conn.execute('''
                INSERT INTO learning_rules 
                (condition, action, priority, confidence, status, source)
                VALUES 
                ('intent_type == "code"', 'reroute:qwen2.5-coder:1.5b', 1, 0.8, 'active', 'test'),
                ('intent_type == "code"', 'reroute:mindchat', 2, 0.7, 'active', 'test'),
                ('intent_type == "question"', 'prefer_model:remote_gpt4', 1, 0.9, 'active', 'test')
            ''')
            conn.commit()
        
        yield path
        
        os.unlink(path)
    
    def test_parse_action_reroute(self):
        """测试reroute动作解析"""
        detector = ConflictDetector()
        action = detector._parse_action("reroute:qwen2.5-coder:1.5b")
        
        assert action["type"] == "reroute"
        assert action["target"] == "qwen2.5-coder:1.5b"
    
    def test_parse_action_prefer(self):
        """测试prefer动作解析"""
        detector = ConflictDetector()
        action = detector._parse_action("prefer_model:remote_gpt4")
        
        assert action["type"] == "prefer"
        assert action["target"] == "remote_gpt4"
    
    def test_parse_action_merge(self):
        """测试merge动作解析"""
        detector = ConflictDetector()
        action = detector._parse_action("merge:reroute:model1|prefer_model:model2")
        
        assert action["type"] == "merge"
        assert len(action["actions"]) == 2
        assert action["actions"][0]["type"] == "reroute"
        assert action["actions"][1]["type"] == "prefer"
    
    def test_detect_conflicts(self, temp_db):
        """测试冲突检测"""
        detector = ConflictDetector()
        detector.db_path = temp_db
        
        conflicts = detector.detect_conflicts()
        
        assert len(conflicts) == 1
        assert conflicts[0]["conflict_type"] == "model_conflict"
        assert "rule1_id" in conflicts[0]
        assert "rule2_id" in conflicts[0]
    
    def test_resolve_conflict_auto(self, temp_db):
        """测试自动解决冲突"""
        detector = ConflictDetector()
        detector.db_path = temp_db
        
        conflicts = detector.detect_conflicts()
        assert len(conflicts) > 0
        
        result = detector.resolve_conflict(conflicts[0], resolution="auto")
        
        assert result["success"] is True
        assert "deactivated" in result
        assert "kept" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])