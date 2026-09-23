#!/usr/bin/env python3
"""Train the patch-based object classifier."""

import argparse
import json
import signal
import sys
from pathlib import Path
from typing import Callable

# TensorFlow reaches for the stdlib `distutils`, which Python 3.12 removed;
# importing setuptools first restores the shim. Must precede any tensorflow
# import (app.object_classifier pulls it in). Same reason as app/api.py.
import setuptools  # noqa: F401

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.object_classifier import (  # noqa: E402
    DEFAULT_MODEL_DIR,
    create_cnn_model,
    generate_synthetic_dataset,
    load_archived_model,
    load_image_dataset,
    save_model,
    train_model,
    stratified_split,
)


def _raise_interrupt(signum, frame):
    """Turn SIGTERM (`kill`) into a KeyboardInterrupt so training stops cleanly."""
    raise KeyboardInterrupt


def train_and_persist(
    model, output: Path, train_fn: Callable[[], None], archive: bool = True
) -> Path:
    """Run `train_fn`, then save `model` to `output`.

    Keras stops `fit()` gracefully when a KeyboardInterrupt arrives between
    batches, so we also route SIGTERM through one — that way an interrupted run
    (Ctrl-C or `kill`) still persists the partially-trained weights. Real errors
    propagate untouched and skip the save, so we never write a broken model.
    When `archive` is set, the save also keeps a timestamped archived copy.
    """
    original = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, _raise_interrupt)
    try:
        train_fn()
    except KeyboardInterrupt:
        print("\nInterrupted — saving partial model...", file=sys.stderr)
    finally:
        signal.signal(signal.SIGTERM, original)
    return save_model(model, output, archive=archive)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        help="CSV with path,label,group,split and explicit train/validation/test holdouts",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Validate --manifest and report counts without training",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Directory with one subfolder per class slug (e.g. data/asteroid/)",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Train on synthetic patches (useful for smoke tests)",
    )
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument(
        "--samples-per-class",
        type=int,
        default=64,
        help="Synthetic examples per class (at least 2 for train/validation splitting)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_MODEL_DIR,
        help="Where to save the trained model",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Skip keeping a timestamped archived copy of the saved model",
    )
    parser.add_argument(
        "--resume-from",
        nargs="?",
        const="",
        default=None,
        metavar="ARCHIVE_NAME",
        help="Continue training from an archived model (newest if no name given)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if (
        sum(bool(value) for value in (args.manifest, args.data_dir, args.synthetic))
        != 1
    ):
        raise SystemExit("Choose exactly one of --manifest, --data-dir or --synthetic")
    if args.prepare_only and not args.manifest:
        raise SystemExit("--prepare-only requires --manifest")
    if args.manifest and args.resume_from is not None:
        raise SystemExit(
            "Manifest runs require a fresh model: prior training provenance is unknown"
        )
    if args.epochs < 1:
        raise SystemExit("--epochs must be positive")
    partitions, report = None, None
    if args.manifest:
        from app.classifier_data import load_manifest
        from app.paths import PROJECT_ROOT

        if not args.manifest.is_absolute():
            args.manifest = PROJECT_ROOT / args.manifest
        partitions, report = load_manifest(args.manifest)
        if args.prepare_only:
            print(json.dumps(report, indent=2))
            return
        if args.output.exists():
            raise SystemExit("Manifest runs require a new output directory")

    if args.resume_from is not None:
        # Empty string means "no name supplied" → load the newest archive.
        model = load_archived_model(args.resume_from or None)
    else:
        model = create_cnn_model()

    completed = False

    def train() -> None:
        nonlocal completed
        if partitions is not None:
            model.fit(
                *partitions["train"],
                validation_data=partitions["validation"],
                epochs=args.epochs,
            )
        elif args.data_dir:
            train_ds, val_ds = load_image_dataset(args.data_dir)
            model.fit(train_ds, validation_data=val_ds, epochs=args.epochs)
        else:
            images, labels = generate_synthetic_dataset(
                samples_per_class=args.samples_per_class
            )
            x_train, y_train, x_val, y_val = stratified_split(images, labels)
            train_model(
                model,
                x_train,
                y_train,
                x_val,
                y_val,
                epochs=args.epochs,
            )
        completed = True

    output = train_and_persist(model, args.output, train, archive=not args.no_archive)
    if report is not None:
        report["status"] = "completed" if completed else "interrupted"
        if completed:
            report["test_metrics"] = model.evaluate(
                *partitions["test"], verbose=0, return_dict=True
            )
        (output / "evaluation.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
    print(f"Saved model to {output}")


if __name__ == "__main__":
    main()
