#!/usr/bin/env python3
"""Train the patch-based object classifier."""

import argparse
from pathlib import Path

from app.object_classifier import (
    DEFAULT_MODEL_DIR,
    create_cnn_model,
    generate_synthetic_dataset,
    load_image_dataset,
    save_model,
    train_model,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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
    parser.add_argument("--samples-per-class", type=int, default=64)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_MODEL_DIR,
        help="Where to save the trained model",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = create_cnn_model()

    if args.data_dir:
        train_ds, val_ds = load_image_dataset(args.data_dir)
        model.fit(train_ds, validation_data=val_ds, epochs=args.epochs)
    elif args.synthetic:
        images, labels = generate_synthetic_dataset(samples_per_class=args.samples_per_class)
        split = int(len(labels) * 0.8)
        train_model(
            model,
            images[:split],
            labels[:split],
            images[split:],
            labels[split:],
            epochs=args.epochs,
        )
    else:
        raise SystemExit("Provide --data-dir with labeled patches or use --synthetic")

    output = save_model(model, args.output)
    print(f"Saved model to {output}")


if __name__ == "__main__":
    main()
