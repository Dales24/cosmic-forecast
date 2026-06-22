import sys
import os
from datetime import datetime, timezone

import numpy as np
import requests as _requests
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add project root so `app.*` imports work when run from app/ directory
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)

_fe = os.path.join(_root, "fe")

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
_NORM_KM = 42164.0   # GEO distance — normalises LEO at ~0.16, GPS at ~0.63


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
                    dt.year, dt.month, dt.day,
                    dt.hour, dt.minute,
                    dt.second + dt.microsecond / 1e6,
                )
                e, r, v = sat.sgp4(jd, fr)
                if e == 0 and r:
                    results.append({
                        "id":      l1[2:7].strip(),
                        "name":    name,
                        "kind":    kind,
                        "x_norm":  r[0] / _NORM_KM,
                        "y_norm":  r[1] / _NORM_KM,
                        "vx_norm": v[0] / _NORM_KM,
                        "vy_norm": v[1] / _NORM_KM,
                        "source":  "celestrak",
                    })
            except Exception:
                pass
            i += 3
        else:
            i += 1
    return results


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

    # Space stations (ISS etc.)
    try:
        resp = _requests.get(
            "https://celestrak.org/pub/TLE/stations.txt", timeout=8
        )
        resp.raise_for_status()
        objects.extend(_propagate_tles(resp.text, dt, limit=3, kind="iss"))
    except Exception:
        pass

    # Active satellites (fill remaining slots)
    remaining = max(0, limit - len(objects))
    if remaining > 0:
        try:
            resp = _requests.get(
                "https://celestrak.org/pub/TLE/active.txt", timeout=8
            )
            resp.raise_for_status()
            objects.extend(
                _propagate_tles(resp.text, dt, limit=remaining, kind="satellite")
            )
        except Exception:
            pass

    # Unidentified — position intentionally unknown
    objects.append({
        "id":      "UNIDENTIFIED-1",
        "name":    "Unidentified \U0001f47d",
        "kind":    "ufo",
        "x_norm":  0.28,
        "y_norm":  -0.20,
        "vx_norm": 0.0,
        "vy_norm": 0.0,
        "source":  "unknown",
    })

    return {"datetime": dt.isoformat(), "objects": objects}


@app.get("/api/objects/{object_slug}")
def get_objects(object_slug: str, date: str | None = None, limit: int = 20):
    from app.data_parser import get_data
    return {"slug": object_slug, "results": get_data(object_slug, date=date, limit=limit)}


@app.get("/api/classify/{obj_id}")
def classify_object(obj_id: int):
    from app.object_classifier import predict_patch
    cnn = _get_cnn()
    rng = np.random.default_rng(seed=obj_id * 137 + 42)
    patch = rng.integers(0, 255, size=(64, 64, 3), dtype=np.uint8)
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
app.mount("/static", StaticFiles(directory=os.path.join(_fe, "static")), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(_fe, "index.html"))


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.api:app", host=host, port=port, reload=False)
