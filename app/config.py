"""Tunable caps on how many objects each catalog may put into a scene.

One scene pulls from CelesTrak, JPL and SIMBAD; without a cap per kind a single
catalog (the ~11k-satellite CelesTrak "active" group) would swamp the map. Every
cap lives here so they can be read and tuned in one place, and each is
overridable at runtime with ``COSMIC_CAP_<KIND>`` (e.g. ``COSMIC_CAP_GALAXY=12``)
without a code change.
"""

from __future__ import annotations

import os

# Kind -> how many objects that catalog may contribute to a single scene.
_SCENE_CAP_DEFAULTS: dict[str, int] = {
    "satellite": 40,
    "iss": 3,
    "space_debris": 10,
    "rocket_body": 10,
    "near_earth_object": 10,
    "galaxy": 6,
    "nebula": 4,
    "star": 6,
    "black_hole": 2,
    "quasar": 3,
    "pulsar": 2,
    "supernova_remnant": 2,
}

# Default page size for the single-catalog /api/objects endpoint.
_OBJECT_QUERY_DEFAULT = 20


def _env_cap(name: str, default: int) -> int:
    """Read cap `name` from COSMIC_CAP_<NAME>, falling back to `default`.

    A negative override is clamped to 0 (show none of that kind). A
    non-numeric one is a deployment mistake, so it raises rather than silently
    running with a cap nobody chose.
    """
    raw = os.environ.get(f"COSMIC_CAP_{name.upper()}")
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(
            f"COSMIC_CAP_{name.upper()} must be an integer, got {raw!r}"
        ) from None
    return max(0, value)


def scene_cap(kind: str) -> int:
    """Cap for one object kind. Unknown kinds are uncapped-by-absence, i.e. 0."""
    return _env_cap(kind, _SCENE_CAP_DEFAULTS.get(kind, 0))


def scene_caps() -> dict[str, int]:
    """Every scene cap, with overrides applied."""
    return {kind: scene_cap(kind) for kind in _SCENE_CAP_DEFAULTS}


def object_limit() -> int:
    """Default record count for /api/objects when the caller doesn't pass one."""
    return _env_cap("object_query", _OBJECT_QUERY_DEFAULT)
