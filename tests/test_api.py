"""Tests for all FastAPI endpoints in app/api.py."""

import io
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.api import (
    app,
    _propagate_tles,
    _jpl_scene_objects,
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


def test_scene_always_includes_ufo():
    """UFO entry is appended even when every data source fails."""
    with _offline_catalogs(patch("app.api._requests.get", side_effect=Exception("x"))):
        r = client.get("/api/scene")
    assert r.status_code == 200
    kinds = [o["kind"] for o in r.json()["objects"]]
    assert "ufo" in kinds


def test_scene_ufo_has_required_fields():
    with _offline_catalogs(patch("app.api._requests.get", side_effect=Exception("x"))):
        r = client.get("/api/scene")
    ufo = next(o for o in r.json()["objects"] if o["kind"] == "ufo")
    for field in (
        "id",
        "name",
        "kind",
        "x_norm",
        "y_norm",
        "vx_norm",
        "vy_norm",
        "source",
    ):
        assert field in ufo, f"missing field: {field}"


def test_scene_accepts_datetime_str():
    with _offline_catalogs(patch("app.api._requests.get", side_effect=Exception("x"))):
        r = client.get("/api/scene?datetime_str=2025-06-01T12:00:00Z")
    assert r.status_code == 200
    assert "2025-06-01" in r.json()["datetime"]


def test_scene_invalid_datetime_falls_back():
    with _offline_catalogs(patch("app.api._requests.get", side_effect=Exception("x"))):
        r = client.get("/api/scene?datetime_str=not-a-date")
    assert r.status_code == 200  # falls back to now, no crash


def test_scene_includes_tle_objects_when_celestrak_responds():
    tle_text = (
        "ISS (ZARYA)\n"
        "1 25544U 98067A   24001.50000000  .00001234  00000-0  27890-4 0  9990\n"
        "2 25544  51.6400 100.0000 0001500  50.0000 310.0000 15.50000000000014\n"
    )
    mock_resp = MagicMock()
    mock_resp.text = tle_text
    mock_resp.raise_for_status = MagicMock()

    with _offline_catalogs(patch("app.api._requests.get", return_value=mock_resp)):
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
        patch("app.api._requests.get", side_effect=Exception("x")),
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
        patch("app.api._requests.get", side_effect=Exception("x")),
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


# ── Catalog scene-object helpers ──────────────────────────────────────────────


def test_stable_angle_is_deterministic_and_in_range():
    assert _stable_angle("2024 XY1") == _stable_angle("2024 XY1")
    assert 0.0 <= _stable_angle("anything") < 2 * np.pi


def test_jpl_scene_objects_placement_and_schema():
    with patch(
        "app.data_parser.fetch_jpl",
        return_value=[{"des": "2024 XY1", "dist": "0.05"}],
    ):
        objs = _jpl_scene_objects("2025-06-01", limit=5)
    assert len(objs) == 1
    obj = objs[0]
    assert obj["kind"] == "near_earth_object"
    assert obj["source"] == "jpl"
    # Symbolic placement lands inside the canvas (radius 0.6–0.95).
    radius = (obj["x_norm"] ** 2 + obj["y_norm"] ** 2) ** 0.5
    assert 0.6 <= radius <= 0.95


def test_jpl_scene_objects_tolerates_missing_dist():
    with patch(
        "app.data_parser.fetch_jpl", return_value=[{"des": "BadRow", "dist": None}]
    ):
        objs = _jpl_scene_objects("2025-06-01", limit=5)
    assert len(objs) == 1  # missing dist falls back to radius floor, no crash


def test_jpl_scene_objects_empty_on_failure():
    with patch("app.data_parser.fetch_jpl", side_effect=Exception("boom")):
        assert _jpl_scene_objects("2025-06-01", limit=5) == []


def test_simbad_scene_objects_maps_radec_to_canvas():
    with patch(
        "app.data_parser.fetch_simbad",
        return_value=[{"main_id": "M31", "ra": 180.0, "dec": 0.0}],
    ):
        objs = _simbad_scene_objects("galaxy", "galaxy", limit=4)
    assert len(objs) == 1
    obj = objs[0]
    assert obj["kind"] == "galaxy"
    # RA 180 -> x 0, Dec 0 -> y 0.
    assert obj["x_norm"] == pytest.approx(0.0)
    assert obj["y_norm"] == pytest.approx(0.0)


def test_simbad_scene_objects_skips_rows_without_coords():
    with patch(
        "app.data_parser.fetch_simbad",
        return_value=[{"main_id": "NoCoords", "ra": None, "dec": None}],
    ):
        assert _simbad_scene_objects("galaxy", "galaxy", limit=4) == []


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
    assert len(result) == 1
    obj = result[0]
    assert obj["kind"] == "iss"
    assert obj["source"] == "celestrak"
    assert abs(obj["x_norm"]) < 1.0  # within GEO distance
    assert abs(obj["y_norm"]) < 1.0


def test_propagate_tles_normalised_by_geo():
    """ISS at ~400 km altitude should give |r_norm| ≈ 0.16 (LEO/GEO ratio)."""
    dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    result = _propagate_tles(_ISS_TLE, dt, limit=1, kind="iss")
    r_norm = (result[0]["x_norm"] ** 2 + result[0]["y_norm"] ** 2) ** 0.5
    assert 0.12 < r_norm < 0.22  # ISS LEO bracket


def test_propagate_tles_returns_velocity():
    dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    result = _propagate_tles(_ISS_TLE, dt, limit=1, kind="iss")
    obj = result[0]
    speed = (obj["vx_norm"] ** 2 + obj["vy_norm"] ** 2) ** 0.5
    # ISS speed ~7.7 km/s → /42164 ≈ 1.8e-4 units/s
    assert 1e-4 < speed < 5e-4


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
