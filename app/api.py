# TensorFlow (imported lazily by the CNN/forecast modules) reaches for the
# stdlib `distutils`, which Python 3.12 removed; importing setuptools first
# restores the compatibility shim. Must precede any tensorflow import.
import setuptools  # noqa: F401

import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import partial
from math import atan2, cos, log10, pi, sin, sqrt

import numpy as np
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import auth, db

# Add project root so `app.*` imports work when run from app/ directory
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)

_front_end = os.path.join(_root, "front_end")

app = FastAPI(title="Cosmic Forecast")

# Compress text responses (JS/CSS/HTML/JSON) over ~1 KB — the 64 KB app.js and
# 21 KB stylesheet shrink by roughly 70% on the wire.
app.add_middleware(GZipMiddleware, minimum_size=1024)


# ── Request metrics (for the admin health monitor) ────────────────────────────
@app.middleware("http")
async def _record_metrics(request, call_next):
    from app.metrics import metrics

    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        metrics.record(
            request.method, request.url.path, 500, (time.perf_counter() - start) * 1000
        )
        raise
    metrics.record(
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - start) * 1000,
    )
    return response


# ── Lazy CNN state ────────────────────────────────────────────────────────────
_cnn_model = None


def _get_cnn():
    global _cnn_model
    if _cnn_model is None:
        from app.object_classifier import (
            create_cnn_model,
            generate_synthetic_dataset,
            train_model,
        )

        # Train once on the synthetic dataset so predictions are actually
        # discriminative — an untrained net collapses to a single class.
        model = create_cnn_model()
        images, labels = generate_synthetic_dataset(samples_per_class=24)
        train_model(model, images, labels, epochs=8)
        _cnn_model = model
    return _cnn_model


# ── Unified scene scale ───────────────────────────────────────────────────────
# Everything shares one map: Earth at the centre (radius 0), the deep sky at the
# rim. Because a LEO satellite and a galaxy can't share a *linear* distance
# scale, the radius grows with the log of geocentric distance, so LEO, GEO, the
# Moon, the planets, and the deep sky fall into successive bands. Direction
# (angle) is always the object's real geocentric right ascension.
_R_INNER = 0.10
_R_OUTER = 0.90
_LOG_D_MIN = log10(6.6e3)  # ~Earth's surface / lowest LEO, km
_LOG_D_MAX = log10(4.6e9)  # ~Neptune at its farthest, km
_DEEP_SKY_RADIUS = 0.95  # galaxies etc.: direction is real, distance is "far"
_AU_KM = 149_597_870.7


def _scene_radius(distance_km: float) -> float:
    """Map a real geocentric distance (km) onto the map's radial scale (log)."""
    if distance_km <= 0:
        return _R_INNER
    frac = (log10(distance_km) - _LOG_D_MIN) / (_LOG_D_MAX - _LOG_D_MIN)
    frac = max(0.0, min(1.0, frac))
    return _R_INNER + frac * (_R_OUTER - _R_INNER)


# ── TLE position propagation ──────────────────────────────────────────────────
def _propagate_tles(tle_text: str, dt: datetime, limit: int, kind: str) -> list[dict]:
    try:
        from sgp4.api import Satrec, jday as sgp4_jday
    except ImportError:
        return []

    lines = [ln.strip() for ln in tle_text.splitlines() if ln.strip()]
    results: list[dict] = []
    i = 0
    while i < len(lines) and len(results) < limit:
        if (
            i + 2 < len(lines)
            and lines[i + 1].startswith("1 ")
            and lines[i + 2].startswith("2 ")
        ):
            name, l1, l2 = lines[i], lines[i + 1], lines[i + 2]
            try:
                sat = Satrec.twoline2rv(l1, l2)
                jd, fr = sgp4_jday(
                    dt.year,
                    dt.month,
                    dt.day,
                    dt.hour,
                    dt.minute,
                    dt.second + dt.microsecond / 1e6,
                )
                err, r, v = sat.sgp4(jd, fr)
                if err == 0 and r:
                    results.append(_tle_scene_object(l1[2:7].strip(), name, kind, r, v))
            except Exception:
                pass
            i += 3
        else:
            i += 1
    return results


def _tle_scene_object(obj_id: str, name: str, kind: str, r, v) -> dict:
    """Place a propagated satellite by real direction + log-scaled distance.

    Angle is the object's real position angle in the equatorial (ECI) plane;
    radius comes from its true geocentric distance. Velocity is expressed as the
    orbit's real angular rate so the animation sweeps it around at the right pace.
    """
    x, y, z = r[0], r[1], r[2]
    distance_km = sqrt(x * x + y * y + z * z)
    angle = atan2(y, x)
    radius = _scene_radius(distance_km)
    r2 = x * x + y * y
    omega = (x * v[1] - y * v[0]) / r2 if r2 else 0.0  # real angular rate, rad/s
    return {
        "id": obj_id,
        "name": name,
        "kind": kind,
        "x_norm": radius * cos(angle),
        "y_norm": radius * sin(angle),
        "vx_norm": -radius * omega * sin(angle),
        "vy_norm": radius * omega * cos(angle),
        "speed_kms": sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2),
        "source": "celestrak",
    }


# ── Near-Earth objects (JPL) ──────────────────────────────────────────────────
# The CAD API gives a real approach distance and speed but no on-sky position,
# so the radius is real (from the distance) while the angle is a deterministic
# placeholder — the one direction we can't source (see docs/known-issues.md).
def _stable_angle(seed: str) -> float:
    """Deterministic angle in radians from a string (Python's hash() is salted)."""
    return (sum(ord(char) for char in seed) % 360) * pi / 180.0


def _jpl_scene_objects(date_str: str, limit: int) -> list[dict]:
    """Near-Earth approaches (JPL CAD) as scene objects for the user's date.

    The approach *distance* is real and sets the object's radius on the shared
    scale; the direction is a deterministic placeholder (CAD gives no position).
    """
    from app.data_parser import fetch_jpl

    try:
        records = fetch_jpl(date_str, limit)
    except Exception:
        return []

    objects: list[dict] = []
    for record in records:
        designation = str(record.get("des", "?"))
        try:
            dist_au = float(record.get("dist", 0.0))
        except (TypeError, ValueError):
            dist_au = 0.0
        try:
            speed_kms = float(record.get("v_rel", 0.0))
        except (TypeError, ValueError):
            speed_kms = 0.0
        angle = _stable_angle(designation)
        radius = _scene_radius(dist_au * _AU_KM)
        objects.append(
            {
                "id": f"NEO-{designation}",
                "name": designation,
                "kind": "near_earth_object",
                "x_norm": radius * cos(angle),
                "y_norm": radius * sin(angle),
                "vx_norm": 0.0,
                "vy_norm": 0.0,
                "speed_kms": speed_kms,
                "source": "jpl",
            }
        )
    return objects


# Deep-space catalogs pulled into every scene (SIMBAD): (slug, kind, limit).
_DEEP_SPACE_SOURCES = [
    ("galaxy", "galaxy", 6),
    ("nebula", "nebula", 4),
    ("star", "star", 6),
    ("black_hole", "black_hole", 2),
    ("quasar", "quasar", 3),
    ("pulsar", "pulsar", 2),
    ("supernova_remnant", "supernova_remnant", 2),
]

# Orbital (TLE) catalogs pulled into every scene from CelesTrak: (slug, kind, limit).
# Satellites use the caller's `limit`; the rest are fixed supporting counts.
_TLE_SCENE_SOURCES = [
    ("space_debris", "space_debris", 10),
    ("rocket_body", "rocket_body", 10),
]


def _celestrak_scene_objects(
    slug: str, kind: str, dt: datetime, limit: int
) -> list[dict]:
    """Fetch a CelesTrak group's TLEs (disk-cached) and propagate them to `dt`."""
    if limit <= 0:
        return []
    from app.data_parser import fetch_celestrak_text

    try:
        tle_text = fetch_celestrak_text(slug)
    except Exception:
        return []
    return _propagate_tles(tle_text, dt, limit=limit, kind=kind)


def _simbad_scene_objects(slug: str, kind: str, limit: int) -> list[dict]:
    """SIMBAD deep-space objects placed by real sky direction.

    Right ascension gives the real angle on the map; the (astronomically vast)
    distance puts them all on the outer sky band, spread slightly by declination.
    They are fixed over the simulation's timescale, so velocity is zero.
    """
    from app.data_parser import fetch_simbad

    try:
        records = fetch_simbad(slug, limit)
    except Exception:
        return []

    objects: list[dict] = []
    for record in records:
        try:
            ra = float(record.get("ra"))
            dec = float(record.get("dec"))
        except (TypeError, ValueError):
            continue
        name = str(record.get("main_id", slug))
        angle = ra * pi / 180.0  # real right ascension
        radius = _DEEP_SKY_RADIUS - (abs(dec) / 90.0) * 0.06  # spread by declination
        objects.append(
            {
                "id": f"{kind}-{name}",
                "name": name,
                "kind": kind,
                "x_norm": radius * cos(angle),
                "y_norm": radius * sin(angle),
                "vx_norm": 0.0,
                "vy_norm": 0.0,
                "speed_kms": 0.0,
                "source": "simbad",
            }
        )
    return objects


# ── Solar-system bodies (real ephemeris) ──────────────────────────────────────
# Real geocentric positions come from app.ephemeris: right ascension gives the
# real angle on the map, distance sets the radius on the shared scale. `speed_kms`
# is the mean orbital speed shown in the panel.
# Each row: (name, speed_kms, description).
_PLANETS = [
    (
        "Mercury",
        47.4,
        "Smallest planet and closest to the Sun; a cratered, airless world of extreme temperature swings.",
    ),  # noqa: E501
    (
        "Venus",
        35.0,
        "A runaway greenhouse under thick clouds of sulfuric acid — the hottest surface in the solar system.",
    ),  # noqa: E501
    (
        "Mars",
        24.1,
        "The red planet; a cold desert world with the tallest volcano and deepest canyon in the solar system.",
    ),  # noqa: E501
    (
        "Jupiter",
        13.1,
        "Largest planet; a gas giant with a centuries-old storm, the Great Red Spot, and dozens of moons.",
    ),  # noqa: E501
    (
        "Saturn",
        9.7,
        "A gas giant famed for its brilliant, wide ring system of ice and rock.",
    ),  # noqa: E501
    (
        "Uranus",
        6.8,
        "An ice giant tipped on its side, orbiting the Sun at a near-right angle.",
    ),  # noqa: E501
    (
        "Neptune",
        5.4,
        "The farthest planet; a deep-blue ice giant with the fastest winds in the solar system.",
    ),  # noqa: E501
]


def _radec_scene_xy(ra_rad: float, distance_km: float) -> tuple[float, float]:
    """Scene x/y for a body at a real right ascension and geocentric distance."""
    radius = _scene_radius(distance_km)
    return radius * cos(ra_rad), radius * sin(ra_rad)


def _planet_scene_objects(dt: datetime) -> list[dict]:
    """The planets at their real geocentric positions for `dt`."""
    from app import ephemeris

    objects: list[dict] = []
    for name, speed_kms, description in _PLANETS:
        ra, dist_km = ephemeris.planet_geocentric(name.lower(), dt)
        x_norm, y_norm = _radec_scene_xy(ra, dist_km)
        objects.append(
            {
                "id": f"planet-{name}",
                "name": name,
                "kind": "planet",
                "x_norm": x_norm,
                "y_norm": y_norm,
                "vx_norm": 0.0,
                "vy_norm": 0.0,
                "speed_kms": speed_kms,
                "source": "ephemeris",
                "description": description,
            }
        )
    return objects


def _sun_scene_object(dt: datetime) -> dict:
    """The Sun at its real geocentric position for `dt`."""
    from app import ephemeris

    x_norm, y_norm = _radec_scene_xy(*ephemeris.sun_geocentric(dt))
    return {
        "id": "body-Sun",
        "name": "Sun",
        "kind": "sun",
        "x_norm": x_norm,
        "y_norm": y_norm,
        "vx_norm": 0.0,
        "vy_norm": 0.0,
        "speed_kms": 0.0,
        "source": "ephemeris",
        "description": (
            "The star at the heart of the solar system; its fusion powers the "
            "light and warmth that make Earth habitable."
        ),
    }


def _moon_scene_object(dt: datetime) -> dict:
    """The Moon at its real geocentric position for `dt`."""
    from app import ephemeris

    x_norm, y_norm = _radec_scene_xy(*ephemeris.moon_geocentric(dt))
    return {
        "id": "body-Moon",
        "name": "Moon",
        "kind": "moon",
        "x_norm": x_norm,
        "y_norm": y_norm,
        "vx_norm": 0.0,
        "vy_norm": 0.0,
        "speed_kms": 1.022,
        "source": "ephemeris",
        "description": (
            "Earth's only natural satellite; its gravity drives the ocean tides "
            "and it always shows us the same face."
        ),
    }


def _earth_scene_object() -> dict:
    """Earth, the observer, fixed at the centre of the map."""
    return {
        "id": "body-Earth",
        "name": "Earth",
        "kind": "earth",
        "x_norm": 0.0,
        "y_norm": 0.0,
        "vx_norm": 0.0,
        "vy_norm": 0.0,
        "speed_kms": 0.0,
        "source": "ephemeris",
        "description": (
            "Our home planet and the observer's vantage point — the map is drawn "
            "as the sky seen from here."
        ),
    }


# ── Request models ────────────────────────────────────────────────────────────
class ForecastObject(BaseModel):
    id: int
    positions: list[list[float]]


class ForecastRequest(BaseModel):
    objects: list[ForecastObject]


# ── API routes ────────────────────────────────────────────────────────────────
# Scenes hit slow external catalogs, so cache each (datetime, limit) result for a
# short window — repeated loads (panning, re-opening) skip the network entirely.
_SCENE_TTL_SECONDS = 45.0
_scene_cache: dict[tuple, tuple[float, dict]] = {}


def _clear_scene_cache() -> None:
    _scene_cache.clear()


@app.get("/api/scene")
def get_scene(datetime_str: str | None = None, limit: int = 40):
    cache_key = (datetime_str, limit)
    cached = _scene_cache.get(cache_key)
    if cached and (time.time() - cached[0]) < _SCENE_TTL_SECONDS:
        return cached[1]

    if datetime_str:
        try:
            dt = datetime.fromisoformat(datetime_str.replace("Z", "+00:00"))
        except ValueError:
            dt = datetime.now(timezone.utc)
    else:
        dt = datetime.now(timezone.utc)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    objects: list[dict] = []

    # All sources are independent, so fetch them concurrently — scene latency
    # becomes the slowest single source, not the sum of all of them. Orbital
    # (CelesTrak TLE) legs: stations + satellites + debris + rocket bodies;
    # plus JPL near-Earth and one SIMBAD query per deep-space type.
    date_str = dt.strftime("%Y-%m-%d")
    tasks = [
        partial(_celestrak_scene_objects, "iss", "iss", dt, 3),
        partial(_celestrak_scene_objects, "satellite", "satellite", dt, limit),
        partial(_jpl_scene_objects, date_str, 10),
    ]
    tasks += [
        partial(_celestrak_scene_objects, slug, kind, dt, lim)
        for slug, kind, lim in _TLE_SCENE_SOURCES
    ]
    tasks += [
        partial(_simbad_scene_objects, slug, kind, lim)
        for slug, kind, lim in _DEEP_SPACE_SOURCES
    ]
    with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
        for result in pool.map(lambda fetch: fetch(), tasks):
            objects.extend(result)

    # Solar-system bodies at their real positions — local, no network.
    objects.append(_earth_scene_object())
    objects.append(_sun_scene_object(dt))
    objects.append(_moon_scene_object(dt))
    objects.extend(_planet_scene_objects(dt))

    # Unidentified — position intentionally unknown
    objects.append(
        {
            "id": "UNIDENTIFIED-1",
            "name": "Unidentified \U0001f47d",
            "kind": "ufo",
            "x_norm": 0.28,
            "y_norm": -0.20,
            "vx_norm": 0.0,
            "vy_norm": 0.0,
            "speed_kms": 0.0,
            "source": "unknown",
        }
    )

    result = {"datetime": dt.isoformat(), "objects": objects}
    _scene_cache[cache_key] = (time.time(), result)
    return result


@app.get("/api/objects/{object_slug}")
def get_objects(object_slug: str, date: str | None = None, limit: int = 20):
    from app.data_parser import get_data

    try:
        results = get_data(object_slug, date=date, limit=limit)
    except ValueError as exc:
        # Unknown slug — a client error, not an upstream failure.
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        # A single external source (CelesTrak/JPL/SIMBAD) failing must not 500
        # the endpoint; degrade to an empty result the UI can handle.
        return {"slug": object_slug, "results": [], "error": "source_unavailable"}

    return {"slug": object_slug, "results": results}


@app.get("/api/classify/{obj_id}")
def classify_object(obj_id: int, kind: str | None = None):
    from app.object_classes import SLUG_TO_INDEX
    from app.object_classifier import predict_patch, synthetic_patch

    cnn = _get_cnn()
    if kind in SLUG_TO_INDEX:
        # Classify a patch characteristic of the clicked object's kind, so the
        # result matches what was clicked instead of being arbitrary noise.
        patch = synthetic_patch(kind, seed=obj_id)
    else:
        rng = np.random.default_rng(seed=obj_id * 137 + 42)
        patch = rng.integers(0, 255, size=(64, 64, 3), dtype=np.uint8)
    return predict_patch(cnn, patch)


@app.post("/api/upload/csv")
async def upload_csv(file: UploadFile = File(...)):
    import csv
    import io as _io
    from app.trajectory_transformer import linear_extrapolation

    text = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(_io.StringIO(text))

    # Required columns
    required = {"id", "x", "y", "timestamp"}
    if not reader.fieldnames or not required.issubset(
        {f.strip().lower() for f in reader.fieldnames}
    ):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail=f"CSV must have columns: {', '.join(sorted(required))}",
        )

    # Normalise header names
    norm = {f.strip(): f.strip().lower() for f in reader.fieldnames}

    groups: dict[str, dict] = {}
    for raw in reader:
        row = {norm.get(k, k.strip().lower()): v.strip() for k, v in raw.items()}
        obj_id = row.get("id", "").strip()
        if not obj_id:
            continue
        if obj_id not in groups:
            groups[obj_id] = {
                "id": obj_id,
                "name": row.get("name", obj_id),
                "kind": row.get("kind", "ufo"),
                "positions": [],
            }
        try:
            groups[obj_id]["positions"].append(
                [float(row["x"]), float(row["y"]), float(row["timestamp"])]
            )
        except (KeyError, ValueError):
            continue

    scene_objects: list[dict] = []
    predictions: list[dict] = []

    for idx, obj_data in enumerate(groups.values()):
        pts = sorted(obj_data["positions"], key=lambda p: p[2])
        if len(pts) < 2:
            continue

        x_now, y_now, _ = pts[-1]
        x_prev, y_prev, t_prev = pts[-2]
        x_curr, y_curr, t_curr = pts[-1]
        dt = t_curr - t_prev
        vx = (x_curr - x_prev) / dt if dt > 0 else 0.0
        vy = (y_curr - y_prev) / dt if dt > 0 else 0.0

        scene_objects.append(
            {
                "id": obj_data["id"],
                "name": obj_data["name"],
                "kind": obj_data["kind"],
                "x_norm": x_now,
                "y_norm": y_now,
                "vx_norm": vx,
                "vy_norm": vy,
                "source": "upload",
            }
        )

        pos_arr = np.array(pts, dtype=np.float32)
        forecast = linear_extrapolation(pos_arr, horizon=50)
        predictions.append({"id": idx, "waypoints": forecast[:, :2].tolist()})

    return {"objects": scene_objects, "predictions": predictions}


@app.post("/api/classify/upload")
async def classify_upload(file: UploadFile = File(...)):
    import io
    from PIL import Image

    contents = await file.read()
    img = Image.open(io.BytesIO(contents)).convert("RGB")
    patch = np.array(img.resize((64, 64)), dtype=np.uint8)
    from app.object_classifier import predict_patch

    cnn = _get_cnn()
    return predict_patch(cnn, patch)


@app.post("/api/forecast")
def api_forecast(body: ForecastRequest):
    from app.trajectory_transformer import linear_extrapolation

    predictions = []
    for obj in body.objects:
        positions = np.array(obj.positions, dtype=np.float32)
        if len(positions) < 2:
            continue
        forecast = linear_extrapolation(positions, horizon=50)
        predictions.append({"id": obj.id, "waypoints": forecast[:, :2].tolist()})
    return {"predictions": predictions}


# ── Auth + saved work ─────────────────────────────────────────────────────────
class RegisterIn(BaseModel):
    username: str
    password: str
    email: str | None = None


class LoginIn(BaseModel):
    username: str
    password: str


class SearchIn(BaseModel):
    name: str
    params: dict


class UploadIn(BaseModel):
    filename: str
    result: dict
    kind: str | None = None


class PreferencesIn(BaseModel):
    theme: str


class CustomObjectIn(BaseModel):
    name: str
    kind: str
    x_norm: float
    y_norm: float


def _public_user(user) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "theme": user["theme"],
        "is_admin": bool(user["is_admin"]),
    }


@app.post("/api/auth/register")
def api_register(body: RegisterIn):
    return auth.register(body.username, body.password, body.email)


@app.post("/api/auth/login")
def api_login(body: LoginIn):
    token = auth.login(body.username, body.password)
    return {"token": token, "username": body.username.strip()}


@app.post("/api/auth/logout", status_code=204)
def api_logout(authorization: str = Header(default="")):
    auth.logout(auth.bearer_token(authorization))


@app.get("/api/auth/me")
def api_me(user=Depends(auth.current_user)):
    return _public_user(user)


@app.put("/api/preferences")
def api_set_preferences(body: PreferencesIn, user=Depends(auth.current_user)):
    """Save the user's current UI theme as their profile default."""
    theme = body.theme.strip()
    if not theme:
        raise HTTPException(422, "theme must not be empty")
    db.set_user_theme(user["id"], theme)
    return {"theme": theme}


@app.get("/api/searches")
def api_list_searches(user=Depends(auth.current_user)):
    return {"searches": db.list_searches(user["id"])}


@app.post("/api/searches")
def api_save_search(body: SearchIn, user=Depends(auth.current_user)):
    return {"id": db.add_search(user["id"], body.name, body.params)}


@app.delete("/api/searches/{search_id}", status_code=204)
def api_delete_search(search_id: int, user=Depends(auth.current_user)):
    if not db.delete_search(user["id"], search_id):
        raise HTTPException(404, "search not found")


@app.get("/api/uploads")
def api_list_uploads(user=Depends(auth.current_user)):
    return {"uploads": db.list_uploads(user["id"])}


@app.post("/api/uploads")
def api_save_upload(body: UploadIn, user=Depends(auth.current_user)):
    return {"id": db.add_upload(user["id"], body.filename, body.kind, body.result)}


@app.delete("/api/uploads/{upload_id}", status_code=204)
def api_delete_upload(upload_id: int, user=Depends(auth.current_user)):
    if not db.delete_upload(user["id"], upload_id):
        raise HTTPException(404, "upload not found")


# ── User-added scene objects ──────────────────────────────────────────────────
def _valid_kind(kind: str) -> bool:
    from app.object_classes import CLASS_SLUGS

    return kind in CLASS_SLUGS


@app.get("/api/custom-objects")
def api_list_custom_objects(user=Depends(auth.current_user)):
    return {"objects": db.list_custom_objects(user["id"])}


@app.post("/api/custom-objects")
def api_add_custom_object(body: CustomObjectIn, user=Depends(auth.current_user)):
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "name must not be empty")
    if not _valid_kind(body.kind):
        raise HTTPException(422, f"unknown kind: {body.kind!r}")
    # Clamp to the map so a bad value can't fling an object off-screen.
    x = max(-1.5, min(1.5, body.x_norm))
    y = max(-1.5, min(1.5, body.y_norm))
    object_id = db.add_custom_object(user["id"], name, body.kind, x, y)
    return {
        "id": object_id,
        "name": name,
        "kind": body.kind,
        "x_norm": x,
        "y_norm": y,
        "vx_norm": 0.0,
        "vy_norm": 0.0,
        "speed_kms": 0.0,
        "source": "custom",
    }


@app.delete("/api/custom-objects/{object_id}", status_code=204)
def api_delete_custom_object(object_id: int, user=Depends(auth.current_user)):
    if not db.delete_custom_object(user["id"], object_id):
        raise HTTPException(404, "custom object not found")


# ── Admin: API health monitor ─────────────────────────────────────────────────
def _probe_sources() -> dict:
    """Live reachability check of the external data sources (short timeouts)."""
    import requests

    checks = {
        "celestrak": "https://celestrak.org/NORAD/elements/gp.php"
        "?GROUP=stations&FORMAT=tle",
        "jpl": "https://ssd-api.jpl.nasa.gov/cad.api"
        "?date-min=now&date-max=%2B1&dist-max=0.05&limit=1",
        "simbad": "https://simbad.u-strasbg.fr/simbad/sim-tap/sync"
        "?REQUEST=doQuery&LANG=ADQL&FORMAT=json&QUERY=SELECT+TOP+1+main_id+FROM+basic",
    }
    out: dict = {}
    for name, url in checks.items():
        start = time.perf_counter()
        try:
            resp = requests.get(url, timeout=6)
            out[name] = {
                "ok": resp.ok,
                "status": resp.status_code,
                "latency_ms": round((time.perf_counter() - start) * 1000, 1),
            }
        except Exception as exc:
            out[name] = {
                "ok": False,
                "status": None,
                "error": type(exc).__name__,
                "latency_ms": round((time.perf_counter() - start) * 1000, 1),
            }
    return out


@app.get("/api/admin/health")
def api_admin_health(check_sources: bool = False, user=Depends(auth.require_admin)):
    from app.metrics import metrics

    data = metrics.snapshot()
    if check_sources:
        data["sources"] = _probe_sources()
    return data


def _ensure_admin_user() -> None:
    """Dev convenience: a default admin/admin login, created if it's missing.

    Bypasses the normal password-length rule on purpose — replace with a real
    admin before any real deployment.
    """
    if db.get_user_by_username("admin"):
        return
    pw_hash, salt = auth.hash_password("admin")
    db.create_user("admin", None, pw_hash, salt, is_admin=True)


@app.on_event("startup")
def _bootstrap_admin() -> None:
    _ensure_admin_user()


# ── Static files + SPA fallback ───────────────────────────────────────────────
_STATIC_MAX_AGE = 3600  # 1 hour; StaticFiles' ETag still forces revalidation after.


class _CachedStaticFiles(StaticFiles):
    """StaticFiles that lets browsers cache assets instead of refetching every load."""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers.setdefault(
            "Cache-Control", f"public, max-age={_STATIC_MAX_AGE}"
        )
        return response


app.mount(
    "/static",
    _CachedStaticFiles(directory=os.path.join(_front_end, "static")),
    name="static",
)


@app.get("/")
def index():
    return FileResponse(os.path.join(_front_end, "index.html"))


@app.get("/help")
def help_page():
    return FileResponse(os.path.join(_front_end, "help.html"))


@app.get("/profile")
def profile_page():
    return FileResponse(os.path.join(_front_end, "profile.html"))


@app.get("/admin")
def admin_page():
    return FileResponse(os.path.join(_front_end, "admin.html"))


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.api:app", host=host, port=port, reload=False)
