"""Tests for app/data_parser.py — routing, parsing, and mocked HTTP calls."""

from unittest.mock import MagicMock, patch

import pytest

from app.data_parser import (
    _parse_tle_text,
    fetch_celestrak,
    fetch_jpl,
    fetch_simbad,
    get_data,
)

# ── _parse_tle_text ───────────────────────────────────────────────────────────

_ISS_TLE = (
    "ISS (ZARYA)\n"
    "1 25544U 98067A   24001.50000000  .00001234  00000-0  27890-4 0  9990\n"
    "2 25544  51.6400 100.0000 0001500  50.0000 310.0000 15.50000000000014\n"
)


def test_parse_valid_single_tle():
    result = _parse_tle_text(_ISS_TLE, limit=5)
    assert len(result) == 1
    assert result[0]["name"] == "ISS (ZARYA)"
    assert result[0]["catalog_id"] == "25544"
    assert result[0]["tle_line1"].startswith("1 ")
    assert result[0]["tle_line2"].startswith("2 ")


def test_parse_tle_epoch_extracted():
    result = _parse_tle_text(_ISS_TLE, limit=1)
    assert result[0]["epoch"] == "24001.50000000"


def test_parse_tle_limit_respected():
    block = _ISS_TLE * 5
    result = _parse_tle_text(block, limit=2)
    assert len(result) == 2


def test_parse_tle_empty_input():
    assert _parse_tle_text("", limit=5) == []


def test_parse_tle_malformed_lines_ignored():
    bad = "GARBAGE\nnot a tle\nalso not a tle\n"
    assert _parse_tle_text(bad, limit=5) == []


def test_parse_tle_mixed_valid_invalid():
    mixed = "JUNK\nstill junk\nyep\n" + _ISS_TLE
    result = _parse_tle_text(mixed, limit=5)
    assert len(result) == 1
    assert result[0]["name"] == "ISS (ZARYA)"


def test_parse_tle_whitespace_stripped():
    padded = "  ISS (ZARYA)  \n" + _ISS_TLE.split("\n", 1)[1]
    result = _parse_tle_text(padded, limit=5)
    assert result[0]["name"] == "ISS (ZARYA)"


# ── fetch_celestrak ───────────────────────────────────────────────────────────

def _mock_response(text=""):
    resp = MagicMock()
    resp.text = text
    resp.raise_for_status = MagicMock()
    return resp


def test_fetch_celestrak_satellite_calls_correct_url():
    with patch("app.data_parser.requests.get", return_value=_mock_response("")) as mock:
        fetch_celestrak("satellite", limit=1)
    url = mock.call_args[0][0]
    assert "active" in url


def test_fetch_celestrak_iss_calls_stations_url():
    with patch("app.data_parser.requests.get", return_value=_mock_response("")) as mock:
        fetch_celestrak("iss", limit=1)
    url = mock.call_args[0][0]
    assert "stations" in url


def test_fetch_celestrak_parses_response():
    with patch("app.data_parser.requests.get", return_value=_mock_response(_ISS_TLE)):
        result = fetch_celestrak("satellite", limit=5)
    assert len(result) == 1
    assert result[0]["name"] == "ISS (ZARYA)"


def test_fetch_celestrak_unknown_slug_raises():
    with pytest.raises(ValueError, match="No CelesTrak URL"):
        fetch_celestrak("nonexistent_slug")


def test_fetch_celestrak_respects_limit():
    with patch("app.data_parser.requests.get", return_value=_mock_response(_ISS_TLE * 10)):
        result = fetch_celestrak("satellite", limit=2)
    assert len(result) <= 2


# ── fetch_jpl ─────────────────────────────────────────────────────────────────

def _jpl_response(data=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "fields": ["des", "cd", "dist", "v_rel"],
        "data": data or [["2024 XY1", "2024-01-15", "0.05", "12.3"]],
    }
    return resp


def test_fetch_jpl_returns_field_dict():
    with patch("app.data_parser.requests.get", return_value=_jpl_response()):
        result = fetch_jpl(limit=5)
    assert len(result) == 1
    assert result[0]["des"] == "2024 XY1"
    assert result[0]["dist"] == "0.05"


def test_fetch_jpl_passes_date_param():
    with patch("app.data_parser.requests.get", return_value=_jpl_response()) as mock:
        fetch_jpl(date="2025-06-01", limit=5)
    params = mock.call_args[1]["params"]
    assert params["date-min"] == "2025-06-01"


def test_fetch_jpl_default_date_is_now():
    with patch("app.data_parser.requests.get", return_value=_jpl_response()) as mock:
        fetch_jpl()
    params = mock.call_args[1]["params"]
    assert params["date-min"] == "now"


def test_fetch_jpl_empty_data():
    resp = _jpl_response(data=[])
    with patch("app.data_parser.requests.get", return_value=resp):
        result = fetch_jpl()
    assert result == []


# ── fetch_simbad ──────────────────────────────────────────────────────────────

def _simbad_response(rows=None):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {
        "metadata": [{"name": "main_id"}, {"name": "ra"}, {"name": "dec"}],
        "data": rows or [["M31", 10.68, 41.27]],
    }
    return resp


def test_fetch_simbad_galaxy_returns_records():
    with patch("app.data_parser.requests.get", return_value=_simbad_response()):
        result = fetch_simbad("galaxy", limit=5)
    assert len(result) == 1
    assert result[0]["main_id"] == "M31"
    assert result[0]["ra"] == 10.68


def test_fetch_simbad_includes_adql_query():
    with patch("app.data_parser.requests.get", return_value=_simbad_response()) as mock:
        fetch_simbad("galaxy", limit=5)
    params = mock.call_args[1]["params"]
    assert "ADQL" in params["LANG"]
    assert "G" in params["QUERY"]


def test_fetch_simbad_unknown_slug_raises():
    with pytest.raises(ValueError, match="No SIMBAD otype"):
        fetch_simbad("not_a_real_type")


def test_fetch_simbad_nebula_slug():
    with patch("app.data_parser.requests.get", return_value=_simbad_response()) as mock:
        fetch_simbad("nebula", limit=3)
    query = mock.call_args[1]["params"]["QUERY"]
    assert "PN" in query


# ── get_data routing ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("slug", ["satellite", "iss", "space_debris", "rocket_body"])
def test_get_data_celestrak_slugs_route_correctly(slug):
    with patch("app.data_parser.fetch_celestrak", return_value=[]) as mock:
        get_data(slug, limit=5)
    mock.assert_called_once_with(slug, 5)


@pytest.mark.parametrize("slug", ["asteroid", "comet", "meteor", "meteoroid", "near_earth_object"])
def test_get_data_jpl_slugs_route_correctly(slug):
    with patch("app.data_parser.fetch_jpl", return_value=[]) as mock:
        get_data(slug, date="2025-01-01", limit=10)
    mock.assert_called_once_with("2025-01-01", 10)


@pytest.mark.parametrize("slug", ["galaxy", "nebula", "star_cluster", "variable_star"])
def test_get_data_simbad_slugs_route_correctly(slug):
    with patch("app.data_parser.fetch_simbad", return_value=[]) as mock:
        get_data(slug, limit=7)
    mock.assert_called_once_with(slug, 7)


def test_get_data_ufo_returns_empty_list():
    assert get_data("ufo") == []


def test_get_data_unknown_slug_raises_value_error():
    with pytest.raises(ValueError, match="Unknown object slug"):
        get_data("bogus_slug")
