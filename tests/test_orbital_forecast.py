"""Synthetic GP fixtures test plumbing only, not scientific accuracy."""

import json
from datetime import timedelta

import numpy as np
import pytest

from app.orbital_forecast import (
    build_splits,
    create_residual_model,
    error_metrics,
    features,
    load_history,
    parse_record,
    predict_position,
    utc,
)
from scripts.train_orbital_forecast import main


def gp(day=1):
    return {
        "OBJECT_ID": "1998-067A",
        "NORAD_CAT_ID": 25544,
        "EPOCH": f"2024-01-{day:02d}T00:00:00.000000",
        "CLASSIFICATION_TYPE": "U",
        "EPHEMERIS_TYPE": 0,
        "ELEMENT_SET_NO": 999,
        "REV_AT_EPOCH": 100,
        "MEAN_MOTION": 15.5,
        "ECCENTRICITY": 0.0005,
        "INCLINATION": 51.6,
        "RA_OF_ASC_NODE": 100,
        "ARG_OF_PERICENTER": 30,
        "MEAN_ANOMALY": 40,
        "BSTAR": 0.0001,
        "MEAN_MOTION_DOT": 0.00001,
        "MEAN_MOTION_DDOT": 0,
    }


def dataset(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(json.dumps([gp(day) for day in range(1, 10)]))
    return path


def test_chronological_splits_purge_crossing_pairs(tmp_path):
    records, metadata = load_history(dataset(tmp_path))
    splits, skipped = build_splits(records, utc("2024-01-04"), utc("2024-01-07"))
    assert {name: len(x) for name, (x, y) in splits.items()} == {
        "train": 2,
        "validation": 2,
        "test": 2,
    }
    assert skipped["boundary"] == 2
    assert metadata["epoch_used_as_availability"] == 9
    assert splits["train"][0].shape == (2, 14)


def test_availability_cannot_leak_future_elements():
    record = parse_record({**gp(), "CREATION_DATE": "2024-01-03T12:00:00Z"})
    with pytest.raises(ValueError, match="availability"):
        features(record, utc("2024-01-02"), 72)
    with pytest.raises(ValueError, match="element-age"):
        features(record, utc("2024-01-05"), 72)


@pytest.mark.parametrize(
    "change",
    [
        {"REF_FRAME": "GCRF"},
        {"BSTAR": "nan"},
        {"ECCENTRICITY": 1.2},
        {"MEAN_MOTION": 0},
        {"INCLINATION": 181},
    ],
)
def test_reject_bad_records(change):
    with pytest.raises(ValueError):
        parse_record({**gp(), **change})


def test_duplicate_epochs_rejected(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(json.dumps([gp(), gp()]))
    with pytest.raises(ValueError, match="Duplicate"):
        load_history(path)


def test_csv_and_timezone(tmp_path):
    import csv

    path = tmp_path / "history.csv"
    row = gp()
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=row)
        writer.writeheader()
        writer.writerow(row)
    records, _ = load_history(path)
    assert len(records) == 1
    assert utc("2024-01-01T01:00:00+01:00") == records[0].epoch


def test_empty_partition_rejected():
    with pytest.raises(ValueError, match="No usable"):
        build_splits([parse_record(gp())], utc("2024-01-04"), utc("2024-01-07"))


def test_metrics_use_vector_distance():
    assert error_metrics(np.array([[3, 4, 0]]), 0)["rmse_km"] == 5


def test_model_roundtrip_and_zero_baseline(tmp_path):
    import tensorflow as tf

    record = parse_record(gp())
    target = record.epoch + timedelta(hours=12)
    x, baseline = features(record, target, 72)
    model = create_residual_model(np.stack([x, x + 1]))
    np.testing.assert_allclose(predict_position(model, record, target, 72), baseline)
    model.train_on_batch(np.stack([x, x + 1]), np.ones((2, 3)))
    expected = predict_position(model, record, target, 72)
    path = tmp_path / "model.keras"
    model.save(path)
    restored = tf.keras.models.load_model(path)
    np.testing.assert_allclose(predict_position(restored, record, target, 72), expected)


def test_cli_prepare_and_training(tmp_path):
    path = dataset(tmp_path)
    output = tmp_path / "run"
    args = [
        "--data",
        str(path),
        "--source",
        "synthetic test fixture",
        "--train-before",
        "2024-01-04",
        "--validation-before",
        "2024-01-07",
        "--output",
        str(output),
        "--epochs",
        "1",
    ]
    prepared = main([*args, "--prepare-only"])
    assert not output.exists()
    assert prepared["split_counts"]["test"] == 2
    report = main(args)
    assert (output / "model.keras").exists()
    assert (
        json.loads((output / "report.json").read_text())["sha256"] == prepared["sha256"]
    )
    assert "sgp4" in report["metrics"]["test"]
    with pytest.raises(ValueError, match="already exists"):
        main(args)
