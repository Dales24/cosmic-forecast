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

Start with MODEL-01, then DATA-02.

## Data sources

- **DATA-02 · T2 · P2 — Rocket-body coverage relies on names.**
  `NAME=R/B` misses objects without that name fragment. Label the selection
  rule and investigate catalog object-type filtering for broader coverage.

## Positions, dates, and search

- **POS-01 · T1 · P2 — Near-Earth object directions are placeholders.**
  CAD supplies approach distance but no sky direction; placement uses a
  deterministic angle. Label placement as illustrative until per-object
  ephemerides provide real coordinates.
- **POS-02 · T2 · P2 — Satellite dates do not select historical elements.**
  Available TLEs are propagated to any requested time. Accuracy degrades away
  from their epoch. Define and validate a propagation interval; the current
  seven-day element-age notice does not establish an accuracy guarantee.
- **POS-03 · T2 · P2 — JPL/SIMBAD objects stay static in simulation.**
  Their scene velocities are zero. This is a display simplification for distant
  objects, but does not model near-Earth motion. Add JPL ephemeris-based motion
  or explicitly label those objects as static.
- **POS-04 · T2 · P2 — Projection distorts apparent proximity.**
  Declination is mostly collapsed. Adjacent map objects can be far apart in
  the sky; spherical position-search results need not look circular on the map.
  Explain the projection or add an RA/Dec sky view.
- **POS-05 · T2 · P2 — Search omits objects without coordinates.**
  Near-Earth objects are excluded; Earth remains as observer. Report excluded
  categories so empty results are clear.
- **POS-06 · T2 · P2 — Solar-system ephemerides are approximate.**
  Validate `app/ephemeris.py` against a reference over the supported date range
  before advertising an accuracy bound or supporting telescope pointing.

## Classification and models

- **MODEL-01 · T1 · P1 — Map classifications use synthetic images.**
  `/api/classify/{id}` classifies a generated patch, not an observation of the
  selected object. Clearly label this as a demo and distinguish it from
  uploaded-image classification. Real claims require real observations.
- **MODEL-02 · T1 · P2 — Synthetic training does not establish scientific validity.**
  Supplied training uses generated patches and synthetic linear tracks.
  Obtain representative data and evaluate
  on held-out observations before presenting scientific performance claims.

## Environment and verification

- **TOOL-01 · T2 · P2 — TensorFlow pin constrains upgrades.**
  Retained intentionally: TensorFlow 2.16 is the last release supporting
  [macOS x86](https://www.tensorflow.org/install/pip). A newer TensorFlow
  requires an explicit platform-support decision and compatibility testing.
