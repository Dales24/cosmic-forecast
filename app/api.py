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
from math import cos, log, pi, sin

import numpy as np
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
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

# ── Lazy CNN state ────────────────────────────────────────────────────────────
_cnn_model = None


def _get_cnn():
    global _cnn_model
    if _cnn_model is None:
        from app.object_classifier import create_cnn_model

        _cnn_model = create_cnn_model()
    return _cnn_model


# ── TLE position propagation ──────────────────────────────────────────────────
_NORM_KM = 42164.0  # GEO distance — normalises LEO at ~0.16, GPS at ~0.63


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
                e, r, v = sat.sgp4(jd, fr)
                if e == 0 and r:
                    results.append(
                        {
                            "id": l1[2:7].strip(),
                            "name": name,
                            "kind": kind,
                            "x_norm": r[0] / _NORM_KM,
                            "y_norm": r[1] / _NORM_KM,
                            "vx_norm": v[0] / _NORM_KM,
                            "vy_norm": v[1] / _NORM_KM,
                            "source": "celestrak",
                        }
                    )
            except Exception:
                pass
            i += 3
        else:
            i += 1
    return results


# ── Catalog objects (JPL / SIMBAD) ────────────────────────────────────────────
# These sources don't share the TLE orbital frame, so scene positions are
# symbolic, not astrometric (see docs/known-issues.md).
def _stable_angle(seed: str) -> float:
    """Deterministic angle in radians from a string (Python's hash() is salted)."""
    return (sum(ord(char) for char in seed) % 360) * pi / 180.0


def _jpl_scene_objects(date_str: str, limit: int) -> list[dict]:
    """Near-Earth approaches (JPL CAD) as scene objects for the user's date.

    CAD gives approach distance/velocity but no on-sky position, so each object
    is placed symbolically: distance sets an outer-ring radius, a stable hash of
    the designation sets the angle.
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
        angle = _stable_angle(designation)
        radius = 0.6 + min(dist_au / 0.2, 1.0) * 0.35  # 0.2 AU = CAD dist-max
        objects.append(
            {
                "id": f"NEO-{designation}",
                "name": designation,
                "kind": "near_earth_object",
                "x_norm": radius * cos(angle),
                "y_norm": radius * sin(angle),
                "vx_norm": 0.0,
                "vy_norm": 0.0,
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
    """SIMBAD deep-space objects placed by sky coordinates (RA/Dec).

    RA (0–360°) maps to x and Dec (−90–90°) to y. These objects are fixed over
    the simulation's timescale, so velocity is zero.
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
        objects.append(
            {
                "id": f"{kind}-{name}",
                "name": name,
                "kind": kind,
                "x_norm": (ra / 180.0 - 1.0) * 0.9,
                "y_norm": (dec / 90.0) * 0.9,
                "vx_norm": 0.0,
                "vy_norm": 0.0,
                "source": "simbad",
            }
        )
    return objects


# ── Solar-system planets ──────────────────────────────────────────────────────
# Real orbital data for the planets (Earth is omitted — it's the scene centre).
# `a_au` (semi-major axis) sets the ring radius, `period_days` drives the angle
# over the scene's date, `v_kms` is the mean orbital velocity shown in the panel.
# Positions are representative (one ring per orbit), matching how JPL/SIMBAD
# objects are placed.
# Each row: (name, a_au, period_days, v_kms, description).
_PLANETS = [
    (
        "Mercury",
        0.387,
        88.0,
        47.4,
        "Smallest planet and closest to the Sun; a cratered, airless world of extreme temperature swings.",
    ),
    (
        "Venus",
        0.723,
        224.7,
        35.0,
        "Second planet; a runaway greenhouse under thick clouds of sulfuric acid, hottest surface in the solar system.",
    ),
    (
        "Mars",
        1.524,
        687.0,
        24.1,
        "The red planet; a cold desert world with the tallest volcano and deepest canyon in the solar system.",
    ),
    (
        "Jupiter",
        5.203,
        4331.0,
        13.1,
        "Largest planet; a gas giant with a centuries-old storm, the Great Red Spot, and dozens of moons.",
    ),
    (
        "Saturn",
        9.537,
        10747.0,
        9.7,
        "Sixth planet; a gas giant famed for its brilliant, wide ring system of ice and rock.",
    ),
    (
        "Uranus",
        19.19,
        30589.0,
        6.8,
        "Seventh planet; an ice giant tipped on its side, orbiting the Sun at a near-right angle.",
    ),
    (
        "Neptune",
        30.07,
        59800.0,
        5.4,
        "Farthest planet; a deep-blue ice giant with the fastest winds in the solar system.",
    ),
]

# Log-radius mapping so all orbits (0.39 AU .. 30 AU) fit the visible ring band.
_PLANET_EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)
_PLANET_RING_MIN, _PLANET_RING_MAX = 0.30, 0.94
_PLANET_AU_MIN, _PLANET_AU_MAX = 0.387, 30.07


def _planet_ring_radius(a_au: float) -> float:
    """Map a planet's orbital distance (AU) onto the scene's ring band (log scale)."""
    span = log(_PLANET_AU_MAX) - log(_PLANET_AU_MIN)
    frac = (log(a_au) - log(_PLANET_AU_MIN)) / span
    return _PLANET_RING_MIN + frac * (_PLANET_RING_MAX - _PLANET_RING_MIN)


def _planet_scene_objects(dt: datetime) -> list[dict]:
    """The planets, placed on their orbital rings at an angle set by `dt`."""
    days = (dt - _PLANET_EPOCH).total_seconds() / 86400.0
    objects: list[dict] = []
    for index, (name, a_au, period_days, v_kms, description) in enumerate(_PLANETS):
        # Spread starting longitudes so planets don't line up on a single spoke.
        angle = index * (2 * pi / len(_PLANETS)) + 2 * pi * (days / period_days)
        radius = _planet_ring_radius(a_au)
        v_norm = v_kms / _NORM_KM  # panel converts back to km/s
        objects.append(
            {
                "id": f"planet-{name}",
                "name": name,
                "kind": "planet",
                "x_norm": radius * cos(angle),
                "y_norm": radius * sin(angle),
                "vx_norm": -v_norm * sin(angle),  # tangential to the orbit
                "vy_norm": v_norm * cos(angle),
                "source": "solar_system",
                "description": description,
            }
        )
    return objects


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

    # Solar-system planets — local, no network, so added directly.
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
def classify_object(obj_id: int):
    from app.object_classifier import predict_patch

    cnn = _get_cnn()
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


def _public_user(user) -> dict:
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "theme": user["theme"],
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


# ── Static files + SPA fallback ───────────────────────────────────────────────
app.mount(
    "/static", StaticFiles(directory=os.path.join(_front_end, "static")), name="static"
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


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.api:app", host=host, port=port, reload=False)
