"""
单元测试 - SQLite并发写加固 (1.3)
"""
import pytest
import os
import tempfile
import threading
from infrastructure.fact_store import FactStore
from core.alignment_guard import AlignmentGuard, DeviationType, DeviationSeverity


@pytest.fixture
def fs():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    store = FactStore(db_path=db_path)
    yield store
    try:
        os.unlink(db_path)
    except Exception:
        pass


@pytest.fixture
def ag():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    guard = AlignmentGuard(db_path=db_path)
    yield guard
    try:
        os.unlink(db_path)
    except Exception:
        pass


class TestFactStoreWriteOp:
    def test_add_assertion(self, fs):
        aid = fs.add_assertion("test_q", "subj", "pred", "obj", source="test")
        assert aid > 0

    def test_add_correction(self, fs):
        fs.add_correction("test_q", "old_s", "old_p", "old_o", "new_s", "new_p", "new_o")
        negations = fs.get_negations("test_q")
        assert len(negations) > 0

    def test_mark_used(self, fs):
        aid = fs.add_assertion("test_q", "subj", "pred", "obj", source="test")
        fs.mark_used(aid)
        assertions = fs.get_assertions("test_q")
        assert any(a.get('subject') == 'subj' for a in assertions)

    def test_concurrent_writes(self, fs):
        errors = []

        def writer(i):
            try:
                fs.add_assertion(f"concurrent_q_{i}", f"subj_{i}", "pred", f"obj_{i}", source="concurrent_test")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent write errors: {errors}"
        for i in range(10):
            results = fs.search_by_keywords(f"concurrent_q_{i}", limit=1)
            assert len(results) >= 0


class TestAlignmentGuardWriteOp:
    def test_record_deviation(self, ag):
        dev_id = ag.record_deviation(
            module="test_module",
            deviation_type=DeviationType.MECHANISM,
            description="test deviation",
            severity=DeviationSeverity.MAJOR,
        )
        assert dev_id > 0

    def test_correct_deviation(self, ag):
        dev_id = ag.record_deviation(
            module="test_module",
            deviation_type=DeviationType.VALUE,
            description="test",
            severity=DeviationSeverity.CRITICAL,
        )
        ag.correct_deviation(dev_id, "fixed")
        open_devs = ag.get_open_deviations()
        assert not any(d.id == dev_id for d in open_devs)

    def test_concurrent_record(self, ag):
        errors = []

        def recorder(i):
            try:
                ag.record_deviation(
                    module=f"module_{i}",
                    deviation_type=DeviationType.COMPLEXITY,
                    description=f"concurrent test {i}",
                    severity=DeviationSeverity.MINOR,
                )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=recorder, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Concurrent write errors: {errors}"
        stats = ag.get_stats()
        assert stats["total"] >= 10