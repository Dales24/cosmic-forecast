# Known Issues & Limitations

Honest accounting of what the data pipeline does and does not do, and the
caveats behind the scene visualization. Grouped by area.

## Data sources

- **"Satellite" may not be the whole catalogue.** The `satellite` slug tries
  three queries in order — `active`, then `starlink`, then `last-30-days` — and
  the first that responds wins. `active` is the canonical set but is CelesTrak's
  most throttled group, so during a throttle window a cold start silently falls
  back to a *subset*, and the map shows (say) only Starlink craft. Nothing in
  the UI distinguishes the two cases; the admin health page records the
  failures that caused the fallback.
- **CelesTrak rate-limits repeated downloads.** Requesting the same GROUP again
  before CelesTrak's data updates returns `403 "GP data has not updated since
  your last successful download"`. A TLE group is now cached on disk and served
  from there for 2h (`_TLE_CACHE_TTL_SECONDS`), matching CelesTrak's own update
  cadence, so repeated scene loads no longer hit the network at all. Past the
  TTL a failed refresh still falls back to the last cached copy, so a throttled
  window degrades to *stale* elements rather than an empty sky.
- **No GP group for rocket bodies.** CelesTrak retired the dedicated file and the
  GP API has no `rocket-bodies` group. Rocket bodies are catalogued with an
  "R/B" suffix in the object name, so the slug queries `NAME=R/B` instead of a
  GROUP. This returns real rocket bodies, but it is a name match — anything
  catalogued without the suffix is missed.
- **Space debris is a single representative field.** `space_debris` is sourced
  from `cosmos-2251-debris` (a large, real debris field), not "all debris" —
  there is no generic debris group.

## Scene positions (x/y coordinates)

Everything now shares **one map** centred on Earth: the **angle** is each
object's real geocentric right ascension, and the **radius** grows with the
*log* of its real geocentric distance (a LEO satellite and a galaxy can't share
a linear distance scale, so distance is honestly compressed). The bands run
Earth → LEO → GEO → Moon → planets → deep sky (`_scene_radius` in `api.py`).

- **Satellites / ISS / debris / rocket bodies:** real sgp4 positions — angle
  from the ECI direction, radius from true geocentric distance, and a real
  orbital angular rate driving the animation. Time-aware.
- **Sun, Moon, planets:** real geocentric positions from `app.ephemeris` (JPL
  Keplerian elements + an abbreviated lunar series), accurate to ~arc-minutes.
- **SIMBAD deep-space:** real right ascension sets the angle; distance is
  effectively infinite, so they sit on the outer sky band (spread by declination).
- **JPL near-Earth objects:** the approach *distance* is real (sets the radius),
  but the CAD API gives no on-sky position, so the **direction is still a
  deterministic placeholder** — the one thing we can't source without ephemeris
  for each body.
- **UFO:** hardcoded at `(0.28, -0.20)` by design — "position intentionally
  unknown."

Lighting note: the Moon's phase follows the real Sun direction, but Earth's and
the planets' shading stay stylised (fixed upper-left), so shadows may not line
up with the Sun's real on-screen position.

## Date / time handling

- **Satellite datetime drives propagation, not fetching.** The user's datetime
  is fed to sgp4 to advance positions, but CelesTrak only serves the *latest*
  elements — there is no historical-TLE-by-date query. Accuracy degrades the
  further the chosen time is from now.
- **Only JPL honors the date.** The UI datetime reaches JPL CAD as `date-min`,
  with `date-max` computed explicitly as `date-min + 30 days`. CAD reads a
  *relative* `date-max` ("+30") as an offset from today, not from `date-min`, so
  the previous relative form searched the wrong window for any other date —
  returning nothing for a future date and six years of approaches for a past
  one. SIMBAD and CelesTrak take no date.
- **Catalog object velocities are zero.** JPL/SIMBAD scene objects get
  `vx_norm = vy_norm = 0`; they don't participate in the forward simulation.
- **`/api/objects/{slug}` is date-aware but unused.** That endpoint forwards the
  date to the right source, but the frontend never calls it; the scene is built
  by `/api/scene` only.

## Position search

`/api/scene?ra=&dec=&radius_deg=` filters the scene to a cone on the sky, using
real great-circle separation against each object's `ra_deg`/`dec_deg`.

- **Objects without a real sky position are excluded from a search.** JPL
  near-Earth objects (CAD gives no direction) and the UFO (unknown by design)
  carry no usable RA/Dec, so a position search drops them rather than filtering
  on a placeholder angle. They still appear in an unfiltered scene. Earth is
  always kept — it's the observer, not a point on the sky.
- **The map projection collapses declination, so the search is more precise
  than the picture.** The scene plots RA as angle and log-distance as radius;
  declination only nudges the deep-sky band slightly. Two objects that look
  adjacent on the map can be far apart on the real sky, and a search cone
  appears as a radial wedge rather than a circle. The filtering is correct; the
  2D rendering is the lossy part.
- **Declinations for solar-system bodies come from the same approximate
  ephemeris as their RA** — good to roughly arc-minutes, not survey-grade.

## Scene effects (motifs and collisions)

- **Explosions are not conjunction analysis.** A burst fires when two moving
  objects come within `COLLISION_DIST_SCENE` (0.006 scene units) *on the map*.
  The map's radius is a **log** of geocentric distance, so two objects that look
  adjacent can be hundreds of km apart in reality. Treat these as a visual
  flourish showing near-passes at map resolution — not a collision prediction,
  and not something to act on.
- **Only an *approach* counts, never mere proximity.** Plenty of real objects
  are permanently co-located on this projection — ISS modules docked to the same
  station, Starlink satellites in formation. A pair must be seen apart before it
  can fire, and must separate again before firing twice (plus a
  `COLLISION_COOLDOWN_MS` guard). Without this, roughly 60 pairs "collided" on
  every single frame from the moment the simulation started.
- **Collisions are cosmetic — nothing is destroyed.** Objects pass through each
  other and keep their trajectories; the burst is drawn over the top.
- **Motifs decorate moving objects only** (`MOTIF_KINDS`: satellites, ISS,
  debris, rocket bodies, UFO). Ornamenting all ~109 objects would bury the deep
  sky. The default theme has no motif by design.

## Caching and freshness

Three cache layers reduce repeated source requests:

- **Scene cache** (`_SCENE_TTL_SECONDS`, 45s): assembled scenes, keyed by
  `datetime_str`, `limit`, `ra`, `dec`, and `radius_deg`. Bounded at
  `_SCENE_CACHE_MAX_ENTRIES` (64), with expired entries pruned on insertion
  and the oldest entries evicted when full. When datetime is omitted, repeated
  requests can reuse the same scene for 45s instead of recomputing for now.
- **Catalog cache** (`_SIMBAD_TTL_SECONDS`, 6h; `_JPL_TTL_SECONDS`, 1h): SIMBAD
  results are keyed by object kind and cap; JPL results by requested date and
  cap. The date is a query input, not a guarantee that upstream data changes
  only once per day. This in-memory cache has no entry limit or expiry sweep;
  expired entries are replaced only when their key is requested again.
- **TLE disk cache** (`_TLE_CACHE_TTL_SECONDS`, 2h): raw CelesTrak text, keyed
  by object slug. After 2h a refresh is attempted; if all candidate URLs fail,
  the existing file is served with no maximum stale age.

These TTLs control cache reuse, not the age of the source observations. A
cached scene can extend reuse of its source data by another 45s, and failed
TLE refreshes can leave much older elements in use. On a scene rebuild, sgp4
propagates those elements to the requested datetime; a scene cache hit reuses
the already computed positions. Propagation does not refresh the elements or
prevent accuracy from degrading as the requested time moves away from their
epoch.

## Classification

- **Classifications are not real.** `/api/classify/{id}` runs the CNN on a
  *random synthetic patch* seeded by the object id — there is no real telescope
  imagery in the pipeline. Output is illustrative only.

## Accounts and storage

- **The default `admin` / `admin` login is gated behind an env flag.**
  `_ensure_admin_user` in `api.py` creates it only when `COSMIC_BOOTSTRAP_ADMIN`
  is truthy (`1`/`true`/`yes`/`on`); otherwise startup makes no admin. It still
  bypasses the minimum-password rule, so enable it for local work only — for a
  real deployment name admins via `COSMIC_ADMIN_USERS` and leave the flag unset.
- **Sessions expire after 7 days.** `db._SESSION_TTL_SECONDS` bounds a token's
  life; `get_user_by_token` ignores rows older than that, and each login sweeps
  expired rows, so the table no longer grows without bound. Logout still
  invalidates a token immediately. There is no sliding refresh — the clock runs
  from when the token was issued.
- **SQLite is opened per query.** Every `db.*` call opens a new connection, sets
  its pragmas, and closes it — roughly 37× the cost of a shared connection on
  repeated reads. Fine at this scale, wasteful at any other.
- **WAL mode is on.** `get_conn` sets `journal_mode = WAL` (real-file DBs only;
  an in-memory test DB stays on the default journal) plus a 5s `busy_timeout`,
  so a read no longer blocks behind a write. Still one connection per query
  (below), so this only softens contention, it doesn't remove it.
- **Per-user indexes exist, per-table scans do not.** `user_id` is indexed on
  every owned table; `sessions.token_hash` and `users.username` are covered by
  their PRIMARY KEY / UNIQUE constraints.

## Models and publishing

- **Both publishable models are trained on synthetic data.** The classifier
  learns from generated patches and the trajectory transformer from synthetic
  linear-motion tracks. `app/model_publish.py` requires every model to carry
  caveats and prints them on the generated model card, so this cannot be
  published silently — but it does mean neither model is scientifically useful
  as shipped.
- **Nothing is trained by default.** `models/` is absent until you run the
  training script; the publish CLI fails with a clear error rather than
  uploading an empty repository.
- **Publishing is opt-in twice over.** `scripts/publish_model.py` is a dry run
  unless given `--push`, and creates private repositories unless given
  `--public`.

## Environment / tooling

- **macOS x86_64 numpy/TensorFlow dylib fragility.** numpy's bundled
  `.dylibs` (libgfortran/libopenblas) were being dropped by uv's default
  hardlink install mode, breaking `import numpy` (often only after TensorFlow
  loaded earlier in the same process). Fixed by `link-mode = "copy"` in
  `pyproject.toml`. If imports break again, rebuild: `rm -rf .venv && uv sync`.
- **TensorFlow pinned to 2.16.2.** Versions ≥ 2.17 dropped macOS x86_64 wheels;
  2.16.2 is the last release with both Linux and Intel-mac wheels.
- **Scripts must be run as modules, from the repo root.**
  `uv run python -m scripts.<name>` works; `uv run python scripts/<name>.py`
  fails with `ModuleNotFoundError: No module named 'app'`, because running a
  file directly puts `scripts/` on `sys.path` instead of the project root.
  Scripts also import `setuptools` before anything TensorFlow-related, for the
  same distutils reason as `app/api.py`. Model paths are relative, so the repo
  root is the required working directory either way.

## Robustness

- **Partial scenes show a data availability notice.** Failed scene sources
  appear in `/api/scene` as `source_warnings` and in a "Map incomplete" notice
  beside the map legend, naming the affected object kinds and sources. Cached
  results retain their warnings; a healthy scene response clears the notice.
  Detailed errors and repeat counts remain in `/api/admin/health`. Successful
  CelesTrak fallback to stale data or a smaller catalog is not flagged by this
  notice.
