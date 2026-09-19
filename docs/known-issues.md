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

Before real-data training, review dataset provenance and evaluation splits.

## Positions, dates, and search

- **POS-01 · T2 · P2 — NEO playback uses a linear tangent.**
  Horizons supplies real scene-time positions and velocities for up to ten
  CAD candidates per scene. Failed queries retain explicitly illustrative,
  static fallbacks and source warnings. Playback uses a linear velocity tangent,
  not continuous orbital propagation; long-duration motion still needs work.
- **POS-02 · T2 · P2 — Satellite dates do not select historical elements.**
  Available TLEs are propagated to any requested time. Accuracy degrades away
  from their epoch. Objects now report signed epoch offsets and flag dates
  outside a +/-7-day display policy. The map summarizes these extrapolations.
  The policy is not an accuracy guarantee; historical validation remains open.
- **POS-06 · T2 · P2 — Solar-system ephemerides are approximate.**
  A 252-position Horizons comparison across 1800–2050 is complete; see
  [sampled results](ephemeris-validation.md). Moon differences reach about
  3.06 degrees. Fix the lunar approximation and validate more densely before
  advertising an accuracy bound or supporting telescope pointing.

## Classification and models

- **MODEL-02 · T1 · P2 — Synthetic training does not establish scientific validity.**
  Supplied training uses generated patches and synthetic linear tracks.
  Obtain representative data and evaluate
  on held-out observations before presenting scientific performance claims.

- **MODEL-03 · T2 · P2 — Historical orbital model needs real-data evaluation.**
  The GP/OMM residual-training pipeline is implemented, but no historical
  dataset has been supplied or trained. Later GP estimates are proxy targets,
  not independent position measurements. Validate against representative
  reference positions and assess orbit, lead-time and unseen-object performance
  before integration. See [historical training](historical-training.md).

## Environment and verification

- **TOOL-01 · T2 · P2 — TensorFlow pin constrains upgrades.**
  Retained intentionally: TensorFlow 2.16 is the last release supporting
  [macOS x86](https://www.tensorflow.org/install/pip). A newer TensorFlow
  requires a platform-support change and compatibility testing. The user has
  confirmed continued multiplatform support, including Intel Macs, so retain
  the pin. CI covers Windows, Linux and Intel macOS; this session ran on Windows.
