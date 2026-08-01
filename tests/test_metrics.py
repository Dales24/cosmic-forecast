"""Tests for app/metrics.py — the in-memory API health collector."""

from app.metrics import Metrics, SceneCapReport


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


# ── SceneCapReport ────────────────────────────────────────────────────────────


def _row(kind, shown, cap, hidden, exact=True):
    return {
        "kind": kind,
        "shown": shown,
        "cap": cap,
        "hidden": hidden,
        "hidden_exact": exact,
    }


def test_scene_cap_report_is_empty_before_any_scene():
    snap = SceneCapReport().snapshot()
    assert snap["at"] is None
    assert snap["kinds"] == []
    assert snap["total_hidden"] == 0


def test_scene_cap_report_totals_and_ordering():
    report = SceneCapReport()
    report.record([_row("iss", 3, 3, 5), _row("satellite", 40, 40, 11000)])
    snap = report.snapshot()
    assert snap["total_shown"] == 43
    assert snap["total_hidden"] == 11005
    assert snap["kinds"][0]["kind"] == "satellite"  # biggest hidden count first
    assert snap["at"] is not None


def test_scene_cap_report_flags_inexact_hidden_counts():
    report = SceneCapReport()
    report.record([_row("iss", 3, 3, 5), _row("galaxy", 6, 6, 1, exact=False)])
    assert report.snapshot()["total_hidden_exact"] is False


def test_scene_cap_report_keeps_only_the_latest_scene():
    report = SceneCapReport()
    report.record([_row("iss", 3, 3, 5)])
    report.record([_row("galaxy", 6, 6, 2)])
    snap = report.snapshot()
    assert [row["kind"] for row in snap["kinds"]] == ["galaxy"]


def test_scene_cap_report_snapshot_does_not_expose_internals():
    report = SceneCapReport()
    report.record([_row("iss", 3, 3, 5)])
    report.snapshot()["kinds"][0]["hidden"] = 999
    assert report.snapshot()["kinds"][0]["hidden"] == 5


def test_scene_cap_report_reset_clears_rows():
    report = SceneCapReport()
    report.record([_row("iss", 3, 3, 5)])
    report.reset()
    assert report.snapshot()["kinds"] == []


# ── SourceFailureLog ──────────────────────────────────────────────────────────


def test_source_failures_start_empty():
    from app.metrics import SourceFailureLog

    assert SourceFailureLog().snapshot() == {"total": 0, "sources": []}


def test_source_failure_records_source_kind_and_error():
    from app.metrics import SourceFailureLog

    log = SourceFailureLog()
    log.record("simbad", "galaxy", "timeout")
    row = log.snapshot()["sources"][0]
    assert row["source"] == "simbad"
    assert row["kind"] == "galaxy"
    assert row["error"] == "timeout"
    assert row["count"] == 1


def test_repeated_failures_count_up_rather_than_pile_up():
    """A source that is down stays one row with a rising count."""
    from app.metrics import SourceFailureLog

    log = SourceFailureLog()
    for _ in range(3):
        log.record("celestrak", "satellite", "403")
    snapshot = log.snapshot()
    assert len(snapshot["sources"]) == 1
    assert snapshot["sources"][0]["count"] == 3
    assert snapshot["total"] == 3


def test_different_kinds_are_tracked_separately():
    from app.metrics import SourceFailureLog

    log = SourceFailureLog()
    log.record("simbad", "galaxy", "timeout")
    log.record("simbad", "pulsar", "timeout")
    assert len(log.snapshot()["sources"]) == 2
    assert log.snapshot()["total"] == 2


def test_source_failure_reset_clears_everything():
    from app.metrics import SourceFailureLog

    log = SourceFailureLog()
    log.record("jpl", "near_earth_object", "boom")
    log.reset()
    assert log.snapshot()["total"] == 0
