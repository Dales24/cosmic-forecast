"""Tests for app/ephemeris.py — geocentric Sun/Moon/planet positions."""

import math
from datetime import datetime, timezone

import pytest

from app import ephemeris

_AU_KM = 149_597_870.7


def _ra_hours(ra_rad: float) -> float:
    return (math.degrees(ra_rad) / 15.0) % 24.0


def test_julian_day_at_j2000():
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert ephemeris._julian_day(dt) == pytest.approx(2451545.0, abs=1e-6)


def test_sun_distance_is_about_one_au():
    dt = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
    _, _, dist_km = ephemeris.sun_geocentric(dt)
    assert 0.98 * _AU_KM <= dist_km <= 1.02 * _AU_KM


def test_sun_ra_at_j2000_is_near_winter_solstice():
    # At the J2000 epoch the Sun sits near RA 18.75h (the winter-solstice point).
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    ra, _, _ = ephemeris.sun_geocentric(dt)
    assert _ra_hours(ra) == pytest.approx(18.75, abs=0.2)


def test_moon_distance_in_real_range():
    dt = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
    _, _, dist_km = ephemeris.moon_geocentric(dt)
    assert 356_000 <= dist_km <= 407_000  # perigee..apogee


def test_planet_distances_are_physical():
    dt = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
    # Rough geocentric distance bounds (AU): each planet stays within them.
    bounds = {
        "mercury": (0.5, 1.5),
        "venus": (0.2, 1.8),
        "mars": (0.3, 2.7),
        "jupiter": (3.9, 6.6),
        "saturn": (8.0, 11.1),
        "uranus": (17.2, 21.2),
        "neptune": (28.8, 31.4),
    }
    for name, (lo, hi) in bounds.items():
        _, _, dist_km = ephemeris.planet_geocentric(name, dt)
        assert lo <= dist_km / _AU_KM <= hi, name


def test_all_planet_names_resolve():
    dt = datetime(2026, 7, 19, tzinfo=timezone.utc)
    for name in ephemeris.PLANET_NAMES:
        ra, _, dist_km = ephemeris.planet_geocentric(name, dt)
        assert 0.0 <= ra < 2 * math.pi
        assert dist_km > 0


def test_sun_declination_tracks_the_seasons():
    """The Sun's dec runs from about -23.4° at the December solstice to +23.4°
    at the June one — the obliquity of the ecliptic."""
    _, dec_dec, _ = ephemeris.sun_geocentric(
        datetime(2026, 12, 21, 12, 0, tzinfo=timezone.utc)
    )
    _, dec_jun, _ = ephemeris.sun_geocentric(
        datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc)
    )
    assert math.degrees(dec_dec) == pytest.approx(-23.4, abs=1.0)
    assert math.degrees(dec_jun) == pytest.approx(23.4, abs=1.0)


def test_declinations_stay_in_range():
    dt = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
    for _, dec, _ in [
        ephemeris.sun_geocentric(dt),
        ephemeris.moon_geocentric(dt),
        *[ephemeris.planet_geocentric(n, dt) for n in ephemeris.PLANET_NAMES],
    ]:
        assert -math.pi / 2 <= dec <= math.pi / 2


def test_planet_declinations_stay_near_the_ecliptic():
    """Planets orbit close to the ecliptic plane, so none strays far in dec."""
    dt = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
    for name in ephemeris.PLANET_NAMES:
        _, dec, _ = ephemeris.planet_geocentric(name, dt)
        assert abs(math.degrees(dec)) <= 30.0, name


def test_positions_change_over_time():
    a = ephemeris.moon_geocentric(datetime(2026, 1, 1, tzinfo=timezone.utc))
    b = ephemeris.moon_geocentric(datetime(2026, 1, 8, tzinfo=timezone.utc))
    assert a != b


def test_naive_datetime_is_treated_as_utc():
    naive = datetime(2026, 7, 19, 12, 0)
    aware = datetime(2026, 7, 19, 12, 0, tzinfo=timezone.utc)
    assert ephemeris.sun_geocentric(naive) == ephemeris.sun_geocentric(aware)
