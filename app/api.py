import sys
import os

import numpy as np
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


# ── Request models ────────────────────────────────────────────────────────────
class ForecastObject(BaseModel):
    id: int
    positions: list[list[float]]


class ForecastRequest(BaseModel):
    objects: list[ForecastObject]


# ── API routes ────────────────────────────────────────────────────────────────
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
