# Known Issues & Limitations

Open issues and accepted limitations, grouped by area. Resolved items are
removed. Rankings below are suggested engineering priorities based on code
inspection, not a security audit or load test.

## Tiers and priorities

| Label | Meaning |
| --- | --- |
| T1 — High | Materially misleading results, potential service interruption, or privileged-access risk under the stated conditions. |
| T2 — Medium | Reduced completeness, reliability, accuracy, or scalability. |
| T3 — Low | Usability, maintenance, or intentional presentation limitation. |
| P0 — Immediate | Confirmed urgent incident or release blocker. None identified in this review. |
| P1 — Next | Address in the next engineering pass. |
| P2 — Planned | Schedule after P1 work. |
| P3 — Backlog | Improve when needed; intentional limitations may remain documented. |

Start with DATA-01 and MODEL-01.
Check AUTH-01 before exposing a deployment.

## Caching and freshness

The six original cache issues are addressed. Scene responses still reuse data
for 45 seconds (30 seconds when sources fail), with 64 entries maximum. The UI
shows scene time, stale-download notices, and a warning for elements older than
7 days. Download age and element epoch are separate measurements; the 7-day
notice is a display heuristic, not a validated propagation accuracy bound.

Catalog storage is capped at 256 entries with expiry pruning. Successful SIMBAD
and JPL results retain their 6-hour/1-hour TTLs; failed results retry after
30 seconds. Same-key requests share work without blocking other keys' fetches.

TLE downloads are validated before atomic replacement. Unchanged files reuse
validated text/metadata in memory. Fresh downloads are reused for 2 hours;
failed refreshes retry after 30 seconds and may serve downloads less than
24 hours old. Older downloads are unavailable, and scene-cache expiry cannot
extend that deadline. The 24-hour bound is on download age, not element epoch.

Locks and request sharing are process-local; separate server workers have
independent caches and can fetch the same source. Atomic file replacement keeps
shared disk readers from seeing partial writes. Cache-hit performance and
concurrency regression tests cover the single-process application model.

## Data sources

- **DATA-01 · T2 · P1 — Satellite fallback silently reduces coverage.**
  Queries try `active`, `starlink`, then `last-30-days`; a fallback can show
  only a subset. Even `active` is not the entire satellite catalog. Failed
  candidates are swallowed inside the fetcher, so a later success also hides
  them from the admin failure log. Return the selected query and fallback
  status, record failed attempts, and label coverage in the UI.
- **DATA-02 · T2 · P2 — Rocket-body coverage relies on names.**
  `NAME=R/B` misses objects without that name fragment. Label the selection
  rule and investigate catalog object-type filtering for broader coverage.
- **DATA-03 · T2 · P2 — Debris represents one collision field.**
  `space_debris` maps to `cosmos-2251-debris`. Label the field in the UI;
  additional fields need explicit selection and deduplication.

## Positions, dates, and search

The map plots right ascension as angle and log geocentric distance as radius.
Satellite positions use sgp4; Sun/Moon/planet positions use the local approximate
ephemeris. JPL CAD requests cover the selected date through 30 days later.
SIMBAD and CelesTrak fetches do not select historical catalogs.

- **POS-01 · T1 · P2 — Near-Earth object directions are placeholders.**
  CAD supplies approach distance but no sky direction; placement uses a
  deterministic angle. Label placement as illustrative until per-object
  ephemerides provide real coordinates.
- **POS-02 · T2 · P2 — Satellite dates do not select historical elements.**
  Available TLEs are propagated to any requested time. Accuracy degrades away
  from their epoch. Show epoch/age and warn outside a validated time interval.
- **POS-03 · T2 · P2 — JPL/SIMBAD objects stay static in simulation.**
  Their scene velocities are zero. This is a display simplification for distant
  objects, but does not model near-Earth motion. Add JPL ephemeris-based motion
  or explicitly label those objects as static.
- **POS-04 · T2 · P2 — Projection distorts apparent proximity.**
  Declination is mostly collapsed. Adjacent map objects can be far apart in
  the sky; spherical position-search results need not look circular on the map.
  Explain the projection or add an RA/Dec sky view.
- **POS-05 · T2 · P2 — Search omits objects without coordinates.**
  Near-Earth objects and the intentional UFO placeholder are excluded; Earth
  remains as observer. Report excluded categories so empty results are clear.
- **POS-06 · T2 · P2 — Solar-system ephemerides are approximate.**
  Validate `app/ephemeris.py` against a reference over the supported date range
  before advertising an accuracy bound or supporting telescope pointing.
- **POS-07 · T3 · P3 — Alternate object endpoint is unused by the UI.**
  The frontend uses `/api/scene`, not `/api/objects/{slug}`. Document intended
  consumers and keep date/source semantics consistent; this is not itself a
  broken date-selection flow.

## Scene effects and presentation

- **FX-01 · T1 · P2 — Explosions can imply real collision predictions.**
  Bursts use projected map distance, not physical conjunction analysis.
  Approach/reseparation and cooldown guards do not establish collision risk.
  Label effects as cosmetic or disable them by default; trajectories continue.
- **FX-02 · T3 · P3 — UFO and motifs are intentional decoration.**
  UFO placement is fixed at `(0.28, -0.20)`; motifs decorate moving kinds only.
  The default theme has none. Preserve clear illustrative labeling.
- **FX-03 · T3 · P3 — Some lighting is stylized.**
  Moon phase follows the Sun direction, but Earth/planet shading uses a fixed
  direction. Align shading with geometry if visual consistency becomes a goal.

## Classification and models

- **MODEL-01 · T1 · P1 — Map classifications use synthetic images.**
  `/api/classify/{id}` classifies a generated patch, not an observation of the
  selected object. Clearly label this as a demo and distinguish it from
  uploaded-image classification. Real claims require real observations.
- **MODEL-02 · T1 · P2 — Synthetic training does not establish scientific validity.**
  Supplied training uses generated patches and synthetic linear tracks.
  Model cards already carry caveats. Obtain representative data and evaluate
  on held-out observations before presenting scientific performance claims.
- **MODEL-03 · T3 · P3 — Trained artifacts require explicit setup.**
  A checkout need not contain models. Document training/artifact setup for
  deployers. Preserve existing missing-artifact checks, dry-run publishing,
  and explicit opt-in for public uploads.

## Accounts and storage

- **AUTH-01 · T1 · P1 — Opt-in bootstrap credentials are predictable.**
  `COSMIC_BOOTSTRAP_ADMIN` enables `admin` / `admin`, bypassing password-length
  checks. It is disabled by default. Keep it off on exposed deployments and
  configure intended admins with `COSMIC_ADMIN_USERS`; consider requiring an
  explicit initial secret or refusing insecure production bootstrap.
- **DB-01 · T2 · P2 — SQLite opens connections per operation.**
  Each call opens a connection and reapplies pragmas. WAL, a 5-second busy
  timeout, and owned-table indexes already exist. Measure realistic concurrent
  load before changing connection lifetime; address measured contention
  without unsafe connection sharing across threads.

## Environment and verification

- **TOOL-01 · T2 · P2 — TensorFlow pin constrains upgrades.**
  Retained intentionally: TensorFlow 2.16 is the last release supporting
  [macOS x86](https://www.tensorflow.org/install/pip). CI now configures Python
  3.12 checks on Linux, Windows, and Intel macOS, including ML/publishing
  imports. Check the PR results for each platform. A newer TensorFlow
  requires an explicit platform-support decision and compatibility testing.
- **TOOL-04 · T2 · P2 — iCloud can stall dependency installation.**
  The workspace's `node_modules` operations still stalled locally. The new
  tracked lockfile passed clean `npm ci` and all 192 Jest tests
  in a temporary directory. Prefer a checkout outside cloud synchronization
  for dependency-heavy development; do not sync virtual environments or
  `node_modules`. This local filesystem issue is separate from reproducibility.

Script invocation and default model paths are now independent of the working
directory. The frontend lockfile is no longer ignored and CI uses `npm ci`.
See [environment setup](environment.md) for supported commands and platforms.
