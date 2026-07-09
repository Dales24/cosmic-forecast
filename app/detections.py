"""Shared data structures for the prediction pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Detection:
    frame_id: int
    timestamp: float
    x: float
    y: float
    patch: np.ndarray | None = None
    classification: dict | None = None


@dataclass
class Track:
    track_id: int
    detections: list[Detection] = field(default_factory=list)

    @property
    def latest(self) -> Detection:
        return self.detections[-1]

    @property
    def object_class(self) -> str | None:
        for detection in reversed(self.detections):
            if detection.classification:
                return detection.classification["class"]
        return None

    def positions(self) -> np.ndarray:
        """Return shape (N, 3) array of [x, y, timestamp]."""
        return np.array(
            [[d.x, d.y, d.timestamp] for d in self.detections],
            dtype=np.float32,
        )


@dataclass
class PredictedPosition:
    x: float
    y: float
    timestamp: float
    uncertainty_x: float
    uncertainty_y: float
    track_id: int
    object_class: str | None = None

    def as_dict(self) -> dict:
        return {
            "x": self.x,
            "y": self.y,
            "timestamp": self.timestamp,
            "uncertainty_x": self.uncertainty_x,
            "uncertainty_y": self.uncertainty_y,
            "track_id": self.track_id,
            "object_class": self.object_class,
        }
