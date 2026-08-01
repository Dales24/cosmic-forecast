# Cosmic Forecast 👽

A prediction system for tracking and forecasting space object trajectories. The pipeline classifies objects from telescope image patches (CNN), builds tracks across frames, and predicts future positions via a Transformer + Kalman filter. Live object data is pulled from CelesTrak, NASA JPL, and SIMBAD.

## Architecture

For the full picture — the CNN → track → transformer → Kalman pipeline, data
sources, API surface, accounts, and how to add a new detection — see
[docs/architecture.md](docs/architecture.md).

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
| `GET` | `/help` · `/profile` · `/admin` | Help, account, and admin-monitor pages |
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
| `GET`/`POST` | `/api/custom-objects` | List / add the user's own scene objects |
| `DELETE` | `/api/custom-objects/{id}` | Delete a custom object |
| `PUT` | `/api/preferences` | Save UI preferences (theme) |
| `GET` | `/api/admin/health` | Request metrics, scene caps, source failures (admin only) |

### Query parameters

`GET /api/scene` — every parameter is optional:

| Param | Default | Meaning |
|-------|---------|---------|
| `datetime_str` | now | ISO 8601 UTC moment to build the scene for. Rejected with 422 if unparseable. |
| `limit` | `COSMIC_CAP_SATELLITE` | Override the satellite cap only |
| `ra`, `dec` | — | Degrees. Give **both** to narrow the scene to a patch of sky; accepts `83.82` or `83.82°` |
| `radius_deg` | `30` | Cone half-angle around `ra`/`dec` (0–180) |

A position search adds a `search` block to the response (`matched`, `searched`,
`radius_deg`). Objects with no real sky position — JPL near-Earth objects and
the UFO — are excluded from a search; see [docs/known-issues.md](docs/known-issues.md).

`GET /api/objects/{slug}` — `date=YYYY-MM-DD`, `limit=20`.

### Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `COSMIC_DB_PATH` | `data/cosmic.db` | SQLite database file |
| `COSMIC_TLE_CACHE_DIR` | `data/tle_cache` | Where CelesTrak TLE text is cached on disk |
| `COSMIC_ADMIN_USERS` | *(empty)* | Comma-separated usernames granted admin on registration |
| `COSMIC_CAP_<KIND>` | see `app/config.py` | Per-kind cap on how many objects a catalog may add to a scene (e.g. `COSMIC_CAP_GALAXY=12`) |

### Caching

Three layers, each keyed on what actually changes — see
[docs/known-issues.md](docs/known-issues.md) for the freshness implications:

- **Scene** (45s, max 64 entries) — whole assembled scenes by datetime/limit/search.
- **Catalog** (SIMBAD 6h, JPL 1h) — keyed on each source's real inputs, not the
  scene datetime, so a new minute doesn't refetch static sky.
- **TLE disk cache** (2h) — raw CelesTrak text, matching its publish cadence.

External-source failures never break a scene; they are logged and surfaced at
`/api/admin/health`.

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
