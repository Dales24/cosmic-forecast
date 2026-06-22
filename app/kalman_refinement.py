"""Kalman filter refinement for predicted object positions."""

from __future__ import annotations

import numpy as np

from app.detections import PredictedPosition, Track


class KalmanRefiner:
    """Constant-velocity Kalman filter in 2D."""

    def __init__(
        self,
        process_noise: float = 0.5,
        measurement_noise: float = 2.0,
    ):
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self._filters: dict[int, _KalmanState] = {}

    def refine(
        self,
        track: Track,
        predicted_xy: np.ndarray,
        target_timestamp: float,
    ) -> PredictedPosition:
        """Fuse transformer prediction with track history."""
        state = self._filters.get(track.track_id)
        if state is None:
            state = _KalmanState.from_track(track, self.process_noise, self.measurement_noise)
            for detection in track.detections:
                dt = max(detection.timestamp - state.timestamp, 1e-6)
                state.predict(dt)
                state.update(np.array([detection.x, detection.y], dtype=np.float64))
                state.timestamp = detection.timestamp
            self._filters[track.track_id] = state

        dt = max(target_timestamp - state.timestamp, 1e-6)
        state.predict(dt)
        state.update(predicted_xy.astype(np.float64))
        state.timestamp = target_timestamp

        return PredictedPosition(
            x=float(state.position[0]),
            y=float(state.position[1]),
            timestamp=target_timestamp,
            uncertainty_x=float(np.sqrt(state.covariance[0, 0])),
            uncertainty_y=float(np.sqrt(state.covariance[1, 1])),
            track_id=track.track_id,
            object_class=track.object_class,
        )


class _KalmanState:
    """State vector: [x, y, vx, vy]."""

    def __init__(
        self,
        state: np.ndarray,
        covariance: np.ndarray,
        process_noise: float,
        measurement_noise: float,
        timestamp: float,
        updated_count: int = 0,
    ):
        self.state = state
        self.covariance = covariance
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.timestamp = timestamp
        self.updated_count = updated_count

    @property
    def position(self) -> np.ndarray:
        return self.state[:2]

    @classmethod
    def from_track(
        cls,
        track: Track,
        process_noise: float,
        measurement_noise: float,
    ) -> _KalmanState:
        latest = track.latest
        previous = track.detections[-2] if len(track.detections) > 1 else latest
        dt = max(latest.timestamp - previous.timestamp, 1e-6)
        velocity = np.array(
            [
                (latest.x - previous.x) / dt,
                (latest.y - previous.y) / dt,
            ],
            dtype=np.float64,
        )
        state = np.array([latest.x, latest.y, velocity[0], velocity[1]], dtype=np.float64)
        covariance = np.eye(4, dtype=np.float64) * 10.0
        return cls(
            state=state,
            covariance=covariance,
            process_noise=process_noise,
            measurement_noise=measurement_noise,
            timestamp=latest.timestamp,
            updated_count=0,
        )

    def predict(self, dt: float) -> None:
        transition = np.array(
            [
                [1, 0, dt, 0],
                [0, 1, 0, dt],
                [0, 0, 1, 0],
                [0, 0, 0, 1],
            ],
            dtype=np.float64,
        )
        process = np.eye(4, dtype=np.float64) * self.process_noise
        process[0, 0] = process[1, 1] = self.process_noise * dt**2
        process[2, 2] = process[3, 3] = self.process_noise

        self.state = transition @ self.state
        self.covariance = transition @ self.covariance @ transition.T + process

    def update(self, measurement: np.ndarray) -> None:
        observation = np.array(
            [[1, 0, 0, 0], [0, 1, 0, 0]],
            dtype=np.float64,
        )
        measurement_noise = np.eye(2, dtype=np.float64) * self.measurement_noise
        innovation = measurement - observation @ self.state
        innovation_cov = observation @ self.covariance @ observation.T + measurement_noise
        kalman_gain = self.covariance @ observation.T @ np.linalg.inv(innovation_cov)

        self.state = self.state + kalman_gain @ innovation
        self.covariance = (
            np.eye(4, dtype=np.float64) - kalman_gain @ observation
        ) @ self.covariance
        self.updated_count += 1
