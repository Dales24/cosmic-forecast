"""Cache bounds, retry, integrity and concurrent-request regressions."""

import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import Mock, patch

import pytest

from app import api, data_parser as parser

TLE = (
    "ISS (ZARYA)\n"
    "1 25544U 98067A   24001.50000000  .00001234  00000-0  27890-4 0  9990\n"
    "2 25544  51.6400 100.0000 0001500  50.0000 310.0000 15.50000000000014\n"
)


@pytest.fixture(autouse=True)
def clean(tmp_path, monkeypatch):
    api._clear_catalog_cache()
    api._clear_scene_cache()
    monkeypatch.setattr(parser, "_TLE_CACHE_DIR", tmp_path)
    yield
    api._clear_catalog_cache()
    api._clear_scene_cache()


def response(text=TLE):
    return Mock(text=text, raise_for_status=Mock())


def test_catalog_bound_and_expiry():
    with patch.object(api, "_CATALOG_CACHE_MAX_ENTRIES", 3):
        for key in range(8):
            api._cached_catalog((key,), 60, lambda: api.CappedObjects([], 0, True))
    assert len(api._catalog_cache) == len(api._catalog_expiry) == 3
    with patch.object(api.time, "time", return_value=time.time() + 61):
        api._cached_catalog((99,), 60, lambda: api.CappedObjects([], 0, True))
    assert list(api._catalog_cache) == [(99,)]


def test_catalog_failure_retries_after_short_ttl():
    fetch = Mock(
        side_effect=[
            api.CappedObjects([], 0, True, "jpl"),
            api.CappedObjects([], 0, True),
        ]
    )
    api._cached_catalog(("jpl",), 3600, fetch)
    api._cached_catalog(("jpl",), 3600, fetch)
    assert fetch.call_count == 1
    with patch.object(api.time, "time", return_value=time.time() + 31):
        assert api._cached_catalog(("jpl",), 3600, fetch).unavailable_source is None
    assert fetch.call_count == 2


def test_concurrent_catalog_misses_share_fetch_and_other_keys_progress():
    entered, release = Event(), Event()

    def fetch():
        entered.set()
        assert release.wait(3)
        return api.CappedObjects([], 0, True)

    fetch = Mock(side_effect=fetch)
    with ThreadPoolExecutor(max_workers=9) as pool:
        jobs = [
            pool.submit(api._cached_catalog, ("slow",), 60, fetch) for _ in range(8)
        ]
        assert entered.wait(3)
        other = pool.submit(
            api._cached_catalog, ("other",), 60, lambda: api.CappedObjects([], 0, True)
        )
        try:
            assert other.result(timeout=2).objects == []
        finally:
            release.set()
        assert all(job.result(timeout=3).objects == [] for job in jobs)
    assert fetch.call_count == 1
    assert api._catalog_keys.entries == {}


@pytest.mark.parametrize(
    "bad", ["", "<html>error</html>", TLE.replace("15.50000000", "bad_number!")]
)
def test_invalid_tle_never_replaces_good_cache(tmp_path, bad):
    path = tmp_path / "iss.tle"
    path.write_text(TLE)
    old = time.time() - parser._TLE_CACHE_TTL_SECONDS - 1
    os.utime(path, (old, old))
    with patch.object(parser.requests, "get", return_value=response(bad)) as get:
        text = parser.fetch_celestrak_text("iss")
        assert text.freshness["stale"]
        assert parser.fetch_celestrak_text("iss") == TLE
    assert get.call_count == 1
    assert path.read_text() == TLE


def test_tle_stale_limit_and_retry_recovery(tmp_path):
    path = tmp_path / "iss.tle"
    path.write_text(TLE)
    old = time.time() - parser._TLE_MAX_STALE_SECONDS - 1
    os.utime(path, (old, old))
    with patch.object(parser.requests, "get", side_effect=OSError("offline")) as get:
        for _ in range(2):
            with pytest.raises(RuntimeError, match="no usable cache"):
                parser.fetch_celestrak_text("iss")
        assert get.call_count == 1
    with (
        patch.object(parser.time, "monotonic", return_value=time.monotonic() + 31),
        patch.object(parser.requests, "get", return_value=response()),
    ):
        assert not parser.fetch_celestrak_text("iss").freshness["stale"]


def test_concurrent_tle_download_once_and_hot_hits_skip_validation(tmp_path):
    with patch.object(parser.requests, "get", return_value=response()) as get:
        with ThreadPoolExecutor(max_workers=8) as pool:
            texts = list(pool.map(parser.fetch_celestrak_text, ["iss"] * 20))
        assert get.call_count == 1
        with patch.object(
            parser, "_validate_tle", side_effect=AssertionError("hot path")
        ):
            assert parser.fetch_celestrak_text("iss") == TLE
    assert all(text == TLE for text in texts)
    assert not list(tmp_path.glob("*.tmp"))


def test_corrupt_fresh_disk_cache_refetched(tmp_path):
    (tmp_path / "iss.tle").write_text("not TLE")
    with patch.object(parser.requests, "get", return_value=response()) as get:
        assert parser.fetch_celestrak_text("iss") == TLE
    assert get.call_count == 1


def test_scene_respects_stale_deadline_and_failure_retry():
    api._cache_scene((1,), {"valid_until": time.time() - 1})
    assert api._cached_scene((1,)) is None
    api._cache_scene((2,), {"source_warnings": [{"source": "jpl"}]})
    with patch.object(api.time, "time", return_value=time.time() + 31):
        assert api._cached_scene((2,)) is None


def test_concurrent_scene_misses_build_once():
    with patch.object(api, "_capped_scene_objects", return_value=([], [])) as fetch:
        with ThreadPoolExecutor(max_workers=8) as pool:
            scenes = list(
                pool.map(lambda _: api.get_scene("2025-01-01T00:00:00Z"), range(20))
            )
    assert fetch.call_count == 1
    assert all(scene == scenes[0] for scene in scenes)
    assert api._scene_keys.entries == {}


def test_scene_carries_tle_freshness_and_deadline():
    downloaded = time.time() - parser._TLE_CACHE_TTL_SECONDS - 1
    text = parser.TLEText(TLE, downloaded, "2024-01-01T12:00:00Z")
    with (
        patch.object(parser, "fetch_celestrak_text", return_value=text),
        patch.object(parser, "fetch_jpl", return_value=[]),
        patch.object(parser, "fetch_simbad", return_value=[]),
    ):
        result = api.get_scene("2025-01-01T00:00:00Z")
    assert len(result["source_freshness"]) == 4
    assert all(row["stale"] for row in result["source_freshness"])
    assert result["valid_until"] == downloaded + parser._TLE_MAX_STALE_SECONDS
    assert result["source_warnings"] == []


def test_expired_tle_becomes_scene_source_warning(tmp_path):
    path = tmp_path / "iss.tle"
    path.write_text(TLE)
    old = time.time() - parser._TLE_MAX_STALE_SECONDS - 1
    os.utime(path, (old, old))
    with patch.object(parser.requests, "get", side_effect=OSError("offline")):
        result = api._celestrak_scene_objects("iss", api._parse_scene_datetime(None), 3)
    assert result.unavailable_source == "celestrak"
    assert result.objects == []


def test_failed_atomic_replace_preserves_disk_and_releases_lock(tmp_path):
    path = tmp_path / "iss.tle"
    path.write_text(TLE)
    old = time.time() - parser._TLE_CACHE_TTL_SECONDS - 1
    os.utime(path, (old, old))
    with (
        patch.object(parser.requests, "get", return_value=response()),
        patch.object(parser.os, "replace", side_effect=OSError("disk failure")),
        pytest.raises(OSError, match="disk failure"),
    ):
        parser.fetch_celestrak_text("iss")
    assert path.read_text() == TLE
    assert not list(tmp_path.glob("*.tmp"))
    assert parser._tle_locks.entries == {}
