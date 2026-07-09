# Known Issues & Limitations

Honest accounting of what the data pipeline does and does not do, and the
caveats behind the scene visualization. Grouped by area.

## Data sources

- **CelesTrak legacy URLs are dead.** The old `https://celestrak.org/pub/TLE/*.txt`
  files now return HTTP 403. We use the GP query API instead
  (`gp.php?GROUP=...&FORMAT=tle`). Mapping: `satellite → active`, `iss → stations`.
- **CelesTrak rate-limits repeated downloads.** Requesting the same GROUP again
  before CelesTrak's data updates returns `403 "GP data has not updated since
  your last successful download"`. Reloading the scene rapidly can therefore
  show *fewer* objects until the cache window passes. We degrade silently.
- **No GP group for rocket bodies.** CelesTrak retired the dedicated file and the
  GP API has no `rocket-bodies` group, so `rocket_body` returns an empty list
  (an unknown group yields a non-TLE body that parses to `[]`) rather than
  mislabeling other objects.
- **Space debris is a single representative field.** `space_debris` is sourced
  from `cosmos-2251-debris` (a large, real debris field), not "all debris" —
  there is no generic debris group.

## Scene positions (x/y coordinates)

The scene mixes objects whose positions come from very different places. They
are **not** on one common physical scale.

- **Satellites / ISS:** real positions from sgp4 propagation of current TLEs,
  normalized by GEO distance (42,164 km). Data-driven and time-aware.
- **SIMBAD deep-space (galaxies, nebulae):** real sky coordinates — RA (0–360°)
  maps to x, Dec (−90–90°) to y. A flat 2D projection, not the orbital frame.
- **JPL near-Earth objects:** **symbolic placement.** The CAD API returns
  approach *distance* and *velocity* but no on-sky position, so distance sets an
  outer-ring radius and a stable hash of the designation sets the angle. The
  distance is real; the on-screen direction is fabricated.
- **UFO:** hardcoded at `(0.28, -0.20)` by design — "position intentionally
  unknown."

## Date / time handling

- **Satellite datetime drives propagation, not fetching.** The user's datetime
  is fed to sgp4 to advance positions, but CelesTrak only serves the *latest*
  elements — there is no historical-TLE-by-date query. Accuracy degrades the
  further the chosen time is from now.
- **Only JPL honors the date.** The UI datetime reaches JPL CAD as `date-min`
  (the approach-window start). SIMBAD and CelesTrak take no date.
- **Catalog object velocities are zero.** JPL/SIMBAD scene objects get
  `vx_norm = vy_norm = 0`; they don't participate in the forward simulation.
- **`/api/objects/{slug}` is date-aware but unused.** That endpoint forwards the
  date to the right source, but the frontend never calls it; the scene is built
  by `/api/scene` only.

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

- **Silent degradation on fetch failure.** Every external fetch is wrapped in
  `try/except` so one source failing never crashes the scene — but failures are
  not surfaced in the UI. A user seeing few objects can't tell a network/rate
  problem from genuinely sparse data.
