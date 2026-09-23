"""Experimental SGP4 residual learning from historical GP/OMM estimates."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sgp4 import omm
from sgp4.api import Satrec, jday

FEATURE_NAMES = [
    "origin_x_km",
    "origin_y_km",
    "origin_z_km",
    "origin_vx_km_s",
    "origin_vy_km_s",
    "origin_vz_km_s",
    "baseline_x_km",
    "baseline_y_km",
    "baseline_z_km",
    "baseline_vx_km_s",
    "baseline_vy_km_s",
    "baseline_vz_km_s",
    "lead_hours",
    "bstar",
]


def utc(value: str) -> datetime:
    """GP timestamps without an offset are defined as UTC."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (
        parsed.replace(tzinfo=timezone.utc)
        if parsed.tzinfo is None
        else parsed.astimezone(timezone.utc)
    )


@dataclass
class OrbitalRecord:
    object_id: int
    epoch: datetime
    available: datetime
    satellite: Satrec


def parse_record(fields: dict) -> OrbitalRecord:
    fields = dict(fields)
    for key, expected in {
        "CENTER_NAME": "EARTH",
        "REF_FRAME": "TEME",
        "TIME_SYSTEM": "UTC",
        "MEAN_ELEMENT_THEORY": "SGP4",
    }.items():
        if fields.get(key) not in (None, "", expected):
            raise ValueError(f"{key} must be {expected}")
    epoch = utc(fields["EPOCH"])
    available = (
        max(epoch, utc(fields["CREATION_DATE"]))
        if fields.get("CREATION_DATE")
        else epoch
    )
    for key in (
        "MEAN_MOTION",
        "ECCENTRICITY",
        "INCLINATION",
        "RA_OF_ASC_NODE",
        "ARG_OF_PERICENTER",
        "MEAN_ANOMALY",
        "BSTAR",
        "MEAN_MOTION_DOT",
        "MEAN_MOTION_DDOT",
    ):
        if not np.isfinite(float(fields[key])):
            raise ValueError(f"{key} must be finite")
    if float(fields["MEAN_MOTION"]) <= 0 or not 0 <= float(fields["ECCENTRICITY"]) < 1:
        raise ValueError("Expected positive mean motion and eccentricity in [0, 1)")
    if not 0 <= float(fields["INCLINATION"]) <= 180:
        raise ValueError("Inclination must be in [0, 180]")
    fields["EPOCH"] = epoch.replace(tzinfo=None).isoformat(timespec="microseconds")
    satellite = Satrec()
    omm.initialize(satellite, fields)
    record = OrbitalRecord(int(fields["NORAD_CAT_ID"]), epoch, available, satellite)
    state(record, epoch)
    return record


def load_history(path: Path) -> tuple[list[OrbitalRecord], dict]:
    """Read strict flat GP JSON/CSV; reject ambiguous duplicate object epochs."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = (
            json.load(stream)
            if path.suffix.lower() == ".json"
            else list(csv.DictReader(stream))
        )
    if not isinstance(rows, list) or not rows:
        raise ValueError("Expected a nonempty list of historical GP records")
    records, seen = [], set()
    for index, fields in enumerate(rows, 1):
        try:
            record = parse_record(fields)
            key = (record.object_id, record.epoch)
            if key in seen:
                raise ValueError(
                    "Duplicate object and epoch; resolve revisions before training"
                )
            seen.add(key)
            records.append(record)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid historical record {index}: {exc}") from exc
    records.sort(key=lambda record: (record.object_id, record.epoch))
    return records, {
        "records": len(records),
        "objects": len({r.object_id for r in records}),
        "epoch_used_as_availability": sum(not row.get("CREATION_DATE") for row in rows),
    }


def state(record: OrbitalRecord, when: datetime) -> np.ndarray:
    jd, fraction = jday(
        when.year,
        when.month,
        when.day,
        when.hour,
        when.minute,
        when.second + when.microsecond / 1e6,
    )
    error, position, velocity = record.satellite.sgp4(jd, fraction)
    result = np.array([*position, *velocity], dtype=np.float64)
    if error or not np.isfinite(result).all():
        raise ValueError(
            f"SGP4 propagation failed for {record.object_id}: code {error}"
        )
    return result


def features(
    record: OrbitalRecord, target: datetime, max_lead_hours: float
) -> tuple[np.ndarray, np.ndarray]:
    lead = (target - record.available).total_seconds() / 3600
    age = (target - record.epoch).total_seconds() / 3600
    if not 0 < lead <= max_lead_hours or age > max_lead_hours:
        raise ValueError(
            "Target must follow availability and stay within the element-age limit"
        )
    origin = state(record, record.available)
    baseline = state(record, target)
    return (
        np.array([*origin, *baseline, lead, record.satellite.bstar], dtype=np.float32),
        baseline[:3],
    )


def build_splits(
    records: list[OrbitalRecord],
    train_before: datetime,
    validation_before: datetime,
    max_lead_hours: float = 72,
) -> tuple[dict, dict]:
    """Pair adjacent epochs per object; purge pairs that cross date boundaries."""
    if (
        train_before >= validation_before
        or not np.isfinite(max_lead_hours)
        or max_lead_hours <= 0
    ):
        raise ValueError(
            "Require ordered split dates and a positive finite maximum lead"
        )
    splits = {name: [] for name in ("train", "validation", "test")}
    skipped = {"boundary": 0, "lead_or_propagation": 0}
    ordered = sorted(records, key=lambda record: (record.object_id, record.epoch))
    for earlier, later in zip(ordered, ordered[1:]):
        if earlier.object_id != later.object_id:
            continue
        if earlier.available < train_before and later.available < train_before:
            split = "train"
        elif (
            train_before <= earlier.available < validation_before
            and later.available < validation_before
        ):
            split = "validation"
        elif earlier.available >= validation_before:
            split = "test"
        else:
            skipped["boundary"] += 1
            continue
        try:
            x, baseline = features(earlier, later.epoch, max_lead_hours)
            reference = state(later, later.epoch)[:3]
        except ValueError:
            skipped["lead_or_propagation"] += 1
            continue
        splits[split].append((x, reference - baseline))
    arrays = {}
    for name, pairs in splits.items():
        if not pairs:
            raise ValueError(
                f"No usable {name} pairs; supply more history or revise split dates"
            )
        arrays[name] = (
            np.stack([p[0] for p in pairs]),
            np.stack([p[1] for p in pairs]).astype(np.float32),
        )
    return arrays, skipped


def create_residual_model(training_features: np.ndarray):
    # Keep data preparation usable without importing TensorFlow.
    import setuptools  # noqa: F401
    import tensorflow as tf

    inputs = tf.keras.Input(shape=(len(FEATURE_NAMES),), name="orbital_features")
    normalization = tf.keras.layers.Normalization()
    normalization.adapt(training_features)
    hidden = tf.keras.layers.Dense(64, activation="relu")(normalization(inputs))
    hidden = tf.keras.layers.Dense(32, activation="relu")(hidden)
    # Start at the SGP4 baseline; learn a TEME position correction in km.
    residual = tf.keras.layers.Dense(3, kernel_initializer="zeros", name="residual_km")(
        hidden
    )
    model = tf.keras.Model(inputs, residual, name="historical_sgp4_residual")
    model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="mse")
    return model


def error_metrics(reference_residual: np.ndarray, correction: np.ndarray) -> dict:
    errors = np.linalg.norm(reference_residual - correction, axis=1)
    return {
        "rmse_km": float(np.sqrt(np.mean(errors**2))),
        "median_km": float(np.median(errors)),
        "p95_km": float(np.percentile(errors, 95)),
    }


def predict_position(
    model, record: OrbitalRecord, target: datetime, max_lead_hours: float
) -> np.ndarray:
    """Return experimental TEME xyz km using the saved model's feature transform."""
    x, baseline = features(record, target, max_lead_hours)
    correction = np.asarray(model.predict(x[None, :], verbose=0))[0]
    if correction.shape != (3,) or not np.isfinite(correction).all():
        raise ValueError("Invalid model correction")
    return baseline + correction
