"""Tests for app/kalman_refinement.py — KalmanRefiner and _KalmanState."""

import numpy as np
import pytest

from app.detections import Detection, Track
from app.kalman_refinement import KalmanRefiner, _KalmanState


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_track(positions, t_start=0.0, dt=1.0, cls="satellite"):
    """Build a Track from a list of (x, y) positions."""
    track = Track(track_id=0, object_class=cls)
    for i, (x, y) in enumerate(positions):
        d = Detection(
            frame_id=i,
            timestamp=t_start + i * dt,
            x=x,
            y=y,
            patch=np.zeros((64, 64, 3), dtype=np.uint8),
            classification=cls,
        )
        track.detections.append(d)
    return track


# ── _KalmanState ──────────────────────────────────────────────────────────────


def test_kalman_state_from_single_detection():
    track = _make_track([(1.0, 2.0)])
    state = _KalmanState.from_track(track, process_noise=0.01, measurement_noise=0.1)
    assert state.x[0] == pytest.approx(1.0)
    assert state.x[1] == pytest.approx(2.0)


def test_kalman_state_velocity_from_two_detections():
    track = _make_track([(0.0, 0.0), (1.0, 2.0)], dt=1.0)
    state = _KalmanState.from_track(track, process_noise=0.01, measurement_noise=0.1)
    # velocity estimate should be ~(1, 2) from constant-velocity model
    assert state.x[2] == pytest.approx(1.0, abs=0.5)
    assert state.x[3] == pytest.approx(2.0, abs=0.5)


def test_kalman_state_covariance_is_positive_definite():
    track = _make_track([(0.0, 0.0), (1.0, 0.0)])
    state = _KalmanState.from_track(track, process_noise=0.01, measurement_noise=0.1)
    eigvals = np.linalg.eigvals(state.P)
    assert np.all(eigvals > 0)


def test_kalman_state_predict_advances_position():
    track = _make_track([(0.0, 0.0), (1.0, 0.0)])
    state = _KalmanState.from_track(track, process_noise=0.01, measurement_noise=0.1)
    x0 = state.x.copy()
    state.predict(dt=1.0)
    # Position should have changed
    assert state.x[0] != x0[0] or state.x[1] != x0[1]


def test_kalman_state_predict_increases_covariance():
    track = _make_track([(0.0, 0.0), (1.0, 0.0)])
    state = _KalmanState.from_track(track, process_noise=0.01, measurement_noise=0.1)
    trace_before = np.trace(state.P)
    state.predict(dt=1.0)
    assert np.trace(state.P) >= trace_before


def test_kalman_state_update_moves_toward_measurement():
    track = _make_track([(0.0, 0.0), (1.0, 0.0)])
    state = _KalmanState.from_track(track, process_noise=0.01, measurement_noise=0.1)
    state.predict(dt=1.0)
    predicted_x = state.x[0]
    measurement = np.array([predicted_x + 5.0, 0.0])
    state.update(measurement)
    # State should have shifted toward the measurement
    assert state.x[0] > predicted_x


def test_kalman_state_update_reduces_covariance():
    track = _make_track([(0.0, 0.0), (1.0, 0.0)])
    state = _KalmanState.from_track(track, process_noise=0.01, measurement_noise=0.1)
    state.predict(dt=1.0)
    trace_before = np.trace(state.P)
    state.update(np.array([2.0, 0.0]))
    assert np.trace(state.P) < trace_before


# ── KalmanRefiner ─────────────────────────────────────────────────────────────


def test_refiner_returns_predicted_position_struct():
    track = _make_track([(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)])
    refiner = KalmanRefiner()
    result = refiner.refine(
        track, predicted_xy=np.array([3.0, 0.0]), target_timestamp=3.0
    )
    assert hasattr(result, "x")
    assert hasattr(result, "y")
    assert hasattr(result, "uncertainty_x")
    assert hasattr(result, "uncertainty_y")


def test_refiner_uncertainty_is_positive():
    track = _make_track([(0.0, 0.0), (1.0, 0.0)])
    refiner = KalmanRefiner()
    result = refiner.refine(track, np.array([2.0, 0.0]), target_timestamp=2.0)
    assert result.uncertainty_x > 0
    assert result.uncertainty_y > 0


def test_refiner_position_close_to_prediction_with_low_noise():
    track = _make_track([(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)])
    refiner = KalmanRefiner(process_noise=1e-6, measurement_noise=1e-6)
    predicted = np.array([3.0, 0.0])
    result = refiner.refine(track, predicted, target_timestamp=3.0)
    assert abs(result.x - 3.0) < 0.5
    assert abs(result.y - 0.0) < 0.5


def test_refiner_track_id_preserved():
    track = _make_track([(0.0, 0.0), (1.0, 0.0)])
    track.track_id = 42
    refiner = KalmanRefiner()
    result = refiner.refine(track, np.array([2.0, 0.0]), target_timestamp=2.0)
    assert result.track_id == 42


def test_refiner_object_class_preserved():
    track = _make_track([(0.0, 0.0), (1.0, 0.0)], cls="asteroid")
    refiner = KalmanRefiner()
    result = refiner.refine(track, np.array([2.0, 0.0]), target_timestamp=2.0)
    assert result.object_class == "asteroid"


def test_refiner_as_dict():
    track = _make_track([(0.0, 0.0), (1.0, 0.0)])
    refiner = KalmanRefiner()
    result = refiner.refine(track, np.array([2.0, 0.0]), target_timestamp=2.0)
    d = result.as_dict()
    assert isinstance(d, dict)
    for key in ("x", "y", "uncertainty_x", "uncertainty_y", "track_id", "object_class"):
        assert key in d


def test_refiner_high_noise_produces_larger_uncertainty():
    track = _make_track([(0.0, 0.0), (1.0, 0.0)])
    low = KalmanRefiner(process_noise=1e-6, measurement_noise=1e-6)
    high = KalmanRefiner(process_noise=10.0, measurement_noise=10.0)
    pred = np.array([2.0, 0.0])
    r_low = low.refine(track, pred, 2.0)
    r_high = high.refine(track, pred, 2.0)
    assert r_high.uncertainty_x >= r_low.uncertainty_x
