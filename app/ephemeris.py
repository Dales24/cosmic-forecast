"""Low-precision geocentric ephemeris for the Sun, Moon, and planets.

Pure math (no external services), intended for approximate scene placement.
Sampled Horizons comparisons do not establish an accuracy bound; the abbreviated
Moon model can differ by degrees over 1800–2050. Everything is returned in the
equatorial frame the scene uses for direction: geocentric right ascension (the
angle) plus distance from Earth in km (the radius).

Planet positions use the JPL "Keplerian Elements for Approximate Positions of
the Major Planets" (Standish); the Moon uses an abbreviated Meeus series.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

_J2000 = 2451545.0
_OBLIQUITY = math.radians(23.43928)  # mean obliquity of the ecliptic at J2000
_AU_KM = 149_597_870.7


# ── Time ──────────────────────────────────────────────────────────────────────
def _julian_day(dt: datetime) -> float:
    """Julian Day (UTC) for a timezone-aware datetime."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    y, m = dt.year, dt.month
    day = (
        dt.day
        + (dt.hour + (dt.minute + (dt.second + dt.microsecond / 1e6) / 60.0) / 60.0)
        / 24.0
    )
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return (
        math.floor(365.25 * (y + 4716))
        + math.floor(30.6001 * (m + 1))
        + day
        + b
        - 1524.5
    )


# ── Planets (Standish Keplerian elements + per-century rates) ──────────────────
# name: (a AU, e, I deg, L deg, longPeri deg, longNode deg) and their rates /cy.
_ELEMENTS: dict[str, tuple[tuple[float, ...], tuple[float, ...]]] = {
    "mercury": (
        (0.38709927, 0.20563593, 7.00497902, 252.25032350, 77.45779628, 48.33076593),
        (0.00000037, 0.00001906, -0.00594749, 149472.67411175, 0.16047689, -0.12534081),
    ),
    "venus": (
        (0.72333566, 0.00677672, 3.39467605, 181.97909950, 131.60246718, 76.67984255),
        (0.00000390, -0.00004107, -0.00078890, 58517.81538729, 0.00268329, -0.27769418),
    ),
    "earth": (
        (1.00000261, 0.01671123, -0.00001531, 100.46457166, 102.93768193, 0.0),
        (0.00000562, -0.00004392, -0.01294668, 35999.37244981, 0.32327364, 0.0),
    ),
    "mars": (
        (1.52371034, 0.09339410, 1.84969142, -4.55343205, -23.94362959, 49.55953891),
        (0.00001847, 0.00007882, -0.00813131, 19140.30268499, 0.44441088, -0.29257343),
    ),
    "jupiter": (
        (5.20288700, 0.04838624, 1.30439695, 34.39644051, 14.72847983, 100.47390909),
        (-0.00011607, -0.00013253, -0.00183714, 3034.74612775, 0.21252668, 0.20469106),
    ),
    "saturn": (
        (9.53667594, 0.05386179, 2.48599187, 49.95424423, 92.59887831, 113.66242448),
        (-0.00125060, -0.00050991, 0.00193609, 1222.49362201, -0.41897216, -0.28867794),
    ),
    "uranus": (
        (19.18916464, 0.04725744, 0.77263783, 313.23810451, 170.95427630, 74.01692503),
        (-0.00196176, -0.00004397, -0.00242939, 428.48202785, 0.40805281, 0.04240589),
    ),
    "neptune": (
        (30.06992276, 0.00859048, 1.77004347, -55.12002969, 44.96476227, 131.78422574),
        (0.00026291, 0.00005105, 0.00035372, 218.45945325, -0.32241464, -0.00508664),
    ),
}

PLANET_NAMES = ("mercury", "venus", "mars", "jupiter", "saturn", "uranus", "neptune")


def _solve_kepler(mean_anomaly: float, e: float) -> float:
    """Eccentric anomaly (rad) from mean anomaly (rad), Newton's method."""
    ecc = mean_anomaly
    for _ in range(12):
        delta = ecc - e * math.sin(ecc) - mean_anomaly
        ecc -= delta / (1 - e * math.cos(ecc))
    return ecc


def _heliocentric_ecliptic(name: str, centuries: float) -> tuple[float, float, float]:
    """Heliocentric J2000 ecliptic rectangular coordinates (AU) for a planet."""
    base, rate = _ELEMENTS[name]
    a = base[0] + rate[0] * centuries
    e = base[1] + rate[1] * centuries
    inc = math.radians(base[2] + rate[2] * centuries)
    mean_long = base[3] + rate[3] * centuries
    long_peri = base[4] + rate[4] * centuries
    long_node = base[5] + rate[5] * centuries

    arg_peri = math.radians(long_peri - long_node)
    node = math.radians(long_node)
    mean_anom = math.radians((mean_long - long_peri) % 360.0)

    ecc = _solve_kepler(mean_anom, e)
    x_orb = a * (math.cos(ecc) - e)
    y_orb = a * math.sqrt(1 - e * e) * math.sin(ecc)

    cos_w, sin_w = math.cos(arg_peri), math.sin(arg_peri)
    cos_o, sin_o = math.cos(node), math.sin(node)
    cos_i, sin_i = math.cos(inc), math.sin(inc)

    x = (cos_w * cos_o - sin_w * sin_o * cos_i) * x_orb + (
        -sin_w * cos_o - cos_w * sin_o * cos_i
    ) * y_orb
    y = (cos_w * sin_o + sin_w * cos_o * cos_i) * x_orb + (
        -sin_w * sin_o + cos_w * cos_o * cos_i
    ) * y_orb
    z = (sin_w * sin_i) * x_orb + (cos_w * sin_i) * y_orb
    return x, y, z


def _ecliptic_to_equatorial(x: float, y: float, z: float) -> tuple[float, float]:
    """Equatorial (right ascension, declination) in rad from ecliptic rectangular.

    RA is normalised to 0–2π; declination is ±π/2.
    """
    y_eq = y * math.cos(_OBLIQUITY) - z * math.sin(_OBLIQUITY)
    z_eq = y * math.sin(_OBLIQUITY) + z * math.cos(_OBLIQUITY)
    ra = math.atan2(y_eq, x) % (2 * math.pi)
    radius = math.sqrt(x * x + y_eq * y_eq + z_eq * z_eq)
    dec = math.asin(z_eq / radius) if radius else 0.0
    return ra, dec


def planet_geocentric(name: str, dt: datetime) -> tuple[float, float, float]:
    """Geocentric (right ascension, declination) in rad and distance in km."""
    centuries = (_julian_day(dt) - _J2000) / 36525.0
    px, py, pz = _heliocentric_ecliptic(name, centuries)
    ex, ey, ez = _heliocentric_ecliptic("earth", centuries)
    gx, gy, gz = px - ex, py - ey, pz - ez
    ra, dec = _ecliptic_to_equatorial(gx, gy, gz)
    dist_km = math.sqrt(gx * gx + gy * gy + gz * gz) * _AU_KM
    return ra, dec, dist_km


def sun_geocentric(dt: datetime) -> tuple[float, float, float]:
    """Geocentric (right ascension, declination) in rad and distance in km."""
    centuries = (_julian_day(dt) - _J2000) / 36525.0
    ex, ey, ez = _heliocentric_ecliptic("earth", centuries)
    # The Sun's geocentric position is the negative of Earth's heliocentric one.
    sx, sy, sz = -ex, -ey, -ez
    ra, dec = _ecliptic_to_equatorial(sx, sy, sz)
    dist_km = math.sqrt(sx * sx + sy * sy + sz * sz) * _AU_KM
    return ra, dec, dist_km


def moon_geocentric(dt: datetime) -> tuple[float, float, float]:
    """Geocentric (right ascension, declination) in rad and distance in km."""
    days = _julian_day(dt) - _J2000
    # Fundamental arguments (deg), abbreviated Meeus.
    mean_long = 218.316 + 13.176396 * days
    mean_anom = math.radians(134.963 + 13.064993 * days)
    elongation = math.radians(297.850 + 12.190749 * days)
    arg_lat = math.radians(93.272 + 13.229350 * days)

    lon = math.radians(
        mean_long
        + 6.289 * math.sin(mean_anom)
        + 1.274 * math.sin(2 * elongation - mean_anom)
        + 0.658 * math.sin(2 * elongation)
    )
    lat = math.radians(5.128 * math.sin(arg_lat))
    dist_km = (
        385000.56
        - 20905.355 * math.cos(mean_anom)
        - 3699.111 * math.cos(2 * elongation - mean_anom)
    )
    # Ecliptic spherical → rectangular → equatorial.
    x = math.cos(lat) * math.cos(lon)
    y = math.cos(lat) * math.sin(lon)
    z = math.sin(lat)
    ra, dec = _ecliptic_to_equatorial(x, y, z)
    return ra, dec, dist_km
