"""Tests for app/trajectory_transformer.py — utilities, model, save/load."""

from pathlib import Path

import numpy as np
import pytest

from app.trajectory_transformer import (
    _denormalize_prediction,
    _normalize_sequence,
    _pad_sequence,
    create_trajectory_transformer,
    generate_synthetic_trajectories,
    linear_extrapolation,
    load_trajectory_model,
    predict_trajectory,
    save_trajectory_model,
    train_trajectory_model,
)


# ── _pad_sequence ─────────────────────────────────────────────────────────────

def test_pad_short_sequence():
    pts = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 1.0]])
    padded = _pad_sequence(pts, seq_len=5)
    assert padded.shape == (5, 3)


def test_pad_exact_length():
    pts = np.arange(15, dtype=float).reshape(5, 3)
    padded = _pad_sequence(pts, seq_len=5)
    assert padded.shape == (5, 3)
    np.testing.assert_array_equal(padded, pts)


def test_truncate_long_sequence():
    pts = np.arange(30, dtype=float).reshape(10, 3)
    padded = _pad_sequence(pts, seq_len=5)
    assert padded.shape == (5, 3)
    # Should keep the LAST seq_len points
    np.testing.assert_array_equal(padded, pts[-5:])


def test_pad_preserves_last_point():
    pts = np.array([[1.0, 2.0, 100.0], [3.0, 4.0, 101.0]])
    padded = _pad_sequence(pts, seq_len=5)
    np.testing.assert_array_equal(padded[-1], pts[-1])
    np.testing.assert_array_equal(padded[-2], pts[-2])


# ── _normalize_sequence ───────────────────────────────────────────────────────

def test_normalize_last_xy_becomes_zero():
    pts = np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 1.0], [3.0, 5.0, 2.0]])
    normed, origin = _normalize_sequence(pts)
    assert normed[-1, 0] == pytest.approx(0.0)
    assert normed[-1, 1] == pytest.approx(0.0)


def test_normalize_returns_origin():
    pts = np.array([[0.0, 0.0, 0.0], [3.0, 5.0, 1.0]])
    _, origin = _normalize_sequence(pts)
    assert origin[0] == pytest.approx(3.0)
    assert origin[1] == pytest.approx(5.0)


def test_normalize_time_scaled():
    pts = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, 2.0]])
    normed, _ = _normalize_sequence(pts)
    # Time differences should be uniform unit steps
    diffs = np.diff(normed[:, 2])
    assert np.allclose(diffs, diffs[0])


def test_normalize_single_point():
    pts = np.array([[5.0, 7.0, 100.0]])
    normed, origin = _normalize_sequence(pts)
    assert normed[0, 0] == pytest.approx(0.0)
    assert normed[0, 1] == pytest.approx(0.0)
    assert origin[0] == pytest.approx(5.0)


# ── _denormalize_prediction ───────────────────────────────────────────────────

def test_denormalize_adds_origin():
    prediction = np.array([[0.1, 0.2], [0.3, 0.4]])
    origin = np.array([10.0, 20.0])
    result = _denormalize_prediction(prediction, origin)
    np.testing.assert_allclose(result[:, 0], [10.1, 10.3])
    np.testing.assert_allclose(result[:, 1], [20.2, 20.4])


def test_denormalize_zero_prediction_returns_origin():
    prediction = np.zeros((5, 2))
    origin = np.array([3.0, 7.0])
    result = _denormalize_prediction(prediction, origin)
    assert np.all(result[:, 0] == pytest.approx(3.0))
    assert np.all(result[:, 1] == pytest.approx(7.0))


# ── linear_extrapolation ──────────────────────────────────────────────────────

def test_linear_extrapolation_shape():
    pts = np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 1.0], [2.0, 4.0, 2.0]])
    result = linear_extrapolation(pts, horizon=10)
    assert result.shape == (10, 3)


def test_linear_extrapolation_constant_velocity():
    pts = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 1.0], [2.0, 0.0, 2.0]])
    result = linear_extrapolation(pts, horizon=5)
    # x should increase by ~1 per step, y stays ~0
    for i, row in enumerate(result):
        expected_x = 3.0 + i  # continues from x=2 at t=2
        assert abs(row[0] - expected_x) < 0.5


def test_linear_extrapolation_with_two_points():
    pts = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])
    result = linear_extrapolation(pts, horizon=3)
    assert result.shape == (3, 3)


def test_linear_extrapolation_timestamps_increase():
    pts = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 1.0]])
    result = linear_extrapolation(pts, horizon=5)
    assert np.all(np.diff(result[:, 2]) > 0)


# ── create_trajectory_transformer ────────────────────────────────────────────

def test_create_transformer_returns_model():
    model = create_trajectory_transformer(seq_len=8, horizon=4, d_model=16)
    assert model is not None


def test_transformer_input_shape():
    model = create_trajectory_transformer(seq_len=8, horizon=4, d_model=16)
    assert model.input_shape == (None, 8, 3)


def test_transformer_output_shape():
    model = create_trajectory_transformer(seq_len=8, horizon=4, d_model=16)
    assert model.output_shape == (None, 4, 2)


# ── generate_synthetic_trajectories ──────────────────────────────────────────

def test_synthetic_trajectories_count():
    seqs, targets = generate_synthetic_trajectories(count=20, seq_len=8, horizon=4, seed=0)
    assert seqs.shape[0] == 20
    assert targets.shape[0] == 20


def test_synthetic_trajectories_shape():
    seqs, targets = generate_synthetic_trajectories(count=10, seq_len=8, horizon=4, seed=0)
    assert seqs.shape[1:] == (8, 3)
    assert targets.shape[1:] == (4, 2)


def test_synthetic_trajectories_reproducible():
    s1, t1 = generate_synthetic_trajectories(count=5, seq_len=4, horizon=2, seed=42)
    s2, t2 = generate_synthetic_trajectories(count=5, seq_len=4, horizon=2, seed=42)
    np.testing.assert_array_equal(s1, s2)
    np.testing.assert_array_equal(t1, t2)


# ── predict_trajectory ────────────────────────────────────────────────────────

def test_predict_trajectory_output_shape():
    model = create_trajectory_transformer(seq_len=8, horizon=4, d_model=16)
    pts = np.column_stack([np.arange(8), np.zeros(8), np.arange(8, dtype=float)])
    result = predict_trajectory(model, pts, seq_len=8)
    assert result.shape == (4, 2)


# ── save and load model ───────────────────────────────────────────────────────

def test_save_and_load_trajectory_model(tmp_path):
    model = create_trajectory_transformer(seq_len=8, horizon=4, d_model=16)
    save_trajectory_model(model, str(tmp_path))

    loaded = load_trajectory_model(str(tmp_path))
    assert loaded is not None
    assert loaded.input_shape == model.input_shape
    assert loaded.output_shape == model.output_shape


def test_loaded_model_produces_same_output(tmp_path):
    model = create_trajectory_transformer(seq_len=8, horizon=4, d_model=16)
    save_trajectory_model(model, str(tmp_path))
    loaded = load_trajectory_model(str(tmp_path))

    pts = np.random.default_rng(0).random((8, 3)).astype(np.float32)
    out1 = predict_trajectory(model, pts, seq_len=8)
    out2 = predict_trajectory(loaded, pts, seq_len=8)
    np.testing.assert_allclose(out1, out2, atol=1e-5)
