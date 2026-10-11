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
  The lunar series/frame/time correction is implemented. The original Moon
  sample improved from 3.06 degrees to 0.00183 degrees; 1,004 quarterly samples
  across 1800–2050 peaked at 0.00393 degrees. See
  [sampled results](ephemeris-validation.md). Planet approximations, historical
  time uncertainty and unknown future leap seconds still prevent continuous
  accuracy guarantees or telescope-pointing claims.

## Classification and models

- **MODEL-02 · T1 · P2 — Synthetic training does not establish scientific validity.**
  Supplied training uses generated patches and synthetic linear tracks.
  Obtain representative data and evaluate
  on held-out observations before presenting scientific performance claims.
  Folder-based training now uses the same 0–1 pixel scale as prediction,
  and synthetic CLI training preserves every class in both partitions.
  See MODEL-04 for holdout integrity and the legacy directory loader.

- **MODEL-03 · T2 · P2 — Historical orbital model needs real-data evaluation.**
  The GP/OMM residual-training pipeline is implemented, but no historical
  dataset has been supplied or trained. Later GP estimates are proxy targets,
  not independent position measurements. Validate against representative
  reference positions and assess orbit, lead-time and unseen-object performance
  before integration. See [historical training](historical-training.md).

- **MODEL-04 · T2 · P1 — Real-image holdout integrity needs dataset review.**
  The new manifest workflow enforces disjoint groups, rejects repeated inputs
  across partitions and evaluates an explicit test set after training. Group
  assignments and near-duplicates still need review on the real dataset.
  Legacy `--data-dir` remains randomly split by image with no independent test
  set. Use [classifier holdouts](classifier-evaluation.md) before real-data runs.

- **MODEL-05 · T2 · P2 — Cross-platform model portability is unverified.**
  CI now exchanges trained synthetic classifier, trajectory and orbital artifacts
  among Windows TensorFlow 2.21 and Linux/Intel macOS TensorFlow 2.16 and checks
  inference outputs, rejecting non-finite values and mismatched output shapes.
  Only the same-runtime Windows check has run locally;
  cross-platform CI results are pending. This checks inference, not optimizer
  resume compatibility or all future trained artifacts.
