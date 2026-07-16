# Cosmic Forecast 👽

A prediction system for tracking and forecasting space object trajectories. The pipeline classifies objects from telescope image patches (CNN), builds tracks across frames, and predicts future positions via a Transformer + Kalman filter. Live object data is pulled from CelesTrak, NASA JPL, and SIMBAD.

## Architecture

```
app/
  api.py                     FastAPI backend — API routes + static file serving
  data_parser.py             Real data fetchers (CelesTrak / JPL / SIMBAD)
  object_classifier.py       Patch CNN — classifies object type from image patch
  object_classes.py          Object type definitions and slugs
  track_builder.py           Associates detections into tracks across frames
  trajectory_transformer.py  Transformer model for trajectory forecasting
  kalman_refinement.py       Kalman filter for position + uncertainty estimation
  pipeline.py                End-to-end: CNN → Track → Transformer → Kalman
front_end/
  index.html                 Static SPA (no server-side rendering)
  static/
    style.css
    app.js                   Canvas rendering, sim controls, API calls
```

## Data Sources

| Object type   | Source              | Endpoint |
|---------------|---------------------|----------|
| Satellite     | CelesTrak (TLE)     | `/api/objects/satellite` |
| ISS           | CelesTrak (TLE)     | `/api/objects/iss` |
| Space debris  | CelesTrak (TLE)     | `/api/objects/space_debris` |
| Rocket body   | CelesTrak (TLE)     | `/api/objects/rocket_body` |
| Asteroid      | NASA JPL SBDB       | `/api/objects/asteroid` |
| Comet         | NASA JPL SBDB       | `/api/objects/comet` |
| Meteor        | NASA JPL SBDB       | `/api/objects/meteor` |
| Meteoroid     | NASA JPL SBDB       | `/api/objects/meteoroid` |
| NEO           | NASA CNEOS          | `/api/objects/near_earth_object` |
| Galaxy        | SIMBAD              | `/api/objects/galaxy` |
| Nebula        | SIMBAD              | `/api/objects/nebula` |
| Star cluster  | SIMBAD              | `/api/objects/star_cluster` |
| Variable star | SIMBAD              | `/api/objects/variable_star` |
| **Unidentified 👽** | — (no catalogued source) | `/api/objects/ufo` |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Frontend SPA |
| `GET` | `/static/*` | CSS and JS assets |
| `GET` | `/api/scene` | Assembled scene (CelesTrak TLEs + JPL + SIMBAD) for a datetime |
| `GET` | `/api/objects/{slug}` | Live data from CelesTrak / JPL / SIMBAD |
| `GET` | `/api/classify/{id}` | CNN classification for a canvas object |
| `POST` | `/api/classify/upload` | CNN classification for an uploaded image |
| `POST` | `/api/upload/csv` | Build a scene from an uploaded positions CSV |
| `POST` | `/api/forecast` | Trajectory extrapolation for tracked objects |

**Accounts & persistence** (SQLite, Bearer-token sessions):

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/register` · `/api/auth/login` · `/api/auth/logout` | Account + session lifecycle |
| `GET` | `/api/auth/me` | Current signed-in user |
| `GET`/`POST` | `/api/searches` | List / save simulation searches |
| `DELETE` | `/api/searches/{id}` | Delete a saved search |
| `GET`/`POST` | `/api/uploads` | List / save classification uploads |
| `DELETE` | `/api/uploads/{id}` | Delete a saved upload |

Query params for `/api/objects/{slug}`: `date=YYYY-MM-DD`, `limit=20`. The DB path
defaults to `data/cosmic.db` (override with `COSMIC_DB_PATH`).

Interactive docs at [`/docs`](http://localhost:8000/docs).

## Running

### Docker (recommended)

```bash
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080).

> macOS Monterey+ uses port 5000 for AirPlay Receiver — the compose file maps `8080 → 8000` to avoid the conflict.

### Local

```bash
uv sync
uv run uvicorn app.api:app --reload
```

> Requires [uv](https://docs.astral.sh/uv/). `uv sync` creates `.venv` from `uv.lock` and fetches Python 3.12 automatically.

Open [http://localhost:8000](http://localhost:8000).

## Usage

1. **Load a scene** — Enter optional RA/Dec and a date + time (defaults to now), then click **Load Scene**. Real objects are fetched from CelesTrak and positioned using sgp4 TLE propagation. The map starts frozen.
2. **Navigate** — drag to pan, scroll to zoom. Objects stay frozen until Play is pressed.
3. **Filter by type** — click any row in the legend to isolate that object kind. Click **All Objects** to reset the filter.
4. **Click any object** — the panel shows its real name, data source, velocity, CNN classification, and orbital coordinates.
5. **Press ▶ Play Simulation** — fetches ML-predicted trajectories and fast-forwards at 200× real time, advancing positions using real velocities and overlaying dashed forecast paths.

## Testing

Backend (Python) — coverage gate is enforced at **≥ 80%** (currently ~97%):

```bash
uv run pytest --cov=. --cov-fail-under=80
```

Frontend (canvas SPA) — Jest + jsdom:

```bash
cd front_end && npm test
```

> **Note:** TensorFlow 2.16 imports `distutils`, which Python 3.12 dropped from
> the stdlib. `setuptools<74` (pinned) restores it at runtime, and the root
> `conftest.py` activates the shim before pytest collects any TF-importing test.

## Training

Organize labelled image patches into subdirectories named by object slug (see `app/object_classes.py`) then run:

```bash
uv run python scripts/train_object_classifier.py
```
