"""Offline vector-parser and live-scene integration regression checks."""

from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

import numpy as np
import pytest

from app import api, horizons
from app.horizons import fetch_vectors as real_fetch_vectors
from app.ephemeris import _julian_day


def test_vector_parser_and_reference_settings():
    date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    response = Mock()
    response.json.return_value = {
        "result": f"$$SOE\n{_julian_day(date)},date,1,2,3,4,5,6,\n$$EOE"
    }
    with patch("app.horizons.requests.get", return_value=response) as get:
        vectors = real_fetch_vectors("433;", [date])
    np.testing.assert_array_equal(vectors[0], [1, 2, 3, 4, 5, 6])
    params = get.call_args.kwargs["params"]
    assert params["CENTER"] == "'500@399'"
    assert params["VEC_CORR"] == "'NONE'"
    assert params["TIME_TYPE"] == "'UT'"


@pytest.mark.parametrize(
    "text",
    [
        "ambiguous target",
        "$$SOE\n0,date,1,2,3,4,5,6\n$$EOE",
        "$$SOE\n2461041.5,date,nan,2,3,4,5,6\n$$EOE",
    ],
)
def test_rejects_unusable_reference_data(text):
    response = Mock()
    response.json.return_value = {"result": text}
    with (
        patch("app.horizons.requests.get", return_value=response),
        pytest.raises(ValueError),
    ):
        real_fetch_vectors("433;", [datetime(2026, 1, 1, tzinfo=timezone.utc)])


def test_positioned_neo_is_searchable_and_cached():
    date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with (
        patch(
            "app.data_parser.fetch_jpl", return_value=[{"des": "433", "dist": "0.1"}]
        ),
        patch(
            "app.horizons.fetch_vectors", return_value=[np.array([1e7, 0, 0, 0, 10, 0])]
        ) as fetch,
    ):
        result = api._jpl_positioned_objects(date, 1)
        again = api._jpl_positioned_objects(date, 1)
    obj = result.objects[0]
    assert fetch.call_count == 1
    assert again is result
    assert obj["position_source"] == "jpl_horizons"
    assert obj["ra_deg"] == 0
    assert obj["vy_norm"] != 0
    assert api._objects_near([obj], 0, 0, 1) == [obj]


def test_positioned_neo_failure_keeps_disclosed_fallback():
    with patch(
        "app.data_parser.fetch_jpl", return_value=[{"des": "433", "dist": "0.1"}]
    ):
        result = api._jpl_positioned_objects(
            datetime(2026, 1, 1, tzinfo=timezone.utc), 1
        )
    assert result.unavailable_source == "jpl_horizons"
    assert "Illustrative" in result.objects[0]["position_note"]
    assert "ra_deg" not in result.objects[0]
