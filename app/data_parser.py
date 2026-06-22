"""
Data fetchers per object type, sourced from the plan:

  Object type   | Source
  --------------|-------------------------
  Satellites    | CelesTrak (TLE)
  ISS           | CelesTrak (TLE)
  Space debris  | CelesTrak (TLE)
  Rocket bodies | CelesTrak (TLE)
  Asteroids     | NASA JPL SBDB
  Comets        | NASA JPL SBDB
  Meteors       | NASA JPL SBDB
  Meteoroids    | NASA JPL SBDB
  NEOs          | NASA CNEOS (JPL CAD API)
  Galaxies      | SIMBAD
  Nebulae       | SIMBAD
  Star clusters | SIMBAD
  Variable stars| SIMBAD
"""

from __future__ import annotations

import requests

_TIMEOUT = 10  # seconds per request

# ── CelesTrak ─────────────────────────────────────────────────────────────────
_CELESTRAK_URLS: dict[str, str] = {
    "satellite":   "https://celestrak.org/pub/TLE/active.txt",
    "iss":         "https://celestrak.org/pub/TLE/stations.txt",
    "space_debris":"https://celestrak.org/pub/TLE/debris.txt",
    "rocket_body": "https://celestrak.org/pub/TLE/rocket-bodies.txt",
}


def _parse_tle_text(text: str, limit: int) -> list[dict]:
    """Parse a raw TLE text blob into a list of structured records."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    records: list[dict] = []
    i = 0
    while i < len(lines) and len(records) < limit:
        if (
            i + 2 < len(lines)
            and lines[i + 1].startswith("1 ")
            and lines[i + 2].startswith("2 ")
        ):
            name, l1, l2 = lines[i], lines[i + 1], lines[i + 2]
            records.append({
                "name":       name,
                "catalog_id": l1[2:7].strip(),
                "epoch":      l1[18:32].strip(),
                "tle_line1":  l1,
                "tle_line2":  l2,
            })
            i += 3
        else:
            i += 1
    return records


def fetch_celestrak(slug: str, limit: int = 20) -> list[dict]:
    url = _CELESTRAK_URLS.get(slug)
    if not url:
        raise ValueError(f"No CelesTrak URL for slug {slug!r}")
    resp = requests.get(url, timeout=_TIMEOUT)
    resp.raise_for_status()
    return _parse_tle_text(resp.text, limit)


# ── NASA JPL Small-Body Database / CNEOS ─────────────────────────────────────
_JPL_CAD_URL = "https://ssd-api.jpl.nasa.gov/cad.api"


def fetch_jpl(date: str | None = None, limit: int = 20) -> list[dict]:
    """Close-approach data from JPL CAD API (covers asteroids, comets, NEOs)."""
    params = {
        "date-min": date or "now",
        "date-max": "+30",
        "dist-max": "0.2",   # within 0.2 AU
        "sort":     "dist",
        "limit":    str(limit),
    }
    resp = requests.get(_JPL_CAD_URL, params=params, timeout=_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()
    fields = payload.get("fields", [])
    return [dict(zip(fields, row)) for row in payload.get("data", [])]


# ── SIMBAD (TAP/ADQL) ────────────────────────────────────────────────────────
_SIMBAD_TAP = "https://simbad.u-strasbg.fr/simbad/sim-tap/sync"

_SIMBAD_OTYPES: dict[str, str] = {
    "galaxy":       "G",
    "nebula":       "PN",   # planetary nebula; broaden with LIKE 'PN%' below
    "star_cluster": "Cl*",
    "variable_star":"V*",
}


def fetch_simbad(slug: str, limit: int = 20) -> list[dict]:
    otype = _SIMBAD_OTYPES.get(slug)
    if not otype:
        raise ValueError(f"No SIMBAD otype for slug {slug!r}")
    adql = (
        f"SELECT TOP {limit} main_id, otype, ra, dec "
        f"FROM basic WHERE otype LIKE '{otype}%'"
    )
    resp = requests.get(
        _SIMBAD_TAP,
        params={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "json", "QUERY": adql},
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    payload = resp.json()
    cols = [c["name"] for c in payload.get("metadata", [])]
    return [dict(zip(cols, row)) for row in payload.get("data", [])]


# ── Routing table ─────────────────────────────────────────────────────────────
def get_data(object_slug: str, date: str | None = None, limit: int = 20) -> list[dict]:
    """
    Fetch observational data for a given object slug.

    Args:
        object_slug: One of the slugs defined in app.object_classes.
        date:        ISO date string (YYYY-MM-DD) used as the query start date
                     where relevant. Defaults to today.
        limit:       Maximum number of records to return.

    Returns:
        List of dicts with source-specific fields.
    """
    celestrak_slugs = {"satellite", "iss", "space_debris", "rocket_body"}
    jpl_slugs = {"asteroid", "comet", "meteor", "meteoroid", "near_earth_object"}
    simbad_slugs = {"galaxy", "nebula", "star_cluster", "variable_star"}

    if object_slug in celestrak_slugs:
        return fetch_celestrak(object_slug, limit)
    if object_slug in jpl_slugs:
        return fetch_jpl(date, limit)
    if object_slug in simbad_slugs:
        return fetch_simbad(object_slug, limit)
    if object_slug == "ufo":
        return []  # no catalogued source — that's the point

    raise ValueError(f"Unknown object slug: {object_slug!r}")
