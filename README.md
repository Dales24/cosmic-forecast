# Cosmic Forecast

A prediction system for tracking and forecasting space object trajectories using NASA Earth data. The pipeline classifies objects from telescope image patches (CNN), builds tracks, and predicts future positions via a Transformer + Kalman filter.

## Architecture

```
app/
  api.py          FastAPI backend (API + static file serving)
  object_classifier.py  Patch CNN — classifies object type from image
  track_builder.py      Associates detections into tracks across frames
  trajectory_transformer.py  Transformer model for trajectory forecasting
  kalman_refinement.py  Kalman filter for position uncertainty estimation
  pipeline.py           End-to-end pipeline: CNN → Track → Transformer → Kalman
fe/
  index.html            Static SPA frontend
  static/
    style.css
    app.js              Canvas rendering, sim controls, API calls
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serves the frontend (`fe/index.html`) |
| `GET` | `/static/*` | Static assets (CSS, JS) |
| `GET` | `/api/classify/{id}` | CNN classification for a canvas object |
| `POST` | `/api/forecast` | Linear trajectory extrapolation for tracked objects |

Interactive docs available at `/docs` (FastAPI auto-generated).

## Running

### With Docker (recommended)

```bash
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080).

> **Note:** macOS Monterey+ reserves port 5000 for AirPlay Receiver. The compose file maps host port `8080` → container port `8000` to avoid this.

### Locally

```bash
# Create and activate a virtual environment
pyenv virtualenv 3.12.3 cosmic && pyenv local cosmic

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app.api:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

## Usage

1. **Enter sky coordinates** — Right Ascension, Declination, and an observation date, then click **Load Scene**. The canvas freezes at the orbital positions for that date.
2. **Click any object** — the panel shows its CNN classification, confidence score, and current coordinates.
3. **Press ▶ Play Simulation** — fetches ML-predicted trajectories from the API and fast-forwards the scene at 200× real time, drawing dashed forecast paths for each object.

## Testing

```bash
pytest
```

## Training

To train the CNN classifier on real image patches, organize data under subdirectories named by class slug (see `app/object_classes.py` for slugs) and run:

```bash
python scripts/train_object_classifier.py
```
