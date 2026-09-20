"""JPL Horizons geometric geocentric ICRF vectors (UTC input, km and km/s)."""

import csv
from threading import Lock
from datetime import timezone
from io import StringIO

import numpy as np
import requests

from app.ephemeris import _julian_day

URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
_request_lock = Lock()


def fetch_vectors(command, dates):
    """One bounded request; callers own caching and source-failure reporting."""
    if not dates or len(dates) > 50:
        raise ValueError("Supply between 1 and 50 dates")
    params = {
        "format": "json",
        "COMMAND": f"'{command}'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'VECTORS'",
        "CENTER": "'500@399'",
        "REF_SYSTEM": "'ICRF'",
        "REF_PLANE": "'FRAME'",
        "VEC_CORR": "'NONE'",
        "TIME_TYPE": "'UT'",
        "OUT_UNITS": "'KM-S'",
        "VEC_TABLE": "'2'",
        "CSV_FORMAT": "'YES'",
        "TLIST": "'" + " ".join(str(_julian_day(d)) for d in dates) + "'",
    }
    with _request_lock:
        response = requests.get(URL, params=params, timeout=15)
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result", "")
    if payload.get("error") or "$$SOE" not in result or "$$EOE" not in result:
        raise ValueError("Horizons did not return an unambiguous vector table")
    rows = list(
        csv.reader(StringIO(result.split("$$SOE", 1)[1].split("$$EOE", 1)[0].strip()))
    )
    if len(rows) != len(dates):
        raise ValueError("Unexpected Horizons vector count")
    vectors = []
    for date, row in zip(dates, rows):
        if len(row) < 8 or abs(float(row[0]) - _julian_day(date)) > 1e-6:
            raise ValueError("Horizons vector epoch mismatch")
        vector = np.array([float(value) for value in row[2:8]])
        if not np.isfinite(vector).all() or np.linalg.norm(vector[:3]) == 0:
            raise ValueError("Invalid Horizons vector")
        vectors.append(vector)
    return vectors
