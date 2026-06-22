"""End-to-end pipeline: Patch CNN → Track Builder → Trajectory Transformer → Kalman → Position."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import tensorflow as tf

from app.detections import Detection, PredictedPosition, Track
from app.kalman_refinement import KalmanRefiner
from app.object_classifier import create_cnn_model, predict_patch
from app.track_builder import TrackBuilder
from app.trajectory_transformer import (
    DEFAULT_HORIZON,
    create_trajectory_transformer,
    linear_extrapolation,
    predict_trajectory,
)


@dataclass
class FrameInput:
    frame_id: int
    timestamp: float
    detections: list[tuple[np.ndarray, float, float]]


@dataclass
class PipelineResult:
    tracks: list[Track]
    predictions: list[PredictedPosition]

    def as_dict(self) -> dict:
        return {
            "tracks": [
                {
                    "track_id": track.track_id,
                    "object_class": track.object_class,
                    "detection_count": len(track.detections),
                    "latest": {
                        "x": track.latest.x,
                        "y": track.latest.y,
                        "timestamp": track.latest.timestamp,
                    },
                }
                for track in self.tracks
            ],
            "predictions": [prediction.as_dict() for prediction in self.predictions],
        }


class ForecastPipeline:
    """
    Patch CNN
        ↓
    Track Builder
        ↓
    Trajectory Transformer
        ↓
    Kalman Filter Refinement
        ↓
    Predicted Position
    """

    def __init__(
        self,
        cnn_model: tf.keras.Model | None = None,
        trajectory_model: tf.keras.Model | None = None,
        track_builder: TrackBuilder | None = None,
        kalman_refiner: KalmanRefiner | None = None,
        forecast_horizon: int = DEFAULT_HORIZON,
    ):
        self.cnn_model = cnn_model or create_cnn_model()
        self.trajectory_model = trajectory_model
        self.track_builder = track_builder or TrackBuilder()
        self.kalman_refiner = kalman_refiner or KalmanRefiner()
        self.forecast_horizon = forecast_horizon

    def classify_patch(self, patch: np.ndarray) -> dict:
        return predict_patch(self.cnn_model, patch)

    def process_frame(self, frame: FrameInput) -> list[Track]:
        detections = []
        for patch, x, y in frame.detections:
            detections.append(
                Detection(
                    frame_id=frame.frame_id,
                    timestamp=frame.timestamp,
                    x=x,
                    y=y,
                    patch=patch,
                    classification=self.classify_patch(patch),
                )
            )
        return self.track_builder.update(detections)

    def predict_positions(
        self,
        tracks: list[Track] | None = None,
        target_timestamp: float | None = None,
    ) -> list[PredictedPosition]:
        tracks = tracks if tracks is not None else self.track_builder.tracks
        predictions: list[PredictedPosition] = []

        if target_timestamp is None and tracks:
            sample = max(tracks, key=lambda track: len(track.detections))
            if len(sample.detections) >= 2:
                positions = sample.positions()
                dt = np.diff(positions[:, 2]).mean()
                target_timestamp = float(positions[-1, 2] + dt * self.forecast_horizon)

        for track in tracks:
            if len(track.detections) < 2:
                continue

            positions = track.positions()
            track_target = target_timestamp
            if track_target is None:
                dt = np.diff(positions[:, 2]).mean()
                track_target = float(positions[-1, 2] + dt * self.forecast_horizon)

            if self.trajectory_model is not None:
                forecast = predict_trajectory(self.trajectory_model, positions)
                predicted_xy = forecast[-1]
            else:
                extrapolated = linear_extrapolation(positions, horizon=self.forecast_horizon)
                predicted_xy = extrapolated[-1, :2]

            predictions.append(
                self.kalman_refiner.refine(
                    track=track,
                    predicted_xy=predicted_xy,
                    target_timestamp=track_target,
                )
            )

        return predictions

    def run(self, frames: list[FrameInput]) -> PipelineResult:
        for frame in frames:
            self.process_frame(frame)

        last_timestamp = frames[-1].timestamp if frames else 0.0
        dt = 1.0
        if len(frames) > 1:
            dt = max(frames[-1].timestamp - frames[-2].timestamp, 1e-6)
        target_timestamp = last_timestamp + dt * self.forecast_horizon

        predictions = self.predict_positions(target_timestamp=target_timestamp)
        return PipelineResult(tracks=self.track_builder.tracks, predictions=predictions)


def create_default_pipeline(
    train_trajectory: bool = False,
    trajectory_epochs: int = 3,
) -> ForecastPipeline:
    """Build a pipeline with optional synthetic trajectory training."""
    trajectory_model = create_trajectory_transformer()
    if train_trajectory:
        from app.trajectory_transformer import (
            generate_synthetic_trajectories,
            train_trajectory_model,
        )

        sequences, targets = generate_synthetic_trajectories(count=128)
        train_trajectory_model(
            trajectory_model,
            sequences,
            targets,
            epochs=trajectory_epochs,
        )

    return ForecastPipeline(
        cnn_model=create_cnn_model(),
        trajectory_model=trajectory_model,
    )
