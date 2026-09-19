# Historical satellite and debris forecasting

The experimental orbital model learns a three-dimensional position correction
to SGP4 from historical GP records. It is separate from the canvas-coordinate
Transformer and is not connected to the live forecast endpoint.

No historical dataset or trained weights are supplied. Tests use fabricated
orbital records solely to verify the software.

## Data contract

Supply a local flat GP/OMM JSON array or CSV with multiple epochs per NORAD ID.
Space-Track's `gp_history` class is one potential source; obtain an authorized
export yourself and retain its provenance. A current catalog snapshot alone
does not provide a training history. Keep data under ignored `data/` and models
under ignored `models/`; do not put credentials in files or source labels.

Required columns:

```text
NORAD_CAT_ID,EPOCH,OBJECT_ID,CLASSIFICATION_TYPE,EPHEMERIS_TYPE,
ELEMENT_SET_NO,REV_AT_EPOCH,MEAN_MOTION,ECCENTRICITY,INCLINATION,
RA_OF_ASC_NODE,ARG_OF_PERICENTER,MEAN_ANOMALY,BSTAR,
MEAN_MOTION_DOT,MEAN_MOTION_DDOT
```

Use the standard GP units: angles in degrees, mean motion in revolutions/day,
and the published GP values for derivatives and BSTAR. Metadata, when present,
must specify EARTH, TEME, UTC and SGP4. Naive timestamps are interpreted as UTC.
Records must have unique `(NORAD_CAT_ID, EPOCH)` pairs; resolve revisions before
import. Invalid records fail validation rather than being silently accepted.

Include `CREATION_DATE` whenever available. Forecast availability is the later
of epoch and creation date. Without creation date, epoch is an explicit proxy;
the report counts these assumptions. This does not prove the record was actually
publicly available at that time. Independently track acquisition/publication
times when designing a realistic backtest.

Format and data-source references:

- [CelesTrak GP formats](https://www.celestrak.org/NORAD/documentation/gp-data-formats.php)
- [Space-Track documentation](https://www.space-track.org/documentation)

## Prepare and train

Choose dates appropriate to your archive. The following dates are examples:

```powershell
uv run python -m scripts.train_orbital_forecast --data data/history.json --source "My historical GP export" --train-before 2023-01-01 --validation-before 2024-01-01 --prepare-only
uv run python -m scripts.train_orbital_forecast --data data/history.json --source "My historical GP export" --train-before 2023-01-01 --validation-before 2024-01-01 --epochs 30 --output models/orbital_run_001
```

Relative paths resolve from the repository root. Existing output directories
are refused. Preparation writes no artifacts. Training saves `model.keras`
and `report.json`, including the dataset hash, provenance, feature order,
date boundaries, counts, skipped pairs, model selection and evaluation metrics.

Adjacent records of each object form examples. The earlier record supplies
the initial state and SGP4 forecast; the later record supplies its estimated
position at its own epoch. The forecast target must follow input availability.
Both lead and total element age must stay within `--max-lead-hours` (default
72). This is a configurable experimental filter, not an accuracy guarantee.
Failed propagation and disallowed leads are counted as skipped pairs.

Examples crossing split boundaries are purged. Training reference availability
must precede the training cutoff, and validation reference availability must
precede the validation cutoff. Test inputs begin at the validation cutoff.
Every partition must contain usable pairs. Objects can recur across partitions;
this evaluates future dates for that population, not unseen-object performance.

The model is a small dense network with normalization fitted only on training
features. Its inputs are the initial and SGP4 target states, forecast lead and
BSTAR. Output is a TEME xyz correction in kilometers. Validation selects the
best epoch through early stopping; if the learned correction fails to improve
validation RMSE over SGP4, the saved model retains a zero correction. Test data
does not select weights. Reports compare SGP4 and the selected model using
3D position-error RMSE, median and 95th percentile in kilometers.

## Load a trained run

```python
import json
import setuptools  # Activate the TensorFlow/Python 3.12 compatibility shim.
import tensorflow as tf
from app.orbital_forecast import parse_record, predict_position, utc
from app.paths import MODEL_ROOT

run = MODEL_ROOT / "orbital_run_001"
model = tf.keras.models.load_model(run / "model.keras")
report = json.loads((run / "report.json").read_text())
# gp_fields is a single GP record, with the columns described above.
record = parse_record(gp_fields)
position_km = predict_position(
    model, record, utc("2024-05-02T12:00:00Z"), report["max_lead_hours"]
)
```

Targets are later catalog estimates, not independent measured positions.
Performance against them cannot establish real-world accuracy or collision
prediction capability. The model does not estimate uncertainty or model
unannounced maneuvers. Lead times follow archive sampling, so evaluate coverage
for your intended objects and forecast horizons before drawing conclusions.
Large exports currently load into memory. Future work includes independent
position references, object-held-out tests, orbit/lead-specific evaluation and
operational availability metadata.
