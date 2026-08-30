# Architecture

Cosmic Forecast detects, classifies, and forecasts the motion of objects in a
telescope's field of view, and renders them on an interactive sky map. This
document explains how the pieces fit together and where to change things.

## At a glance

```
                         ┌────────────────────────── front_end/ ──────────────────────────┐
                         │  index.html + static/app.js (canvas SPA)                        │
                         │   • sky map render (stars, Sun/Moon/planets, Earth, objects)    │
                         │   • sim controls (play / pan / zoom / filter)                   │
                         │   • image + CSV upload, accounts UI (auth.js)                   │
                         └───────────────▲───────────────────────────▲─────────────────────┘
                                         │ JSON over HTTP            │
                         ┌───────────────┴───────────────────────────┴─────────────────────┐
                         │                         app/api.py (FastAPI)                     │
                         │   /api/scene  /api/objects  /api/classify  /api/forecast         │
                         │   /api/upload/csv  /api/classify/upload                          │
                         │   /api/auth/*     /api/searches  /api/uploads                    │
                         └───┬───────────────┬───────────────┬──────────────┬──────────────┘
                             │               │               │              │
                    data_parser.py     pipeline.py       auth.py + db.py   object_classifier.py
                   (CelesTrak/JPL/     (CNN → Track →     (SQLite accounts   (patch CNN)
                    SIMBAD fetchers)    Transformer →      + saved work)
                                        Kalman)
```

## The forecasting pipeline (`app/pipeline.py`)

`ForecastPipeline` chains four stages, each owned by its own module so it can be
tested and swapped in isolation:

```
Patch CNN → Track Builder → Trajectory Transformer → Kalman Refinement → Predicted Position
```

| Stage | Module | Role |
|-------|--------|------|
| **Patch CNN** | [`object_classifier.py`](../app/object_classifier.py) | Classifies an image patch into one of the object classes (see below). Trained on a synthetic dataset; created lazily. |
| **Track Builder** | [`track_builder.py`](../app/track_builder.py) | Associates per-frame detections into tracks across time (nearest-neighbour within a distance gate). |
| **Trajectory Transformer** | [`trajectory_transformer.py`](../app/trajectory_transformer.py) | Sequence model that forecasts the next position from a track's history. Falls back to linear extrapolation when no model is loaded. |
| **Kalman Refinement** | [`kalman_refinement.py`](../app/kalman_refinement.py) | Smooths the prediction and yields a position estimate at a target timestamp. |

Shared types (`Detection`, `Track`, `PredictedPosition`) live in
[`detections.py`](../app/detections.py); object categories in
[`object_classes.py`](../app/object_classes.py). Pure algorithm code stays out of
`api.py` — routes only wire modules together.

## Object classes & data sources

Every detectable object is an `ObjectClass(name, slug, group)` in
[`object_classes.py`](../app/object_classes.py), grouped as **natural**,
**artificial**, **deep_space**, or **unknown**. The live sky map pulls real
objects from three external catalogs via [`data_parser.py`](../app/data_parser.py):

| Source | Provides | Kinds |
|--------|----------|-------|
| **CelesTrak** (GP/TLE) | Orbital elements, propagated with `sgp4` | `iss`, `satellite`, `space_debris`, `rocket_body` |
| **JPL** (CAD API) | Near-Earth close approaches | `near_earth_object` (also `asteroid`/`comet` slugs) |
| **SIMBAD** (TAP/ADQL) | Deep-space objects by `otype` | `galaxy`, `nebula`, `star_cluster`, `variable_star`, `star`, `black_hole`, `quasar`, `pulsar`, `supernova_remnant` |

`get_data(slug)` routes a slug to the right fetcher; SIMBAD-backed slugs are
derived from the `_SIMBAD_OTYPES` map so the two never drift. Every fetcher
handles timeouts and bad responses gracefully — one source failing never crashes
the scene (it just contributes fewer objects).

### Positioning note

Only CelesTrak objects have true astrometric positions (from TLE propagation).
JPL and SIMBAD objects are placed **symbolically** — JPL by approach distance +
a stable hash angle, SIMBAD by RA/Dec mapped to the canvas. See
[`known-issues.md`](known-issues.md).

## API surface (`app/api.py`)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/scene` | Assemble the live scene for a datetime (CelesTrak + JPL + SIMBAD). |
| `GET` | `/api/objects/{slug}` | Raw catalog rows for one object type. |
| `GET` | `/api/classify/{id}` | CNN classification for a canvas object. |
| `POST` | `/api/classify/upload` | CNN classification for an uploaded image. |
| `POST` | `/api/upload/csv` | Build a scene from a positions CSV. |
| `POST` | `/api/forecast` | Trajectory extrapolation for tracked objects. |
| `POST` | `/api/auth/register` · `login` · `logout`, `GET /api/auth/me` | Accounts + sessions. |
| `GET`/`POST`/`DELETE` | `/api/searches`, `/api/uploads` | Per-account saved work. |

The CNN is created lazily (`_get_cnn`) so importing the app is cheap and the
model only loads on first classification.

## Accounts & persistence

- [`auth.py`](../app/auth.py) — PBKDF2 password hashing, bearer-token sessions
  (only the token's SHA-256 is stored), and the `current_user` FastAPI dependency.
- [`db.py`](../app/db.py) — SQLite (stdlib `sqlite3`, no extra deps): `users`,
  `sessions`, `saved_searches`, `saved_uploads`. DB path via `COSMIC_DB_PATH`.

## Frontend (`front_end/`)

A dependency-free canvas SPA. [`app.js`](../front_end/static/app.js) pre-renders a
space backdrop offscreen, then each animation frame draws the twinkling star
field, the Sun/Moon/decorative planets, Earth (with a day/night terminator), and
the live scene objects (styled per kind via `KIND_STYLES` / `KIND_NAMES`). It
handles pan/zoom, the play/forecast simulation, legend filtering, and the upload
flows; [`auth.js`](../front_end/static/auth.js) adds the accounts UI.

## Adding a new detection

Because the model is data-driven, a new deep-space kind is a small, uniform change
(the recent black-hole / star / quasar / pulsar / SNR pack followed exactly this):

1. Add an `ObjectClass(...)` to [`object_classes.py`](../app/object_classes.py).
2. Map its slug to a SIMBAD `otype` in `_SIMBAD_OTYPES` (or add a fetcher for a
   new source) in [`data_parser.py`](../app/data_parser.py).
3. Add a `_simbad_scene_objects(...)` call in the scene assembly in
   [`api.py`](../app/api.py).
4. Add a `KIND_STYLES` + `KIND_NAMES` entry (colour, size, label) in
   [`app.js`](../front_end/static/app.js).
5. Add tests (class registry, otype routing, scene inclusion, frontend kind).

Note: adding a class grows `NUM_CLASSES`, so the CNN's output layer widens and it
retrains on the synthetic dataset — scene placement uses the real catalogs, so the
map updates immediately regardless.

## Testing & tooling

- **Backend:** `uv run pytest --cov-fail-under=80` (coverage gate; currently ~97%).
- **Frontend:** `cd front_end && npm test` (Jest + jsdom).
- **Style:** black + flake8 via pre-commit.

See [`../README.md`](../README.md) for run instructions and
[`known-issues.md`](known-issues.md) for current limitations.
