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

import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

_TIMEOUT = 10  # seconds per request

# CelesTrak returns HTTP 403 ("GP data has not updated since your last
# successful download") when a group is re-fetched inside its 2-hour update
# window. We cache each successful download and fall back to it on any failure,
# so a throttled refresh never empties the scene. Override dir with COSMIC_TLE_CACHE_DIR.
_TLE_CACHE_DIR = Path(os.environ.get("COSMIC_TLE_CACHE_DIR", "data/tle_cache"))
# CelesTrak republishes a group about every 2h; within that, a re-download
# returns the same bytes (or a 403), so serve the cached copy instead.
_TLE_CACHE_TTL_SECONDS = 2 * 60 * 60

# ── CelesTrak ─────────────────────────────────────────────────────────────────
# CelesTrak retired the legacy /pub/TLE/*.txt files (now HTTP 403); use the GP
# query API. There is no generic "debris" or "rocket-bodies" group, so debris is
# sourced from a representative field (Cosmos 2251 collision fragments).
_CELESTRAK_GP = "https://celestrak.org/NORAD/elements/gp.php"
# Each slug maps to an ordered list of candidate queries; the first that returns
# data wins. "active" is the canonical all-satellites catalog but is CelesTrak's
# most heavily throttled group (403 within its 2h update window), so it falls
# back to large subsets — otherwise a cold start during a throttle window shows
# zero satellites.
_CELESTRAK_URLS: dict[str, list[str]] = {
    "satellite": [
        f"{_CELESTRAK_GP}?GROUP=active&FORMAT=tle",
        f"{_CELESTRAK_GP}?GROUP=starlink&FORMAT=tle",
        f"{_CELESTRAK_GP}?GROUP=last-30-days&FORMAT=tle",
    ],
    "iss": [f"{_CELESTRAK_GP}?GROUP=stations&FORMAT=tle"],
    "space_debris": [f"{_CELESTRAK_GP}?GROUP=cosmos-2251-debris&FORMAT=tle"],
    # CelesTrak has no GP group for rocket bodies. They are catalogued with the
    # "R/B" suffix in the object name, so query by NAME instead of GROUP.
    "rocket_body": [f"{_CELESTRAK_GP}?NAME=R/B&FORMAT=tle"],
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
            records.append(
                {
                    "name": name,
                    "catalog_id": l1[2:7].strip(),
                    "epoch": l1[18:32].strip(),
                    "tle_line1": l1,
                    "tle_line2": l2,
                }
            )
            i += 3
        else:
            i += 1
    return records


def _tle_cache_path(slug: str) -> Path:
    return _TLE_CACHE_DIR / f"{slug}.tle"


def _cached_tle_age(path: Path) -> float | None:
    """Seconds since the cache file was written, or None if there isn't one."""
    try:
        return time.time() - path.stat().st_mtime
    except OSError:
        return None


def fetch_celestrak_text(slug: str) -> str:
    """Fetch a CelesTrak group as raw TLE text, cached on disk.

    A cache younger than `_TLE_CACHE_TTL_SECONDS` is served straight from disk:
    CelesTrak only republishes a group every ~2h, so re-downloading per scene
    costs a round trip per group and returns identical bytes. Otherwise each
    candidate query is tried in order and the first success is cached. A stale
    cache still beats nothing, so it is served if every candidate fails
    (notably the 403 CelesTrak returns for an unchanged group).
    Raises only when all candidates fail and no cache exists.
    """
    urls = _CELESTRAK_URLS.get(slug)
    if not urls:
        raise ValueError(f"No CelesTrak URL for slug {slug!r}")
    path = _tle_cache_path(slug)

    age = _cached_tle_age(path)
    if age is not None and age < _TLE_CACHE_TTL_SECONDS:
        return path.read_text()

    for url in urls:
        try:
            resp = requests.get(url, timeout=_TIMEOUT)
            resp.raise_for_status()
        except Exception:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(resp.text)
        return resp.text

    if path.exists():
        return path.read_text()
    raise RuntimeError(f"All CelesTrak sources failed for slug {slug!r}")


def fetch_celestrak(slug: str, limit: int = 20) -> list[dict]:
    return _parse_tle_text(fetch_celestrak_text(slug), limit)


# ── NASA JPL Small-Body Database / CNEOS ─────────────────────────────────────
_JPL_CAD_URL = "https://ssd-api.jpl.nasa.gov/cad.api"

# How far past the requested date to look for close approaches.
_JPL_WINDOW_DAYS = 30


def _jpl_window_end(date: str | None) -> str:
    """Date-max for a window of `_JPL_WINDOW_DAYS` starting at `date`.

    CAD reads a relative date-max ("+30") as an offset from *today*, not from
    date-min, so any date but "now" needs the end spelled out — otherwise a past
    date searches everything up to today and a future one searches nothing.
    """
    relative = f"+{_JPL_WINDOW_DAYS}"
    if not date or date == "now":
        return relative
    try:
        start = datetime.strptime(date[:10], "%Y-%m-%d")
    except ValueError:
        return relative  # let CAD reject the malformed date-min itself
    return (start + timedelta(days=_JPL_WINDOW_DAYS)).strftime("%Y-%m-%d")


def fetch_jpl(date: str | None = None, limit: int = 20) -> list[dict]:
    """Close-approach data from JPL CAD API (covers asteroids, comets, NEOs)."""
    params = {
        "date-min": date or "now",
        "date-max": _jpl_window_end(date),
        "dist-max": "0.2",  # within 0.2 AU
        "sort": "dist",
        "limit": str(limit),
    }
    resp = requests.get(_JPL_CAD_URL, params=params, timeout=_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()
    fields = payload.get("fields", [])
    return [dict(zip(fields, row)) for row in payload.get("data", [])]


# ── SIMBAD (TAP/ADQL) ────────────────────────────────────────────────────────
_SIMBAD_TAP = "https://simbad.u-strasbg.fr/simbad/sim-tap/sync"

_SIMBAD_OTYPES: dict[str, str] = {
    "galaxy": "G",
    "nebula": "PN",  # planetary nebula
    "star_cluster": "Cl*",
    "variable_star": "V*",
    "star": "*",
    "black_hole": "BH",
    "quasar": "QSO",
    "pulsar": "Psr",
    "supernova_remnant": "SNR",
}


def fetch_simbad(slug: str, limit: int = 20) -> list[dict]:
    otype = _SIMBAD_OTYPES.get(slug)
    if not otype:
        raise ValueError(f"No SIMBAD otype for slug {slug!r}")
    # SIMBAD's `otype` column rejects LIKE ("LIKE not supported on otype"); it
    # only supports exact equality, which already matches the type's subtree.
    adql = (
        f"SELECT TOP {limit} main_id, otype, ra, dec "
        f"FROM basic WHERE otype = '{otype}'"
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

    if object_slug in celestrak_slugs:
        return fetch_celestrak(object_slug, limit)
    if object_slug in jpl_slugs:
        return fetch_jpl(date, limit)
    if object_slug in _SIMBAD_OTYPES:  # every SIMBAD-backed deep-space slug
        return fetch_simbad(object_slug, limit)
    if object_slug == "ufo":
        return []  # no catalogued source — that's the point

    raise ValueError(f"Unknown object slug: {object_slug!r}")
