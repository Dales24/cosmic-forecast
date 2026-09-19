"""Train an experimental SGP4 residual model on local historical GP JSON/CSV."""

import argparse
import hashlib
import json
from pathlib import Path

from app.orbital_forecast import (
    FEATURE_NAMES,
    build_splits,
    create_residual_model,
    error_metrics,
    load_history,
    utc,
)
from app.paths import MODEL_ROOT, PROJECT_ROOT


def repo_path(value):
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", required=True, type=repo_path, help="Historical GP JSON array or CSV"
    )
    parser.add_argument(
        "--source", required=True, help="Dataset provenance label (no credentials)"
    )
    parser.add_argument(
        "--train-before", required=True, type=utc, help="Exclusive UTC training cutoff"
    )
    parser.add_argument(
        "--validation-before",
        required=True,
        type=utc,
        help="Exclusive UTC validation cutoff",
    )
    parser.add_argument(
        "--max-lead-hours",
        type=float,
        default=72,
        help="Maximum forecast lead AND element age; experimental, not an accuracy bound",
    )
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--output", type=repo_path, default=MODEL_ROOT / "orbital_residual"
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Validate data and report split counts without training or writing artifacts",
    )
    args = parser.parse_args(argv)
    if args.epochs < 1 or args.batch_size < 1:
        parser.error("epochs and batch size must be positive")
    records, dataset = load_history(args.data)
    splits, skipped = build_splits(
        records, args.train_before, args.validation_before, args.max_lead_hours
    )
    report = {
        "schema_version": 1,
        "status": "experimental",
        "reference": "Later GP estimates propagated at their own epochs; not measured ground truth",
        "source": args.source,
        "sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
        "dataset": dataset,
        "split_counts": {k: len(v[0]) for k, v in splits.items()},
        "skipped_pairs": skipped,
        "train_before": args.train_before.isoformat(),
        "validation_before": args.validation_before.isoformat(),
        "max_lead_hours": args.max_lead_hours,
        "seed": args.seed,
        "features": FEATURE_NAMES,
        "frame": "TEME",
        "output_units": "km",
        "evaluation_scope": "Future dates for this object population; not unseen-object generalization",
    }
    if args.prepare_only:
        print(json.dumps(report, indent=2))
        return report
    if args.output.exists():
        raise ValueError("Output already exists; choose a new run directory")
    import setuptools  # noqa: F401
    import tensorflow as tf

    tf.keras.utils.set_random_seed(args.seed)
    tf.config.experimental.enable_op_determinism()
    model = create_residual_model(splits["train"][0])
    # Preserve the untrained zero correction if training cannot beat SGP4 on validation.
    initial_weights = model.get_weights()
    history = model.fit(
        *splits["train"],
        validation_data=splits["validation"],
        epochs=args.epochs,
        batch_size=args.batch_size,
        verbose=2,
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=5, restore_best_weights=True
            )
        ],
    )
    val_x, val_y = splits["validation"]
    val_prediction = model.predict(val_x, verbose=0)
    improved = (
        error_metrics(val_y, val_prediction)["rmse_km"]
        < error_metrics(val_y, 0)["rmse_km"]
    )
    if not improved:
        model.set_weights(initial_weights)
    report["selection"] = "learned_correction" if improved else "sgp4_zero_correction"
    report["epochs_completed"] = len(history.history["loss"])
    report["batch_size"] = args.batch_size
    report["tensorflow_version"] = tf.__version__
    report["metrics"] = {}
    for name in ("validation", "test"):
        x, y = splits[name]
        report["metrics"][name] = {
            "sgp4": error_metrics(y, 0),
            "selected_model": error_metrics(y, model.predict(x, verbose=0)),
        }
    args.output.mkdir(parents=True, exist_ok=False)
    model.save(args.output / "model.keras")
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    main()
