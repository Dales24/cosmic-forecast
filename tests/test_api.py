"""Tests for all FastAPI endpoints in app/api.py."""

import io
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import api
from app.api import (
    app,
    _propagate_tles,
    _jpl_scene_objects,
    _planet_scene_objects,
    _simbad_scene_objects,
    _stable_angle,
)

client = TestClient(app)


@contextmanager
def _offline_catalogs(requests_patch):
    """Run a scene request with JPL/SIMBAD stubbed offline.

    Scene assembly also calls data_parser.fetch_jpl/fetch_simbad; stub them so
    tests never touch the real APIs. `requests_patch` controls the CelesTrak leg.
    """
    with (
        requests_patch,
        patch("app.data_parser.fetch_jpl", side_effect=Exception("offline")),
        patch("app.data_parser.fetch_simbad", side_effect=Exception("offline")),
    ):
        yield


# ── GET / ─────────────────────────────────────────────────────────────────────


def test_index_returns_html():
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_help_page_served():
    r = client.get("/help")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Help" in r.text


def test_profile_page_served():
    r = client.get("/profile")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Profile" in r.text


def test_admin_page_served():
    r = client.get("/admin")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Admin" in r.text


# ── GET /api/objects/{object_slug} ────────────────────────────────────────────


def test_get_objects_passes_query_params_to_data_parser():
    rows = [{"name": "Ceres", "date": "2025-06-01"}]
    with patch("app.data_parser.get_data", return_value=rows) as mock_get:
        r = client.get("/api/objects/asteroid?date=2025-06-01&limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "asteroid"
    assert body["results"] == rows
    mock_get.assert_called_once_with("asteroid", date="2025-06-01", limit=5)


def test_get_objects_defaults_when_no_query():
    with patch("app.data_parser.get_data", return_value=[]) as mock_get:
        r = client.get("/api/objects/comet")
    assert r.status_code == 200
    assert r.json() == {"slug": "comet", "results": []}
    mock_get.assert_called_once_with("comet", date=None, limit=20)


def test_get_objects_unknown_slug_returns_404():
    with patch(
        "app.data_parser.get_data", side_effect=ValueError("Unknown object slug")
    ):
        r = client.get("/api/objects/not_a_real_slug")
    assert r.status_code == 404


def test_get_objects_source_failure_degrades_gracefully():
    # A single external source failing must not 500 the endpoint.
    with patch(
        "app.data_parser.get_data", side_effect=RuntimeError("SIMBAD unreachable")
    ):
        r = client.get("/api/objects/galaxy")
    assert r.status_code == 200
    body = r.json()
    assert body["results"] == []
    assert body["error"] == "source_unavailable"


# ── GET /api/classify/{obj_id} ────────────────────────────────────────────────

_MOCK_CLASSIFICATION = {
    "class": "Satellite",
    "slug": "satellite",
    "group": "artificial",
    "confidence": 0.85,
    "probabilities": {"satellite": 0.85},
}


def _patched_classify():
    return (
        patch("app.api._get_cnn", return_value=MagicMock()),
        patch("app.object_classifier.predict_patch", return_value=_MOCK_CLASSIFICATION),
    )


def test_classify_returns_valid_structure():
    with patch("app.api._get_cnn", return_value=MagicMock()):
        with patch(
            "app.object_classifier.predict_patch", return_value=_MOCK_CLASSIFICATION
        ):
            r = client.get("/api/classify/0")
    assert r.status_code == 200
    data = r.json()
    assert "class" in data
    assert "confidence" in data
    assert "group" in data
    assert data["input_source"] == "synthetic_patch"
    assert data["is_demo"] is True
    assert "not an observation" in data["notice"]


def test_classify_uses_a_kind_specific_patch():
    """With a kind, the classified patch is the one characteristic of that kind."""
    from app.object_classifier import synthetic_patch

    captured = {}

    def capture(model, patch):
        captured["patch"] = patch
        return _MOCK_CLASSIFICATION

    with patch("app.api._get_cnn", return_value=MagicMock()):
        with patch("app.object_classifier.predict_patch", side_effect=capture):
            r = client.get("/api/classify/0?kind=galaxy")
    assert r.status_code == 200
    assert np.array_equal(captured["patch"], synthetic_patch("galaxy", seed=0))


def test_classify_deterministic_patch_for_same_id():
    """Same obj_id always generates the same random patch."""
    seen = []

    def capture(model, patch):
        seen.append(patch.copy())
        return _MOCK_CLASSIFICATION

    with patch("app.api._get_cnn", return_value=MagicMock()):
        with patch("app.object_classifier.predict_patch", side_effect=capture):
            client.get("/api/classify/7")
            client.get("/api/classify/7")

    assert np.array_equal(seen[0], seen[1])


def test_classify_different_ids_produce_different_patches():
    seen = {}

    def capture(model, patch):
        seen[id(patch)] = patch.copy()
        return _MOCK_CLASSIFICATION

    with patch("app.api._get_cnn", return_value=MagicMock()):
        with patch("app.object_classifier.predict_patch", side_effect=capture):
            client.get("/api/classify/1")
            client.get("/api/classify/2")

    patches = list(seen.values())
    assert len(patches) == 2
    assert not np.array_equal(patches[0], patches[1])


# ── POST /api/forecast ────────────────────────────────────────────────────────


def test_forecast_returns_waypoints():
    payload = {
        "objects": [
            {
                "id": 0,
                "positions": [
                    [0.10, 0.20, 1000.0],
                    [0.11, 0.21, 1001.0],
                    [0.12, 0.22, 1002.0],
                ],
            }
        ]
    }
    r = client.post("/api/forecast", json=payload)
    assert r.status_code == 200
    preds = r.json()["predictions"]
    assert len(preds) == 1
    assert preds[0]["id"] == 0
    assert len(preds[0]["waypoints"]) > 0


def test_forecast_skips_single_point_objects():
    payload = {"objects": [{"id": 0, "positions": [[0.1, 0.2, 1000.0]]}]}
    r = client.post("/api/forecast", json=payload)
    assert r.status_code == 200
    assert r.json()["predictions"] == []


def test_forecast_handles_multiple_objects():
    payload = {
        "objects": [
            {"id": 0, "positions": [[0.1, 0.2, 1000.0], [0.11, 0.21, 1001.0]]},
            {"id": 1, "positions": [[0.3, 0.4, 1000.0], [0.31, 0.41, 1001.0]]},
        ]
    }
    r = client.post("/api/forecast", json=payload)
    assert r.status_code == 200
    preds = r.json()["predictions"]
    assert len(preds) == 2
    assert {p["id"] for p in preds} == {0, 1}


def test_forecast_empty_objects_list():
    r = client.post("/api/forecast", json={"objects": []})
    assert r.status_code == 200
    assert r.json()["predictions"] == []


# ── GET /api/scene ────────────────────────────────────────────────────────────


def test_scene_does_not_fabricate_unidentified_objects():
    """The live scene contains only sourced or computed objects."""
    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x"))
    ):
        r = client.get("/api/scene")
    assert r.status_code == 200
    kinds = [o["kind"] for o in r.json()["objects"]]
    assert "ufo" not in kinds


def test_scene_accepts_datetime_str():
    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x"))
    ):
        r = client.get("/api/scene?datetime_str=2025-06-01T12:00:00Z")
    assert r.status_code == 200
    assert "2025-06-01" in r.json()["datetime"]


def test_scene_rejects_invalid_datetime():
    """Better a clear error than silently serving *now* for the picked date."""
    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x"))
    ):
        r = client.get("/api/scene?datetime_str=not-a-date")
    assert r.status_code == 422
    assert "ISO 8601" in r.json()["detail"]


def test_scene_empty_datetime_means_now():
    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x"))
    ):
        r = client.get("/api/scene?datetime_str=")
    assert r.status_code == 200


# ── Position search ───────────────────────────────────────────────────────────


def test_angular_separation_basics():
    assert api._angular_separation_deg(0, 0, 0, 0) == pytest.approx(0.0)
    assert api._angular_separation_deg(0, 0, 90, 0) == pytest.approx(90.0)
    assert api._angular_separation_deg(0, 90, 0, -90) == pytest.approx(180.0)
    # Wrapping across RA 0/360 is a short hop, not a long way round.
    assert api._angular_separation_deg(359, 0, 1, 0) == pytest.approx(2.0)


def test_objects_near_keeps_only_what_is_inside_the_cone():
    objects = [
        {"kind": "star", "ra_deg": 10.0, "dec_deg": 0.0},  # 10° away
        {"kind": "star", "ra_deg": 40.0, "dec_deg": 0.0},  # 40° away
    ]
    near = api._objects_near(objects, 0.0, 0.0, 30.0)
    assert [o["ra_deg"] for o in near] == [10.0]


def test_objects_near_drops_objects_with_no_sky_position():
    """JPL close approaches and the UFO carry no direction, so a position
    search cannot honestly claim they are in the requested patch."""
    objects = [
        {"kind": "near_earth_object", "ra_deg": None, "dec_deg": None},
        {"kind": "ufo"},
    ]
    assert api._objects_near(objects, 0.0, 0.0, 180.0) == []


def test_objects_near_always_keeps_earth():
    """Earth is the observer, not a point of sky that can be out of frame."""
    earth = {"kind": "earth"}
    assert api._objects_near([earth], 123.0, -45.0, 1.0) == [earth]


def test_scene_position_search_narrows_the_result():
    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x"))
    ):
        full = client.get("/api/scene?datetime_str=2025-06-01T12:00:00Z").json()
        narrow = client.get(
            "/api/scene?datetime_str=2025-06-01T12:00:00Z&ra=180&dec=0&radius_deg=10"
        ).json()

    assert narrow["search"]["matched"] <= narrow["search"]["searched"]
    assert len(narrow["objects"]) < len(full["objects"])
    for obj in narrow["objects"]:
        if obj["kind"] == "earth":
            continue
        assert (
            api._angular_separation_deg(obj["ra_deg"], obj["dec_deg"], 180.0, 0.0)
            <= 10.0
        )


def test_scene_accepts_a_degree_sign_on_coordinates():
    """The form's placeholder shows "83.82°", so that must parse."""
    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x"))
    ):
        r = client.get("/api/scene?ra=83.82%C2%B0&dec=-5.39%C2%B0")
    assert r.status_code == 200
    assert r.json()["search"]["ra_deg"] == pytest.approx(83.82)
    assert r.json()["search"]["dec_deg"] == pytest.approx(-5.39)


@pytest.mark.parametrize(
    "query",
    [
        "ra=10",  # dec missing
        "dec=10",  # ra missing
        "ra=abc&dec=0",  # not a number
        "ra=0&dec=200",  # dec out of range
        "ra=0&dec=0&radius_deg=0",  # empty cone
        "ra=0&dec=0&radius_deg=200",  # bigger than the sky
    ],
)
def test_scene_rejects_bad_position_searches(query):
    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x"))
    ):
        r = client.get("/api/scene?" + query)
    assert r.status_code == 422


def test_scene_without_coordinates_returns_no_search_block():
    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x"))
    ):
        r = client.get("/api/scene?datetime_str=2025-06-01T12:00:00Z")
    assert "search" not in r.json()


def test_scene_objects_carry_sky_coordinates():
    """Position search is only meaningful if the objects expose real RA/Dec."""
    tle_text = (
        "ISS (ZARYA)\n"
        "1 25544U 98067A   24001.50000000  .00001234  00000-0  27890-4 0  9990\n"
        "2 25544  51.6400 100.0000 0001500  50.0000 310.0000 15.50000000000014\n"
    )
    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", return_value=tle_text)
    ):
        objects = client.get("/api/scene?datetime_str=2024-01-01T12:00:00Z").json()[
            "objects"
        ]

    for kind in ("iss", "planet", "sun", "moon"):
        placed = [o for o in objects if o["kind"] == kind]
        assert placed, f"no {kind} in scene"
        for obj in placed:
            assert 0.0 <= obj["ra_deg"] < 360.0, kind
            assert -90.0 <= obj["dec_deg"] <= 90.0, kind


# ── Scene cache ───────────────────────────────────────────────────────────────


def test_scene_cache_evicts_expired_entries_and_stays_bounded():
    """One entry per distinct datetime, so an unbounded cache would only grow."""
    api._clear_scene_cache()
    for index in range(api._SCENE_CACHE_MAX_ENTRIES + 10):
        api._cache_scene((f"key-{index}", None), {"objects": []})
    assert len(api._scene_cache) <= api._SCENE_CACHE_MAX_ENTRIES

    api._clear_scene_cache()
    api._cache_scene(("stale", None), {"objects": []})
    with patch("app.api.time.time", return_value=time.time() + 999):
        assert api._cached_scene(("stale", None)) is None
    assert "stale" not in [key[0] for key in api._scene_cache]


def test_scene_cache_returns_the_same_payload_within_its_ttl():
    api._clear_scene_cache()
    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x"))
    ) as _:
        first = client.get("/api/scene?datetime_str=2025-06-01T12:00:00Z").json()
    # No catalog patch this time: a miss would try the network and differ.
    second = client.get("/api/scene?datetime_str=2025-06-01T12:00:00Z").json()
    assert first == second


def test_scene_naive_datetime_is_treated_as_utc():
    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x"))
    ):
        r = client.get("/api/scene?datetime_str=2025-06-01T12:00:00")
    assert r.status_code == 200
    assert r.json()["datetime"] == "2025-06-01T12:00:00+00:00"


def test_scene_includes_tle_objects_when_celestrak_responds():
    tle_text = (
        "ISS (ZARYA)\n"
        "1 25544U 98067A   24001.50000000  .00001234  00000-0  27890-4 0  9990\n"
        "2 25544  51.6400 100.0000 0001500  50.0000 310.0000 15.50000000000014\n"
    )
    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", return_value=tle_text)
    ):
        r = client.get("/api/scene?datetime_str=2024-01-01T12:00:00Z")

    assert r.status_code == 200
    iss_objects = [o for o in r.json()["objects"] if o["kind"] == "iss"]
    assert len(iss_objects) >= 1


def test_scene_passes_user_date_to_jpl():
    """The UI datetime must reach JPL CAD as the approach-window start date."""
    captured = {}

    def fake_jpl(date, limit):
        captured["date"] = date
        return []

    with (
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x")),
        patch("app.data_parser.fetch_jpl", side_effect=fake_jpl),
        patch("app.data_parser.fetch_simbad", return_value=[]),
    ):
        r = client.get("/api/scene?datetime_str=2025-06-01T12:00:00Z")

    assert r.status_code == 200
    assert captured["date"] == "2025-06-01"


def test_scene_includes_jpl_and_simbad_objects():
    jpl_records = [{"des": "2024 XY1", "dist": "0.05"}]
    simbad_records = [{"main_id": "M31", "ra": 10.68, "dec": 41.27}]

    with (
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x")),
        patch("app.data_parser.fetch_jpl", return_value=jpl_records),
        patch("app.data_parser.fetch_simbad", return_value=simbad_records),
    ):
        r = client.get("/api/scene")

    objects = r.json()["objects"]
    kinds = {o["kind"] for o in objects}
    assert "near_earth_object" in kinds
    assert "galaxy" in kinds and "nebula" in kinds
    # Every catalog object carries the full scene-object schema.
    for obj in objects:
        for field in ("id", "name", "kind", "x_norm", "y_norm", "source"):
            assert field in obj


def test_scene_includes_deep_space_pack():
    """Black holes, stars, quasars, pulsars, and SNRs reach the scene from SIMBAD."""
    record = [{"main_id": "Cyg X-1", "ra": 299.59, "dec": 35.2}]
    with (
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x")),
        patch("app.data_parser.fetch_jpl", return_value=[]),
        patch("app.data_parser.fetch_simbad", return_value=record),
    ):
        r = client.get("/api/scene")

    kinds = {o["kind"] for o in r.json()["objects"]}
    for kind in ("star", "black_hole", "quasar", "pulsar", "supernova_remnant"):
        assert kind in kinds, f"missing {kind}"


def test_scene_includes_all_orbital_categories():
    """ISS, satellites, debris, and rocket bodies all reach the scene from TLEs."""
    tle_text = (
        "ISS (ZARYA)\n"
        "1 25544U 98067A   24001.50000000  .00001234  00000-0  27890-4 0  9990\n"
        "2 25544  51.6400 100.0000 0001500  50.0000 310.0000 15.50000000000014\n"
    )
    with (
        patch("app.data_parser.fetch_celestrak_text", return_value=tle_text),
        patch("app.data_parser.fetch_jpl", return_value=[]),
        patch("app.data_parser.fetch_simbad", return_value=[]),
    ):
        r = client.get("/api/scene")

    kinds = {o["kind"] for o in r.json()["objects"]}
    for kind in ("iss", "satellite", "space_debris", "rocket_body"):
        assert kind in kinds, f"missing {kind}"


def test_scene_selects_one_debris_field_and_reports_it():
    fetched = []

    def fake_tle(slug):
        fetched.append(slug)
        return _ISS_TLE

    with (
        patch("app.data_parser.fetch_celestrak_text", side_effect=fake_tle),
        patch("app.data_parser.fetch_jpl", return_value=[]),
        patch("app.data_parser.fetch_simbad", return_value=[]),
    ):
        r = client.get("/api/scene?debris_field=iridium-33")

    assert r.status_code == 200
    assert "space_debris_iridium_33" in fetched
    assert "space_debris_cosmos_2251" not in fetched
    coverage = r.json()["debris_coverage"]
    assert coverage["label"] == "Iridium 33 debris"
    debris = [o for o in r.json()["objects"] if o["kind"] == "space_debris"]
    assert debris and debris[0]["debris_field"] == "iridium-33"


def test_scene_all_debris_fields_deduplicate_catalog_ids():
    with (
        patch("app.data_parser.fetch_celestrak_text", return_value=_ISS_TLE),
        patch("app.data_parser.fetch_jpl", return_value=[]),
        patch("app.data_parser.fetch_simbad", return_value=[]),
    ):
        r = client.get("/api/scene?debris_field=all")

    debris = [o for o in r.json()["objects"] if o["kind"] == "space_debris"]
    assert len(debris) == 1
    assert r.json()["debris_coverage"]["duplicates_removed"] == 2


def test_scene_reports_a_partially_unavailable_debris_union():
    def fake_tle(slug):
        if slug == "space_debris_iridium_33":
            raise OSError("offline")
        return _ISS_TLE

    with (
        patch("app.data_parser.fetch_celestrak_text", side_effect=fake_tle),
        patch("app.data_parser.fetch_jpl", return_value=[]),
        patch("app.data_parser.fetch_simbad", return_value=[]),
    ):
        r = client.get("/api/scene?debris_field=all")

    assert r.status_code == 200
    assert r.json()["debris_coverage"]["unavailable_groups"] == ["iridium-33"]
    warning = next(
        row for row in r.json()["source_warnings"] if row["kind"] == "space_debris"
    )
    assert "iridium-33" in warning["detail"]


def test_scene_rejects_unknown_debris_field():
    r = client.get("/api/scene?debris_field=not-a-field")
    assert r.status_code == 422


def test_scene_is_cached_within_ttl():
    """A repeat scene load is served from cache and doesn't refetch catalogs."""
    calls = {"jpl": 0}

    def fake_jpl(date, limit):
        calls["jpl"] += 1
        return []

    with (
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x")),
        patch("app.data_parser.fetch_jpl", side_effect=fake_jpl),
        patch("app.data_parser.fetch_simbad", return_value=[]),
    ):
        first = client.get("/api/scene")
        second = client.get("/api/scene")

    assert first.status_code == 200 and second.status_code == 200
    assert calls["jpl"] == 1  # second request hit the cache, not the network


def test_scene_returns_satellite_fallback_coverage():
    from app.data_parser import TLEText

    text = TLEText(
        _ISS_TLE,
        time.time(),
        "2024-01-01T12:00:00Z",
        {
            "selected_query": "starlink",
            "selected_label": "Starlink subset",
            "fallback": True,
            "failed_attempts": [{"query": "active", "error": "403"}],
        },
    )
    with (
        patch("app.data_parser.fetch_celestrak_text", return_value=text),
        patch("app.data_parser.fetch_jpl", return_value=[]),
        patch("app.data_parser.fetch_simbad", return_value=[]),
    ):
        r = client.get("/api/scene")

    coverage = r.json()["satellite_coverage"]
    assert coverage["selected_query"] == "starlink"
    assert coverage["fallback"] is True
    assert coverage["failed_attempts"][0]["query"] == "active"


def test_scene_returns_rocket_body_name_coverage():
    from app.data_parser import TLEText

    text = TLEText(
        _ISS_TLE,
        time.time(),
        "2024-01-01T12:00:00Z",
        {
            "selected_query": "R/B",
            "selected_label": "Names containing R/B",
            "fallback": False,
            "failed_attempts": [],
        },
    )
    with (
        patch("app.data_parser.fetch_celestrak_text", return_value=text),
        patch("app.data_parser.fetch_jpl", return_value=[]),
        patch("app.data_parser.fetch_simbad", return_value=[]),
    ):
        r = client.get("/api/scene")

    coverage = r.json()["rocket_body_coverage"]
    assert coverage["selected_query"] == "R/B"
    assert coverage["selected_label"] == "Names containing R/B"


# ── Scene object caps ─────────────────────────────────────────────────────────
# Caps live in app.config; every scene reports what they left out to the admin
# monitor (app.metrics.scene_cap_report).


def _cap_row(kind):
    from app.metrics import scene_cap_report

    rows = {row["kind"]: row for row in scene_cap_report.snapshot()["kinds"]}
    return rows[kind]


def test_scene_reports_exact_hidden_count_for_tle_cap(monkeypatch):
    """CelesTrak sends the whole group, so the hidden count is a real total."""
    monkeypatch.setenv("COSMIC_CAP_ISS", "1")
    with (
        patch("app.data_parser.fetch_celestrak_text", return_value=_ISS_TLE * 3),
        patch("app.data_parser.fetch_jpl", return_value=[]),
        patch("app.data_parser.fetch_simbad", return_value=[]),
    ):
        r = client.get("/api/scene")

    assert r.status_code == 200
    assert len([o for o in r.json()["objects"] if o["kind"] == "iss"]) == 1
    row = _cap_row("iss")
    assert row == {
        "kind": "iss",
        "shown": 1,
        "cap": 1,
        "hidden": 2,
        "hidden_exact": True,
    }


def test_scene_reports_nothing_hidden_when_under_the_cap(monkeypatch):
    monkeypatch.setenv("COSMIC_CAP_ISS", "5")
    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", return_value=_ISS_TLE)
    ):
        client.get("/api/scene")

    row = _cap_row("iss")
    assert row["hidden"] == 0 and row["hidden_exact"] is True


def test_scene_probes_one_past_the_cap_on_query_side_sources(monkeypatch):
    """SIMBAD/JPL cap in the query, so ask for cap+1 to detect a truncated page."""
    monkeypatch.setenv("COSMIC_CAP_GALAXY", "2")
    requested = {}

    def fake_simbad(slug, limit):
        requested[slug] = limit
        return [{"main_id": f"G{i}", "ra": float(i), "dec": 0.0} for i in range(limit)]

    with (
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x")),
        patch("app.data_parser.fetch_jpl", return_value=[]),
        patch("app.data_parser.fetch_simbad", side_effect=fake_simbad),
    ):
        r = client.get("/api/scene")

    assert requested["galaxy"] == 3  # cap + 1
    # Only the cap reaches the scene; the probe record is reported as hidden.
    assert len([o for o in r.json()["objects"] if o["kind"] == "galaxy"]) == 2
    row = _cap_row("galaxy")
    assert row["shown"] == 2
    assert row["hidden"] == 1 and row["hidden_exact"] is False  # "at least one more"


def test_scene_reports_hidden_near_earth_objects(monkeypatch):
    monkeypatch.setenv("COSMIC_CAP_NEAR_EARTH_OBJECT", "1")

    def fake_jpl(date, limit):
        return [{"des": f"2024 X{i}", "dist": "0.05"} for i in range(limit)]

    with (
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x")),
        patch("app.data_parser.fetch_jpl", side_effect=fake_jpl),
        patch("app.data_parser.fetch_simbad", return_value=[]),
    ):
        r = client.get("/api/scene")

    assert (
        len([o for o in r.json()["objects"] if o["kind"] == "near_earth_object"]) == 1
    )
    row = _cap_row("near_earth_object")
    assert row["hidden"] == 1 and row["hidden_exact"] is False


def test_zero_cap_drops_a_kind_without_fetching_it(monkeypatch):
    monkeypatch.setenv("COSMIC_CAP_SPACE_DEBRIS", "0")
    fetched = []

    def fake_celestrak(slug):
        fetched.append(slug)
        return _ISS_TLE

    with (
        patch("app.data_parser.fetch_celestrak_text", side_effect=fake_celestrak),
        patch("app.data_parser.fetch_jpl", return_value=[]),
        patch("app.data_parser.fetch_simbad", return_value=[]),
    ):
        r = client.get("/api/scene")

    assert "space_debris" not in fetched  # capped at 0 -> no network call
    assert not [o for o in r.json()["objects"] if o["kind"] == "space_debris"]
    assert _cap_row("space_debris") == {
        "kind": "space_debris",
        "shown": 0,
        "cap": 0,
        "hidden": 0,
        "hidden_exact": True,
    }


def test_scene_limit_param_overrides_the_satellite_cap(monkeypatch):
    monkeypatch.setenv("COSMIC_CAP_SATELLITE", "40")
    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", return_value=_ISS_TLE * 3)
    ):
        r = client.get("/api/scene?limit=2")

    assert len([o for o in r.json()["objects"] if o["kind"] == "satellite"]) == 2
    assert _cap_row("satellite")["cap"] == 2


def test_scene_caps_report_survives_offline_catalogs():
    """Every capped kind is still reported when its source is unreachable."""
    from app.api import _CAPPED_SCENE_KINDS
    from app.metrics import scene_cap_report

    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x"))
    ):
        client.get("/api/scene")

    snap = scene_cap_report.snapshot()
    assert {row["kind"] for row in snap["kinds"]} == set(_CAPPED_SCENE_KINDS)
    assert snap["total_hidden"] == 0  # nothing fetched, so nothing was capped out


# ── Catalog scene-object helpers ──────────────────────────────────────────────


def test_stable_angle_is_deterministic_and_in_range():
    assert _stable_angle("2024 XY1") == _stable_angle("2024 XY1")
    assert 0.0 <= _stable_angle("anything") < 2 * np.pi


def test_jpl_scene_objects_placement_and_schema():
    with patch(
        "app.data_parser.fetch_jpl",
        return_value=[{"des": "2024 XY1", "dist": "0.05"}],
    ):
        objs = _jpl_scene_objects("2025-06-01", cap=5).objects
    assert len(objs) == 1
    obj = objs[0]
    assert obj["kind"] == "near_earth_object"
    assert obj["source"] == "jpl"
    # Real approach distance sets the radius on the shared scale (inside the rim).
    radius = (obj["x_norm"] ** 2 + obj["y_norm"] ** 2) ** 0.5
    assert 0.10 <= radius <= 0.95


def test_jpl_scene_objects_tolerates_missing_dist():
    with patch(
        "app.data_parser.fetch_jpl", return_value=[{"des": "BadRow", "dist": None}]
    ):
        objs = _jpl_scene_objects("2025-06-01", cap=5).objects
    assert len(objs) == 1  # missing dist falls back to radius floor, no crash


def test_jpl_scene_objects_empty_on_failure():
    with patch("app.data_parser.fetch_jpl", side_effect=Exception("boom")):
        assert _jpl_scene_objects("2025-06-01", cap=5).objects == []


def test_simbad_scene_objects_maps_radec_to_canvas():
    with patch(
        "app.data_parser.fetch_simbad",
        return_value=[{"main_id": "M31", "ra": 180.0, "dec": 0.0}],
    ):
        objs = _simbad_scene_objects("galaxy", cap=4).objects
    assert len(objs) == 1
    obj = objs[0]
    assert obj["kind"] == "galaxy"
    # Angle is real RA (180° -> pointing -x), on the outer sky band (dec 0).
    radius = (obj["x_norm"] ** 2 + obj["y_norm"] ** 2) ** 0.5
    assert radius == pytest.approx(0.95, abs=0.01)
    assert obj["x_norm"] == pytest.approx(-0.95, abs=0.01)
    assert obj["y_norm"] == pytest.approx(0.0, abs=1e-6)


def test_simbad_scene_objects_skips_rows_without_coords():
    with patch(
        "app.data_parser.fetch_simbad",
        return_value=[{"main_id": "NoCoords", "ra": None, "dec": None}],
    ):
        assert _simbad_scene_objects("galaxy", cap=4).objects == []


def test_planet_scene_objects_schema_and_placement():
    dt = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
    objs = _planet_scene_objects(dt)

    assert len(objs) == 7  # Mercury..Neptune (Earth is the scene centre)
    names = [o["name"] for o in objs]
    assert names[0] == "Mercury" and names[-1] == "Neptune"

    for obj in objs:
        for field in (
            "id",
            "name",
            "kind",
            "x_norm",
            "y_norm",
            "vx_norm",
            "vy_norm",
            "speed_kms",
            "source",
            "description",
        ):
            assert field in obj, f"missing {field}"
        assert obj["kind"] == "planet"
        assert obj["source"] == "ephemeris"
        assert obj["description"]
        # Every planet lands inside the shared radial scale.
        radius = (obj["x_norm"] ** 2 + obj["y_norm"] ** 2) ** 0.5
        assert 0.10 <= radius <= 0.95


def test_planet_velocity_shows_real_orbital_speed():
    # Mercury's mean orbital speed (~47.4 km/s) is reported for the panel.
    mercury = _planet_scene_objects(datetime(2025, 1, 1, tzinfo=timezone.utc))[0]
    assert mercury["name"] == "Mercury"
    assert mercury["speed_kms"] == pytest.approx(47.4)


def test_planet_positions_advance_with_date():
    a = _planet_scene_objects(datetime(2025, 1, 1, tzinfo=timezone.utc))[0]
    b = _planet_scene_objects(datetime(2025, 4, 1, tzinfo=timezone.utc))[0]
    assert (a["x_norm"], a["y_norm"]) != (b["x_norm"], b["y_norm"])


def test_scene_includes_planets_when_catalogs_offline():
    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("x"))
    ):
        r = client.get("/api/scene")
    planets = [o for o in r.json()["objects"] if o["kind"] == "planet"]
    assert len(planets) == 7
    assert all(o["description"] for o in planets)


# ── POST /api/upload/csv ──────────────────────────────────────────────────────

VALID_CSV = (
    b"id,name,kind,x,y,timestamp\n"
    b"SAT001,My Satellite,satellite,0.120,-0.050,1704067200\n"
    b"SAT001,My Satellite,satellite,0.130,-0.060,1704068200\n"
    b"SAT001,My Satellite,satellite,0.140,-0.070,1704069200\n"
    b"UFO01,Unknown,ufo,0.280,-0.200,1704067200\n"
    b"UFO01,Unknown,ufo,0.285,-0.205,1704068200\n"
)


def test_csv_upload_returns_objects_and_predictions():
    r = client.post(
        "/api/upload/csv", files={"file": ("data.csv", VALID_CSV, "text/csv")}
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data["objects"]) == 2
    assert len(data["predictions"]) == 2


def test_csv_upload_object_fields():
    r = client.post(
        "/api/upload/csv", files={"file": ("data.csv", VALID_CSV, "text/csv")}
    )
    obj = r.json()["objects"][0]
    for f in ("id", "name", "kind", "x_norm", "y_norm", "vx_norm", "vy_norm", "source"):
        assert f in obj
    assert obj["source"] == "upload"


def test_csv_upload_uses_latest_position():
    r = client.post(
        "/api/upload/csv", files={"file": ("data.csv", VALID_CSV, "text/csv")}
    )
    sat = next(o for o in r.json()["objects"] if o["id"] == "SAT001")
    assert abs(sat["x_norm"] - 0.140) < 1e-6
    assert abs(sat["y_norm"] - (-0.070)) < 1e-6


def test_csv_upload_computes_velocity():
    csv_data = (
        b"id,name,kind,x,y,timestamp\n"
        b"A,Sat,satellite,0.10,0.20,1000\n"
        b"A,Sat,satellite,0.12,0.24,2000\n"
    )
    r = client.post("/api/upload/csv", files={"file": ("v.csv", csv_data, "text/csv")})
    obj = r.json()["objects"][0]
    assert abs(obj["vx_norm"] - 2e-5) < 1e-10  # (0.12-0.10)/1000
    assert abs(obj["vy_norm"] - 4e-5) < 1e-10  # (0.24-0.20)/1000


def test_csv_upload_missing_required_columns():
    r = client.post(
        "/api/upload/csv",
        files={"file": ("bad.csv", b"name,x\nSat,0.1\n", "text/csv")},
    )
    assert r.status_code == 422
    assert "columns" in r.json()["detail"].lower()


def test_csv_upload_skips_single_point_object():
    csv_data = b"id,name,kind,x,y,timestamp\nOBJ1,test,satellite,0.1,0.2,1000\n"
    r = client.post("/api/upload/csv", files={"file": ("f.csv", csv_data, "text/csv")})
    assert r.status_code == 200
    assert r.json()["objects"] == []


def test_csv_upload_handles_bom():
    bom_csv = b"\xef\xbb\xbfid,name,kind,x,y,timestamp\nB,b,ufo,0.1,0.2,1\nB,b,ufo,0.2,0.3,2\n"
    r = client.post("/api/upload/csv", files={"file": ("bom.csv", bom_csv, "text/csv")})
    assert r.status_code == 200
    assert len(r.json()["objects"]) == 1


def test_csv_upload_default_kind_for_missing_kind_column():
    csv_data = (
        b"id,name,x,y,timestamp\nX,Object X,0.2,0.3,1000\nX,Object X,0.3,0.4,2000\n"
    )
    r = client.post("/api/upload/csv", files={"file": ("k.csv", csv_data, "text/csv")})
    assert r.status_code == 200
    # kind column absent → defaults to 'ufo'
    assert r.json()["objects"][0]["kind"] == "ufo"


# ── POST /api/classify/upload ─────────────────────────────────────────────────


def test_classify_upload_returns_classification():
    from PIL import Image

    img = Image.fromarray(np.zeros((100, 100, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    mock_result = {
        "class": "Galaxy",
        "slug": "galaxy",
        "group": "deep_space",
        "confidence": 0.72,
        "probabilities": {},
    }
    with patch("app.api._get_cnn", return_value=MagicMock()):
        with patch("app.object_classifier.predict_patch", return_value=mock_result):
            r = client.post(
                "/api/classify/upload",
                files={"file": ("test.png", buf, "image/png")},
            )
    assert r.status_code == 200
    assert r.json()["class"] == "Galaxy"
    assert r.json()["input_source"] == "uploaded_image"
    assert r.json()["is_demo"] is False
    assert "uploaded image" in r.json()["notice"]


def test_search_reports_exclusions_and_provenance():
    with (
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("offline")),
        patch(
            "app.data_parser.fetch_jpl",
            return_value=[{"des": "Test NEO", "dist": "0.05"}],
        ),
        patch(
            "app.data_parser.fetch_simbad",
            return_value=[{"main_id": "Test star", "ra": 10, "dec": 20}],
        ),
    ):
        full = client.get("/api/scene?datetime_str=2025-06-01").json()
        narrow = client.get(
            "/api/scene?datetime_str=2025-06-01&ra=0&dec=0&radius_deg=180"
        ).json()
        cached = client.get(
            "/api/scene?datetime_str=2025-06-01&ra=0&dec=0&radius_deg=180"
        ).json()
    neo = next(obj for obj in full["objects"] if obj["source"] == "jpl")
    assert "Illustrative placement" in neo["position_note"]
    assert "Static" in neo["motion_note"]
    assert all(
        "Static" in obj["motion_note"]
        for obj in full["objects"]
        if obj["source"] == "simbad"
    )
    search = narrow["search"]
    assert search["excluded_without_coordinates"] == {"near_earth_object": 1}
    assert search["observer_count"] == 1
    assert search["searched"] == len(full["objects"]) - 2
    assert search["matched"] == len(narrow["objects"]) - 1
    assert cached["search"] == search


def test_classify_upload_resizes_to_64x64():
    from PIL import Image

    captured = []

    def capture(model, patch):
        captured.append(patch.shape)
        return _MOCK_CLASSIFICATION

    img = Image.fromarray(np.zeros((200, 300, 3), dtype=np.uint8))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    with patch("app.api._get_cnn", return_value=MagicMock()):
        with patch("app.object_classifier.predict_patch", side_effect=capture):
            client.post(
                "/api/classify/upload", files={"file": ("big.png", buf, "image/png")}
            )

    assert captured == [(64, 64, 3)]


# ── _propagate_tles helper ────────────────────────────────────────────────────

_ISS_TLE = (
    "ISS (ZARYA)\n"
    "1 25544U 98067A   24001.50000000  .00001234  00000-0  27890-4 0  9990\n"
    "2 25544  51.6400 100.0000 0001500  50.0000 310.0000 15.50000000000014\n"
)


def test_propagate_tles_produces_valid_position():
    dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    result = _propagate_tles(_ISS_TLE, dt, limit=1, kind="iss")
    assert result[0]["outside_propagation_policy"] is False
    assert result[0]["tle_epoch_offset_days"] == pytest.approx(0)
    assert len(result) == 1
    obj = result[0]
    assert obj["kind"] == "iss"
    assert obj["source"] == "celestrak"
    assert abs(obj["x_norm"]) < 1.0
    assert abs(obj["y_norm"]) < 1.0


@pytest.mark.parametrize("day", [9, 20])
def test_tle_outside_epoch_policy_is_disclosed(day):
    result = _propagate_tles(
        _ISS_TLE, datetime(2024, 1, day, 12, tzinfo=timezone.utc), limit=1, kind="iss"
    )
    assert result[0]["outside_propagation_policy"] is True
    assert "not an accuracy guarantee" in result[0]["motion_note"]


def test_propagate_tles_radius_in_leo_band():
    """The ISS (~420 km up) lands in the innermost LEO band of the scale."""
    dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    result = _propagate_tles(_ISS_TLE, dt, limit=1, kind="iss")
    r_norm = (result[0]["x_norm"] ** 2 + result[0]["y_norm"] ** 2) ** 0.5
    assert 0.10 <= r_norm < 0.13


def test_propagate_tles_reports_real_speed_and_motion():
    dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    obj = _propagate_tles(_ISS_TLE, dt, limit=1, kind="iss")[0]
    # Real ISS orbital speed is ~7.66 km/s (shown in the panel).
    assert obj["speed_kms"] == pytest.approx(7.66, abs=0.3)
    # It also carries a non-zero scene velocity so the animation sweeps it round.
    assert (obj["vx_norm"] ** 2 + obj["vy_norm"] ** 2) ** 0.5 > 0


def test_propagate_tles_respects_limit():
    three_tles = _ISS_TLE * 3  # crude repeat
    dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
    result = _propagate_tles(three_tles, dt, limit=1, kind="satellite")
    assert len(result) <= 1


def test_propagate_tles_ignores_malformed_lines():
    dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
    result = _propagate_tles(
        "GARBAGE\nnot tle\nalso not\n", dt, limit=5, kind="satellite"
    )
    assert result == []


def test_propagate_tles_without_sgp4_returns_empty():
    import sys

    dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
    saved = sys.modules.pop("sgp4.api", None)
    sys.modules["sgp4.api"] = None  # force ImportError on from sgp4.api import ...
    try:
        result = _propagate_tles(_ISS_TLE, dt, limit=1, kind="iss")
        assert result == []
    finally:
        if saved is not None:
            sys.modules["sgp4.api"] = saved
        else:
            sys.modules.pop("sgp4.api", None)


# ── Static delivery: compression + browser caching ────────────────────────────
def test_static_assets_are_cacheable():
    """Static files carry a Cache-Control header so browsers don't refetch them."""
    resp = client.get("/static/app.js")
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "public, max-age=3600"


def test_large_static_assets_are_gzipped():
    """The GZip middleware compresses sizeable assets when the client accepts it."""
    resp = client.get("/static/app.js", headers={"accept-encoding": "gzip"})
    assert resp.status_code == 200
    assert resp.headers.get("content-encoding") == "gzip"


# ── Source failure reporting ──────────────────────────────────────────────────


def test_scene_records_source_failures_instead_of_hiding_them():
    """Degrading silently makes an outage look like an empty sky (claude.md §3)."""
    from app.metrics import source_failures

    with _offline_catalogs(
        patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("403"))
    ):
        r = client.get("/api/scene?datetime_str=2025-06-01T12:00:00Z")

    assert r.status_code == 200  # the scene still builds
    warnings = r.json()["source_warnings"]
    assert {row["source"] for row in warnings} == {"celestrak", "jpl", "simbad"}
    assert all(set(row) == {"source", "kind"} for row in warnings)
    assert (
        client.get("/api/scene?datetime_str=2025-06-01T12:00:00Z").json()[
            "source_warnings"
        ]
        == warnings
    )
    snapshot = source_failures.snapshot()
    assert snapshot["total"] > 0
    sources = {row["source"] for row in snapshot["sources"]}
    assert {"celestrak", "jpl", "simbad"} <= sources


def test_source_failure_is_logged(caplog):
    with caplog.at_level("WARNING", logger="app.api"):
        with _offline_catalogs(
            patch("app.data_parser.fetch_celestrak_text", side_effect=Exception("403"))
        ):
            client.get("/api/scene?datetime_str=2025-06-01T12:00:00Z")
    assert any("fetch failed" in record.message for record in caplog.records)


def test_healthy_scene_records_no_failures():
    from app.metrics import source_failures

    tle_text = (
        "ISS (ZARYA)\n"
        "1 25544U 98067A   24001.50000000  .00001234  00000-0  27890-4 0  9990\n"
        "2 25544  51.6400 100.0000 0001500  50.0000 310.0000 15.50000000000014\n"
    )
    with (
        patch("app.data_parser.fetch_celestrak_text", return_value=tle_text),
        patch("app.data_parser.fetch_jpl", return_value=[]),
        patch("app.data_parser.fetch_simbad", return_value=[]),
    ):
        response = client.get("/api/scene?datetime_str=2024-01-01T12:00:00Z")
    assert response.json()["source_warnings"] == []
    assert source_failures.snapshot()["total"] == 0
