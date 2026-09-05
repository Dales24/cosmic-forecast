#!/usr/bin/env python3
"""Run the cosmic forecast pipeline on synthetic frame data."""

import json
import argparse
import sys
from pathlib import Path

import numpy as np

# TensorFlow reaches for the stdlib `distutils`, which Python 3.12 removed;
# importing setuptools first restores the shim. Must precede any tensorflow
# import (app.object_classifier pulls it in). Same reason as app/api.py.
import setuptools  # noqa: F401

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.object_classifier import generate_synthetic_dataset  # noqa: E402
from app.pipeline import FrameInput, create_default_pipeline  # noqa: E402


def build_linear_motion_frames(
    steps: int = 10,
    velocity: tuple[float, float] = (3.0, 2.0),
) -> list[FrameInput]:
    images, _ = generate_synthetic_dataset(samples_per_class=1, seed=7)
    patch = images[0]
    frames = []
    x, y = 100.0, 100.0

    for frame_id in range(steps):
        frames.append(
            FrameInput(
                frame_id=frame_id,
                timestamp=float(frame_id),
                detections=[(patch, x, y)],
            )
        )
        x += velocity[0]
        y += velocity[1]

    return frames


def main() -> None:
    pipeline = create_default_pipeline(train_trajectory=True, trajectory_epochs=3)
    result = pipeline.run(build_linear_motion_frames())

    print(json.dumps(result.as_dict(), indent=2))


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    main()
