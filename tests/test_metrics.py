"""Tests for app/metrics.py — the in-memory API health collector."""

from app.metrics import Metrics


def test_records_totals_and_status_classes():
    m = Metrics()
    m.record("GET", "/api/scene", 200, 12.0)
    m.record("GET", "/api/scene", 200, 8.0)
    m.record("GET", "/api/objects/x", 404, 3.0)
    snap = m.snapshot()
    assert snap["total_requests"] == 3
    assert snap["status_classes"]["2xx"] == 2
    assert snap["status_classes"]["4xx"] == 1
    assert snap["error_count"] == 0


def test_captures_server_errors_only():
    m = Metrics()
    m.record("GET", "/boom", 500, 5.0)
    m.record("GET", "/ok", 200, 5.0)
    snap = m.snapshot()
    assert snap["error_count"] == 1
    assert snap["error_rate"] == 0.5
    assert len(snap["recent_errors"]) == 1
    assert snap["recent_errors"][0]["path"] == "/boom"


def test_recent_errors_are_capped_and_newest_first():
    m = Metrics()
    for i in range(40):
        m.record("GET", f"/e{i}", 500, 1.0)
    snap = m.snapshot()
    assert len(snap["recent_errors"]) == 25  # ring buffer cap
    assert snap["recent_errors"][0]["path"] == "/e39"  # newest first


def test_top_paths_ranks_by_volume():
    m = Metrics()
    for _ in range(5):
        m.record("GET", "/hot", 200, 1.0)
    m.record("GET", "/cold", 200, 1.0)
    top = m.snapshot()["top_paths"]
    assert top[0] == {"path": "/hot", "count": 5}


def test_reset_clears_counters():
    m = Metrics()
    m.record("GET", "/x", 200, 1.0)
    m.reset()
    assert m.snapshot()["total_requests"] == 0
