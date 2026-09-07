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
import tempfile
import math
import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from app.cache_lock import KeyLocks

import requests

_TIMEOUT = 10  # seconds per request

# CelesTrak returns HTTP 403 ("GP data has not updated since your last
# successful download") when a group is re-fetched inside its 2-hour update
# window. Keep validated downloads with a bounded fallback age.
# Override the directory with COSMIC_TLE_CACHE_DIR.
_TLE_CACHE_DIR = Path(os.environ.get("COSMIC_TLE_CACHE_DIR", "data/tle_cache"))
# CelesTrak republishes a group about every 2h; within that, a re-download
# returns the same bytes (or a 403), so serve the cached copy instead.
_TLE_CACHE_TTL_SECONDS = 2 * 60 * 60
_TLE_MAX_STALE_SECONDS = 24 * 60 * 60
_TLE_RETRY_SECONDS = 30
_tle_locks = KeyLocks()
_tle_memory = {}
_tle_retry = {}


class TLEText(str):
    """String-compatible text carrying the exact cached download's metadata."""

    def __new__(cls, text, downloaded_at, oldest_epoch, coverage=None):
        value = super().__new__(cls, text)
        age = max(0, time.time() - downloaded_at)
        value.freshness = {
            "downloaded_at": downloaded_at,
            "oldest_epoch": oldest_epoch,
            "stale": age >= _TLE_CACHE_TTL_SECONDS,
            "valid_until": downloaded_at + _TLE_MAX_STALE_SECONDS,
        }
        value.coverage = coverage
        return value


def _validate_tle(text):
    """Reject incomplete/non-numeric records before replacing a good download."""
    from sgp4.api import Satrec

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or len(lines) % 3:
        raise ValueError("Incomplete TLE response")
    epochs = []
    for offset in range(0, len(lines), 3):
        name, first, second = lines[offset : offset + 3]
        if (
            len(first) != 69
            or len(second) != 69
            or not first.startswith("1 ")
            or not second.startswith("2 ")
            or first[2:7] != second[2:7]
        ):
            raise ValueError("Malformed TLE response")
        year = int(first[18:20])
        day = float(first[20:32])
        if not 1 <= day < 367:
            raise ValueError("Invalid TLE epoch")
        for field in (
            second[8:16],
            second[17:25],
            second[34:42],
            second[43:51],
            second[52:63],
        ):
            if not math.isfinite(float(field)):
                raise ValueError("Non-finite orbital elements")
        int(second[26:33])
        sat = Satrec.twoline2rv(first, second)
        if sat.error or sat.no_kozai <= 0:
            raise ValueError("Invalid orbital elements")
        epoch = datetime(2000 + year if year < 57 else 1900 + year, 1, 1)
        epochs.append((epoch + timedelta(days=day - 1)).isoformat() + "Z")
    return min(epochs)


# ── CelesTrak ─────────────────────────────────────────────────────────────────
# CelesTrak retired the legacy /pub/TLE/*.txt files (now HTTP 403); use the GP
# query API. CelesTrak exposes major debris events as separate groups.
_CELESTRAK_GP = "https://celestrak.org/NORAD/elements/gp.php"
DEBRIS_FIELDS = {
    "all": {
        "label": "All supported debris fields",
        "groups": ("cosmos-2251", "iridium-33", "fengyun-1c"),
    },
    "cosmos-2251": {"label": "Cosmos 2251 debris", "groups": ("cosmos-2251",)},
    "iridium-33": {"label": "Iridium 33 debris", "groups": ("iridium-33",)},
    "fengyun-1c": {"label": "Fengyun 1C debris", "groups": ("fengyun-1c",)},
}
DEFAULT_DEBRIS_FIELD = "all"
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
    # Keep the public object endpoint backward-compatible while scene requests
    # use the field-specific cache keys below.
    "space_debris": [f"{_CELESTRAK_GP}?GROUP=cosmos-2251-debris&FORMAT=tle"],
    "space_debris_cosmos_2251": [
        f"{_CELESTRAK_GP}?GROUP=cosmos-2251-debris&FORMAT=tle"
    ],
    "space_debris_iridium_33": [f"{_CELESTRAK_GP}?GROUP=iridium-33-debris&FORMAT=tle"],
    "space_debris_fengyun_1c": [f"{_CELESTRAK_GP}?GROUP=fengyun-1c-debris&FORMAT=tle"],
    # CelesTrak has no GP group for rocket bodies. They are catalogued with the
    # "R/B" suffix in the object name, so query by NAME instead of GROUP.
    "rocket_body": [f"{_CELESTRAK_GP}?NAME=R/B&FORMAT=tle"],
}


def debris_cache_slug(group: str) -> str:
    """Return the safe, field-specific cache slug for a CelesTrak group."""
    return "space_debris_" + group.replace("-", "_")


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


def _tle_metadata_path(slug: str) -> Path:
    return _TLE_CACHE_DIR / f"{slug}.json"


def _query_name(url: str) -> str:
    query = parse_qs(urlparse(url).query)
    return (query.get("GROUP") or query.get("NAME") or ["unknown"])[0]


def _query_label(query: str) -> str:
    return {
        "active": "Active satellites",
        "starlink": "Starlink subset",
        "last-30-days": "Last 30 days subset",
    }.get(query, query)


def _read_tle_metadata(slug: str) -> dict:
    try:
        return json.loads(_tle_metadata_path(slug).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {
            "selected_query": "unknown",
            "selected_label": "Cached source (query unknown)",
            "fallback": None,
            "failed_attempts": [],
        }


def _write_tle_metadata(slug: str, metadata: dict) -> None:
    path = _tle_metadata_path(slug)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as output:
            temporary = Path(output.name)
            json.dump(metadata, output)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _record_candidate_failure(slug: str, query: str, exc: Exception) -> None:
    from app.metrics import source_failures

    source_failures.record("celestrak", f"{slug}:{query}", str(exc))


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
    candidate query is validated and atomically cached. Failed refreshes retry
    after 30 seconds and may use a validated download less than 24 hours old.
    Same-slug misses share a refresh within this process; unchanged disk files
    reuse parsed metadata in memory. Raises if no usable download remains.
    """
    urls = _CELESTRAK_URLS.get(slug)
    if not urls:
        raise ValueError(f"No CelesTrak URL for slug {slug!r}")
    with _tle_locks.hold(slug):
        path = _tle_cache_path(slug)
        cached = None
        try:
            stat = path.stat()
            signature = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
            memory = _tle_memory.get(slug)
            if memory and memory[0] == signature:
                text, epoch, coverage = memory[1:]
            else:
                text = path.read_text()
                epoch = _validate_tle(text)
                coverage = _read_tle_metadata(slug)
                _tle_memory[slug] = (signature, text, epoch, coverage)
            cached = TLEText(text, stat.st_mtime, epoch, coverage)
        except (OSError, ValueError):
            pass
        if cached and not cached.freshness["stale"]:
            return cached
        retry_path, retry_at = _tle_retry.get(slug, (None, 0))
        failed_attempts = []
        if retry_path != str(path.resolve()) or time.monotonic() >= retry_at:
            for candidate_index, url in enumerate(urls):
                query = _query_name(url)
                try:
                    resp = requests.get(url, timeout=_TIMEOUT)
                    resp.raise_for_status()
                    epoch = _validate_tle(resp.text)
                except Exception as exc:
                    failed_attempts.append({"query": query, "error": str(exc)})
                    _record_candidate_failure(slug, query, exc)
                    continue
                coverage = {
                    "selected_query": query,
                    "selected_label": _query_label(query),
                    "fallback": candidate_index > 0,
                    "failed_attempts": failed_attempts,
                }
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(
                        mode="w",
                        encoding="utf-8",
                        dir=path.parent,
                        suffix=".tmp",
                        delete=False,
                    ) as output:
                        temporary = Path(output.name)
                        output.write(resp.text)
                    os.replace(temporary, path)
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
                stat = path.stat()
                signature = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
                _write_tle_metadata(slug, coverage)
                _tle_memory[slug] = (signature, resp.text, epoch, coverage)
                _tle_retry.pop(slug, None)
                return TLEText(resp.text, stat.st_mtime, epoch, coverage)
            _tle_retry[slug] = (
                str(path.resolve()),
                time.monotonic() + _TLE_RETRY_SECONDS,
            )
        if cached and time.time() < cached.freshness["valid_until"]:
            if failed_attempts:
                cached.coverage = {
                    **(cached.coverage or {}),
                    "refresh_failed_attempts": failed_attempts,
                }
            return cached
        raise RuntimeError(
            f"All CelesTrak sources failed for slug {slug!r}; no usable cache"
        )


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
