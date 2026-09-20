"""Tests for app/ephemeris.py — geocentric Sun/Moon/planet positions."""

import math
from datetime import datetime, timezone

import pytest

from app import ephemeris


# JPL Horizons: target 301, center 500@399, geometric ICRF vectors, UTC input.
# Retrieved 2026-09-20; fixed references keep regressions independent of network.
@pytest.mark.parametrize(
    "year,xyz",
    [
        (1800, (396128.7529367695, 30860.10192782005, -7712.90478733641)),
        (1850, (-321065.3279393155, 161599.4361221236, 72954.20259972815)),
        (1900, (114417.1769038338, -323782.2898176595, -124088.4990442399)),
        (1950, (106028.4721480495, 337134.9700781353, 179319.9818915324)),
        (2000, (-262121.7685015786, -293953.9054548166, -88682.35809446021)),
        (2026, (53752.42566938213, 313249.4597561493, 169827.6738198773)),
        (2050, (327050.7213087169, 176104.9782905012, 93782.87678473604)),
    ],
)
def test_moon_against_independent_horizons_reference(year, xyz):
    ra, dec, distance = ephemeris.moon_geocentric(
        datetime(year, 1, 2, tzinfo=timezone.utc)
    )
    ref_distance = math.sqrt(sum(value * value for value in xyz))
    unit = (math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec))
    cosine = sum(a * b for a, b in zip(unit, xyz)) / ref_distance
    error = math.degrees(math.acos(max(-1, min(1, cosine))))
    assert error < 0.01  # Regression threshold for these dates, not a universal bound.
    assert abs(distance - ref_distance) < 30


def test_lunar_time_conversion_and_timezone_equivalence():
    from datetime import timedelta

    assert ephemeris._tt_offset_seconds(
        datetime(2000, 1, 1, tzinfo=timezone.utc)
    ) == pytest.approx(64.184)
    assert ephemeris._tt_offset_seconds(
        datetime(2026, 1, 1, tzinfo=timezone.utc)
    ) == pytest.approx(69.184)
    expected = ephemeris.moon_geocentric(datetime(2026, 1, 2, tzinfo=timezone.utc))
    local = datetime(2026, 1, 1, 18, tzinfo=timezone(timedelta(hours=-6)))
    assert ephemeris.moon_geocentric(local) == pytest.approx(expected)
    assert ephemeris.moon_geocentric(datetime(2026, 1, 2)) == pytest.approx(expected)


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
