import sys
import os
from datetime import datetime, timezone
from math import cos, pi, sin

import numpy as np
import requests as _requests
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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
_CELESTRAK_GP = "https://celestrak.org/NORAD/elements/gp.php"


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


# ── Request models ────────────────────────────────────────────────────────────
class ForecastObject(BaseModel):
    id: int
    positions: list[list[float]]


class ForecastRequest(BaseModel):
    objects: list[ForecastObject]


# ── API routes ────────────────────────────────────────────────────────────────
@app.get("/api/scene")
def get_scene(datetime_str: str | None = None, limit: int = 15):
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

    # Space stations (ISS etc.). CelesTrak's legacy /pub/TLE/*.txt files now 403;
    # the GP query API is the supported source.
    stations_url = f"{_CELESTRAK_GP}?GROUP=stations&FORMAT=tle"
    try:
        resp = _requests.get(stations_url, timeout=8)
        resp.raise_for_status()
        objects.extend(_propagate_tles(resp.text, dt, limit=3, kind="iss"))
    except Exception:
        pass

    # Active satellites (fill remaining slots)
    remaining = max(0, limit - len(objects))
    if remaining > 0:
        active_url = f"{_CELESTRAK_GP}?GROUP=active&FORMAT=tle"
        try:
            resp = _requests.get(active_url, timeout=8)
            resp.raise_for_status()
            objects.extend(
                _propagate_tles(resp.text, dt, limit=remaining, kind="satellite")
            )
        except Exception:
            pass

    # Near-Earth objects (JPL CAD) — the user's date drives the approach window.
    objects.extend(_jpl_scene_objects(dt.strftime("%Y-%m-%d"), limit=5))

    # Deep-space catalog objects (SIMBAD) — static over the sim timescale.
    objects.extend(_simbad_scene_objects("galaxy", "galaxy", limit=4))
    objects.extend(_simbad_scene_objects("nebula", "nebula", limit=3))

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

    return {"datetime": dt.isoformat(), "objects": objects}


@app.get("/api/objects/{object_slug}")
def get_objects(object_slug: str, date: str | None = None, limit: int = 20):
    from app.data_parser import get_data

    return {
        "slug": object_slug,
        "results": get_data(object_slug, date=date, limit=limit),
    }


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


# ── Static files + SPA fallback ───────────────────────────────────────────────
app.mount(
    "/static", StaticFiles(directory=os.path.join(_front_end, "static")), name="static"
)


@app.get("/")
def index():
    return FileResponse(os.path.join(_front_end, "index.html"))


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.api:app", host=host, port=port, reload=False)
