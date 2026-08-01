# Known Issues & Limitations

Honest accounting of what the data pipeline does and does not do, and the
caveats behind the scene visualization. Grouped by area.

## Data sources

- **CelesTrak legacy URLs are dead.** The old `https://celestrak.org/pub/TLE/*.txt`
  files now return HTTP 403. We use the GP query API instead
  (`gp.php?GROUP=...&FORMAT=tle`). Mapping: `satellite → active`, `iss → stations`.
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

Three independent layers, each keyed on what actually changes:

- **Scene cache** (`_SCENE_TTL_SECONDS`, 45s): whole assembled scenes, keyed by
  datetime + limit + search. Bounded at `_SCENE_CACHE_MAX_ENTRIES` (64) with
  expiry pruning, since every distinct datetime is its own key.
- **Catalog cache** (`_SIMBAD_TTL_SECONDS` 6h, `_JPL_TTL_SECONDS` 1h): keyed on
  each source's *real* inputs, not the scene datetime — SIMBAD deep-space
  objects are fixed on this timescale and JPL's list changes only by date.
- **TLE disk cache** (`_TLE_CACHE_TTL_SECONDS`, 2h): raw CelesTrak text.

Consequence: a scene can be served from data up to the relevant TTL old. For
deep-space objects that's harmless; for satellites the sgp4 propagation always
runs against the requested datetime, so only the *elements* age, not the
positions computed from them.

## Classification

- **Classifications are not real.** `/api/classify/{id}` runs the CNN on a
  *random synthetic patch* seeded by the object id — there is no real telescope
  imagery in the pipeline. Output is illustrative only.

## Environment / tooling

- **macOS x86_64 numpy/TensorFlow dylib fragility.** numpy's bundled
  `.dylibs` (libgfortran/libopenblas) were being dropped by uv's default
  hardlink install mode, breaking `import numpy` (often only after TensorFlow
  loaded earlier in the same process). Fixed by `link-mode = "copy"` in
  `pyproject.toml`. If imports break again, rebuild: `rm -rf .venv && uv sync`.
- **TensorFlow pinned to 2.16.2.** Versions ≥ 2.17 dropped macOS x86_64 wheels;
  2.16.2 is the last release with both Linux and Intel-mac wheels.

## Robustness

- **Degradation on fetch failure is quiet for users, visible to admins.** Every
  external fetch is wrapped in `try/except` so one source failing never crashes
  the scene. Failures now go through `api._source_unavailable`, which logs a
  warning and records the source, kind, error and a repeat count for
  `/api/admin/health` (shown on the admin page). The end user still sees only a
  sparser map — they can't tell a network problem from genuinely sparse data —
  but the information is no longer lost.
